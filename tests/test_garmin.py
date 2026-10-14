"""Smoke tests for phone-to-watch API with no OpenAI key or hardware."""
import os
import tempfile
from pathlib import Path

os.environ["DATABASE_PATH"] = str(Path(tempfile.mkdtemp()) / "garmin-test.sqlite")
os.environ.pop("DATABASE_URL",None)
os.environ["GARMIN_SHARED_TOKEN"] = "local-test-token"

from fastapi.testclient import TestClient
from server.main import app

client = TestClient(app)
auth = {"Authorization":"Bearer local-test-token"}
def test_existing_watch_protocol():
    assert client.get("/api/watch", headers=auth).status_code == 200
    assert client.get("/api/watch").status_code == 401

def test_demo_persists_when_client_reopens():
    r = client.post("/api/demo",headers=auth)
    assert r.status_code == 200,r.text
    first = client.get("/api/watch",headers=auth).json()
    second = client.get("/api/watch",headers=auth).json()
    assert first["id"] == second["id"]
    assert any("Connection" in x for x in first["lines"])

def test_long_answer_pages_without_watch_update():
    text = " ".join("testing" for _ in range(1700))
    posted = client.post("/api/relay",headers=auth,json={"text":text})
    assert posted.status_code == 200,posted.text
    first = client.get("/api/watch",headers=auth).json()
    assert first["sections"] > 1,first
    assert len(first["lines"]) <= 85
    advanced = client.post("/api/section",headers=auth,json={"delta":1})
    assert advanced.status_code == 200,advanced.text
    second = client.get("/api/watch",headers=auth).json()
    assert second["section"] == 2
    assert first["lines"] != second["lines"]
    assert client.get("/api/latest",headers=auth).json()["answer"] == text
    assert client.post("/api/section",headers=auth,json={"delta":-1}).json()["section"] == 1

def test_history_and_selection():
    history = client.get("/api/history",headers=auth).json()["messages"]
    assert len(history)>=2
    chosen = client.post("/api/select",headers=auth,json={"id":history[-1]["id"]})
    assert chosen.status_code == 200
    watch = client.get("/api/watch",headers=auth).json()
    assert watch["id"] == history[-1]["id"]
    assert client.post("/api/select",headers=auth,json={"id":999999}).status_code == 404

def test_storage_status_explicit():
    data = client.get("/health").json()
    assert data["persistent"] is False
