import json, time, os
from cryptography.fernet import Fernet

AUDIT_FILE = os.getenv("AUDIT_FILE", "effin/audit_ledger.jsonl")
FERNET_KEY = os.getenv("FERNET_KEY")

fernet = Fernet(FERNET_KEY.encode())

def write_event(event: dict):
    """Encrypt and append audit event."""
    event["ts"] = time.time()
    raw = json.dumps(event).encode()
    token = fernet.encrypt(raw)

    # ensure directory exists
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)

    with open(AUDIT_FILE, "ab") as f:
        f.write(token + b"\n")
