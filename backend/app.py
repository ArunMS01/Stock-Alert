from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os
import requests
import yfinance as yf
import atexit
from datetime import datetime, time
import pytz
import uuid

app = Flask(__name__)

ALERTS_FILE = "alerts.json"
USERS_FILE = "telegram_users.json"
BOT_TOKEN = "7675262445:AAEWZbsGgEHcdFa5gW0zWcDOigI0p_S84NY"  # Replace with your bot token

def is_market_open():
    india_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(india_tz).time()
    market_open = time(9, 15)
    market_close = time(15, 30)
    return market_open <= now <= market_close

def load_alerts():
    if not os.path.exists(ALERTS_FILE):
        return []
    with open(ALERTS_FILE, "r") as f:
        return json.load(f)

def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)

def load_users():
    if not os.path.exists(USERS_FILE):
        print("ℹ️ No users file found. Creating a new one.")
        return {}
    with open(USERS_FILE, "r") as f:
        try:
            data = f.read()
            print(f"Users File Content: {data}")
            return json.loads(data)
        except json.JSONDecodeError:
            print("❌ Error: The users file is empty or contains invalid JSON. Returning empty dictionary.")
            return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def sync_users_from_telegram():
    print("🔄 Syncing users from Telegram on startup...")
    try:
        updates = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates").json()
        if not updates.get("ok"):
            print("❌ Failed to get updates:", updates)
            return
        registered_users = load_users()
        new_users = 0
        for update in updates.get("result", []):
            msg = update.get("message", {}) or update.get("edited_message", {})
            user = msg.get("from", {})
            username = user.get("username")
            chat_id = user.get("id")
            if username:
                username = "@" + username
                if username not in registered_users:
                    registered_users[username] = chat_id
                    new_users += 1
                    print(f"✅ Registered: {username} → Chat ID: {chat_id}")
        if new_users:
            save_users(registered_users)
            print(f"💾 Saved {new_users} new user(s) to {USERS_FILE}")
        else:
            print("ℹ️ No new users to register.")
    except Exception as e:
        print(f"❌ Exception during user sync: {e}")

def send_telegram_alert(chat_id, message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": chat_id, "text": message}
    )

def get_price(symbol):
    if not is_market_open():
        print(f"ℹ️ Market closed — skipping price fetch for {symbol}")
        return None

    if not symbol.endswith(".NS"):
        symbol = symbol + ".NS"

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        if hist.empty:
            print(f"❌ No price data for {symbol}")
            return None
        price = hist["Close"].iloc[-1]
        print(f"✅ Fetched price for {symbol}: ₹{price}")
        return round(price, 2)
    except Exception as e:
        print(f"❌ Error fetching price for {symbol}: {e}")
        return None

# === New endpoints for user signup/login ===

@app.route("/get-users", methods=["GET"])
def get_users():
    users = load_users()
    return jsonify(list(users.keys()))

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    if not username or not username.startswith("@"):
        return jsonify({"error": "Invalid username"}), 400

    users = load_users()
    if username in users:
        return jsonify({"error": "Username already registered"}), 400

    # Initially save with None chat_id until user messages the bot
    users[username] = None
    save_users(users)
    return jsonify({"message": "User registered successfully", "username": username}), 200

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    print("Login request data:", data)  # debug log
    username = data.get("username")
    if not username or not username.startswith("@"):
        return jsonify({"error": "Invalid username"}), 400

    users = load_users()
    print("Users loaded for login:", users)  # debug log
    if username in users:
        return jsonify({"message": "Login successful", "username": username}), 200
    else:
        return jsonify({"error": "User not registered"}), 401

@app.route("/add-alert", methods=["POST"])
def add_alert():
    data = request.get_json()
    symbol = data["symbol"].upper()
    if not symbol.endswith(".NS"):
        symbol = symbol + ".NS"

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1d")
    if hist.empty:
        return jsonify({"error": "Invalid NSE symbol or no data available"}), 400

    alert = {
        "id": str(uuid.uuid4()),  # unique id for each alert
        "symbol": symbol,
        "condition": data["condition"],
        "price": data["price"],
        "username": data["username"]
    }
    alerts = load_alerts()
    alerts.append(alert)
    save_alerts(alerts)
    return jsonify({"message": "Alert saved", "alert_id": alert["id"]}), 200

@app.route("/alerts", methods=["POST"])
def get_alerts():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    alerts = load_alerts()
    if username:
        alerts = [alert for alert in alerts if alert["username"] == username]
    return jsonify(alerts)

@app.route("/delete-alert", methods=["POST"])
def delete_alert():
    data = request.get_json()
    alert_id = data.get("id")
    if not alert_id:
        return jsonify({"error": "Alert ID is required"}), 400

    alerts = load_alerts()
    new_alerts = [alert for alert in alerts if alert["id"] != alert_id]

    if len(new_alerts) == len(alerts):
        return jsonify({"message": "No matching alert found to delete."}), 404

    save_alerts(new_alerts)
    return jsonify({"message": "Alert deleted successfully."}), 200

# === Manual check endpoint for testing ===

@app.route("/check-alerts", methods=["GET"])
def check_alerts():
    result = run_alert_check()
    return jsonify(result), 200

def run_alert_check():
    sync_users_from_telegram()
    alerts = load_alerts()
    users = load_users()
    triggered = []
    remaining_alerts = []

    for alert in alerts:
        current_price = get_price(alert["symbol"])

        if current_price is None:
            print(f"ℹ️ Skipping alert for {alert['symbol']} because price unavailable.")
            remaining_alerts.append(alert)
            continue

        hit = (alert["condition"] == "above" and current_price > alert["price"]) or \
              (alert["condition"] == "below" and current_price < alert["price"])

        if hit:
            username = alert["username"]
            chat_id = users.get(username)
            if chat_id:
                message = f"🔔 {alert['symbol']} is {alert['condition']} {alert['price']} (Current: {current_price})"
                send_telegram_alert(chat_id, message)
                triggered.append(alert)
            # Do NOT add alert to remaining list — delete after triggered
        else:
            remaining_alerts.append(alert)

    save_alerts(remaining_alerts)

    removed_count = len(alerts) - len(remaining_alerts)
    print(f"🗑️ Removed {removed_count} triggered alert(s).")

    if triggered:
        print(f"✅ Triggered {len(triggered)} alert(s): {triggered}")
    else:
        print("ℹ️ No alerts triggered this cycle.")

    return {"triggered": triggered}

# === Scheduler to check alerts every minute ===

scheduler = BackgroundScheduler()
scheduler.add_job(func=run_alert_check, trigger="interval", minutes=5)
scheduler.start()

atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    # Sync users once on startup
    sync_users_from_telegram()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
