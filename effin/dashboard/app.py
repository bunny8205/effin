import streamlit as st
import os, json, time
import numpy as np
from cryptography.fernet import Fernet
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

st.set_page_config(page_title="EFFIN Dashboard", layout="wide")
st.title("🔐 EFFIN – Multi-Bank Encrypted Fraud Intelligence Dashboard")

# ----------------------------------------------------
# NEW: VIEW MODE SELECTOR (FEATURE 2)
# ----------------------------------------------------
view_mode = st.selectbox(
    "View Mode",
    ["Bank Analyst", "Regulator / Auditor"]
)

# Show regulator warning
if view_mode == "Regulator / Auditor":
    st.warning(
        "Regulator View: Read-only, metadata-only, encrypted insights. "
        "No customer or transaction identifiers exposed."
    )

# ----------------------------------------------------
# BANK SELECTOR
# ----------------------------------------------------
bank = st.selectbox("Select Bank Node:", ["bank1", "bank2", "bank3"])
AUDIT_FILE = f"C:/Users/rameeza/PycharmProjects/effin/audit_{bank}.jsonl"



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
            st.info(" No decryptable entries yet. Wait for the node to generate traffic.")
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
        # TRANSACTION SUMMARY (WITH REGULATOR VIEW)
        # ----------------------------------------------------
        if view_mode == "Regulator / Auditor":
            st.subheader("📊 Transaction Volume (Redacted)")
            st.info("Transaction details hidden in regulator mode.")
        else:
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
        # NEW: ENCRYPTED FRAUD RING GRAPH (FEATURE 1)
        # ----------------------------------------------------
        st.subheader(" Encrypted Fraud Ring Graph")

        G = nx.Graph()

        for a in alerts:
            ring = a.get("ring_id")
            src = a.get("bank_id")
            dst = a.get("matched_bank")

            if ring and src and dst:
                G.add_node(src, bank=src)
                G.add_node(dst, bank=dst)
                # Add edge with ring ID as attribute
                if G.has_edge(src, dst):
                    # Increase weight if edge already exists
                    G[src][dst]['weight'] += 1
                    # Add ring ID to set of rings for this edge
                    if 'rings' not in G[src][dst]:
                        G[src][dst]['rings'] = set()
                    G[src][dst]['rings'].add(ring)
                else:
                    G.add_edge(src, dst, ring=ring, weight=1, rings={ring})

        if len(G.nodes) == 0:
            st.info("No fraud rings detected yet.")
        else:
            pos = nx.spring_layout(G, seed=42)
            fig, ax = plt.subplots(figsize=(10, 6))

            # Custom node colors (green for current bank, red for others)
            node_colors = ["#4CAF50" if n == bank else "#FF5252" for n in G.nodes]

            # Draw with customized appearance
            nx.draw(
                G,
                pos,
                with_labels=True,
                node_size=1200,
                node_color=node_colors,
                edge_color="#FFA726",
                width=[G[u][v]['weight'] * 2 for u, v in G.edges()],  # Thicker edges for more connections
                ax=ax,
                font_size=10,
                font_weight='bold'
            )

            # Add title
            ax.set_title(
                f"Fraud Ring Network - {len(G.edges())} connections, {len(set().union(*[G[u][v]['rings'] for u, v in G.edges()]))} unique rings",
                fontsize=12, pad=20)

            st.pyplot(fig)

            # Show ring statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Banks in Network", len(G.nodes))
            with col2:
                st.metric("Cross-Bank Links", len(G.edges()))
            with col3:
                unique_rings = len(set().union(*[G[u][v].get('rings', set()) for u, v in G.edges()]))
                st.metric("Unique Fraud Rings", unique_rings)

        st.markdown("---")

        # ----------------------------------------------------
        # 🤝 CROSS-BANK SIMILARITY MATRIX
        # ----------------------------------------------------
        st.subheader(" Cross-Bank Similarity Matrix")

        banks = ["bank1", "bank2", "bank3"]
        matrix = pd.DataFrame(0, index=banks, columns=banks)

        for a in alerts:
            src = a.get("bank_id")
            dst = a.get("matched_bank")
            if src in banks and dst in banks:
                matrix.loc[src, dst] += 1

        st.dataframe(matrix)

        st.markdown("---")

        # ----------------------------------------------------
        # 📊 ANN DISTANCE HISTOGRAM
        # ----------------------------------------------------
        st.subheader("📊 ANN Distance Distribution")

        if alerts:
            distances = [a.get("distance", 0) for a in alerts]
            df_dist = pd.DataFrame({"distance": distances})
            st.bar_chart(df_dist)
        else:
            st.write("No fraud alerts yet.")

        st.markdown("---")

        # ----------------------------------------------------
        # 🚨 ALERT DETAILS (WITH REGULATOR REDACTION)
        # ----------------------------------------------------
        st.subheader("🚨 Fraud Alerts (Cross-Bank)")

        if not alerts:
            st.success("✔ No fraud alerts detected.")
        else:
            for a in alerts:
                ts = a.get("timestamp") or a.get("ts")

                if view_mode == "Regulator / Auditor":
                    # Redacted summary for regulators
                    short_summary = (
                        f"⚠️ {a.get('bank_id', 'Unknown')} → {a.get('matched_bank', 'Unknown')} | "
                        f"Ring: {a.get('ring_id', 'Unknown')} | "
                        f"Distance: {a.get('distance', 0):.3f}"
                    )
                else:
                    # Full details for bank analysts
                    short_summary = (
                        f"⚠️ {a.get('bank_id', 'Unknown')} → {a.get('matched_bank', 'Unknown')} | "
                        f"TX {a.get('tx_id', '')[:6]}… matched {a.get('matched_id', '')[:6]}… | "
                        f"Ring: {a.get('ring_id', 'Unknown')} | "
                        f"dist={a.get('distance', 0):.3f}"
                    )

                with st.expander(short_summary):
                    if view_mode == "Regulator / Auditor":
                        # Redacted details for regulators
                        st.markdown(
                            f"""
                            ### 🚨 Encrypted Fraud Alert (Regulator View)
                            **Alert ID:** `{a.get('alert_id', 'Unknown')}`  
                            **Source Bank:** `{a.get('bank_id', 'Unknown')}`  
                            **Matched Bank:** `{a.get('matched_bank', 'Unknown')}`  
                            **Similarity Distance:** `{a.get('distance', 0):.4f}`  
                            **Fraud Ring ID:** `{a.get('ring_id', 'Unknown')}`  
                            **Timestamp:** `{time.ctime(ts) if ts else "unknown"}`  

                            ---
                            #### 📌 Regulatory Insight  
                            This encrypted alert indicates coordinated fraud activity across banking institutions.  
                            No customer or transaction identifiers are exposed in this view.  

                            The fraud ring pattern suggests organized criminal activity spanning multiple banks,  
                            detected via privacy-preserving federated learning while maintaining full encryption.
                            """
                        )
                    else:
                        # Full details for bank analysts
                        st.markdown(
                            f"""
                            ### 🚨 Fraud Alert  
                            **Alert ID:** `{a.get('alert_id', 'Unknown')}`  
                            **Source Bank:** `{a.get('bank_id', 'Unknown')}`  
                            **Matched Bank:** `{a.get('matched_bank', 'Unknown')}`  
                            **Transaction ID:** `{a.get('tx_id', 'Unknown')}`  
                            **Matched Transaction:** `{a.get('matched_id', 'Unknown')}`  
                            **Similarity Distance:** `{a.get('distance', 0):.4f}`  
                            **Fraud Ring ID:** `{a.get('ring_id', 'Unknown')}`  
                            **Timestamp:** `{time.ctime(ts) if ts else "unknown"}`  

                            ---
                            #### 📌 Explanation  
                            This alert was triggered because the transaction embedding from **{a.get('bank_id', 'Unknown')}**  
                            was extremely similar to a known fraud pattern in **{a.get('matched_bank', 'Unknown')}**.  

                            The fraud ring identifier `{a.get('ring_id', 'Unknown')}` links this to organized criminal activity  
                            detected across the federated banking network.  

                            The encrypted-in-use CyborgDB index identified high similarity while keeping  
                            all sensitive data fully encrypted end-to-end.
                            """
                        )

        st.markdown("---")
        st.caption("EFFIN — Privacy-Preserving Federated Fraud Detection • Powered by CyborgDB")

    # Sleep but DO NOT reload → no scroll jump
    time.sleep(REFRESH_INTERVAL)
