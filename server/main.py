import os,hmac,hashlib,textwrap
from pathlib import Path
from fastapi import FastAPI,BackgroundTasks,Header,HTTPException,Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from .store import latest,insert,wrap
from .ai import generate
app=FastAPI(title="Garmin GPT",docs_url=None,redoc_url=None)
app.mount("/static",StaticFiles(directory=Path(__file__).parent/"static"),name="static")
TOKEN=os.getenv("GARMIN_SHARED_TOKEN","")
def auth(value):
    if not TOKEN: raise HTTPException(503,"Pairing token not configured")
    if not value or not hmac.compare_digest(value,"Bearer "+TOKEN):
        raise HTTPException(401,"Invalid pairing token")
class Prompt(BaseModel):
    question:str=Field(min_length=1,max_length=800)
class SharedAnswer(BaseModel):
    text:str=Field(min_length=1,max_length=120000)
@app.get("/")
def homepage(): return FileResponse(Path(__file__).parent/"static"/"index.html")
@app.get("/health")
def health(): return {"ok":True,"paired":bool(TOKEN),"openai_configured":bool(os.getenv("OPENAI_API_KEY"))}
@app.post("/api/demo")
def demo(authorization:str|None=Header(None)):
    auth(authorization)
    id=insert("Garmin connection test","Connection successful! This message came from your Render server to your Garmin Instinct 3 Solar. Press DOWN to scroll, UP to go back, and GPS to refresh. Send a question from your iPhone.","ready")
    return {"id":id,"status":"ready"}
@app.post("/api/prompt",status_code=202)
def prompt(data:Prompt,tasks:BackgroundTasks,authorization:str|None=Header(None)):
    auth(authorization)
    question=data.question.strip()
    if not question: raise HTTPException(422,"Question must not be blank")
    id=insert(question)
    tasks.add_task(generate,id)
    return {"id":id,"status":"thinking"}
@app.post("/api/relay")
def relay(data:SharedAnswer,authorization:str|None=Header(None)):
    auth(authorization)
    answer=data.text.strip()
    if not answer: raise HTTPException(422,"No text supplied")
    id=insert("Copied from ChatGPT",answer,"ready")
    return {"id":id,"status":"ready"}
@app.get("/api/latest")
def get_latest(authorization:str|None=Header(None)):
    auth(authorization)
    r=latest()
    if not r: return {"id":0,"status":"empty","question":"","answer":"","lines":[]}
    a=r["answer"] if r["status"]=="ready" else (r["error"] if r["status"]=="error" else "")
    return {"id":r["id"],"status":r["status"],"question":r["question"],"answer":a,"lines":wrap(a)}
@app.get("/api/watch")
def watch(authorization:str|None=Header(None)):
    auth(authorization)
    r=latest()
    if not r: return {"id":0,"status":"empty","lines":[]}
    a=r["answer"] if r["status"]=="ready" else (r["error"] if r["status"]=="error" else "")
    return {"id":r["id"],"status":r["status"],"lines":wrap(a)}

@app.get("/api/v2/watch")
def watch_paged(offset:int=Query(0,ge=0,le=100000),limit:int=Query(42,ge=1,le=42),authorization:str|None=Header(None)):
    auth(authorization)
    row=latest()
    if row is None:
        return {"id":0,"status":"empty","tag":"","total":0,"offset":0,"lines":[]}
    state=row["status"]
    if state=="thinking":
        return {"id":row["id"],"status":"thinking","tag":"","total":0,"offset":0,"lines":[]}
    answer=row["answer"] if state=="ready" else row["error"]
    paragraphs=answer.replace("\r\n","\n").split("\n")
    all_lines=[]
    for part in paragraphs:
        all_lines.extend(textwrap.wrap(part,width=19,break_long_words=True,break_on_hyphens=False) or [""])
    total=len(all_lines)
    actual_offset=offset if offset < total else 0
    return {"id":row["id"],"status":state,
            "tag":hashlib.sha256(answer.encode("utf-8")).hexdigest()[:16],
            "total":total,"offset":actual_offset,
            "lines":all_lines[actual_offset:actual_offset+limit]}
