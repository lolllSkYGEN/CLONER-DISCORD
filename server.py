from flask import Flask, request, jsonify
import json
import secrets
import string
from datetime import datetime, timedelta
import os

# ===========================
# Конфигурация
# ===========================
KEYS_FILE = "keys.json"
ADMIN_SECRET = os.getenv("ADMIN_SECRET")

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_keys(keys):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

def generate_key():
    parts = [''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)) for _ in range(3)]
    return "CLONE-" + "-".join(parts)

# ===========================
# Flask App
# ===========================
app = Flask(__name__)

@app.route("/")
def index():
    return "Discord Cloner License Server — OK ✅"

@app.route("/create_key", methods=["POST"])
def create_key():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    if data.get("secret") != ADMIN_SECRET:
        return jsonify({"error": "Access denied"}), 403

    days = data.get("days", 30)
    if not isinstance(days, int) or days < 1 or days > 365:
        days = 30

    key = generate_key()
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()

    keys = load_keys()
    keys[key] = {
        "activated": False,
        "hwid": None,
        "expires_at": expires_at,
        "license_days": days,
        "created_at": datetime.now().isoformat()
    }
    save_keys(keys)

    return jsonify({
        "key": key,
        "expires_at": expires_at,
        "license_days": days
    }), 200

@app.route("/activate_key", methods=["POST"])
def activate_key():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    key = data.get("key")
    hwid = data.get("hwid")
    if not key or not hwid:
        return jsonify({"error": "Missing key or HWID"}), 400

    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Invalid key"}), 400

    license_data = keys[key]
    if license_data["activated"]:
        if license_data["hwid"] != hwid:
            return jsonify({"error": "Key already activated on another device"}), 400
    else:
        license_data.update({
            "activated": True,
            "hwid": hwid,
            "activated_at": datetime.now().isoformat()
        })
        save_keys(keys)

    return jsonify({
        "expires_at": license_data["expires_at"],
        "license_days": license_data["license_days"]
    }), 200

@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json()
    key = data.get("key")
    hwid = data.get("hwid")
    if not key or not hwid:
        return jsonify({"valid": False, "error": "Missing key or HWID"}), 400

    keys = load_keys()
    if key not in keys:
        return jsonify({"valid": False, "error": "Invalid key"}), 403

    lic = keys[key]
    now = datetime.now()
    if not lic["activated"]:
        return jsonify({"valid": False, "error": "Key not activated"}), 403
    if lic["hwid"] != hwid:
        return jsonify({"valid": False, "error": "HWID mismatch"}), 403
    if now >= datetime.fromisoformat(lic["expires_at"]):
        return jsonify({"valid": False, "error": "License expired"}), 403

    return jsonify({"valid": True, "expires_at": lic["expires_at"]}), 200

@app.route("/list_keys", methods=["GET"])
def list_keys():
    return jsonify(load_keys()), 200

# ===========================
# Запуск — для Render
# ===========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
