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

if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL не задан в Environment Variables!")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Таблица лицензий
    cur.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            activated BOOLEAN DEFAULT FALSE,
            hwid TEXT,
            expires_at TEXT,
            license_days INTEGER,
            created_at TEXT
        )
    ''')
    # Таблица сессий
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            key TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (key) REFERENCES licenses(key) ON DELETE CASCADE
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
    init_db()
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
        ON CONFLICT (key) DO NOTHING
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
    init_db()
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
    lic = cur.fetchone()
    if not lic:
        cur.close()
        conn.close()
        return jsonify({"error": "Invalid key"}), 400

    if lic["activated"]:
        if lic["hwid"] != hwid:
            cur.close()
            conn.close()
            return jsonify({"error": "Key already activated on another device"}), 400
    else:
        cur.execute('''
            UPDATE licenses SET activated = TRUE, hwid = %s WHERE key = %s
        ''', (hwid, key))
        conn.commit()

    # Создаём сессию
    session_id = secrets.token_urlsafe(32)
    cur.execute('''
        INSERT INTO sessions (session_id, key, created_at)
        VALUES (%s, %s, %s)
    ''', (session_id, key, datetime.now().isoformat()))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"session_id": session_id}), 200

@app.route("/validate_session", methods=["POST"])
def validate_session():
    init_db()
    data = request.get_json()
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"valid": False, "error": "Missing session_id"}), 400

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute('''
        SELECT l.* FROM sessions s
        JOIN licenses l ON s.key = l.key
        WHERE s.session_id = %s
    ''', (session_id,))
    lic = cur.fetchone()
    cur.close()
    conn.close()

    if not lic:
        return jsonify({"valid": False, "error": "Invalid session"}), 403
    if not lic["activated"]:
        return jsonify({"valid": False, "error": "Key not activated"}), 403
    if datetime.now() >= datetime.fromisoformat(lic["expires_at"]):
        return jsonify({"valid": False, "error": "License expired"}), 403

    return jsonify({
        "valid": True,
        "expires_at": lic["expires_at"]
    }), 200

@app.route("/list_keys", methods=["GET"])
def list_keys():
    init_db()
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM licenses")
    keys = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({k["key"]: dict(k) for k in keys}), 200

# ===========================
# Запуск — для Render
# ===========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
