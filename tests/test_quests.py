import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine

client = TestClient(app)

def setup_module():
    # fresh in-memory SQLite per test run
    Base.metadata.create_all(bind=engine)

def teardown_module():
    Base.metadata.drop_all(bind=engine)


def test_create_and_complete():
    # 1 create
    r = client.post("/quests/", json={"description": "Read 10 pages", "reward_xp": 50})
    assert r.status_code == 201, r.text
    quest_id = r.json()["id"]

    # 2 complete
    r2 = client.patch(f"/quests/{quest_id}/complete")
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "completed"
