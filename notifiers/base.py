from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    @abstractmethod
    def send_alert(self, route: dict, offers: list[dict], reasons: list[str]) -> None:
        """Send a price alert. Implementations must not raise — log and swallow errors."""

    @staticmethod
    def format_message(route: dict, offers: list[dict], reasons: list[str]) -> str:
        name = route.get("name", f"{route['origin']} -> {route['destination']}")

        dep_cfg = route.get("departure_date_range")
        ret_cfg = route.get("return_date_range")
        if dep_cfg:
            date_searched = f"{dep_cfg['from']} to {dep_cfg['to']}"
            if ret_cfg:
                date_searched += f"  |  Return searched: {ret_cfg['from']} to {ret_cfg['to']}"
        else:
            dep = route.get("departure_date", "")
            ret = route.get("return_date")
            date_searched = dep + (f"  |  Return: {ret}" if ret else "  (one-way)")

        reason_text = "\n           ".join(f"- {r}" for r in reasons)

        lines = [
            f"Flight Price Alert: {name}",
            f"Route    : {route['origin']} -> {route['destination']}",
            f"Searched : {date_searched}",
            f"Cabin    : {route.get('cabin', 'ECONOMY')}  |  Adults: {route.get('adults', 1)}",
            f"",
            f"Top {len(offers)} Most Competitive Options:",
            f"  {'#':<3}  {'Airline':<20}  {'Price':>10}  {'Departure':>12}  {'Return':>12}",
            f"  {'-'*3}  {'-'*20}  {'-'*10}  {'-'*12}  {'-'*12}",
        ]

        for i, offer in enumerate(offers, 1):
            airline = offer.get("carrier", "Unknown")
            price = f"{offer['currency']} {offer['price']:.2f}"
            dep_date = offer.get("departure_date", "N/A")
            ret_date = offer.get("return_date") or "One-way"
            lines.append(
                f"  #{i:<3} {airline:<20}  {price:>10}  {dep_date:>12}  {ret_date:>12}"
            )

        lines += [
            f"",
            f"Alert    : {reason_text}",
        ]

        return "\n".join(lines)
