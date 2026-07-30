from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, request_log
from app.repositories.file_store import FileStore
from app.services.ai import AIService
from app.services.contact import ContactService
from app.services.mailer import EmailService
from app.services.rate_limiter import FileRateLimiter

logger = logging.getLogger(__name__)


def error_response(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    configure_logging(settings.data_dir, settings.log_level)
    store = FileStore(settings.data_dir)
    ai = AIService(settings)
    mailer = EmailService(settings, store)
    contact_service = ContactService(store, ai, mailer)
    rate_limiter = FileRateLimiter(
        store,
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("Starting %s %s", settings.app_name, settings.app_version)
        yield
        logger.info("Stopping %s", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API сервиса формы обратной связи с AI-анализом обращений.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.state.settings = settings
    app.state.store = store
    app.state.contact_service = contact_service
    app.state.rate_limiter = rate_limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = time.perf_counter()
        response = None
        error_name = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error_name = type(exc).__name__
            raise
        finally:
            request_log(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code if response else 500,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                    "error": error_name,
                }
            )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_response("validation_error", "Проверьте входные данные.", jsonable_encoder(exc.errors())),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and {"code", "message"}.issubset(detail):
            content = {"error": detail}
        else:
            content = error_response(f"http_{exc.status_code}", str(detail), None)
        return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception for %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_response("internal_error", "Внутренняя ошибка сервера.", None),
        )

    app.include_router(router)
    return app


app = create_app()
