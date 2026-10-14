import os
from .store import connect

def generate(message_id):
    try:
        from openai import OpenAI
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("No API key configured")
        with connect() as db:
            question=db.execute("SELECT question FROM messages WHERE id=?",(message_id,)).fetchone()["question"]
            previous=db.execute("SELECT question,answer FROM messages WHERE status='ready' AND id<? ORDER BY id DESC LIMIT 5",(message_id,)).fetchall()
        items=[{"role":"system","content":"Answer briefly in plain text for a monochrome wristwatch. No Markdown or tables; ideally under 1000 characters."}]
        for m in reversed(previous):
            items.append({"role":"user","content":m["question"]})
            items.append({"role":"assistant","content":m["answer"]})
        items.append({"role":"user","content":question})
        result=OpenAI(timeout=45).responses.create(model=os.getenv("OPENAI_MODEL","gpt-4.1-mini"),input=items,max_output_tokens=450)
        answer=result.output_text.strip() or "No answer generated"
        with connect() as db:
            db.execute("UPDATE messages SET answer=?,status='ready' WHERE id=?",(answer,message_id))
    except Exception as e:
        print("Generation error:",type(e).__name__,str(e)[:200],flush=True)
        with connect() as db:
            db.execute("UPDATE messages SET status='error',error=? WHERE id=?",("OpenAI failed; check key and logs",message_id))
