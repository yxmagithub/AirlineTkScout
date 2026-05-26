import logging

import requests

from config import TelegramConfig
from .base import BaseNotifier

logger = logging.getLogger(__name__)

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier(BaseNotifier):
    def send_alert(self, route: dict, offers: list[dict], reasons: list[str]) -> None:
        if not TelegramConfig.enabled:
            logger.debug("Telegram notifier skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
            return

        text = self.format_message(route, offers, reasons)
        url = _API_URL.format(token=TelegramConfig.bot_token)
        payload = {
            "chat_id": TelegramConfig.chat_id,
            "text": f"<pre>{text}</pre>",
            "parse_mode": "HTML",
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            logger.info("Telegram alert sent to chat %s", TelegramConfig.chat_id)
        except requests.RequestException as e:
            logger.error("Failed to send Telegram alert: %s", e)
