import os,sqlite3,textwrap
from contextlib import contextmanager
from pathlib import Path
DB=os.getenv("DATABASE_PATH","/tmp/garmin-gpt.db")
@contextmanager
def connect():
    Path(DB).parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB,timeout=20)
    con.row_factory=sqlite3.Row
    try:
        yield con
        con.commit()
    finally: con.close()
with connect() as c:
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT DEFAULT '', status TEXT, error TEXT DEFAULT '')")
def latest():
    with connect() as c:
        return c.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 1").fetchone()
def insert(question,answer="",status="thinking"):
    from fastapi import HTTPException
    with connect() as c:
        r=c.execute("SELECT status FROM messages ORDER BY id DESC LIMIT 1").fetchone()
        if r and r["status"]=="thinking": raise HTTPException(409,"Previous request still processing")
        return c.execute("INSERT INTO messages(question,answer,status) VALUES(?,?,?)",(question,answer,status)).lastrowid
def wrap(answer):
    result=[]
    for p in answer.replace("\r\n","\n").split("\n"):
        result.extend(textwrap.wrap(p,width=19,break_long_words=True,break_on_hyphens=False) or [""])
    return result[:99]+["[rest on phone]"] if len(result)>100 else result
