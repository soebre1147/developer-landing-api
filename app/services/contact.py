import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.models.contact import ContactRequest
from app.repositories.file_store import FileStore
from app.services.ai import AIService
from app.services.mailer import EmailService

logger = logging.getLogger(__name__)


class ContactService:
    def __init__(self, store: FileStore, ai: AIService, mailer: EmailService):
        self.store = store
        self.ai = ai
        self.mailer = mailer

    async def submit(self, request: ContactRequest) -> dict:
        contact_id = uuid4().hex
        received_at = datetime.now(timezone.utc)
        ai_result = await self.ai.analyze(request.comment)
        record = {
            "id": contact_id,
            "received_at": received_at.isoformat(),
            "name": request.name,
            "phone": request.phone,
            "email": str(request.email),
            "comment": request.comment,
            "ai": ai_result.model_dump(mode="json"),
        }

        notifications = await self.mailer.send_contact_notifications(record)
        record["notifications"] = notifications
        self.store.save_contact(record)
        logger.info("Contact %s accepted; notifications=%s", contact_id, notifications)

        return {
            "id": contact_id,
            "status": "received",
            "received_at": received_at,
            "ai": ai_result,
            "notifications": notifications,
        }

