Here is the **properly formatted Markdown (`.md`) file**, clean, professional, and **ready to paste directly** into your repo as
👉 **`RUN_INSTRUCTIONS.md`** or **`README.md`**.

Everything is correctly fenced, titled, and readable on GitHub.

---

````md
# 🚀 EFFIN – Running Instructions (Local Demo)

This document explains how to run the **Encrypted Federated Fraud Intelligence Network (EFFIN)** locally with a **3-bank simulation**, encrypted vector search using **CyborgDB**, and a **real-time Streamlit dashboard**.

---

## 📌 Prerequisites

Ensure the following are installed:

- Python **3.9+**
- **Docker** & Docker Desktop (running)
- **Git**
- PowerShell (Windows) or Terminal (macOS/Linux)

---

## 📥 Step 1: Clone the Repository

```bash
git clone https://github.com/bunny8205/effin.git
cd effin
````

---

## 🧪 Step 2: Create & Activate Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🔐 Step 3: Configure Environment Variables

Create a `.env` file in the project root **or set variables manually**.

### Required Variables

```powershell
$env:CYBORGDB_API_KEY="cyborg_9e0a3d56d0624ee2a8d2acc9d1f4a5f3"
$env:CYBORGDB_ENDPOINT="http://localhost:8000"
$env:FERNET_KEY="PASTE_BASE64_FERNET_KEY_HERE"
```

Generate a Fernet key if needed:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 🐳 Step 4: Start CyborgDB (Docker)

Ensure Docker Engine is running, then execute:

```powershell
docker run -p 8000:8000 `
  -e CYBORGDB_API_KEY=cyborg_9e0a3d56d0624ee2a8d2acc9d1f4a5f3 `
  cyborginc/cyborgdb-service:latest
```

CyborgDB will be available at:

```
http://localhost:8000
```

---

## 🏦 Step 5: Start Bank Nodes (3 Terminals)

Each bank must run in a **separate terminal window**.

---

### ▶️ Bank 1

```powershell
$env:BANK_ID="bank1"
$env:INDEX_NAME="effin_global_fraud_index"
$env:AUDIT_FILE="audit_bank1.jsonl"
$env:PROM_PORT="8001"

python -m effin.node
```

---

### ▶️ Bank 2

```powershell
$env:BANK_ID="bank2"
$env:INDEX_NAME="effin_global_fraud_index"
$env:AUDIT_FILE="audit_bank2.jsonl"
$env:PROM_PORT="8002"

python -m effin.node
```

---

### ▶️ Bank 3

```powershell
$env:BANK_ID="bank3"
$env:INDEX_NAME="effin_global_fraud_index"
$env:AUDIT_FILE="audit_bank3.jsonl"
$env:PROM_PORT="8003"

python -m effin.node
```

Each bank:

* Generates transactions independently
* Writes encrypted embeddings to a shared CyborgDB index
* Detects cross-bank fraud patterns securely

---

## 📊 Step 6: Run Streamlit Dashboard

Open a **new terminal**, navigate to the `effin` directory:

```bash
cd effin
```

Run the dashboard:

```bash
streamlit run dashboard/app.py --server.port 8501
```

Open in browser:

```
http://localhost:8501
```

---

## 🖥️ Dashboard Capabilities

* Bank selector: `bank1`, `bank2`, `bank3`
* Live metrics:

  * Transactions processed
  * Fraud alerts
  * Fraud rate
  * TPS
* Cross-bank similarity matrix
* Encrypted audit trail visualization

---

## 🔐 Security Notes

* All transaction embeddings are encrypted client-side
* CyborgDB never receives plaintext financial data
* Audit logs are stored as encrypted JSONL files
* Cross-bank detection runs using encrypted vector search

---

## 🛑 Stopping the System

* Stop bank nodes: `Ctrl + C` in each terminal
* Stop Streamlit: `Ctrl + C`
* Stop CyborgDB: `Ctrl + C` or stop the Docker container

---

## ✅ Expected Output

You should observe:

* Continuous transaction ingestion
* Real-time cross-bank fraud alerts
* Encrypted audit logs
* No plaintext customer or transaction data exposure

---

## 🔗 Repository

GitHub: [https://github.com/bunny8205/effin/](https://github.com/bunny8205/effin/)

---

```



Just say 👍
```
