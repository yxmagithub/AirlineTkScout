import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GmailConfig
from .base import BaseNotifier

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


class EmailNotifier(BaseNotifier):
    def send_alert(self, route: dict, offers: list[dict], reasons: list[str]) -> None:
        if not GmailConfig.enabled:
            logger.debug("Email notifier skipped: GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set.")
            return

        best = offers[0]
        subject = (
            f"Flight Alert: {route['origin']}→{route['destination']} "
            f"@ {best['currency']} {best['price']:.2f}"
        )
        body = self.format_message(route, offers, reasons)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = GmailConfig.address
        msg["To"] = GmailConfig.recipient
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(_to_html(body), "html"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(GmailConfig.address, GmailConfig.app_password)
                server.sendmail(GmailConfig.address, GmailConfig.recipient, msg.as_string())
            logger.info("Email alert sent to %s", GmailConfig.recipient)
        except Exception as e:
            logger.error("Failed to send email alert: %s", e)


def _to_html(plain: str) -> str:
    return "<pre style='font-family:monospace;font-size:14px'>" + plain + "</pre>"
