import streamlit as st
import requests
import yfinance as yf

# API Base URL
API_BASE = "http://127.0.0.1:5000"

TELEGRAM_BOT_USERNAME = "Order_ms_bot"
BOT_LINK = f"https://t.me/{TELEGRAM_BOT_USERNAME}"

st.title("📈 Stock Alert System")

# Telegram registration info
st.markdown("### 💬 Telegram Setup")
st.info(f"""
Before you receive alerts, **you must send a message** to our Telegram bot so we can get your Chat ID.
👉 [Click here to message the bot]({BOT_LINK})
""")

# Validate stock symbol using yfinance
def validate_symbol(symbol):
    if not symbol:
        return False
    try:
        ticker = yf.Ticker(symbol + '.NS')
        hist = ticker.history(period="1d")
        return not hist.empty
    except:
        return False

# New Alert Form
st.header("Set a New Price Alert")

symbol = st.text_input("Stock Symbol (e.g., RELIANCE, TATAMOTORS)").strip().upper()
condition = st.selectbox("Condition", ["above", "below"])
price = st.number_input("Target Price", min_value=0.0, step=0.1)
username = st.text_input("Your Telegram Username (e.g., @john_doe)").strip()

# Validation Checks
symbol_valid = validate_symbol(symbol) if symbol else None
username_valid = username.startswith("@") if username else None
price_valid = price > 0

# Show validation errors
if symbol and not symbol_valid:
    st.error("❌ Invalid stock symbol. Please enter a valid NSE stock symbol.")
if username and not username_valid:
    st.error("❌ Please enter a valid Telegram username starting with '@'.")
if price == 0:
    st.error("❌ Price must be greater than 0.")

# Disable submission button if validations fail
can_submit = symbol_valid and username_valid and price_valid

if st.button("Add Alert", disabled=not can_submit):
    try:
        response = requests.post(
            f"{API_BASE}/add-alert",
            json={
                "symbol": symbol,
                "condition": condition,
                "price": price,
                "username": username,
            },
        )
        if response.status_code == 200:
            st.success("✅ Alert added successfully!")
            st.info("⏳ Make sure you have sent a message to the bot so alerts can be delivered.")
        else:
            try:
                error_msg = response.json().get("error", "Failed to add alert.")
            except:
                error_msg = "Failed to add alert."
            st.error(f"❌ {error_msg}")
    except Exception as e:
        st.error(f"⚠️ Failed to connect to backend: {e}")

# User Alerts Section
st.header("📋 Your Active Alerts")

username_for_alerts = st.text_input("Enter your Telegram username to view your alerts (e.g., @john_doe)").strip()

if username_for_alerts and not username_for_alerts.startswith("@"):
    st.error("❌ Please enter a valid Telegram username starting with '@'.")
elif username_for_alerts:

    def fetch_alerts(username):
        try:
            response = requests.post(f"{API_BASE}/alerts", json={"username": username})
            if response.status_code == 200:
                return response.json()
            else:
                st.error("⚠️ Failed to fetch your alerts.")
                return []
        except Exception as e:
            st.error(f"⚠️ Failed to fetch your alerts: {e}")
            return []

    if "alerts_list" not in st.session_state:
        st.session_state.alerts_list = []

    if st.button("Fetch My Alerts"):
        st.session_state.alerts_list = fetch_alerts(username_for_alerts)
        st.session_state.show_refresh = False

    user_alerts = [alert for alert in st.session_state.alerts_list if alert["username"] == username_for_alerts]

    if user_alerts:
        for alert in user_alerts:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"🔔 {alert['symbol']} | {alert['condition']} {alert['price']} | User: {alert['username']}")
            with col2:
                delete_label = f"Delete-{alert['id']}"
                if st.button("🗑️", key=delete_label):
                    try:
                        del_response = requests.post(f"{API_BASE}/delete-alert", json={"id": alert["id"]})
                        if del_response.status_code == 200:
                            st.success(f"✅ Deleted alert for {alert['symbol']} {alert['condition']} {alert['price']}")
                            # Clear alerts and ask user to refresh manually
                            st.session_state.alerts_list = []
                            st.session_state.show_refresh = True
                        else:
                            st.error("❌ Failed to delete alert.")
                    except Exception as e:
                        st.error(f"⚠️ Error deleting alert: {e}")

        if st.session_state.get("show_refresh", False):
            if st.button("🔄 Refresh Alerts"):
                st.session_state.alerts_list = fetch_alerts(username_for_alerts)
                st.session_state.show_refresh = False
    else:
        st.info("No active alerts for your username.")
