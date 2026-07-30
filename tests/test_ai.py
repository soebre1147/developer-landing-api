import asyncio

from app.core.config import Settings
from app.services.ai import AIService


def test_ai_fallback_without_key():
    result = asyncio.run(AIService(Settings(openai_api_key=None, ai_enabled=True)).analyze("Нужна консультация"))
    assert result.available is False
    assert result.fallback is True
    assert result.error


def test_ai_response_json_parser():
    parsed = AIService._parse_json("```json\n{\"sentiment\": \"positive\", \"intent\": \"pricing\"}\n```")
    assert parsed["sentiment"] == "positive"
    assert parsed["intent"] == "pricing"
