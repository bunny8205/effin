# effin/node/ingest.py
import asyncio
import uuid
import time
import random
import numpy as np
import os

# ----------------------------------------------
# BANK ID for multi-bank simulation
# ----------------------------------------------
BANK_ID = os.getenv("BANK_ID", "bank1")

# ----------------------------------------------
# NORMAL behavior signature per bank
# (used to generate consistent behavioral patterns)
# ----------------------------------------------
BANK_SIGNATURES = {
    "bank1": np.array([0.10, 0.20, 0.30, 0.40]),
    "bank2": np.array([0.55, 0.42, 0.28, 0.15]),
    "bank3": np.array([0.90, 0.10, 0.10, 0.30]),
}

if BANK_ID not in BANK_SIGNATURES:
    BANK_SIGNATURES[BANK_ID] = np.random.rand(4)

# ----------------------------------------------
# GLOBAL SHARED FRAUD SIGNAL
# This causes cross-bank similarity → ALERTS
# ----------------------------------------------
FRAUD_VECTOR = np.array([0.25, 0.22, 0.31, 0.45])

# % of transactions that are fraud (demo mode)
FRAUD_PROBABILITY = float(os.getenv("FRAUD_PROB", "0.10"))

# ----------------------------------------------
# Static categorical fields for realism
# ----------------------------------------------
MERCHANTS_NORMAL = [
    "GroceryMart", "GasStation", "OnlineStore", "CafeLux",
    "ElectronicsHub", "TravelDesk"
]

MERCHANT_FRAUD = [
    "EvilMuleNetwork", "SuspiciousShop", "CardTestingBot"
]

LOCATIONS_NORMAL = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune"]
LOCATIONS_FRAUD = ["Unknown", "ProxyServer", "DarkWebNode"]

DEVICES_NORMAL = ["devA", "devB", "devC", "devD"]
DEVICES_FRAUD = ["fraudDevice001", "fraudDevice002"]


# ----------------------------------------------
# GENERATE A SINGLE TRANSACTION
# ----------------------------------------------
def generate_transaction():
    """
    Generate a realistic transaction including:
    - amount
    - merchant
    - location
    - device fingerprint
    - timestamp
    - fraud flag
    - BANK-SPECIFIC NUMERIC SIGNATURE (weakened)
    """
    is_fraud = np.random.rand() < FRAUD_PROBABILITY

    if is_fraud:
        # ⚠️ FRAUD MUST NOT INCLUDE BANK SIGNATURE
        # This ensures cross-bank similarity
        base_vec = FRAUD_VECTOR
        noise = np.random.normal(0, 0.01, 4)

        merchant = random.choice(MERCHANT_FRAUD)
        location = random.choice(LOCATIONS_FRAUD)
        device = random.choice(DEVICES_FRAUD)

        amount = round(random.uniform(4500, 5000), 2)

    else:
        # Normal traffic remains bank-specific but weakened
        base_vec = BANK_SIGNATURES[BANK_ID] * 0.3
        noise = np.random.normal(0, 0.05, 4)

        merchant = random.choice(MERCHANTS_NORMAL)
        location = random.choice(LOCATIONS_NORMAL)
        device = random.choice(DEVICES_NORMAL)

        amount = round(random.uniform(50, 3000), 2)

    # Final 4-dim numeric feature
    features = (base_vec + noise).tolist()

    return {
        "tx_id": str(uuid.uuid4()),
        "timestamp": time.time(),
        "amount": amount,
        "merchant_category": merchant,
        "location": location,
        "device_fingerprint": device,
        "feature_signature": features,  # encoder uses this
        "bank_id": BANK_ID,
        "is_fraud": is_fraud
    }


# ----------------------------------------------
# STREAM TRANSACTIONS INTO QUEUE
# ----------------------------------------------
async def tx_producer(q: asyncio.Queue, tps: float = 3.0):
    """
    Generate ~tps transactions per second.
    """
    delay = 1.0 / max(tps, 0.1)

    while True:
        tx = generate_transaction()
        await q.put(tx)
        await asyncio.sleep(delay)
