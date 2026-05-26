from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    @abstractmethod
    def send_alert(self, route: dict, offers: list[dict], reasons: list[str]) -> None:
        """Send a price alert. Implementations must not raise — log and swallow errors."""

    @staticmethod
    def format_message(route: dict, offers: list[dict], reasons: list[str]) -> str:
        name = route.get("name", f"{route['origin']} → {route['destination']}")

        dep_cfg = route.get("departure_date_range")
        ret_cfg = route.get("return_date_range")
        if dep_cfg:
            date_searched = f"searched {dep_cfg['from']} – {dep_cfg['to']}"
            if ret_cfg:
                date_searched += f", return {ret_cfg['from']} – {ret_cfg['to']}"
        else:
            dep = route.get("departure_date", "")
            ret = route.get("return_date")
            date_searched = dep + (f" → {ret}" if ret else " (one-way)")

        reason_text = "\n         ".join(f"- {r}" for r in reasons)

        lines = [
            f"Flight Price Alert: {name}",
            f"Route   : {route['origin']} → {route['destination']}",
            f"Dates   : {date_searched}",
            f"Cabin   : {route.get('cabin', 'ECONOMY')}  |  Adults: {route.get('adults', 1)}",
            f"",
            f"Top {len(offers)} Most Competitive Options:",
        ]

        for i, offer in enumerate(offers, 1):
            stops = offer.get("stops", 0)
            stop_label = "non-stop" if stops == 0 else f"{stops} stop(s)"
            dep_date = offer.get("departure_date", "")
            ret_date = offer.get("return_date")
            date_str = dep_date + (f" → {ret_date}" if ret_date else "")
            lines.append(
                f"  #{i}  {offer['currency']} {offer['price']:.2f}"
                f"  |  {offer['carrier']}"
                f"  |  {stop_label}"
                f"  |  {date_str}"
            )

        lines += [
            f"",
            f"Alert   : {reason_text}",
        ]

        return "\n".join(lines)
