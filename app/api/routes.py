import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import Settings
from app.models.contact import ContactRequest, ContactResponse, HealthResponse, MetricsResponse
from app.services.contact import ContactService
from app.services.rate_limiter import FileRateLimiter, RateLimitExceeded

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["contact"])


def client_ip(request: Request) -> str:
    settings: Settings = request.app.state.settings
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(request: Request) -> None:
    limiter: FileRateLimiter = request.app.state.rate_limiter
    try:
        limiter.check(client_ip(request))
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limit_exceeded",
                "message": "Слишком много обращений. Повторите попытку позже.",
                "details": {"retry_after_seconds": exc.retry_after},
            },
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Принять обращение с формы обратной связи",
    description=(
        "Валидирует контактные данные, выполняет AI-анализ комментария, "
        "сохраняет обращение и отправляет два уведомления: владельцу сайта и пользователю. "
        "Если AI недоступен, обращение всё равно принимается с fallback-статусом."
    ),
    dependencies=[Depends(enforce_rate_limit)],
)
async def create_contact(request: ContactRequest, http_request: Request) -> ContactResponse:
    service: ContactService = http_request.app.state.contact_service
    return await service.submit(request)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверить состояние сервиса",
)
async def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        checks={
            "storage": "ok",
            "email_backend": settings.email_backend,
            "ai": "configured" if settings.openai_api_key and settings.ai_enabled else "fallback",
        },
    )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Получить статистику обращений",
)
async def metrics(request: Request) -> MetricsResponse:
    data = request.app.state.store.get_metrics()
    return MetricsResponse(**data)

