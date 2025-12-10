# effin/common/crypto.py
import os
from cryptography.fernet import Fernet
import numpy as np
import hashlib

FERNET_KEY = os.getenv("FERNET_KEY")  # must be base64 urlsafe string

if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY not set in env")

fernet = Fernet(FERNET_KEY.encode())


def encrypt_vector(vec: np.ndarray) -> bytes:
    """
    Convert float32 numpy vector to raw bytes then encrypt with Fernet.
    Returns raw Fernet token bytes.
    """
    b = vec.astype(np.float32).tobytes()
    token = fernet.encrypt(b)
    return token


def decrypt_vector(token: bytes, dtype=np.float32, shape=None) -> np.ndarray:
    """
    Decrypt a Fernet token (bytes) and return a numpy array.
    """
    b = fernet.decrypt(token)
    arr = np.frombuffer(b, dtype=dtype)
    if shape:
        arr = arr.reshape(shape)
    return arr


# ----------------------------
# JSON-friendly helpers
# ----------------------------
def encrypt_vector_b64(vec: np.ndarray) -> str:
    """
    Encrypt vector and return Fernet token string (utf-8).
    """
    token = encrypt_vector(vec)  # bytes
    return token.decode()


def decrypt_vector_b64(token_b64: str, dtype=np.float32, shape=None) -> np.ndarray:
    """
    Decrypt a Fernet token string (utf-8) and return numpy array.
    """
    token = token_b64.encode()
    return decrypt_vector(token, dtype=dtype, shape=shape)


# ----------------------------
# Raw bytes helpers
# ----------------------------
def encrypt_bytes_b64(data: bytes) -> str:
    """Encrypt bytes and return token as utf-8 string."""
    return fernet.encrypt(data).decode()


def decrypt_bytes_b64(token_b64: str) -> bytes:
    """Decrypt token string (utf-8) and return raw bytes."""
    return fernet.decrypt(token_b64.encode())


# ----------------------------
# Utility: hash tx_id for index metadata
# ----------------------------
def hash_id_hex(short_id: str, length: int = 12) -> str:
    """
    Return a short hex digest suitable for storing in index metadata instead of raw tx_id.
    """
    h = hashlib.sha256(short_id.encode()).hexdigest()
    return h[:length]
