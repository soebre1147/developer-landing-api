import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(data_dir: Path, level: str = "INFO") -> None:
    """Configure console logs and a rotating application log file once per process."""

    data_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if getattr(root, "_contact_api_configured", False):
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root.setLevel(numeric_level)

    console = logging.StreamHandler()
    console.setLevel(numeric_level)
    console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    file_handler = RotatingFileHandler(
        data_dir / "app.log",
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root.addHandler(console)
    root.addHandler(file_handler)
    root._contact_api_configured = True


def request_log(message: dict) -> None:
    """Write one structured request event to the dedicated request log."""

    logging.getLogger("contact_api.requests").info(
        json.dumps(message, ensure_ascii=False, separators=(",", ":"))
    )

