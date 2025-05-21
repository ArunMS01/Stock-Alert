import streamlit as st
import requests
import yfinance as yf

API_BASE = "https://stock-alert-odjb.onrender.com"
TELEGRAM_BOT_USERNAME = "Order_ms_bot"  # ⬅️ Replace this
BOT_LINK = f"https://t.me/{TELEGRAM_BOT_USERNAME}"

st.title("📈 Stock Alert System")

st.markdown("### 💬 Telegram Setup")
st.info(f"""
Before you receive alerts, **you must send a message** to our Telegram bot so we can get your Chat ID.
👉 [Click here to message the bot]({BOT_LINK})
""")

# Validate symbol function
def validate_symbol(symbol):
    if not symbol:
        return False
    try:
        ticker = yf.Ticker(symbol + ".NS")
        hist = ticker.history(period="1d")
        return not hist.empty
    except:
        return False

# Get user inputs outside the form to enable instant validation
symbol = st.text_input("Stock Symbol (e.g., RELIANCE,TATAMOTORS)").strip().upper()
condition = st.selectbox("Condition", ["above", "below"])
price = st.number_input("Target Price", min_value=0.0, step=0.1)
username = st.text_input("Your Telegram Username (e.g., @john_doe)").strip()

# Validation
symbol_valid = validate_symbol(symbol) if symbol else None
username_valid = username.startswith("@") if username else None
price_valid = price > 0

if symbol and not symbol_valid:
    st.error("❌ Invalid stock symbol. Please enter a valid NSE stock symbol.")
if username and not username_valid:
    st.error("❌ Please enter a valid Telegram username starting with '@'.")
if price == 0:
    st.error("❌ Price must be greater than 0.")

# Disable submit if validation fails
can_submit = symbol_valid and username_valid and price_valid

if st.button("Add Alert", disabled=not can_submit):
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

# Show active alerts for user
st.header("📋 Your Active Alerts")
username_for_alerts = st.text_input("Enter your Telegram username to view your alerts (e.g., @john_doe)").strip()

if username_for_alerts and username_for_alerts.startswith("@"):
    try:
        response = requests.post(f"{API_BASE}/alerts", json={"username": username_for_alerts})
        if response.status_code == 200:
            alerts = response.json()
            if alerts:
                for alert in alerts:
                    st.write(
                        f"🔔 {alert['symbol']} | {alert['condition']} {alert['price']} | User: {alert['username']}"
                    )
            else:
                st.info("No active alerts for your username.")
        else:
            st.error("⚠️ Failed to fetch your alerts.")
    except Exception as e:
        st.error(f"⚠️ Failed to fetch your alerts: {e}")
elif username_for_alerts:
    st.error("❌ Please enter a valid Telegram username starting with '@'.")
