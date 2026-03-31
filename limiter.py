"""
IP-based rate limiter using SQLite.
- Max 2 requests per IP address
- Resets after 24h
- IPs stored as SHA-256 hash (privacy)
"""
import sqlite3
import hashlib
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "rate_limit.db"
MAX_REQUESTS = 10
WINDOW_SECONDS = 24 * 60 * 60  # 24 hours


def _hash_ip(ip: str) -> str:
    """Hash IP before storing — never store raw IPs."""
    return hashlib.sha256(ip.encode()).hexdigest()


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rate_limit (
            ip_hash   TEXT PRIMARY KEY,
            count     INTEGER NOT NULL DEFAULT 0,
            first_use REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


def get_real_ip(request) -> str:
    """
    Extract real IP — check proxy headers first.
    X-Forwarded-For can contain multiple IPs: take the first (original client).
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # "client_ip, proxy1, proxy2" → take first
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.headers.get("X-Real-IP") or request.client.host
    return ip


def check_and_increment(ip: str) -> dict:
    """
    Check if IP is allowed and increment counter.
    Returns: { allowed: bool, count: int, remaining: int, reset_in_seconds: int }
    """
    ip_hash = _hash_ip(ip)
    now = time.time()

    with _get_db() as conn:
        row = conn.execute(
            "SELECT count, first_use FROM rate_limit WHERE ip_hash = ?",
            (ip_hash,)
        ).fetchone()

        if row is None:
            # First time — create entry
            conn.execute(
                "INSERT INTO rate_limit (ip_hash, count, first_use) VALUES (?, 1, ?)",
                (ip_hash, now)
            )
            return {"allowed": True, "count": 1, "remaining": MAX_REQUESTS - 1, "reset_in": WINDOW_SECONDS}

        count, first_use = row
        elapsed = now - first_use

        # Window expired → reset
        if elapsed > WINDOW_SECONDS:
            conn.execute(
                "UPDATE rate_limit SET count = 1, first_use = ? WHERE ip_hash = ?",
                (now, ip_hash)
            )
            return {"allowed": True, "count": 1, "remaining": MAX_REQUESTS - 1, "reset_in": WINDOW_SECONDS}

        # Within window
        if count >= MAX_REQUESTS:
            reset_in = int(WINDOW_SECONDS - elapsed)
            return {"allowed": False, "count": count, "remaining": 0, "reset_in": reset_in}

        # Increment
        new_count = count + 1
        conn.execute(
            "UPDATE rate_limit SET count = ? WHERE ip_hash = ?",
            (new_count, ip_hash)
        )
        return {"allowed": True, "count": new_count, "remaining": MAX_REQUESTS - new_count, "reset_in": int(WINDOW_SECONDS - elapsed)}
