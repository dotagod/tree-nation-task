from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.store import store

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    store.clear()
    yield
    store.clear()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def test_first_visit_creates_customer():
    ts = _utc_now().isoformat().replace("+00:00", "Z")
    response = client.post(
        "/api/visits",
        json={"customer_id": "cust-1", "timestamp": ts},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["customer_id"] == "cust-1"
    assert data["total_visits"] == 1
    assert data["visits_toward_next_tree"] == 1
    assert data["trees_planted"] == 0
    assert data["tree_just_planted"] is False


def test_nth_visit_plants_tree(monkeypatch):
    monkeypatch.setattr(settings, "visits_per_tree", 5)
    base = _utc_now()

    for i in range(4):
        ts = (base + timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
        response = client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts})
        assert response.status_code == 201
        assert response.json()["tree_just_planted"] is False

    ts = (base + timedelta(minutes=4)).isoformat().replace("+00:00", "Z")
    response = client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts})

    assert response.status_code == 201
    data = response.json()
    assert data["total_visits"] == 5
    assert data["visits_toward_next_tree"] == 0
    assert data["trees_planted"] == 1
    assert data["tree_just_planted"] is True


def test_progress_resets_after_tree_planted(monkeypatch):
    monkeypatch.setattr(settings, "visits_per_tree", 3)
    base = _utc_now()

    for i in range(3):
        ts = (base + timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
        client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts})

    ts = (base + timedelta(minutes=3)).isoformat().replace("+00:00", "Z")
    response = client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts})

    data = response.json()
    assert data["total_visits"] == 4
    assert data["trees_planted"] == 1
    assert data["visits_toward_next_tree"] == 1


def test_config_change_plants_tree_when_progress_exceeds_threshold():
    base = _utc_now()

    for i in range(4):
        ts = (base + timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
        client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts})

    response = client.put(
        "/api/customers/cust-1/config",
        json={"visits_per_tree": 3},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["trees_planted"] == 1
    assert data["visits_toward_next_tree"] == 1


def test_hourly_aggregation():
    base = _utc_now().replace(minute=0, second=0, microsecond=0) - timedelta(minutes=30)
    ts = base.isoformat().replace("+00:00", "Z")

    for _ in range(2):
        client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts})

    response = client.get("/api/stats/hourly?hours=24")
    assert response.status_code == 200

    hour_prefix = base.strftime("%Y-%m-%dT%H")
    buckets = response.json()["buckets"]
    target = next(b for b in buckets if b["hour"].startswith(hour_prefix))
    assert target["visits"] == 2
    assert len(target["customers"]) == 1
    assert target["customers"][0]["customer_id"] == "cust-1"
    assert target["customers"][0]["visits"] == 2


def test_hourly_different_hours():
    now = _utc_now().replace(minute=0, second=0, microsecond=0)
    ts1 = (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    ts2 = now.isoformat().replace("+00:00", "Z")

    client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts1})
    client.post("/api/visits", json={"customer_id": "cust-2", "timestamp": ts2})

    response = client.get("/api/stats/hourly?hours=24")
    buckets = {b["hour"][:13]: b["visits"] for b in response.json()["buckets"]}

    assert buckets[(now - timedelta(hours=1)).strftime("%Y-%m-%dT%H")] == 1
    assert buckets[now.strftime("%Y-%m-%dT%H")] == 1


def test_list_customers():
    ts = _utc_now().isoformat().replace("+00:00", "Z")
    client.post("/api/visits", json={"customer_id": "cust-b", "timestamp": ts})
    client.post("/api/visits", json={"customer_id": "cust-a", "timestamp": ts})

    response = client.get("/api/customers")
    assert response.status_code == 200

    customers = response.json()["customers"]
    assert [customer["customer_id"] for customer in customers] == ["cust-a", "cust-b"]
    assert customers[0]["total_visits"] == 1
    assert customers[0]["trees_planted"] == 0


def test_get_customer():
    ts = _utc_now().isoformat().replace("+00:00", "Z")
    client.post("/api/visits", json={"customer_id": "cust-42", "timestamp": ts})

    response = client.get("/api/customers/cust-42")
    assert response.status_code == 200
    data = response.json()
    assert data["total_visits"] == 1
    assert data["visits_toward_next_tree"] == 1
    assert data["last_connection_at"] is not None


def test_get_customer_not_found():
    response = client.get("/api/customers/unknown")
    assert response.status_code == 404


def test_tree_events_audit_trail(monkeypatch):
    monkeypatch.setattr(settings, "visits_per_tree", 2)
    base = _utc_now()

    for i in range(2):
        ts = (base + timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
        client.post("/api/visits", json={"customer_id": "cust-1", "timestamp": ts})

    response = client.get("/api/trees/events")
    assert response.status_code == 200

    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["customer_id"] == "cust-1"
    assert events[0]["visits_per_tree"] == 2


def test_api_validation_empty_customer_id():
    response = client.post("/api/visits", json={"customer_id": ""})
    assert response.status_code == 422


def test_get_config():
    response = client.get("/api/config")
    assert response.status_code == 200
    assert "default_visits_per_tree" in response.json()


def test_set_customer_config():
    response = client.put(
        "/api/customers/cust-1/config",
        json={"visits_per_tree": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "cust-1"
    assert data["visits_per_tree"] == 3
    assert data["total_visits"] == 0


def test_per_customer_visits_per_tree(monkeypatch):
    monkeypatch.setattr(settings, "visits_per_tree", 5)

    client.put("/api/customers/cust-a/config", json={"visits_per_tree": 3})
    client.put("/api/customers/cust-b/config", json={"visits_per_tree": 10})

    base = _utc_now() - timedelta(minutes=20)
    for i in range(3):
        ts = (base + timedelta(minutes=i)).isoformat().replace("+00:00", "Z")
        response = client.post("/api/visits", json={"customer_id": "cust-a", "timestamp": ts})
        assert response.status_code == 201

    assert response.json()["trees_planted"] == 1
    assert response.json()["tree_just_planted"] is True

    for i in range(3):
        ts = (base + timedelta(minutes=i + 10)).isoformat().replace("+00:00", "Z")
        response = client.post("/api/visits", json={"customer_id": "cust-b", "timestamp": ts})
        assert response.status_code == 201

    assert response.json()["trees_planted"] == 0
    assert response.json()["tree_just_planted"] is False


def test_get_customer_includes_visits_per_tree():
    client.put("/api/customers/cust-42/config", json={"visits_per_tree": 7})
    ts = _utc_now().isoformat().replace("+00:00", "Z")
    client.post("/api/visits", json={"customer_id": "cust-42", "timestamp": ts})

    response = client.get("/api/customers/cust-42")
    assert response.status_code == 200
    assert response.json()["visits_per_tree"] == 7


def test_dashboard_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
