from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Developer Landing API"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False

    data_dir: Path = Path("data")
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    trust_proxy_headers: bool = False

    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60

    email_backend: str = "console"
    email_from: str = "no-reply@example.com"
    owner_email: str = "owner@example.com"
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[SecretStr] = None
    smtp_use_tls: bool = True

    ai_enabled: bool = True
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o-mini"
    ai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: Optional[SecretStr] = None
    ai_timeout_seconds: float = 12.0

    @field_validator("email_backend")
    @classmethod
    def validate_email_backend(cls, value: str) -> str:
        value = value.lower().strip()
        if value not in {"console", "smtp"}:
            raise ValueError("EMAIL_BACKEND must be either console or smtp")
        return value

    @field_validator("rate_limit_requests", "rate_limit_window_seconds")
    @classmethod
    def validate_positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("rate limit values must be positive")
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_username and self.smtp_password)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
