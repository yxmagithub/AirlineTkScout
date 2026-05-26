import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required env var: {key}")
    return val


class SerpApiConfig:
    api_key: str = _require("SERPAPI_KEY")


class GmailConfig:
    enabled: bool = bool(os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"))
    address: str = os.getenv("GMAIL_ADDRESS", "")
    app_password: str = os.getenv("GMAIL_APP_PASSWORD", "")
    recipient: str = os.getenv("ALERT_EMAIL_TO", os.getenv("GMAIL_ADDRESS", ""))


class TelegramConfig:
    enabled: bool = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")


def load_routes() -> dict:
    routes_file = BASE_DIR / "routes.yaml"
    if not routes_file.exists():
        raise FileNotFoundError(f"routes.yaml not found at {routes_file}")
    with open(routes_file, "r") as f:
        return yaml.safe_load(f)
