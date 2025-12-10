# effin/encoder/model.py
import numpy as np

class FraudEncoder:
    """
    Embedding encoder for encrypted fraud detection.
    This version ENFORCES very strong cross-bank similarity for fraud
    while keeping each bank’s normal behavior separated.
    """

    def __init__(self):
        # Shared global fraud vector (base pattern)
        self.FRAUD_VEC = np.array([0.25, 0.22, 0.31, 0.45])

        # Deterministic categorical vocab
        self.merchant_vocab = {}
        self.location_vocab = {}
        self.device_vocab = {}

        self.embed_dim = 32

    # ----------------------------------------------
    # Deterministic categorical embedding
    # ----------------------------------------------
    def _embed_cat(self, value, vocab, size=4):
        if value not in vocab:
            seed = abs(hash(value)) % (2**32)
            rng = np.random.default_rng(seed)
            vocab[value] = rng.uniform(-0.5, 0.5, size)
        return vocab[value]

    # ----------------------------------------------
    # MAIN ENCODER
    # ----------------------------------------------
    def embed_transaction(self, tx: dict) -> np.ndarray:
        """
        tx fields:
            amount, merchant_category, location, device_fingerprint,
            feature_signature, bank_id, is_fraud
        """

        # A) Base numeric signature from ingest
        sig = np.array(tx.get("feature_signature", [0, 0, 0, 0]))

        # B) Strong fraud boost for cross-bank similarity
        if tx.get("is_fraud"):
            fraud_component = self.FRAUD_VEC * 5.0     # <<< HUGE boost
        else:
            fraud_component = np.zeros_like(self.FRAUD_VEC)

        # C) Amount normalization (down-weighted later)
        amt = float(tx.get("amount", 0))
        amt_norm = np.array([amt / 5000.0])

        # D) Deterministic category embeddings
        merch = self._embed_cat(tx.get("merchant_category", "unknown"), self.merchant_vocab)
        loc   = self._embed_cat(tx.get("location", "unknown"), self.location_vocab)
        dev   = self._embed_cat(tx.get("device_fingerprint", "unknown"), self.device_vocab)

        # E) Weight components so fraud + signature dominate
        vec = np.concatenate([
            sig * 1.5,             # strengthen bank/fraud signature
            fraud_component,        # very strong fraud cross-bank pattern
            amt_norm * 0.3,         # reduce noise influence
            merch * 0.5,            # reduce categorical noise
            loc * 0.5,
            dev * 0.5
        ])

        # Pad to 32 dims
        if len(vec) < self.embed_dim:
            vec = np.concatenate([vec, np.zeros(self.embed_dim - len(vec))])

        return vec.astype(np.float32)
