import logging
from datetime import date, timedelta
from itertools import product
from typing import Optional

from amadeus import Client, ResponseError

from config import AmadeusConfig

logger = logging.getLogger(__name__)

_client: Optional[Client] = None

_MAX_COMBINATIONS = 50  # cap API calls per route per check cycle


def get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(
            client_id=AmadeusConfig.client_id,
            client_secret=AmadeusConfig.client_secret,
            hostname=AmadeusConfig.environment,
        )
    return _client


def get_cheapest_offer(route: dict) -> Optional[dict]:
    """Return the cheapest filtered offer across all date combinations for a route."""
    dep_dates = _departure_dates(route)
    ret_dates = _return_dates(route)

    combinations = list(product(dep_dates, ret_dates))

    # Filter by trip length constraint
    trip_len = route.get("trip_length_days")
    if trip_len and ret_dates != [None]:
        combinations = [
            (dep, ret) for dep, ret in combinations
            if ret is not None and _trip_days(dep, ret) is not None
            and trip_len.get("min", 0) <= _trip_days(dep, ret) <= trip_len.get("max", 9999)
        ]

    if len(combinations) > _MAX_COMBINATIONS:
        logger.warning(
            "Route '%s' has %d date combinations — capped at %d to limit API calls. "
            "Increase step_days to reduce calls.",
            route.get("name", f"{route['origin']}→{route['destination']}"),
            len(combinations),
            _MAX_COMBINATIONS,
        )
        combinations = combinations[:_MAX_COMBINATIONS]

    best: Optional[dict] = None
    for dep_date, ret_date in combinations:
        offer = _fetch_offer(route, dep_date, ret_date)
        if offer and (best is None or offer["price"] < best["price"]):
            best = offer

    return best


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_offer(route: dict, dep_date: str, ret_date: Optional[str]) -> Optional[dict]:
    """Fetch cheapest offer for a single (departure_date, return_date) pair."""
    max_stops = route.get("max_stops")

    params: dict = {
        "originLocationCode": route["origin"],
        "destinationLocationCode": route["destination"],
        "departureDate": dep_date,
        "adults": route.get("adults", 1),
        "currencyCode": route.get("currency", "USD"),
        "max": 10 if max_stops is not None and max_stops > 0 else 5,
    }

    if ret_date:
        params["returnDate"] = ret_date

    cabin = route.get("cabin", "ECONOMY").upper()
    if cabin != "ECONOMY":
        params["travelClass"] = cabin

    # Non-stop filter: the API supports nonStop=true for 0 stops
    if max_stops == 0:
        params["nonStop"] = "true"

    try:
        response = get_client().shopping.flight_offers_search.get(**params)
    except ResponseError as e:
        logger.error(
            "Amadeus API error for %s→%s on %s: %s",
            route["origin"], route["destination"], dep_date, e,
        )
        return None

    offers = response.data
    if not offers:
        return None

    # Sort by price ascending; the API does this but be explicit
    offers.sort(key=lambda o: float(o["price"]["grandTotal"]))

    # Apply max_stops post-filter for values > 0 (API only has nonStop flag)
    if max_stops is not None and max_stops > 0:
        offers = [o for o in offers if _max_stops_in_offer(o) <= max_stops]

    if not offers:
        logger.debug(
            "No offers matching max_stops=%s for %s→%s on %s",
            max_stops, route["origin"], route["destination"], dep_date,
        )
        return None

    best = offers[0]
    price = float(best["price"]["grandTotal"])
    currency = best["price"]["currency"]
    carriers = best.get("validatingAirlineCodes", [])
    carrier = carriers[0] if carriers else "Unknown"
    stops = _max_stops_in_offer(best)

    try:
        first_seg = best["itineraries"][0]["segments"][0]
        last_seg = best["itineraries"][0]["segments"][-1]
        departure_time = first_seg["departure"]["at"]
        arrival_time = last_seg["arrival"]["at"]
    except (KeyError, IndexError):
        departure_time = arrival_time = ""

    return {
        "price": price,
        "currency": currency,
        "carrier": carrier,
        "departure_date": dep_date,
        "return_date": ret_date,
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "stops": stops,
        "offer_id": best["id"],
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


def _trip_days(dep: str, ret: Optional[str]) -> Optional[int]:
    if ret is None:
        return None
    return (date.fromisoformat(ret) - date.fromisoformat(dep)).days
