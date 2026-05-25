from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    @abstractmethod
    def send_alert(self, route: dict, offer: dict, reasons: list[str]) -> None:
        """Send a price alert. Implementations must not raise — log and swallow errors."""

    @staticmethod
    def format_message(route: dict, offer: dict, reasons: list[str]) -> str:
        name = route.get("name", f"{route['origin']} → {route['destination']}")
        price = offer["price"]
        currency = offer["currency"]
        carrier = offer["carrier"]
        stops = offer.get("stops", 0)
        stop_label = "non-stop" if stops == 0 else f"{stops} stop(s)"

        # Best dates found (may differ from route config if date ranges are used)
        dep_date = offer.get("departure_date") or route.get("departure_date", "")
        ret_date = offer.get("return_date") or route.get("return_date")
        date_str = dep_date + (f" → {ret_date}" if ret_date else " (one-way)")

        # Show date range in config if applicable
        dep_cfg = route.get("departure_date_range")
        ret_cfg = route.get("return_date_range")
        if dep_cfg:
            searched = f"  (searched {dep_cfg['from']} – {dep_cfg['to']}"
            if ret_cfg:
                searched += f", return {ret_cfg['from']} – {ret_cfg['to']}"
            searched += ")"
        else:
            searched = ""

        reason_text = "\n  - ".join(reasons)

        lines = [
            f"Flight Price Alert: {name}",
            f"Route  : {route['origin']} → {route['destination']}",
            f"Dates  : {date_str}{searched}",
            f"Cabin  : {route.get('cabin', 'ECONOMY')}  |  Adults: {route.get('adults', 1)}",
            f"Price  : {currency} {price:.2f}  ({carrier}, {stop_label})",
            f"Reason : - {reason_text}",
        ]
        return "\n".join(lines)
