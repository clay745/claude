import requests
import time
from datetime import datetime, timedelta
import pytz

BASE_URL = "https://a.klaviyo.com/api"
REVISION = "2024-02-15"

METRIC_PLACED_ORDER = "Placed Order"
METRIC_RECEIVED_EMAIL = "Received Email"
METRIC_BOUNCED_EMAIL = "Bounced Email"
METRIC_OPENED_EMAIL = "Opened Email"
METRIC_CLICKED_EMAIL = "Clicked Email"
METRIC_SUBSCRIBED = "Subscribed to Email Marketing"
METRIC_UNSUBSCRIBED = "Unsubscribed from Email Marketing"


class KlaviyoClient:
    def __init__(self, api_key: str, timezone: str = "America/Chicago"):
        self.headers = {
            "Authorization": f"Klaviyo-API-Key {api_key}",
            "revision": REVISION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.tz = pytz.timezone(timezone)
        self._metric_cache: dict = {}

    def _get(self, url: str, params: dict = None) -> dict:
        # Accept either a full URL or a path
        full_url = url if url.startswith("http") else f"{BASE_URL}/{url}"
        r = requests.get(full_url, headers=self.headers, params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict, retries: int = 3) -> dict:
        for attempt in range(retries):
            r = requests.post(f"{BASE_URL}/{path}", headers=self.headers, json=body)
            if r.status_code == 429:
                wait = 2 ** attempt
                print(f"  [rate limit] waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()
        r.raise_for_status()
        return {}

    def yesterday_range(self) -> tuple[str, str]:
        today = datetime.now(self.tz).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = today - timedelta(days=1)
        fmt = "%Y-%m-%dT%H:%M:%S"
        return yesterday.strftime(fmt), today.strftime(fmt)

    def yesterday_date(self) -> str:
        today = datetime.now(self.tz)
        yesterday = today - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")

    def _load_metrics(self) -> dict:
        if self._metric_cache:
            return self._metric_cache

        metrics = {}
        url = f"{BASE_URL}/metrics"
        while url:
            data = self._get(url)
            for m in data.get("data", []):
                metrics[m["attributes"]["name"]] = m["id"]
            url = data.get("links", {}).get("next")  # full URL, pass directly
            time.sleep(0.3)

        self._metric_cache = metrics
        return metrics

    def _aggregate(self, metric_name: str, measurement: str, start: str, end: str) -> float:
        metrics = self._load_metrics()
        metric_id = metrics.get(metric_name)
        if not metric_id:
            print(f"  [warn] metric not found: {metric_name}")
            return 0.0

        body = {
            "data": {
                "type": "metric-aggregate",
                "attributes": {
                    "metric_id": metric_id,
                    "interval": "day",
                    "page_size": 500,
                    "measurements": [measurement],
                    "filter": (
                        f"greater-or-equal(datetime,{start}),"
                        f"less-than(datetime,{end})"
                    ),
                    "timezone": str(self.tz),
                },
            }
        }

        result = self._post("metric-aggregates", body)
        attrs = result.get("data", {}).get("attributes", {})
        dates = attrs.get("dates", [])
        data_rows = attrs.get("data", [])

        if not dates or not data_rows:
            return 0.0

        yesterday = self.yesterday_date()
        for i, d in enumerate(dates):
            if d[:10] == yesterday:
                values = data_rows[0].get("measurements", {}).get(measurement, [])
                return float(values[i]) if i < len(values) else 0.0

        return 0.0

    def get_total_email_list(self) -> int:
        # Use lists endpoint to count all profiles — simpler and more reliable
        try:
            data = self._get(f"{BASE_URL}/profiles", {"page[size]": 1})
            return data.get("meta", {}).get("total", 0)
        except Exception as e:
            print(f"  [warn] could not get total profiles: {e}")
            return 0

    def get_send_type(self, start: str, end: str) -> str:
        try:
            data = self._get(f"{BASE_URL}/campaigns", {
                "filter": (
                    f"greater-or-equal(scheduled_at,{start}),"
                    f"less-than(scheduled_at,{end}),"
                    "equals(status,'Sent')"
                ),
                "fields[campaign]": "id",
                "page[size]": 1,
            })
            had_campaign = len(data.get("data", [])) > 0
        except Exception:
            had_campaign = False

        flow_sent = self._aggregate(METRIC_SENT_EMAIL, "count", start, end)
        had_flow = flow_sent > 0 and not had_campaign

        if had_campaign and had_flow:
            return "Both"
        elif had_campaign:
            return "Campaign"
        elif had_flow:
            return "Flow"
        return "—"

    def fetch(self) -> dict:
        start, end = self.yesterday_range()

        received = self._aggregate(METRIC_RECEIVED_EMAIL, "count", start, end)
        time.sleep(0.5)
        bounced = self._aggregate(METRIC_BOUNCED_EMAIL, "count", start, end)
        time.sleep(0.5)
        opened = self._aggregate(METRIC_OPENED_EMAIL, "count", start, end)
        time.sleep(0.5)
        clicked = self._aggregate(METRIC_CLICKED_EMAIL, "count", start, end)
        time.sleep(0.5)
        revenue = self._aggregate(METRIC_PLACED_ORDER, "sum_value", start, end)
        time.sleep(0.5)
        gained = self._aggregate(METRIC_SUBSCRIBED, "count", start, end)
        time.sleep(0.5)
        lost = self._aggregate(METRIC_UNSUBSCRIBED, "count", start, end)
        time.sleep(0.5)

        total_list = self.get_total_email_list()
        time.sleep(0.5)
        send_type = self.get_send_type(start, end)

        emails_sent = int(received + bounced)
        deliverability = round(received / emails_sent * 100, 2) if emails_sent else 0.0
        open_rate = round(opened / received * 100, 2) if received else 0.0
        click_rate = round(clicked / received * 100, 2) if received else 0.0

        return {
            "email_revenue": round(revenue, 2),
            "emails_sent": emails_sent,
            "deliverability": deliverability,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "total_email_list": total_list,
            "email_gain": int(gained),
            "email_lost": int(lost),
            "email_net": int(gained - lost),
            "type": send_type,
        }
