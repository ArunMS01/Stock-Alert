from flask import Flask, request, jsonify
import json
import os
import requests
import yfinance as yf

app = Flask(__name__)

ALERTS_FILE = "alerts.json"
USERS_FILE = "telegram_users.json"
BOT_TOKEN = "7675262445:AAEWZbsGgEHcdFa5gW0zWcDOigI0p_S84NY"  # Replace with your actual bot token

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
            data = f.read()  # Read raw data
            print(f"Users File Content: {data}")  # Print raw data for debugging
            return json.loads(data)  # Attempt to parse JSON
        except json.JSONDecodeError:
            print("❌ Error: The users file is empty or contains invalid JSON. Returning empty dictionary.")
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
    else:
        print("ℹ️ No new users to register.")

def send_telegram_alert(chat_id, message):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": chat_id, "text": message}
    )

def get_price(symbol):
    try:
        ticker = yf.Ticker(symbol + ".NS")  # Append '.NS' for NSE stocks
        price = ticker.history(period="1d")["Close"].iloc[-1]
        print(f"✅ Fetched price for {symbol}: ₹{price}")
        return round(price, 2)
    except Exception as e:
        print(f"❌ Error fetching price for {symbol}: {e}")
        return 0.0

# API endpoints
@app.route("/add-alert", methods=["POST"])
def add_alert():
    data = request.get_json()
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

@app.route("/alerts", methods=["GET"])
def get_alerts():
    return jsonify(load_alerts())

@app.route("/check-alerts", methods=["GET"])
def check_alerts():
    register_users_from_updates()
    alerts = load_alerts()
    users = load_users()

    triggered = []
    for alert in alerts:
        current_price = get_price(alert["symbol"])
        hit = (alert["condition"] == "above" and current_price > alert["price"]) or \
              (alert["condition"] == "below" and current_price < alert["price"])

        if hit:
            username = alert["username"]
            chat_id = users.get(username)
            if chat_id:
                message = f"🔔 {alert['symbol']} is {alert['condition']} {alert['price']} (Current: {current_price})"
                send_telegram_alert(chat_id, message)
                triggered.append(alert)

    return jsonify({"triggered": triggered}), 200

if __name__ == "__main__":
    app.run(debug=True)
