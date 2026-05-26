import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import flight_client as amadeus_client
import price_tracker
from notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)

_ALERT_COOLDOWN_HOURS = 24


def build_route_id(route: dict) -> str:
    dep_part = _range_key(route.get("departure_date_range"), route.get("departure_date", ""))
    ret_part = _range_key(route.get("return_date_range"), route.get("return_date") or "OW")
    return "-".join([
        route["origin"],
        route["destination"],
        dep_part,
        ret_part,
        route.get("cabin", "ECONOMY"),
        str(route.get("adults", 1)),
    ])


def check_route(route: dict, notifiers: list[BaseNotifier]) -> None:
    route_id = build_route_id(route)
    name = route.get("name", f"{route['origin']}→{route['destination']}")

    logger.info("Checking prices for: %s", name)

    offers = amadeus_client.get_top_offers(route)
    if not offers:
        logger.warning("No offers returned for %s — skipping.", name)
        return

    best = offers[0]
    price = best["price"]
    currency = best["currency"]

    logger.info(
        "  Top %d offers found. Cheapest: %s %.2f (%s, %s stop(s), dep %s)",
        len(offers), currency, price, best["carrier"],
        best.get("stops", 0), best.get("departure_date", ""),
    )

    last = price_tracker.get_last_price(route_id)
    price_tracker.save_price(route_id, best)

    alert_cfg = route.get("alert", {})
    max_price = alert_cfg.get("max_price")
    drop_percent = alert_cfg.get("drop_percent")

    reasons: list[str] = []

    if max_price is not None and price < max_price:
        reasons.append(
            f"cheapest price {currency} {price:.2f} is below your target of {currency} {max_price:.2f}"
        )

    if last is not None and drop_percent is not None:
        prev = last["price"]
        if prev > 0:
            pct_drop = (prev - price) / prev * 100
            if pct_drop >= drop_percent:
                reasons.append(
                    f"price dropped {pct_drop:.1f}% "
                    f"(was {currency} {prev:.2f}, now {currency} {price:.2f})"
                )

    if not reasons:
        logger.info("  No alert conditions met.")
        return

    if not _should_alert(route_id, price):
        logger.info("  Alert conditions met but within cooldown window — skipping notification.")
        return

    logger.info("  Sending alerts: %s", "; ".join(reasons))
    for notifier in notifiers:
        notifier.send_alert(route, offers, reasons)

    price_tracker.log_alert(route_id, price, "; ".join(reasons))


def _should_alert(route_id: str, current_price: float) -> bool:
    last_alert = price_tracker.get_last_alert(route_id)
    if last_alert is None:
        return True
    if current_price < last_alert["price"] * 0.95:
        return True
    sent_at = datetime.fromisoformat(last_alert["sent_at"])
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - sent_at > timedelta(hours=_ALERT_COOLDOWN_HOURS)


def _range_key(range_cfg: Optional[dict], fallback: str) -> str:
    if range_cfg:
        return f"{range_cfg['from']}_{range_cfg['to']}"
    return fallback
