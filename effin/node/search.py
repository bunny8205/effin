# effin/node/search.py

import httpx
import numpy as np
from typing import Dict, Any, List, Optional


class CyborgWrapper:
    def __init__(self, endpoint: str, api_key: str, index_key: Optional[str] = None, timeout: float = 30.0):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.index_key = index_key or ""

        self.headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key
        }

        self.client = httpx.AsyncClient(timeout=timeout)

    # -------------------------------------------------------------
    # CREATE INDEX (32 dims)
    # -------------------------------------------------------------
    async def create_index(self, index_name: str, vector_dimension: int = 32, index_config: Optional[dict] = None):

        payload = {
            "index_name": index_name,
            "index_key": self.index_key,
            "index_config": index_config or {
                "type": "ivfflat",
                "dimension": vector_dimension
            }
        }

        url = f"{self.endpoint}/v1/indexes/create"
        resp = await self.client.post(url, json=payload, headers=self.headers)

        if resp.status_code in (400, 409):
            print(f"[INFO] Index '{index_name}' already exists — continuing.")
            return {"status": "exists"}

        resp.raise_for_status()
        print(f"[SUCCESS] Index '{index_name}' created.")
        return resp.json()

    # -------------------------------------------------------------
    # ENSURE INDEX EXISTS
    # -------------------------------------------------------------
    async def ensure_index_exists(self, index_name: str, vector_dim: int = 32):

        list_url = f"{self.endpoint}/v1/indexes/list"
        resp = await self.client.get(list_url, headers=self.headers)

        try:
            resp.raise_for_status()
        except Exception:
            print("[WARN] Could not list indexes — attempting create.")
            return await self.create_index(index_name, vector_dim)

        indexes = resp.json().get("indexes", [])
        if index_name in indexes:
            print(f"[INFO] Index '{index_name}' exists.")
            return

        print(f"[INFO] Index '{index_name}' missing — creating…")
        return await self.create_index(index_name, vector_dim)

    # -------------------------------------------------------------
    # UPSERT (batch)
    # We keep numeric float vectors in "vector" and preserve any metadata.
    # -------------------------------------------------------------
    async def batch_upsert(self, index_name: str, items: List[Dict]):

        url = f"{self.endpoint}/v1/vectors/upsert"

        payload = {
            "index_name": index_name,
            "index_key": self.index_key,
            "items": [
                {
                    "id": it["id"],
                    # numeric vector must be a list of floats for CyborgDB
                    "vector": it["vector"].tolist() if hasattr(it["vector"], "tolist") else list(it["vector"]),
                    "metadata": it.get("metadata", {})
                }
                for it in items
            ]
        }

        resp = await self.client.post(url, json=payload, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    # -------------------------------------------------------------
    # SINGLE UPSERT (for tests)
    # -------------------------------------------------------------
    async def upsert(self, index_name: str, id: str, vector: np.ndarray, metadata: dict):
        url = f"{self.endpoint}/v1/vectors/upsert"

        payload = {
            "index_name": index_name,
            "index_key": self.index_key,
            "items": [{
                "id": id,
                "vector": vector.tolist(),
                "metadata": metadata
            }]
        }

        resp = await self.client.post(url, json=payload, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    # -------------------------------------------------------------
    # SINGLE QUERY (numeric)
    # -------------------------------------------------------------
    async def query(self, index_name: str, vector: np.ndarray, top_k: int = 5, include=None):

        url = f"{self.endpoint}/v1/vectors/query"

        payload = {
            "index_name": index_name,
            "index_key": self.index_key,
            "query_vectors": [vector.tolist()],     # correct JSON shape
            "top_k": top_k,
            "include": include or ["distance", "metadata"]
        }

        resp = await self.client.post(url, json=payload, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    # -------------------------------------------------------------
    # BATCH QUERY (numeric)
    # -------------------------------------------------------------
    async def batch_query(self, index_name: str, vectors: List[np.ndarray], top_k: int = 5):

        url = f"{self.endpoint}/v1/vectors/query"

        payload = {
            "index_name": index_name,
            "index_key": self.index_key,
            "query_vectors": [v.tolist() for v in vectors],
            "top_k": top_k,
            "include": ["distance", "metadata"]
        }

        resp = await self.client.post(url, json=payload, headers=self.headers)
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        await self.client.aclose()
