from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
import json
import os
import requests
import yfinance as yf
import atexit

app = Flask(__name__)

ALERTS_FILE = "alerts.json"
USERS_FILE = "telegram_users.json"
BOT_TOKEN = "7675262445:AAEWZbsGgEHcdFa5gW0zWcDOigI0p_S84NY"  # Replace this with your actual bot token

# Helper functions
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
            return json.load(f)
        except json.JSONDecodeError:
            print("❌ Error: Invalid JSON in users file.")
            return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def register_users_from_updates():
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

def send_telegram_alert(chat_id, message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": chat_id, "text": message}
    )

def get_price(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        price = ticker.history(period="1d")["Close"].iloc[-1]
        print(f"✅ Fetched price for {symbol}: ₹{price}")
        return round(price, 2)
    except Exception as e:
        print(f"❌ Error fetching price for {symbol}: {e}")
        return None

def is_valid_stock(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")
        hist = ticker.history(period="1d")
        return not hist.empty
    except:
        return False

# API Endpoints

@app.route("/add-alert", methods=["POST"])
def add_alert():
    data = request.get_json()

    required_fields = ["symbol", "condition", "price", "username"]
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields."}), 400

    if not is_valid_stock(data["symbol"]):
        return jsonify({"error": f"{data['symbol']} is not a valid stock symbol."}), 400

    alert = {
        "symbol": data["symbol"],
        "condition": data["condition"],
        "price": data["price"],
        "username": data["username"]
    }

    alerts = load_alerts()
    alerts.append(alert)
    save_alerts(alerts)
    return jsonify({"message": "Alert saved"}), 200

@app.route("/alerts", methods=["POST"])
def get_alerts():
    data = request.get_json()
    if not data or "username" not in data:
        return jsonify({"error": "Missing 'username' in request body."}), 400

    username = data["username"]

    alerts = load_alerts()
    user_alerts = [alert for alert in alerts if alert["username"] == username]

    return jsonify(user_alerts), 200

@app.route("/check-alerts", methods=["GET"])
def check_alerts():
    username = request.args.get("username")  # optional, for filtering alerts check to a specific user
    result = run_alert_check(username)
    return jsonify(result), 200

# Background job function
def run_alert_check(username=None):
    register_users_from_updates()
    alerts = load_alerts()
    users = load_users()

    triggered = []
    remaining_alerts = []

    for alert in alerts:
        if username and alert["username"] != username:
            remaining_alerts.append(alert)
            continue

        current_price = get_price(alert["symbol"])
        if current_price is None:
            remaining_alerts.append(alert)
            continue

        hit = (alert["condition"] == "above" and current_price > alert["price"]) or \
              (alert["condition"] == "below" and current_price < alert["price"])

        if hit:
            user_chat_id = users.get(alert["username"])
            if user_chat_id:
                message = f"🔔 {alert['symbol']} is {alert['condition']} {alert['price']} (Current: {current_price})"
                send_telegram_alert(user_chat_id, message)
                triggered.append(alert)
        else:
            remaining_alerts.append(alert)

    save_alerts(remaining_alerts)

    if triggered:
        print(f"✅ Triggered & removed {len(triggered)} alert(s): {triggered}")
    else:
        print("ℹ️ No alerts triggered this cycle.")

    return {"triggered": triggered}

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(func=run_alert_check, trigger="interval", minutes=1)
scheduler.start()

# Gracefully shut down the scheduler
atexit.register(lambda: scheduler.shutdown())

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
