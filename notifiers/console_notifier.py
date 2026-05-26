import logging

from .base import BaseNotifier

logger = logging.getLogger(__name__)


class ConsoleNotifier(BaseNotifier):
    def send_alert(self, route: dict, offers: list[dict], reasons: list[str]) -> None:
        msg = self.format_message(route, offers, reasons)
        border = "=" * 60
        logger.info("\n%s\n%s\n%s", border, msg, border)
