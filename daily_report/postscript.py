import requests
from datetime import datetime, timedelta
import pytz

BASE_URL = "https://api.postscript.io/api/v2"


class PostscriptClient:
    def __init__(self, api_key: str, timezone: str = "America/New_York"):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.tz = pytz.timezone(timezone)

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{BASE_URL}/{path}", headers=self.headers, params=params or {})
        r.raise_for_status()
        return r.json()

    def yesterday_range(self) -> tuple[str, str]:
        today = datetime.now(self.tz).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        return (
            yesterday.strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d"),
        )

    def get_subscriber_stats(self, start: str, end: str) -> tuple[int, int, int]:
        """Returns (total_list, gained, lost) for the given date range."""
        data = self._get("subscribers", {
            "start_date": start,
            "end_date": end,
            "limit": 1,
        })
        # Postscript returns summary counts in the response meta/summary
        summary = data.get("data", {})
        total = summary.get("total_subscribers", 0)
        gained = summary.get("new_subscribers", 0)
        lost = summary.get("unsubscribers", 0)
        return int(total), int(gained), int(lost)

    def get_revenue(self, start: str, end: str) -> float:
        """Returns SMS attributed revenue for the given date range."""
        data = self._get("analytics/revenue", {
            "start_date": start,
            "end_date": end,
        })
        return float(data.get("data", {}).get("revenue", 0.0))

    def get_popup_conversion_rate(self, start: str, end: str) -> float:
        """Returns popup opt-in conversion rate as a percentage."""
        data = self._get("signup_units/analytics", {
            "start_date": start,
            "end_date": end,
        })
        entries = data.get("data", [])
        if not entries:
            return 0.0
        # Average conversion rate across all active popups
        rates = [e.get("conversion_rate", 0.0) for e in entries if e.get("conversion_rate") is not None]
        return round(sum(rates) / len(rates) * 100, 2) if rates else 0.0

    def fetch(self) -> dict:
        start, end = self.yesterday_range()

        total_list, gained, lost = self.get_subscriber_stats(start, end)
        revenue = self.get_revenue(start, end)
        popup_rate = self.get_popup_conversion_rate(start, end)

        return {
            "sms_revenue": round(revenue, 2),
            "total_sms_list": total_list,
            "sms_gain": gained,
            "sms_lost": lost,
            "sms_net": gained - lost,
            "popup_opt_in": popup_rate,
        }
