# Тестовое для ООО Лаборатория Интернет

Готовое тестовое задание: backend-сервис для лендинга разработчика. Реализован на Python 3.9+ и FastAPI. Сервис проходит полный цикл `запрос → валидация → бизнес-логика → AI-анализ → уведомления → ответ`.

## Возможности

- `POST /api/contact` — форма обратной связи с валидацией имени, телефона, email и комментария.
- Два уведомления: владельцу сайта и копия пользователю.
- AI-функция: анализ тональности, категории обращения, краткого summary и черновика ответа.
- Graceful fallback: без `OPENAI_API_KEY` или при ошибке AI запрос всё равно принимается, а в ответе выставляется `ai.fallback=true`.
- Rate limiting на файловом хранилище: по умолчанию 5 обращений в минуту с одного IP.
- Логирование всех HTTP-запросов и ошибок в `data/app.log`.
- JSONL-хранилище обращений и локальный outbox писем в `data/`.
- `GET /api/health` и `GET /api/metrics`.
- Автоматическая Swagger/OpenAPI-документация: `/docs`, `/redoc`, `/openapi.json`.
- CORS, глобальный обработчик ошибок, Dockerfile и docker-compose.

## Быстрый запуск

Требуется Python 3.9+.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate

python -m pip install -r requirements.txt
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/macOS

uvicorn app.main:app --reload
```

После запуска:

- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

Для реальной отправки писем укажите `EMAIL_BACKEND=smtp` и заполните SMTP-переменные. Для локального запуска используется `EMAIL_BACKEND=console`: два письма сохраняются в `data/emails.jsonl`, поэтому полный сценарий можно проверить без внешних учетных данных.

## Пример запроса

```bash
curl -X POST http://127.0.0.1:8000/api/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Анна Смирнова",
    "phone": "+7 999 123-45-67",
    "email": "anna@example.com",
    "comment": "Нужна интеграция формы обратной связи с AI-анализом обращений."
  }'
```

Пример ответа без настроенного ключа AI:

```json
{
  "id": "4aa0b5e6a7e74c5fb9dce2d1c0f7ea42",
  "status": "received",
  "received_at": "2026-07-29T19:00:00Z",
  "ai": {
    "available": false,
    "provider": "openai",
    "sentiment": null,
    "intent": null,
    "summary": null,
    "suggested_reply": null,
    "fallback": true,
    "error": "AI is disabled or OPENAI_API_KEY is not configured"
  },
  "notifications": {
    "owner": "queued",
    "user": "queued"
  }
}
```

## Переменные окружения

Все настройки находятся в `.env.example`.

| Переменная | Назначение | Значение по умолчанию |
| --- | --- | --- |
| `DATA_DIR` | каталог JSONL/JSON/log-файлов | `data` |
| `CORS_ORIGINS` | origins через запятую | localhost:3000, localhost:5173 |
| `RATE_LIMIT_REQUESTS` | число запросов в окне | `5` |
| `RATE_LIMIT_WINDOW_SECONDS` | размер окна rate limit | `60` |
| `EMAIL_BACKEND` | `console` или `smtp` | `console` |
| `OWNER_EMAIL` | адрес владельца сайта | `owner@example.com` |
| `AI_ENABLED` | включить AI-интеграцию | `true` |
| `OPENAI_API_KEY` | ключ OpenAI | пусто |
| `AI_MODEL` | модель OpenAI-compatible API | `gpt-4o-mini` |
| `TRUST_PROXY_HEADERS` | доверять `X-Forwarded-For` | `false` |

## Архитектура

```text
app/
├── main.py                     # создание FastAPI-приложения, CORS, middleware, handlers
├── api/routes.py               # HTTP-контроллеры и dependency rate limit
├── core/config.py              # типизированные настройки из .env
├── core/logging.py             # приложение + structured request logging
├── models/contact.py           # DTO и строгая валидация Pydantic
├── repositories/file_store.py # JSONL/JSON repository с атомарной записью
└── services/
    ├── contact.py              # orchestration бизнес-сценария
    ├── ai.py                   # OpenAI-compatible API и fallback
    ├── mailer.py               # SMTP или локальный outbox
    └── rate_limiter.py         # sliding window rate limiting
```

Слои разделены по ответственности: route не знает деталей хранения, сервис сценария не знает деталей HTTP, а интеграции AI/email изолированы и легко заменяются в тестах.

## Хранение данных

- `data/contacts.jsonl` — принятые обращения и результат AI/уведомлений.
- `data/emails.jsonl` — сообщения local outbox при `EMAIL_BACKEND=console`.
- `data/rate_limits.json` — timestamps запросов по ключу клиента.
- `data/metrics.json` — агрегированная статистика.
- `data/app.log` — приложение и все запросы с методом, путём, статусом и длительностью.

Для production рекомендуется заменить файловый repository на PostgreSQL/Redis: текущая реализация намеренно соответствует условию задания и не требует базы данных.

## Ошибки и безопасность

- Невалидные данные возвращают `422` с единым форматом `{ "error": { ... } }`.
- Rate limit возвращает `429` и заголовок `Retry-After`.
- Непредвиденные ошибки возвращают `500`, детали исключения не выдаются клиенту, полная ошибка пишется в лог.
- Логин и комментарий ограничены по длине; поля не допускают лишние ключи и управляющие символы.
- Данные в письмах экранируются; ключ AI и SMTP-пароль читаются только из переменных окружения.
- `X-Forwarded-For` учитывается только при явном `TRUST_PROXY_HEADERS=true`.

## Тесты

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

Покрыты happy path, структурированная валидация, rate limiting, health/metrics, AI fallback и разбор JSON-ответа AI.

## Docker

```bash
copy .env.example .env       # Windows
docker compose up --build
```

## Postman и CI/CD

Готовая коллекция находится в `postman/Developer-Landing-API.postman_collection.json`. Она содержит health-check, happy path, metrics и проверку validation error.

В `.github/workflows/ci.yml` настроен GitHub Actions для Python 3.9, 3.11 и 3.12: установка зависимостей, `ruff check` и полный набор pytest-тестов.

Для деплоя на Render добавлен `render.yaml`: сервис запускается через Uvicorn, использует `/api/health` как health check и получает SMTP/AI/CORS-секреты из переменных окружения. Persistent disk монтируется в `/app/data`, чтобы файловое хранилище не терялось при перезапуске.

Публичная ссылка в комплект не включена, так как для её создания нужны учетная запись хостинга и секреты владельца. После подключения репозитория к Render Blueprint деплой выполняется без изменения кода.

## Что сделано с помощью AI

AI использовался как помощник при проектировании слоистой структуры, подготовке черновиков DTO/интеграций и тестовых сценариев. Вручную проверены и доработаны: обработка ошибок FastAPI, поведение fallback, безопасная работа с секретами, атомарная запись файлов, rate limiting, формат OpenAPI и локальный email outbox. Внешний AI API во время проверки не вызывается: тесты работают с fallback и изолированным временным каталогом.
