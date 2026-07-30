import asyncio
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from typing import Any

from app.core.config import Settings
from app.repositories.file_store import FileStore

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    pass


class EmailService:
    def __init__(self, settings: Settings, store: FileStore):
        self.settings = settings
        self.store = store

    async def send_contact_notifications(self, contact: dict[str, Any]) -> dict[str, str]:
        owner_message = self._message(
            recipient=self.settings.owner_email,
            subject=f"Новое обращение с сайта: {contact['name']}",
            body=self._owner_body(contact),
        )
        user_message = self._message(
            recipient=contact["email"],
            subject="Спасибо за обращение",
            body=self._user_body(contact),
        )

        try:
            if self.settings.email_backend == "smtp":
                if not self.settings.smtp_configured:
                    raise NotificationError("SMTP backend is selected but SMTP settings are incomplete")
                await asyncio.to_thread(self._send_smtp, owner_message)
                await asyncio.to_thread(self._send_smtp, user_message)
                return {"owner": "sent", "user": "sent"}

            # Console backend is a durable local outbox: it makes the project runnable without credentials.
            for message in (owner_message, user_message):
                self.store.append_jsonl(
                    self.store.emails_path,
                    {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "backend": "console",
                        "to": message["to"],
                        "subject": message["subject"],
                        "body": message.get_content(),
                    },
                )
            logger.info("Contact notifications written to local outbox for %s", contact["id"])
            return {"owner": "queued", "user": "queued"}
        except Exception:
            logger.exception("Notification delivery failed for contact %s", contact["id"])
            return {"owner": "failed", "user": "failed"}

    def _send_smtp(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as server:
            if self.settings.smtp_use_tls:
                server.starttls()
            if self.settings.smtp_username and self.settings.smtp_password:
                server.login(self.settings.smtp_username, self.settings.smtp_password.get_secret_value())
            server.send_message(message)

    def _message(self, recipient: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self.settings.email_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        return message

    @staticmethod
    def _owner_body(contact: dict[str, Any]) -> str:
        ai = contact["ai"]
        return (
            f"Новое обращение #{contact['id']}\n\n"
            f"Имя: {contact['name']}\nТелефон: {contact['phone']}\nEmail: {contact['email']}\n\n"
            f"Комментарий:\n{contact['comment']}\n\n"
            f"AI-анализ: доступен={ai['available']}, тональность={ai.get('sentiment')}, "
            f"тип={ai.get('intent')}"
        )

    @staticmethod
    def _user_body(contact: dict[str, Any]) -> str:
        name = escape(contact["name"])
        return (
            f"Здравствуйте, {name}!\n\n"
            "Мы получили ваше обращение и свяжемся с вами в ближайшее время.\n"
            f"Номер обращения: {contact['id']}\n\n"
            "Это автоматическое письмо, пожалуйста, не отвечайте на него."
        )
