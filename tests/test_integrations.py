import asyncio
from email.message import EmailMessage

from app.core.config import Settings
from app.models.contact import ContactRequest
from app.repositories.file_store import FileStore
from app.services.ai import AIService
from app.services.contact import ContactService
from app.services.mailer import EmailService


class FakeAIClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, endpoint, headers, json):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": '{"sentiment":"positive","intent":"consultation",'
                                '"summary":"Клиенту нужна консультация.",'
                                '"suggested_reply":"Спасибо, мы свяжемся с вами."}'
                            }
                        }
                    ]
                }

        return Response()


def test_openai_success_path_is_parsed():
    settings = Settings(openai_api_key="test-key", ai_enabled=True)
    service = AIService(settings, http_client_factory=lambda timeout: FakeAIClient())
    result = asyncio.run(service.analyze("Нужна консультация по проекту"))

    assert result.available is True
    assert result.fallback is False
    assert result.sentiment == "positive"
    assert result.intent == "consultation"


def test_smtp_path_sends_two_messages_without_network(tmp_path, monkeypatch):
    settings = Settings(
        data_dir=tmp_path / "data",
        email_backend="smtp",
        smtp_host="smtp.example.com",
        smtp_username="user",
        smtp_password="password",
    )
    store = FileStore(settings.data_dir)
    mailer = EmailService(settings, store)
    sent: list[EmailMessage] = []
    monkeypatch.setattr(mailer, "_send_smtp", lambda message: sent.append(message))

    result = asyncio.run(
        mailer.send_contact_notifications(
            {
                "id": "abc123",
                "name": "Анна",
                "phone": "+79991234567",
                "email": "anna@example.com",
                "comment": "Здравствуйте",
                "ai": {"available": False, "sentiment": None, "intent": None},
            }
        )
    )

    assert result == {"owner": "sent", "user": "sent"}
    assert [message["To"] for message in sent] == ["owner@example.com", "anna@example.com"]


def test_contact_service_persists_ai_and_delivery_result(tmp_path):
    settings = Settings(data_dir=tmp_path / "data", email_backend="console", ai_enabled=False)
    store = FileStore(settings.data_dir)
    service = ContactService(store, AIService(settings), EmailService(settings, store))
    request = ContactRequest(
        name="Анна Смирнова",
        phone="+7 999 123-45-67",
        email="anna@example.com",
        comment="Нужна консультация по интеграции.",
    )

    result = asyncio.run(service.submit(request))
    assert result["status"] == "received"
    assert result["ai"].fallback is True
    assert result["notifications"]["owner"] == "queued"
    assert store.get_metrics()["total_contacts"] == 1

