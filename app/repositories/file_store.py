import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FileStore:
    """Small JSONL/JSON repository suitable for the assignment and local deployment."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.contacts_path = data_dir / "contacts.jsonl"
        self.emails_path = data_dir / "emails.jsonl"
        self.rate_limits_path = data_dir / "rate_limits.json"
        self.metrics_path = data_dir / "metrics.json"
        self._lock = threading.RLock()

    def append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        with self._lock, path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def save_contact(self, record: dict[str, Any]) -> None:
        with self._lock:
            self.append_jsonl(self.contacts_path, record)
            metrics = self.get_metrics()
            metrics["total_contacts"] += 1
            if record.get("notifications", {}).get("owner") in {"sent", "queued"} and record.get(
                "notifications", {}
            ).get("user") in {"sent", "queued"}:
                metrics["successful_notifications"] += 1
            else:
                metrics["failed_notifications"] += 1
            if record.get("ai", {}).get("available"):
                metrics["ai_available"] += 1
            if record.get("ai", {}).get("fallback"):
                metrics["ai_fallback"] += 1
            metrics["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write_json_atomic(self.metrics_path, metrics)

    def get_metrics(self) -> dict[str, Any]:
        with self._lock:
            if not self.metrics_path.exists():
                return {
                    "total_contacts": 0,
                    "successful_notifications": 0,
                    "failed_notifications": 0,
                    "ai_available": 0,
                    "ai_fallback": 0,
                    "updated_at": None,
                }
            try:
                return json.loads(self.metrics_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return {
                    "total_contacts": 0,
                    "successful_notifications": 0,
                    "failed_notifications": 0,
                    "ai_available": 0,
                    "ai_fallback": 0,
                    "updated_at": None,
                }

    def load_rate_limits(self) -> dict[str, list[float]]:
        with self._lock:
            if not self.rate_limits_path.exists():
                return {}
            try:
                data = json.loads(self.rate_limits_path.read_text(encoding="utf-8"))
                return {key: [float(value) for value in values] for key, values in data.items()}
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                return {}

    def save_rate_limits(self, data: dict[str, list[float]]) -> None:
        with self._lock:
            self._write_json_atomic(self.rate_limits_path, data)

    @staticmethod
    def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

