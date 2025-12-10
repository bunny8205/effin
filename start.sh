#!/bin/bash

echo "Starting CyborgDB..."
docker run -d -p 8000:8000 \
  -e CYBORGDB_API_KEY=$CYBORGDB_API_KEY \
  cyborginc/cyborgdb-service:latest

sleep 5

echo "Starting bank1..."
BANK_ID=bank1 INDEX_NAME=effin_global_fraud_index AUDIT_FILE=audit_bank1.jsonl PROM_PORT=8001 python -m effin.node &

echo "Starting bank2..."
BANK_ID=bank2 INDEX_NAME=effin_global_fraud_index AUDIT_FILE=audit_bank2.jsonl PROM_PORT=8002 python -m effin.node &

echo "Starting bank3..."
BANK_ID=bank3 INDEX_NAME=effin_global_fraud_index AUDIT_FILE=audit_bank3.jsonl PROM_PORT=8003 python -m effin.node &

echo "Starting Streamlit dashboard..."
streamlit run effin/dashboard/app.py --server.port 8501 --server.address 0.0.0.0
