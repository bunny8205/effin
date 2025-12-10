# tests/test_encoder.py
from effin.encoder.model import FraudEncoder
import numpy as np

def test_embed_shape():
    enc = FraudEncoder()
    tx = {"amount": 10, "merchant_category": "Grocery", "location": "Mumbai", "device_fingerprint": "devA"}
    v = enc.embed_transaction(tx)
    assert v.shape[0] > 0
    assert isinstance(v, np.ndarray)
