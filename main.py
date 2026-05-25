#!/usr/bin/env python3
"""
Flight Ticket Price Monitor
Usage:
    python main.py            # run monitor loop (uses check_interval_minutes from routes.yaml)
    python main.py --once     # check prices once and exit
"""

import argparse
import logging
import sys
import time

import config as cfg
import price_tracker
from monitor import check_route
from notifiers import ConsoleNotifier, EmailNotifier, TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def build_notifiers() -> list:
    notifiers = [ConsoleNotifier()]
    if cfg.GmailConfig.enabled:
        notifiers.append(EmailNotifier())
        logger.info("Email notifier enabled (%s → %s)", cfg.GmailConfig.address, cfg.GmailConfig.recipient)
    if cfg.TelegramConfig.enabled:
        notifiers.append(TelegramNotifier())
        logger.info("Telegram notifier enabled (chat %s)", cfg.TelegramConfig.chat_id)
    return notifiers


def run_once(routes: list, notifiers: list) -> None:
    for route in routes:
        try:
            check_route(route, notifiers)
        except Exception as e:
            logger.error("Unexpected error checking route %s: %s", route.get("name", "?"), e, exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight ticket price monitor")
    parser.add_argument("--once", action="store_true", help="Check prices once and exit")
    args = parser.parse_args()

    price_tracker.init_db()

    routes_cfg = cfg.load_routes()
    routes = routes_cfg.get("routes", [])
    interval_minutes = routes_cfg.get("check_interval_minutes", 60)

    if not routes:
        logger.error("No routes defined in routes.yaml. Exiting.")
        sys.exit(1)

    notifiers = build_notifiers()

    logger.info("Flight Price Monitor started. Monitoring %d route(s).", len(routes))
    for r in routes:
        logger.info("  - %s", r.get("name", f"{r['origin']}→{r['destination']}"))

    if args.once:
        run_once(routes, notifiers)
        return

    logger.info("Check interval: every %d minute(s). Press Ctrl+C to stop.", interval_minutes)
    while True:
        run_once(routes, notifiers)
        logger.info("Next check in %d minute(s).", interval_minutes)
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()
