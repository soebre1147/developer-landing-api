from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture()
def app(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path / "data",
        email_backend="console",
        ai_enabled=True,
        rate_limit_requests=5,
        rate_limit_window_seconds=60,
    )
    return create_app(settings)


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def payload():
    return {
        "name": "Анна Смирнова",
        "phone": "+7 999 123-45-67",
        "email": "anna@example.com",
        "comment": "Нужна интеграция формы обратной связи с AI-анализом обращений.",
    }

