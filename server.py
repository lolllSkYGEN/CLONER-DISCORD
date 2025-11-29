from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import secrets
import string
from datetime import datetime, timedelta
import os

# ===========================
# Конфигурация
# ===========================
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_SECRET = os.getenv("ADMIN_SECRET")

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            activated BOOLEAN DEFAULT FALSE,
            hwid TEXT,
            expires_at TEXT,
            license_days INTEGER,
            created_at TEXT,
            activated_at TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

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
    if not 
        return jsonify({"error": "Invalid JSON"}), 400

    if data.get("secret") != ADMIN_SECRET:
        return jsonify({"error": "Access denied"}), 403

    days = data.get("days", 30)
    if not isinstance(days, int) or days < 1 or days > 365:
        days = 30

    key = "CLONE-" + "-".join(
        [''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4)) for _ in range(3)]
    )
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO licenses (key, activated, hwid, expires_at, license_days, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (key, False, None, expires_at, days, datetime.now().isoformat()))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "key": key,
        "expires_at": expires_at,
        "license_days": days
    }), 200

@app.route("/activate_key", methods=["POST"])
def activate_key():
    data = request.get_json()
    if not 
        return jsonify({"error": "Invalid JSON"}), 400

    key = data.get("key")
    hwid = data.get("hwid")
    if not key or not hwid:
        return jsonify({"error": "Missing key or HWID"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM licenses WHERE key = %s", (key,))
    license_data = cur.fetchone()
    if not license_data:
        cur.close()
        conn.close()
        return jsonify({"error": "Invalid key"}), 400

    if license_data["activated"]:
        if license_data["hwid"] != hwid:
            cur.close()
            conn.close()
            return jsonify({"error": "Key already activated on another device"}), 400
    else:
        cur.execute('''
            UPDATE licenses
            SET activated = TRUE, hwid = %s, activated_at = %s
            WHERE key = %s
        ''', (hwid, datetime.now().isoformat(), key))
        conn.commit()

    cur.execute("SELECT * FROM licenses WHERE key = %s", (key,))
    updated = cur.fetchone()
    cur.close()
    conn.close()

    return jsonify({
        "expires_at": updated["expires_at"],
        "license_days": updated["license_days"]
    }), 200

@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json()
    key = data.get("key")
    hwid = data.get("hwid")
    if not key or not hwid:
        return jsonify({"valid": False, "error": "Missing key or HWID"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM licenses WHERE key = %s", (key,))
    lic = cur.fetchone()
    cur.close()
    conn.close()

    if not lic:
        return jsonify({"valid": False, "error": "Invalid key"}), 403
    if not lic["activated"]:
        return jsonify({"valid": False, "error": "Key not activated"}), 403
    if lic["hwid"] != hwid:
        return jsonify({"valid": False, "error": "HWID mismatch"}), 403
    if datetime.now() >= datetime.fromisoformat(lic["expires_at"]):
        return jsonify({"valid": False, "error": "License expired"}), 403

    return jsonify({"valid": True, "expires_at": lic["expires_at"]}), 200

@app.route("/list_keys", methods=["GET"])
def list_keys():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM licenses")
    keys = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({k["key"]: dict(k) for k in keys}), 200

# ===========================
# Запуск
# ===========================
if __name__ == "__main__":
    init_db()  # Создаём таблицу при старте
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
