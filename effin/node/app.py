# effin/node/app.py
import asyncio
import os
import time
import json
import uuid
from typing import List, Dict

from prometheus_client import Counter, Histogram, start_http_server

from effin.encoder.model import FraudEncoder
from effin.node.ingest import tx_producer
from effin.node.search import CyborgWrapper
from effin.common.crypto import encrypt_vector_b64, hash_id_hex
from cryptography.fernet import Fernet
import numpy as np


# ------------------------------------------------------------
# ENVIRONMENT CONFIG
# ------------------------------------------------------------
# IMPORTANT: default INDEX_NAME changed to a single shared global index
# so all banks write/read to the same encrypted vector index for cross-bank detection.
INDEX_NAME = os.getenv("INDEX_NAME", "effin_global_fraud_index")
INDEX_KEY = os.getenv("INDEX_KEY", "")
TOP_K = int(os.getenv("TOP_K", "5"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "32"))
TRAIN_AFTER = int(os.getenv("TRAIN_AFTER", "500"))

# Support both a distance threshold (lower-is-better) and a similarity threshold (higher-is-better)
ALERT_DISTANCE_THRESHOLD = float(os.getenv("ALERT_DISTANCE_THRESHOLD", "0.3"))
ALERT_SIMILARITY_THRESHOLD = float(os.getenv("ALERT_SIMILARITY_THRESHOLD", "0.7"))

BANK_ID = os.getenv("BANK_ID", "bank1")
AUDIT_FILE = os.getenv("AUDIT_FILE", f"audit_{BANK_ID}.jsonl")
PROM_PORT = int(os.getenv("PROM_PORT", "8001"))

# Debugging: prints full ANN results when true
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() in ("1", "true", "yes")


# ------------------------------------------------------------
# METRICS
# ------------------------------------------------------------
Q_COUNTER = Counter("effin_queries_total", "Total queries processed", ["worker"])
UPSERT_COUNTER = Counter("effin_upserts_total", "Total upsert operations", ["worker"])
ALERT_COUNTER = Counter("effin_alerts_total", "Total alerts emitted", ["severity"])
LATENCY_HIST = Histogram("effin_query_latency_seconds", "Query latency seconds")

# ------------------------------------------------------------
# MODEL + SEARCH CLIENT
# ------------------------------------------------------------
encoder = FraudEncoder()

cy = CyborgWrapper(
    endpoint=os.getenv("CYBORGDB_ENDPOINT"),
    api_key=os.getenv("CYBORGDB_API_KEY"),
    index_key=INDEX_KEY
)

q = asyncio.Queue(maxsize=5000)
_upsert_count = 0
_upsert_lock = asyncio.Lock()

# ------------------------------------------------------------
# ENCRYPTED AUDIT LOG
# (unchanged — audit remains Fernet-encrypted JSONL)
# ------------------------------------------------------------
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY missing")

fernet = Fernet(FERNET_KEY.encode())


def append_audit(event: dict):
    raw = json.dumps(event).encode()
    token = fernet.encrypt(raw)
    with open(AUDIT_FILE, "ab") as f:
        f.write(token + b"\n")


# ------------------------------------------------------------
# ENSURE INDEX EXISTS (DROP + RECREATE FRESH INDEX)
# ------------------------------------------------------------
async def ensure_index_exists():
    """
    Always delete existing index and recreate it cleanly.
    Useful during development to guarantee a fresh ANN graph.
    """
    try:
        # Try deleting the index first (ignore errors if it doesn't exist)
        await cy.client.post(
            f"{cy.endpoint}/v1/indexes/delete",
            json={"index_name": INDEX_NAME, "index_key": INDEX_KEY},
            headers=cy.headers
        )
        print(f"[INFO] Deleted existing index '{INDEX_NAME}'")
    except Exception as e:
        print(f"[WARN] Could not delete index (may not exist): {e}")

    # Now recreate a fresh index
    try:
        resp = await cy.client.post(
            f"{cy.endpoint}/v1/indexes/create",
            json={
                "index_name": INDEX_NAME,
                "index_key": INDEX_KEY,
                "index_config": {
                    "type": "ivfflat",
                    "dimension": 32
                }
            },
            headers=cy.headers
        )
        print(f"[SUCCESS] Created new index '{INDEX_NAME}'")
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to create index '{INDEX_NAME}': {e}")
        raise


