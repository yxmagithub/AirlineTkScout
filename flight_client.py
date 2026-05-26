import logging
from datetime import date, timedelta
from itertools import product
from typing import Optional

import requests

from config import SerpApiConfig

logger = logging.getLogger(__name__)

_SERPAPI_URL = "https://serpapi.com/search"
_MAX_COMBINATIONS = 50
_TOP_N = 3

# SerpAPI travel_class values
_CABIN_MAP = {
    "ECONOMY": 1,
    "PREMIUM_ECONOMY": 2,
    "BUSINESS": 3,
    "FIRST": 4,
}

# SerpAPI stops values: max_stops in routes.yaml → stops param
# 0=any, 1=nonstop only, 2=1 stop or fewer, 3=2 stops or fewer
_STOPS_MAP = {0: 1, 1: 2, 2: 3}


def get_top_offers(route: dict, top_n: int = _TOP_N) -> list[dict]:
    """Return up to top_n cheapest Google Flights offers for a route."""
    dep_dates = _departure_dates(route)
    ret_dates = _return_dates(route)

    combinations = list(product(dep_dates, ret_dates))

    trip_len = route.get("trip_length_days")
    if trip_len and ret_dates != [None]:
        combinations = [
            (dep, ret) for dep, ret in combinations
            if ret is not None
            and trip_len.get("min", 0) <= _trip_days(dep, ret) <= trip_len.get("max", 9999)
            and _trip_days(dep, ret) > 0
        ]

    if len(combinations) > _MAX_COMBINATIONS:
        logger.warning(
            "Route '%s' has %d date combinations — capped at %d. Increase step_days.",
            route.get("name", f"{route['origin']}→{route['destination']}"),
            len(combinations),
            _MAX_COMBINATIONS,
        )
        combinations = combinations[:_MAX_COMBINATIONS]

    all_offers: list[dict] = []

    if len(combinations) == 1:
        dep_date, ret_date = combinations[0]
        all_offers = _fetch_offers(route, dep_date, ret_date, count=top_n * 3)
    else:
        for dep_date, ret_date in combinations:
            offers = _fetch_offers(route, dep_date, ret_date, count=1)
            if offers:
                all_offers.append(offers[0])

    all_offers.sort(key=lambda o: o["price"])
    return all_offers[:top_n]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_offers(
    route: dict,
    dep_date: str,
    ret_date: Optional[str],
    count: int = 5,
) -> list[dict]:
    max_stops = route.get("max_stops")
    currency = route.get("currency", "USD")

    params: dict = {
        "engine": "google_flights",
        "departure_id": route["origin"],
        "arrival_id": route["destination"],
        "outbound_date": dep_date,
        "adults": route.get("adults", 1),
        "currency": currency,
        "travel_class": _CABIN_MAP.get(route.get("cabin", "ECONOMY").upper(), 1),
        "hl": "en",
        "api_key": SerpApiConfig.api_key,
    }

    if ret_date:
        params["return_date"] = ret_date
    else:
        params["type"] = 2  # one-way

    if max_stops is not None and max_stops in _STOPS_MAP:
        params["stops"] = _STOPS_MAP[max_stops]

    try:
        resp = requests.get(_SERPAPI_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error(
            "SerpAPI request failed for %s→%s on %s: %s",
            route["origin"], route["destination"], dep_date, e,
        )
        return []

    if "error" in data:
        logger.error("SerpAPI error: %s", data["error"])
        return []

    raw_offers = data.get("best_flights", []) + data.get("other_flights", [])
    raw_offers.sort(key=lambda f: f.get("price", float("inf")))

    results = []
    for raw in raw_offers[:count]:
        parsed = _parse_offer(raw, dep_date, ret_date, currency)
        if parsed:
            results.append(parsed)

    return results


def _parse_offer(
    raw: dict,
    dep_date: str,
    ret_date: Optional[str],
    currency: str,
) -> Optional[dict]:
    try:
        price = float(raw["price"])
        flights = raw.get("flights", [])
        if not flights:
            return None

        first_seg = flights[0]
        last_seg = flights[-1]

        airline = first_seg.get("airline", "Unknown")
        dep_time = first_seg.get("departure_airport", {}).get("time", "")
        arr_time = last_seg.get("arrival_airport", {}).get("time", "")
        stops = len(flights) - 1
        duration = raw.get("total_duration", 0)

    except (KeyError, TypeError, ValueError) as e:
        logger.debug("Failed to parse SerpAPI offer: %s", e)
        return None

    return {
        "price": price,
        "currency": currency,
        "carrier": airline,
        "departure_date": dep_date,
        "return_date": ret_date,
        "departure_time": dep_time,
        "arrival_time": arr_time,
        "stops": stops,
        "duration_minutes": duration,
    }


def _departure_dates(route: dict) -> list[str]:
    r = route.get("departure_date_range")
    if r:
        return _date_range(r["from"], r["to"], r.get("step_days", 1))
    return [route["departure_date"]]


def _return_dates(route: dict) -> list[Optional[str]]:
    r = route.get("return_date_range")
    if r:
        return _date_range(r["from"], r["to"], r.get("step_days", 1))
    return [route.get("return_date") or None]


def _date_range(from_str: str, to_str: str, step: int = 1) -> list[str]:
    start = date.fromisoformat(from_str)
    end = date.fromisoformat(to_str)
    result, current = [], start
    while current <= end:
        result.append(current.isoformat())
        current += timedelta(days=step)
    return result


def _trip_days(dep: str, ret: Optional[str]) -> int:
    if ret is None:
        return 0
    return (date.fromisoformat(ret) - date.fromisoformat(dep)).days
