"""SQLite for development; persistent PostgreSQL when DATABASE_URL is configured."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

POSTGRES = bool(os.environ.get("DATABASE_URL"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", "/tmp/garmin-gpt.db")

class SqlConnection:
    def __init__(self, raw):
        self.raw = raw
    def execute(self, statement, parameters=()):
        if POSTGRES:
            statement = statement.replace("?", "%s")
        return self.raw.execute(statement, parameters)

@contextmanager
def connect():
    if POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        raw = psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
    else:
        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        raw = sqlite3.connect(DATABASE_PATH, timeout=20)
        raw.row_factory = sqlite3.Row
    try:
        yield SqlConnection(raw)
        raw.commit()
    except BaseException:
        raw.rollback()
        raise
    finally:
        raw.close()

def initialize():
    message_pk = "BIGSERIAL PRIMARY KEY" if POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"
    with connect() as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id " + message_pk + ", question TEXT NOT NULL, "
            "answer TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, "
            "error TEXT NOT NULL DEFAULT '')"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS reader_state ("
            "id INTEGER PRIMARY KEY, message_id BIGINT, "
            "section_index INTEGER NOT NULL DEFAULT 0)"
        )
        db.execute(
            "INSERT INTO reader_state(id,message_id,section_index) "
            "VALUES(1,NULL,0) ON CONFLICT(id) DO NOTHING"
        )

initialize()
