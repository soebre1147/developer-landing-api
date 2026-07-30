from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_contact_full_flow(client: TestClient, payload: dict, app):
    response = client.post("/api/contact", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert body["ai"]["fallback"] is True
    assert body["notifications"] == {"owner": "queued", "user": "queued"}
    assert len(body["id"]) == 32
    assert (app.state.store.data_dir / "contacts.jsonl").exists()
    assert len((app.state.store.data_dir / "emails.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_validation_error_is_structured(client: TestClient, payload: dict):
    payload["email"] = "not-an-email"
    payload["phone"] = "abc"

    response = client.post("/api/contact", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["details"]


def test_rate_limit_returns_retry_after(tmp_path: Path, payload: dict):
    settings = Settings(
        data_dir=tmp_path / "data",
        email_backend="console",
        ai_enabled=False,
        rate_limit_requests=1,
        rate_limit_window_seconds=60,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.post("/api/contact", json=payload).status_code == 201
        response = client.post("/api/contact", json=payload)

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1
    assert response.json()["error"]["code"] == "rate_limit_exceeded"


def test_health_and_metrics(client: TestClient, payload: dict):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/metrics").json()["total_contacts"] == 0
    client.post("/api/contact", json=payload)
    metrics = client.get("/api/metrics").json()
    assert metrics["total_contacts"] == 1
    assert metrics["successful_notifications"] == 1

