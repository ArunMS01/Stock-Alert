import streamlit as st
import requests
import yfinance as yf

API_BASE = "https://stock-alert-odjb.onrender.com"
TELEGRAM_BOT_USERNAME = "Order_ms_bot"
BOT_LINK = f"https://t.me/{TELEGRAM_BOT_USERNAME}"

st.title("📈 Stock Alert System")
st.info("""
**Step 1:** Please add the bot in your Telegram.  
**Step 2:** Fill the form according to your requirement about which stock alert you need for what price.  
**Step 3:** By your Telegram username, you can see your alerts.  
**⚠️ Always add `@` before your Telegram username.**  
**⚠️ The stock symbol should be in CAPSLOCK.**
""")

# 📢 Telegram Registration Info
st.markdown("### 💬 Telegram Setup")
st.info(f"""
Before you receive alerts, **you must send a message** to our Telegram bot so we can get your Chat ID.
👉 [Click here to message the bot]({BOT_LINK})
""")

# 📌 Validate stock symbol using yfinance
def validate_symbol(symbol):
    if not symbol:
        return False
    try:
        ticker = yf.Ticker(symbol + ".NS")
        hist = ticker.history(period="1d")
        return not hist.empty
    except:
        return False

# 📊 New Alert Form
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

# 📋 Fetch User Alerts
st.header("📋 Your Active Alerts")

username_for_alerts = st.text_input("Enter your Telegram username to view your alerts (e.g., @john_doe)").strip()

if username_for_alerts and not username_for_alerts.startswith("@"):
    st.error("❌ Please enter a valid Telegram username starting with '@'.")
elif username_for_alerts:
    if st.button("Fetch My Alerts"):
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