# ------------------------------------------------------------
# WORKER LOGIC
# ------------------------------------------------------------
async def worker_consume(name: str):
    global _upsert_count
    batch: List[Dict] = []

    while True:
        tx = await q.get()
        start = time.time()

        try:
            vec = encoder.embed_transaction(tx)

            # Normalize embedding for ANN stability (L2)
            vec = vec / (np.linalg.norm(vec) + 1e-12)

            # ---------------------------
            # Encrypt the vector (Fernet) and keep encrypted token in metadata
            # ---------------------------
            enc_token_str = encrypt_vector_b64(vec)  # string of Fernet token

            # metadata for the index: include bank_id and an anonymized tx reference and encrypted vector token
            metadata = {
                "bank_id": BANK_ID,
                # hashed tx reference (not raw tx_id)
                "tx_ref": hash_id_hex(tx["tx_id"]),
                # encrypted token stored in metadata for compliance/retrieval (safe because it's Fernet)
                "enc_vec": enc_token_str
            }

            batch.append({
                "id": tx["tx_id"],    # id used by index (keeps original id so you can map locally)
                "vector": vec,        # numeric vector required by CyborgDB
                "metadata": metadata
            })

            # ----------------------------------------------------
            # PROCESS BATCH
            # ----------------------------------------------------
            if len(batch) >= BATCH_SIZE:

                await cy.batch_upsert(INDEX_NAME, batch)
                UPSERT_COUNTER.labels(worker=name).inc(len(batch))

                # TRAIN
                async with _upsert_lock:
                    _upsert_count += len(batch)
                    if _upsert_count >= TRAIN_AFTER:
                        try:
                            await cy.client.post(
                                f"{cy.endpoint}/v1/indexes/train",
                                json={"index_name": INDEX_NAME, "index_key": INDEX_KEY},
                                headers=cy.headers
                            )
                        except Exception:
                            pass
                        _upsert_count = 0

                # QUERY batch (numeric vectors)
                vectors = [item["vector"] for item in batch]

                with LATENCY_HIST.time():
                    result = await cy.batch_query(INDEX_NAME, vectors, top_k=TOP_K)

                Q_COUNTER.labels(worker=name).inc(len(batch))

                # ALERT CHECK
                # result expected shape: {"results": [[neighbor, neighbor, ...], [...]]}
                for i, group in enumerate(result.get("results", [])):
                    # debug-print entire neighbor group for visibility
                    if DEBUG_MODE:
                        print(f"[DEBUG] Query {i} neighbors raw:", group)

                    for neighbor in group:
                        # neighbor contains 'distance' (numeric) and 'metadata'
                        dist = neighbor.get("distance")
                        score = neighbor.get("score") or neighbor.get("similarity")
                        meta2 = neighbor.get("metadata", {})

                        # debug each neighbor details
                        if DEBUG_MODE:
                            print(f"[DEBUG] neighbor id={neighbor.get('id')} meta={meta2} distance={dist} score={score}")

                        # REQUIRE: different bank
                        if meta2.get("bank_id") == BANK_ID:
                            continue

                        triggered = False

                        # Use similarity/distance thresholds as before
                        if score is not None:
                            try:
                                s = float(score)
                                if s >= ALERT_SIMILARITY_THRESHOLD:
                                    triggered = True
                            except Exception:
                                pass
                        elif dist is not None:
                            try:
                                d = float(dist)
                                if d <= ALERT_DISTANCE_THRESHOLD:
                                    triggered = True
                            except Exception:
                                pass

                        if triggered:
                            alert = {
                                "alert_id": str(uuid.uuid4()),
                                "tx_id": batch[i]["id"],
                                "matched_id": neighbor.get("id"),
                                "distance": dist,
                                "score": score,
                                "bank_id": BANK_ID,
                                "matched_bank": meta2.get("bank_id"),
                                "matched_tx_ref": meta2.get("tx_ref"),
                                "timestamp": time.time()
                            }
                            ALERT_COUNTER.labels(severity="high").inc()
                            print("ALERT:", alert)
                            append_audit(alert)

                batch.clear()

            # ALWAYS LOG TX (local audit stores tx_id in encrypted ledger)
            append_audit({
                "event": "tx_processed",
                "bank_id": BANK_ID,
                "tx_id": tx["tx_id"],
                "timestamp": time.time(),
                "is_fraud": tx.get("is_fraud", False)
            })

        except Exception as e:
            print(f"[ERROR worker {name}] {e}")

        finally:
            q.task_done()
            LATENCY_HIST.observe(time.time() - start)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
async def main(tps=20.0, workers=2):
    start_http_server(PROM_PORT)

    await ensure_index_exists()

    worker_tasks = [
        asyncio.create_task(worker_consume(f"worker-{i}"))
        for i in range(workers)
    ]

    producer_task = asyncio.create_task(tx_producer(q, tps=tps))

    print(f"EFFIN node running → {BANK_ID} | audit={AUDIT_FILE} | port {PROM_PORT} | index={INDEX_NAME}")
    await asyncio.gather(producer_task, *worker_tasks)


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()

    asyncio.run(
        main(
            tps=float(os.getenv("TPS", "20")),
            workers=int(os.getenv("WORKERS", "2"))
        )
    )
