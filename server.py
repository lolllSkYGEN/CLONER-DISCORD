from flask import Flask, request, jsonify
import json
import secrets
import string
from datetime import datetime, timedelta
import os

KEYS_FILE = "keys.json"
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "supersecret123")

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=2)

def generate_key():
    parts = [''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)) for _ in range(3)]
    return "SHARK-" + "-".join(parts)

app = Flask(__name__)

@app.route("/")
def alive():
    return "Discord Cloner License Server — OK ✅"

@app.route("/create_key", methods=["POST"])
def create_key():
    data = request.get_json()
    if data.get("secret") != ADMIN_SECRET:
        return jsonify({"error": "Access denied"}), 403

    days = data.get("days", 30)
    key = generate_key()
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()

    keys = load_keys()
    keys[key] = {
        "activated": False,
        "hwid": None,
        "expires_at": expires_at,
        "license_days": days
    }
    save_keys(keys)

    return jsonify({
        "key": key,
        "expires_at": expires_at,
        "license_days": days
    })

@app.route("/activate_key", methods=["POST"])
def activate_key():
    data = request.get_json()
    key = data.get("key")
    hwid = data.get("hwid")
    if not key or not hwid:
        return jsonify({"error": "Missing key or HWID"}), 400

    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Invalid key"}), 400

    license_data = keys[key]
    if license_data["activated"] and license_data["hwid"] != hwid:
        return jsonify({"error": "Key already used on another device"}), 400

    if not license_data["activated"]:
        license_data.update({
            "activated": True,
            "hwid": hwid,
            "activated_at": datetime.now().isoformat()
        })
        save_keys(keys)

    return jsonify({
        "expires_at": license_data["expires_at"],
        "license_days": license_data["license_days"]
    })

@app.route("/list_keys", methods=["GET"])
def list_keys():
    return jsonify(load_keys())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
