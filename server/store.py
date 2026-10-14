"""Message persistence and server-side paging for the existing Garmin PRG."""
import math
import textwrap
from fastapi import HTTPException
from .storage import connect, POSTGRES

WATCH_SECTION_LINES = 84
WIDTH = 19

def wrap(answer):
    """Full answer is preserved; the watch receives a selected, bounded slice."""
    output = []
    for paragraph in (answer or "").replace("\r\n", "\n").split("\n"):
        output.extend(
            textwrap.wrap(paragraph, width=WIDTH, break_long_words=True,
                          break_on_hyphens=False) or [""]
        )
    return output

def latest():
    with connect() as db:
        return db.execute(
            "SELECT m.*, s.section_index FROM messages m "
            "JOIN reader_state s ON s.message_id=m.id "
            "WHERE s.id=1"
        ).fetchone()

def insert(question, answer="", status="thinking"):
    with connect() as db:
        last = db.execute(
            "SELECT status FROM messages ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if last and last["status"] == "thinking":
            raise HTTPException(409, "Previous question is still processing")
        new = db.execute(
            "INSERT INTO messages(question,answer,status) VALUES(?,?,?) RETURNING id",
            (question,answer,status)
        ).fetchone()
        mid = new["id"]
        db.execute(
            "UPDATE reader_state SET message_id=?,section_index=0 WHERE id=1",
            (mid,)
        )
    return mid

def recent(limit=20):
    with connect() as db:
        result = db.execute(
            "SELECT id,question,status,substr(answer,1,150) AS preview "
            "FROM messages ORDER BY id DESC LIMIT ?",
            (min(int(limit),50),)
        ).fetchall()
        return [dict(row) for row in result]

def select_message(mid):
    with connect() as db:
        row = db.execute(
            "SELECT id FROM messages WHERE id=?", (mid,)
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Saved message not found")
        db.execute(
            "UPDATE reader_state SET message_id=?,section_index=0 WHERE id=1",
            (mid,)
        )

def count_sections(text):
    return max(1, math.ceil(len(wrap(text)) / WATCH_SECTION_LINES))

def shift_section(delta):
    with connect() as db:
        row = db.execute(
            "SELECT m.answer,s.section_index FROM reader_state s "
            "JOIN messages m ON m.id=s.message_id WHERE s.id=1"
        ).fetchone()
        if row is None:
            raise HTTPException(404, "No saved answer to page through")
        count = count_sections(row["answer"])
        new_index = max(0,min(count-1,int(row["section_index"])+int(delta)))
        db.execute("UPDATE reader_state SET section_index=? WHERE id=1",(new_index,))
        return {"section":new_index+1,"sections":count}

def display_lines(row):
    if not row or row["status"] != "ready":
        return []
    all_lines = wrap(row["answer"])
    count = max(1,math.ceil(len(all_lines)/WATCH_SECTION_LINES))
    idx = max(0,min(int(row["section_index"]),count-1))
    chunk = all_lines[idx*WATCH_SECTION_LINES:(idx+1)*WATCH_SECTION_LINES]
    if count > 1:
        return ["[PART "+str(idx+1)+"/"+str(count)+"]"] + chunk
    return chunk

def metadata(row):
    if row is None:
        return {"section":0,"sections":0}
    count = count_sections(row["answer"]) if row["status"]=="ready" else 1
    idx = max(0,min(int(row["section_index"]),count-1))
    return {"section":idx+1,"sections":count}

def persistent():
    return POSTGRES
