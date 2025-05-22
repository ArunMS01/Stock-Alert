import streamlit as st
import requests
import yfinance as yf

API_BASE = "https://stock-alert-odjb.onrender.com"

st.title("📈 Stock Alert System")

# Telegram Setup info
st.markdown("### 💬 Telegram Setup")
TELEGRAM_BOT_USERNAME = "Order_ms_bot"
BOT_LINK = f"https://t.me/{TELEGRAM_BOT_USERNAME}"
st.info(f"""
Before you receive alerts, **send a message** to our Telegram bot so we can get your Chat ID.
👉 [Click here to message the bot]({BOT_LINK})
""")

# Common Telegram Username input
username = st.text_input("Your Telegram Username (e.g., @john_doe)").strip()

# Validate stock symbol with yfinance
def validate_symbol(symbol):
    if not symbol:
        return False
    try:
        ticker = yf.Ticker(symbol + '.NS')
        hist = ticker.history(period="1d")
        return not hist.empty
    except:
        return False

# Tabs
tab1, tab2, tab3 = st.tabs(["➕ Set Single Alert", "📋 My Alerts", "➕📊 Bulk Add Alerts"])

# ---------- Tab 1: Single Alert ----------
with tab1:
    st.subheader("Set a New Price Alert")

    symbol = st.text_input("Stock Symbol (e.g., RELIANCE, TATAMOTORS)").strip().upper()
    condition = st.selectbox("Condition", ["above", "below"])
    price = st.number_input("Target Price", min_value=0.0, step=0.1)

    if st.button("Add Alert"):
        if not username.startswith("@"):
            st.error("❌ Please enter a valid Telegram username starting with '@'.")
        elif not validate_symbol(symbol):
            st.error("❌ Invalid stock symbol.")
        elif price <= 0:
            st.error("❌ Price must be greater than 0.")
        else:
            try:
                response = requests.post(f"{API_BASE}/add-alert", json={
                    "symbol": symbol, "condition": condition, "price": price, "username": username
                })
                if response.status_code == 200:
                    st.success("✅ Alert added successfully!")
                else:
                    st.error(f"❌ {response.json().get('error', 'Failed to add alert.')}")
            except Exception as e:
                st.error(f"⚠️ Connection error: {e}")

# ---------- Tab 2: View & Manage Alerts ----------
with tab2:
    st.subheader("📋 Your Active Alerts")

    def fetch_alerts(username):
        try:
            response = requests.post(f"{API_BASE}/alerts", json={"username": username})
            if response.status_code == 200:
                return response.json()
            else:
                st.error("⚠️ Failed to fetch your alerts.")
                return []
        except Exception as e:
            st.error(f"⚠️ Error fetching alerts: {e}")
            return []

    if st.button("Fetch My Alerts"):
        if not username.startswith("@"):
            st.error("❌ Please enter a valid Telegram username starting with '@'.")
        else:
            alerts = fetch_alerts(username)
            if alerts:
                for alert in alerts:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"🔔 {alert['symbol']} | {alert['condition']} {alert['price']}")
                    with col2:
                        if st.button("🗑️", key=f"delete-{alert['id']}"):
                            try:
                                del_response = requests.post(f"{API_BASE}/delete-alert", json={"id": alert["id"]})
                                if del_response.status_code == 200:
                                    st.success(f"✅ Deleted alert for {alert['symbol']}")
                                else:
                                    st.error("❌ Failed to delete alert.")
                            except Exception as e:
                                st.error(f"⚠️ Delete error: {e}")
            else:
                st.info("No active alerts found.")

# ---------- Tab 3: Bulk Add ----------
with tab3:
    st.subheader("➕📊 Set Multiple Stock Alerts")

    if "bulk_alerts" not in st.session_state:
        st.session_state.bulk_alerts = [{"symbol": "", "condition": "above", "price": 0.0}]

    if st.button("➕ Add Another Alert"):
        st.session_state.bulk_alerts.append({"symbol": "", "condition": "above", "price": 0.0})

    for idx, alert in enumerate(st.session_state.bulk_alerts):
        st.markdown(f"#### Alert {idx+1}")
        col1, col2, col3 = st.columns([3, 2, 2])
        with col1:
            st.session_state.bulk_alerts[idx]["symbol"] = st.text_input(f"Symbol {idx+1}", value=alert["symbol"], key=f"symbol_{idx}").strip().upper()
        with col2:
            st.session_state.bulk_alerts[idx]["condition"] = st.selectbox(f"Condition {idx+1}", ["above", "below"], index=0 if alert["condition"]=="above" else 1, key=f"condition_{idx}")
        with col3:
            st.session_state.bulk_alerts[idx]["price"] = st.number_input(f"Price {idx+1}", min_value=0.0, step=0.1, value=alert["price"], key=f"price_{idx}")

    if st.button("🚀 Submit All Alerts"):
        if not username.startswith("@"):
            st.error("❌ Please enter a valid Telegram username starting with '@'.")
        else:
            all_valid = True
            for alert in st.session_state.bulk_alerts:
                if not validate_symbol(alert["symbol"]):
                    st.error(f"❌ Invalid stock symbol: {alert['symbol']}")
                    all_valid = False
                elif alert["price"] <= 0:
                    st.error(f"❌ Price must be greater than 0 for {alert['symbol']}")
                    all_valid = False

            if all_valid:
                for alert in st.session_state.bulk_alerts:
                    try:
                        response = requests.post(f"{API_BASE}/add-alert", json={
                            "symbol": alert["symbol"],
                            "condition": alert["condition"],
                            "price": alert["price"],
                            "username": username,
                        })
                        if response.status_code == 200:
                            st.success(f"✅ Added alert: {alert['symbol']} {alert['condition']} {alert['price']}")
                        else:
                            st.error(f"❌ {alert['symbol']}: {response.json().get('error', 'Failed')}")
                    except Exception as e:
                        st.error(f"⚠️ Error adding {alert['symbol']}: {e}")

                st.session_state.bulk_alerts = [{"symbol": "", "condition": "above", "price": 0.0}]
