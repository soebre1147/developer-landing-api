from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ContactRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=2, max_length=100, examples=["Анна Смирнова"])
    phone: str = Field(min_length=5, max_length=30, examples=["+7 999 123-45-67"])
    email: EmailStr = Field(examples=["anna@example.com"])
    comment: str = Field(
        min_length=5,
        max_length=5_000,
        examples=["Нужна интеграция формы обратной связи с AI-анализом обращений."],
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if any(ord(char) < 32 for char in value):
            raise ValueError("name contains control characters")
        if not any(char.isalpha() for char in value):
            raise ValueError("name must contain letters")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        allowed = set("0123456789+()- ")
        if any(char not in allowed for char in value):
            raise ValueError("phone contains unsupported characters")
        if sum(char.isdigit() for char in value) < 5:
            raise ValueError("phone must contain at least five digits")
        return value

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str) -> str:
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("comment contains control characters")
        return value


class AIAnalysis(BaseModel):
    available: bool
    provider: str
    sentiment: Literal["positive", "neutral", "negative"] | None = None
    intent: str | None = None
    summary: str | None = None
    suggested_reply: str | None = None
    fallback: bool = False
    error: str | None = None


class DeliveryStatus(BaseModel):
    owner: Literal["sent", "queued", "failed"]
    user: Literal["sent", "queued", "failed"]


class ContactResponse(BaseModel):
    id: str
    status: Literal["received"]
    received_at: datetime
    ai: AIAnalysis
    notifications: DeliveryStatus


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str
    checks: dict[str, str]


class MetricsResponse(BaseModel):
    total_contacts: int
    successful_notifications: int
    failed_notifications: int
    ai_available: int
    ai_fallback: int
    updated_at: datetime | None = None
