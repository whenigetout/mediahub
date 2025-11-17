# db.py
import sqlite3
from pathlib import Path
import json

DB_PATH = Path("jav_metadata.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_conn():
    # timeout helps if a brief lock occurs
    return sqlite3.connect(str(DB_PATH), timeout=30, isolation_level=None, check_same_thread=False)

def init_db():
    conn = get_conn()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS jav (
        code TEXT PRIMARY KEY,
        metadata_json TEXT,
        url TEXT,
        status TEXT
    )
    """)
    conn.commit()
    conn.close()

def upsert(code: str, metadata: dict, url: str = "", status: str = "Success"):
    conn = get_conn()
    j = json.dumps(metadata, ensure_ascii=False)
    # use a simple upsert
    conn.execute("""
    INSERT INTO jav(code, metadata_json, url, status) VALUES (?, ?, ?, ?)
    ON CONFLICT(code) DO UPDATE SET
      metadata_json=excluded.metadata_json,
      url=excluded.url,
      status=excluded.status
    """, (code, j, url, status))
    conn.commit()
    conn.close()
