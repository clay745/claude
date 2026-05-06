import requests
from datetime import datetime, timedelta
import pytz

BASE_URL = "https://api.postscript.io/api/v2"


class PostscriptClient:
    def __init__(self, api_key: str, timezone: str = "America/Chicago"):
        # Postscript supports both Bearer and Token auth — try Token (private key standard)
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.tz = pytz.timezone(timezone)
        self._shop_id = None

    def _get(self, path: str, params: dict = None) -> dict:
        url = path if path.startswith("http") else f"{BASE_URL}/{path}"
        r = requests.get(url, headers=self.headers, params=params or {})
        r.raise_for_status()
        return r.json()

    def yesterday_range(self) -> tuple[str, str]:
        today = datetime.now(self.tz).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    def get_shop_id(self) -> str | None:
        if self._shop_id:
            return self._shop_id
        try:
            data = self._get("shops")
            shops = data.get("data", data) if isinstance(data, dict) else data
            if shops and len(shops) > 0:
                shop = shops[0] if isinstance(shops, list) else shops
                self._shop_id = shop.get("id") or shop.get("shop_id")
                return self._shop_id
        except Exception as e:
            print(f"  [warn] could not get Postscript shop ID: {e}")
        return None

    def get_subscriber_stats(self, start: str, end: str) -> tuple[int, int, int]:
        shop_id = self.get_shop_id()
        endpoints_to_try = []
        if shop_id:
            endpoints_to_try.append(f"shops/{shop_id}/subscribers/stats")
            endpoints_to_try.append(f"shops/{shop_id}/subscribers")
        endpoints_to_try += ["subscribers/stats", "subscribers"]

        for endpoint in endpoints_to_try:
            try:
                data = self._get(endpoint, {"start_date": start, "end_date": end})
                # Try to extract counts from various response shapes
                result = data.get("data", data)
                if isinstance(result, dict):
                    total = result.get("total_subscribers") or result.get("total") or result.get("count", 0)
                    gained = result.get("new_subscribers") or result.get("subscribed") or result.get("gained", 0)
                    lost = result.get("unsubscribers") or result.get("unsubscribed") or result.get("lost", 0)
                    return int(total), int(gained), int(lost)
            except Exception:
                continue

        print(f"  [warn] Postscript subscriber stats unavailable — returning 0s")
        return 0, 0, 0

    def get_revenue(self, start: str, end: str) -> float:
        shop_id = self.get_shop_id()
        endpoints_to_try = []
        if shop_id:
            endpoints_to_try.append(f"shops/{shop_id}/revenue")
            endpoints_to_try.append(f"shops/{shop_id}/analytics/revenue")
            endpoints_to_try.append(f"shops/{shop_id}/sales")
        endpoints_to_try += ["revenue", "analytics/revenue", "sales"]

        for endpoint in endpoints_to_try:
            try:
                data = self._get(endpoint, {"start_date": start, "end_date": end})
                result = data.get("data", data)
                if isinstance(result, dict):
                    rev = result.get("revenue") or result.get("total_revenue") or result.get("attributed_revenue", 0)
                    return float(rev)
            except Exception:
                continue

        print(f"  [warn] Postscript revenue unavailable — returning 0")
        return 0.0

    def get_popup_conversion_rate(self, start: str, end: str) -> float:
        shop_id = self.get_shop_id()
        endpoints_to_try = []
        if shop_id:
            endpoints_to_try.append(f"shops/{shop_id}/signup_units/analytics")
            endpoints_to_try.append(f"shops/{shop_id}/popups/analytics")
            endpoints_to_try.append(f"shops/{shop_id}/keywords/analytics")
        endpoints_to_try += ["signup_units/analytics", "popups", "keywords"]

        for endpoint in endpoints_to_try:
            try:
                data = self._get(endpoint, {"start_date": start, "end_date": end})
                entries = data.get("data", [])
                if isinstance(entries, list) and entries:
                    rates = [e.get("conversion_rate", 0.0) for e in entries if e.get("conversion_rate") is not None]
                    if rates:
                        return round(sum(rates) / len(rates) * 100, 2)
                elif isinstance(entries, dict):
                    rate = entries.get("conversion_rate", 0.0)
                    if rate:
                        return round(float(rate) * 100, 2)
            except Exception:
                continue

        print(f"  [warn] Postscript popup conversion unavailable — returning 0")
        return 0.0

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
