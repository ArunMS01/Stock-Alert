
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from telegram import Bot

app = Flask(__name__)
CORS(app)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = Bot(token=TOKEN)

USERS_FILE = 'telegram_users.json'
ALERTS_FILE = 'alerts.json'

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

@app.route('/register', methods=['POST'])
def register_user():
    user_id = request.json.get('user_id')
    users = load_json(USERS_FILE)
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)
        return jsonify({"message": "User registered successfully"}), 201
    return jsonify({"message": "User already exists"}), 200

@app.route('/alerts', methods=['GET', 'POST'])
def manage_alerts():
    if request.method == 'POST':
        alert = request.json.get('message')
        alerts = load_json(ALERTS_FILE)
        alerts.append({"message": alert})
        save_json(ALERTS_FILE, alerts)
        send_alert_to_all(alert)
        return jsonify({"message": "Alert sent"}), 201
    else:
        alerts = load_json(ALERTS_FILE)
        return jsonify(alerts), 200

def send_alert_to_all(message):
    users = load_json(USERS_FILE)
    for user_id in users:
        try:
            bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send to {user_id}: {e}")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
