import streamlit as st
import requests

API_BASE = "https://stock-alert-odjb.onrender.com"
TELEGRAM_BOT_USERNAME = "Order_ms_bot"  # ⬅️ Replace this
BOT_LINK = f"https://t.me/{TELEGRAM_BOT_USERNAME}"

st.title("📈 Stock Alert System")

# 🚨 Telegram Registration Help
st.markdown("### 💬 Telegram Setup")
st.info(f"""
Before you receive alerts, **you must send a message** to our Telegram bot so we can get your Chat ID.
👉 [Click here to message the bot]({BOT_LINK})
""")

# Alert Form
st.header("Set a New Price Alert")
with st.form("alert_form"):
    symbol = st.text_input("Stock Symbol (e.g., RELIANCE,TATAMOTORS)")
    condition = st.selectbox("Condition", ["above", "below"])
    price = st.number_input("Target Price", min_value=0.0, step=0.1)
    username = st.text_input("Your Telegram Username (e.g., @john_doe)")
    submitted = st.form_submit_button("Add Alert")

    if submitted:
        if not username.startswith("@"):
            st.error("❌ Please enter a valid Telegram username starting with '@'.")
        else:
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

# Show Active Alerts for the user only
st.header("📋 Your Active Alerts")
username_for_alerts = st.text_input("Enter your Telegram username to view your alerts (e.g., @john_doe)")
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
