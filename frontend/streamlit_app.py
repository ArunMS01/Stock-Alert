import streamlit as st

# Set config — must be first Streamlit command
st.set_page_config(page_title="📈 Stock Alert System", page_icon="📊")

import requests
import yfinance as yf
import streamlit.components.v1 as components

API_BASE = "https://stock-alert-odjb.onrender.com"

TELEGRAM_BOT_USERNAME = "Order_ms_bot"
BOT_LINK = f"https://t.me/{TELEGRAM_BOT_USERNAME}"

# Inject JS+CSS to auto-open sidebar and show a slide hint
components.html(
    """
    <style>
    .slide-hint {
        position: fixed;
        top: 12px;
        left: 12px;
        background: #fffa;
        color: #333;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 13px;
        z-index: 1000;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    </style>

    <div class="slide-hint">👉 Slide or tap top-left menu</div>

    <script>
    window.addEventListener('load', function() {
        const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.style.transform = 'translateX(0%)';
        }
        const expander = window.parent.document.querySelector('[data-testid="stSidebar"] button[aria-label="Close sidebar"]');
        if (expander) {
            expander.click();
        }
    });
    </script>
    """,
    height=0
)

def signup():
    st.sidebar.header("🆕 Signup")
    st.sidebar.markdown(f"👉 Please message our Telegram bot first: [Click here to open bot]({BOT_LINK})")

    telegram_username = st.sidebar.text_input("Your Telegram Username (start with @)", key="signup_telegram").strip()

    if st.sidebar.button("Create Account"):
        if not telegram_username.startswith("@"):
            st.sidebar.error("Telegram username must start with '@'")
            return False

        try:
            resp = requests.post(f"{API_BASE}/signup", json={
                "username": telegram_username,
                "telegram_username": telegram_username
            })
            if resp.status_code == 200:
                st.sidebar.success("✅ Account created! Please login below.")
                st.session_state.signup_telegram = ""
                return True
            else:
                err = resp.json().get("error", "Unknown error")
                st.sidebar.error(f"Signup failed: {err}")
                return False
        except Exception as e:
            st.sidebar.error(f"Signup error: {e}")
            return False
    return False

def login(users_dict):
    st.sidebar.header("🔐 Login")

    def do_login():
        telegram_username = st.session_state.login_telegram.strip()
        if telegram_username in users_dict:
            st.session_state.logged_in_user = telegram_username
            st.sidebar.success(f"Logged in as {telegram_username}")
            st.session_state.show_login = False
        else:
            st.sidebar.error("User not found. Please signup.")

    st.sidebar.text_input(
        "Enter your Telegram Username (start with @)",
        key="login_telegram",
        on_change=do_login
    )

def fetch_users():
    try:
        resp = requests.get(f"{API_BASE}/get-users")
        if resp.status_code == 200:
            return resp.json()
        else:
            st.sidebar.error("Failed to load users from backend.")
            return {}
    except Exception as e:
        st.sidebar.error(f"Error fetching users: {e}")
        return {}

def validate_symbol(symbol):
    if not symbol:
        return False
    try:
        ticker = yf.Ticker(symbol + '.NS')
        hist = ticker.history(period="1d")
        return not hist.empty
    except:
        return False

# Session state flags
if "show_login" not in st.session_state:
    st.session_state.show_login = True
if "refresh_alerts" not in st.session_state:
    st.session_state.refresh_alerts = False

# Logout
if st.session_state.get("logged_in_user") and st.sidebar.button("Logout"):
    st.session_state.pop("logged_in_user")
    st.session_state.show_login = True
    st.session_state.refresh_alerts = False
    st.query_params.clear()
    st.stop()

# If not logged in — show signup/login and a welcome message
if st.session_state.show_login or "logged_in_user" not in st.session_state:
    users = fetch_users()
    signup()
    login(users)

    st.markdown("""
        <div style="text-align: center; margin-top: 120px;">
            <h2>📈 Welcome to Stock Alert System 📊</h2>
            <p style="font-size:16px;">Use the sidebar to signup or login and start setting your stock alerts.</p>
        </div>
    """, unsafe_allow_html=True)

    st.stop()

username = st.session_state.logged_in_user

st.title("📈 Stock Alert System")
st.markdown(f"""
Welcome **{username}**!  
Make sure you have messaged our bot [here]({BOT_LINK}) to receive alerts.
""")

tab1, tab2, tab3 = st.tabs(["➕ Set Single Alert", "📋 My Alerts", "➕📊 Bulk Add Alerts"])

with tab1:
    st.subheader("Set a New Price Alert")

    symbol = st.text_input("Stock Symbol (e.g., RELIANCE, TATAMOTORS)").strip().upper()
    condition = st.selectbox("Condition", ["above", "below"])
    price = st.number_input("Target Price", min_value=0.0, step=0.1)

    if st.button("Add Alert"):
        if not validate_symbol(symbol):
            st.error("❌ Invalid stock symbol.")
        elif price <= 0:
            st.error("❌ Price must be greater than 0.")
        else:
            try:
                response = requests.post(f"{API_BASE}/add-alert", json={
                    "symbol": symbol,
                    "condition": condition,
                    "price": price,
                    "username": username
                })
                if response.status_code == 200:
                    st.success("✅ Alert added successfully!")
                    st.session_state.refresh_alerts = True
                else:
                    st.error(f"❌ {response.json().get('error', 'Failed to add alert.')}")
            except Exception as e:
                st.error(f"⚠️ Connection error: {e}")

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

    if "alerts_cache" not in st.session_state:
        st.session_state.alerts_cache = fetch_alerts(username)

    if st.button("🔄 Refresh Alerts"):
        st.session_state.alerts_cache = fetch_alerts(username)

    alerts = st.session_state.alerts_cache

    if alerts:
        for alert in alerts:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"🔔 {alert['symbol']} | {alert['condition']} {alert['price']}")
            with col2:
                delete_key = f"delete-{alert['id']}"
                if st.button("🗑️", key=delete_key):
                    try:
                        del_response = requests.post(f"{API_BASE}/delete-alert", json={"id": alert["id"]})
                        if del_response.status_code == 200:
                            st.success(f"✅ Deleted alert for {alert['symbol']}")
                            st.session_state.alerts_cache = fetch_alerts(username)
                        else:
                            st.error("❌ Failed to delete alert.")
                    except Exception as e:
                        st.error(f"⚠️ Delete error: {e}")
    else:
        st.info("No active alerts found.")

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
            st.session_state.bulk_alerts[idx]["symbol"] = st.text_input(
                f"Symbol {idx+1}", value=alert["symbol"], key=f"symbol_{idx}").strip().upper()
        with col2:
            st.session_state.bulk_alerts[idx]["condition"] = st.selectbox(
                f"Condition {idx+1}", ["above", "below"],
                index=0 if alert["condition"] == "above" else 1, key=f"condition_{idx}")
        with col3:
            st.session_state.bulk_alerts[idx]["price"] = st.number_input(
                f"Price {idx+1}", min_value=0.0, step=0.1,
                value=alert["price"], key=f"price_{idx}")

    if st.button("🚀 Submit All Alerts"):
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
            st.session_state.refresh_alerts = True
