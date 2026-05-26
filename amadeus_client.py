import logging
from datetime import date, timedelta
from itertools import product
from typing import Optional

from amadeus import Client, ResponseError

from config import AmadeusConfig

logger = logging.getLogger(__name__)

_client: Optional[Client] = None

_MAX_COMBINATIONS = 50  # cap API calls per route per check cycle
_TOP_N = 3              # number of results to surface per route


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(
            client_id=AmadeusConfig.client_id,
            client_secret=AmadeusConfig.client_secret,
            hostname=AmadeusConfig.environment,
        )
    return _client


def get_top_offers(route: dict, top_n: int = _TOP_N) -> list[dict]:
    """
    Return up to top_n cheapest filtered offers for a route.

    - Single date pair  → one API call, returns top_n offers from that response.
    - Date ranges       → one API call per combination, keeps cheapest-per-combination,
                          then returns the global top_n across all combinations.
    """
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
            "Route '%s' has %d date combinations — capped at %d. "
            "Increase step_days to reduce API calls.",
            route.get("name", f"{route['origin']}→{route['destination']}"),
            len(combinations),
            _MAX_COMBINATIONS,
        )
        combinations = combinations[:_MAX_COMBINATIONS]

    all_offers: list[dict] = []

    if len(combinations) == 1:
        # Single date pair: fetch several offers at once
        dep_date, ret_date = combinations[0]
        all_offers = _fetch_offers(route, dep_date, ret_date, count=top_n * 3)
    else:
        # Multiple date combinations: get cheapest per pair, collect, rank globally
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
    """Fetch and filter flight offers for a single (departure_date, return_date) pair."""
    max_stops = route.get("max_stops")

    params: dict = {
        "originLocationCode": route["origin"],
        "destinationLocationCode": route["destination"],
        "departureDate": dep_date,
        "adults": route.get("adults", 1),
        "currencyCode": route.get("currency", "USD"),
        "max": max(count * 2, 10) if (max_stops is not None and max_stops > 0) else count,
    }

    if ret_date:
        params["returnDate"] = ret_date

    cabin = route.get("cabin", "ECONOMY").upper()
    if cabin != "ECONOMY":
        params["travelClass"] = cabin

    if max_stops == 0:
        params["nonStop"] = "true"

    try:
        response = get_client().shopping.flight_offers_search.get(**params)
    except ResponseError as e:
        logger.error(
            "Amadeus API error for %s→%s on %s: %s",
            route["origin"], route["destination"], dep_date, e,
        )
        return []

    raw_offers = response.data or []
    raw_offers.sort(key=lambda o: float(o["price"]["grandTotal"]))

    if max_stops is not None and max_stops > 0:
        raw_offers = [o for o in raw_offers if _max_stops_in_offer(o) <= max_stops]

    result = []
    for raw in raw_offers[:count]:
        parsed = _parse_offer(raw, dep_date, ret_date)
        if parsed:
            result.append(parsed)

    return result


def _parse_offer(raw: dict, dep_date: str, ret_date: Optional[str]) -> Optional[dict]:
    try:
        price = float(raw["price"]["grandTotal"])
        currency = raw["price"]["currency"]
        carriers = raw.get("validatingAirlineCodes", [])
        carrier = carriers[0] if carriers else "Unknown"
        stops = _max_stops_in_offer(raw)

        first_seg = raw["itineraries"][0]["segments"][0]
        last_seg = raw["itineraries"][0]["segments"][-1]
        departure_time = first_seg["departure"]["at"]
        arrival_time = last_seg["arrival"]["at"]
    except (KeyError, IndexError, ValueError) as e:
        logger.debug("Failed to parse offer: %s", e)
        return None

    return {
        "price": price,
        "currency": currency,
        "carrier": carrier,
        "departure_date": dep_date,
        "return_date": ret_date,
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "stops": stops,
        "offer_id": raw.get("id", ""),
    }


def _max_stops_in_offer(offer: dict) -> int:
    return max(
        len(itin["segments"]) - 1
        for itin in offer.get("itineraries", [{}])
    )


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
