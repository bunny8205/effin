import streamlit as st
import os, json, time
import numpy as np
from cryptography.fernet import Fernet
import pandas as pd

st.set_page_config(page_title="EFFIN Dashboard", layout="wide")
st.title("🔐 EFFIN – Multi-Bank Encrypted Fraud Intelligence Dashboard")

# ----------------------------------------------------
# BANK SELECTOR
# ----------------------------------------------------
bank = st.selectbox("Select Bank Node:", ["bank1", "bank2", "bank3"])
AUDIT_FILE = f"C:/Users/rameeza/PycharmProjects/effin/audit_{bank}.jsonl"

st.write(f"📁 **Audit Source:** `{AUDIT_FILE}`")

# ----------------------------------------------------
# Load Fernet key
# ----------------------------------------------------
FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    st.error("❌ FERNET_KEY missing — cannot decrypt audit logs.")
    st.stop()

fernet = Fernet(FERNET_KEY.encode())


# ----------------------------------------------------
# Decrypt helper
# ----------------------------------------------------
def tail_decrypt(path, n=500):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, "rb") as f:
        lines = f.readlines()[-n:]

    for L in reversed(lines):
        try:
            data = fernet.decrypt(L.strip())
            items.append(json.loads(data))
        except:
            items.append({"error": "decrypt_failed"})
    return items


# ----------------------------------------------------
# SMOOTH AUTO REFRESH (NO PAGE RELOAD)
# ----------------------------------------------------
# Refresh interval (seconds)
REFRESH_INTERVAL = 5

# A placeholder where all dynamic content will go
container = st.empty()

while True:
    with container.container():
        events = tail_decrypt(AUDIT_FILE)

        if not events:
            st.info("ℹ️ No decryptable entries yet. Wait for the node to generate traffic.")
            time.sleep(REFRESH_INTERVAL)
            continue

        alerts = [e for e in events if e.get("alert_id")]
        txs = [e for e in events if e.get("event") == "tx_processed"]

        # ----------------------------------------------------
        # METRICS SUMMARY BAR
        # ----------------------------------------------------
        col1, col2, col3, col4 = st.columns(4)

        total_tx = len(txs)
        total_alerts = len(alerts)

        if txs:
            time_span = (txs[0]["timestamp"] - txs[-1]["timestamp"]) or 1
            tps = total_tx / time_span
        else:
            tps = 0

        fraud_rate = (total_alerts / total_tx * 100) if total_tx else 0

        col1.metric("Transactions (recent)", total_tx)
        col2.metric("Fraud Alerts", total_alerts)
        col3.metric("Fraud Rate %", f"{fraud_rate:.2f}%")
        col4.metric("TPS", f"{tps:.2f}")

        st.markdown("---")

        # ----------------------------------------------------
        # TRANSACTION SUMMARY
        # ----------------------------------------------------
        st.subheader(f"📊 Recent Transactions — `{bank}`")

        if txs:
            for t in txs[:40]:
                ts = t.get("timestamp") or t.get("ts")
                st.markdown(
                    f"""
                    <div style="padding:6px; border-left:4px solid #4CAF50; margin-bottom:4px;">
                        🟢 <b>TX:</b> {t['tx_id']}  
                        <br><small>🕒 {time.ctime(ts) if ts else "unknown"}</small>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.write("No transactions recorded yet.")

        st.markdown("---")

        # ----------------------------------------------------
        # 📈 ALERTS TIMELINE
        # ----------------------------------------------------
        st.subheader("📈 Fraud Alerts Timeline")

        if alerts:
            df_alerts = pd.DataFrame([
                {"timestamp": a["timestamp"], "distance": a["distance"]}
                for a in alerts
            ])
            df_alerts["time_str"] = df_alerts["timestamp"].apply(
                lambda x: time.strftime("%H:%M:%S", time.localtime(x))
            )
            st.line_chart(df_alerts.set_index("time_str")["distance"])
        else:
            st.info("No alerts yet.")

        st.markdown("---")

        # ----------------------------------------------------
        # 🤝 CROSS-BANK SIMILARITY MATRIX
        # ----------------------------------------------------
        st.subheader("🤝 Cross-Bank Similarity Matrix")

        banks = ["bank1", "bank2", "bank3"]
        matrix = pd.DataFrame(0, index=banks, columns=banks)

        for a in alerts:
            src = a["bank_id"]
            dst = a["matched_bank"]
            if src in banks and dst in banks:
                matrix.loc[src, dst] += 1

        st.dataframe(matrix)

        st.markdown("---")

        # ----------------------------------------------------
        # 📊 ANN DISTANCE HISTOGRAM
        # ----------------------------------------------------
        st.subheader("📊 ANN Distance Distribution")

        if alerts:
            distances = [a["distance"] for a in alerts]
            df_dist = pd.DataFrame({"distance": distances})
            st.bar_chart(df_dist)
        else:
            st.write("No fraud alerts yet.")

        st.markdown("---")

        # ----------------------------------------------------
        # 🚨 ALERT DETAILS
        # ----------------------------------------------------
        st.subheader("🚨 Fraud Alerts (Cross-Bank)")

        if not alerts:
            st.success("✔ No fraud alerts detected.")
        else:
            for a in alerts:
                ts = a.get("timestamp") or a.get("ts")
                short_summary = (
                    f"⚠️ {a['bank_id']} → {a['matched_bank']} | "
                    f"TX {a['tx_id'][:6]}… matched {a['matched_id'][:6]}… "
                    f" | dist={a['distance']:.3f}"
                )

                with st.expander(short_summary):
                    st.markdown(
                        f"""
                        ### 🚨 Fraud Alert  
                        **Alert ID:** `{a['alert_id']}`  
                        **Source Bank:** `{a['bank_id']}`  
                        **Matched Bank:** `{a['matched_bank']}`  
                        **Transaction ID:** `{a['tx_id']}`  
                        **Matched Transaction:** `{a['matched_id']}`  
                        **Similarity Distance:** `{a['distance']:.4f}`  
                        **Timestamp:** `{time.ctime(ts) if ts else "unknown"}`  

                        ---
                        #### 📌 Explanation  
                        This alert was triggered because the transaction embedding from **{a['bank_id']}**  
                        was extremely similar to a known fraud pattern in **{a['matched_bank']}**.

                        The encrypted-in-use CyborgDB index identified high similarity while keeping  
                        all sensitive data fully encrypted end-to-end.
                        """
                    )

        st.markdown("---")
        st.caption("EFFIN — Privacy-Preserving Federated Fraud Detection • Powered by CyborgDB")

    # Sleep but DO NOT reload → no scroll jump
    time.sleep(REFRESH_INTERVAL)
