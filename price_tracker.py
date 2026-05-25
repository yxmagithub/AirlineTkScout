import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "prices.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id        TEXT    NOT NULL,
                price           REAL    NOT NULL,
                currency        TEXT    NOT NULL,
                carrier         TEXT,
                departure_date  TEXT,
                return_date     TEXT,
                stops           INTEGER,
                checked_at      TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id    TEXT    NOT NULL,
                price       REAL    NOT NULL,
                alert_type  TEXT    NOT NULL,
                sent_at     TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ph_route ON price_history(route_id, checked_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_al_route ON alert_log(route_id, sent_at)")


def save_price(route_id: str, offer: dict) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO price_history
               (route_id, price, currency, carrier, departure_date, return_date, stops, checked_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                route_id,
                offer["price"],
                offer["currency"],
                offer.get("carrier"),
                offer.get("departure_date"),
                offer.get("return_date"),
                offer.get("stops"),
                _now(),
            ),
        )


def get_last_price(route_id: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """SELECT price, currency, carrier, departure_date, return_date, stops, checked_at
               FROM price_history WHERE route_id=? ORDER BY checked_at DESC LIMIT 1""",
            (route_id,),
        ).fetchone()
    if row:
        return {
            "price": row[0], "currency": row[1], "carrier": row[2],
            "departure_date": row[3], "return_date": row[4],
            "stops": row[5], "checked_at": row[6],
        }
    return None


def get_last_alert(route_id: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT price, sent_at FROM alert_log WHERE route_id=? ORDER BY sent_at DESC LIMIT 1",
            (route_id,),
        ).fetchone()
    return {"price": row[0], "sent_at": row[1]} if row else None


def log_alert(route_id: str, price: float, alert_type: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO alert_log (route_id, price, alert_type, sent_at) VALUES (?,?,?,?)",
            (route_id, price, alert_type, _now()),
        )


def get_price_history(route_id: str, limit: int = 30) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT price, currency, carrier, departure_date, return_date, stops, checked_at
               FROM price_history WHERE route_id=? ORDER BY checked_at DESC LIMIT ?""",
            (route_id, limit),
        ).fetchall()
    return [
        {"price": r[0], "currency": r[1], "carrier": r[2],
         "departure_date": r[3], "return_date": r[4], "stops": r[5], "checked_at": r[6]}
        for r in rows
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
