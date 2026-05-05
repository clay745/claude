import requests
from datetime import datetime, timedelta
from typing import Optional
import pytz

BASE_URL = "https://a.klaviyo.com/api"
REVISION = "2024-02-15"

# Klaviyo metric names — these must match exactly what's in your account
METRIC_PLACED_ORDER = "Placed Order"
METRIC_SENT_EMAIL = "Sent Email"
METRIC_DELIVERED_EMAIL = "Delivered Email"
METRIC_OPENED_EMAIL = "Opened Email"
METRIC_CLICKED_EMAIL = "Clicked Email"
METRIC_SUBSCRIBED = "Subscribed to List"
METRIC_UNSUBSCRIBED = "Unsubscribed"


class KlaviyoClient:
    def __init__(self, api_key: str, timezone: str = "America/New_York"):
        self.headers = {
            "Authorization": f"Klaviyo-API-Key {api_key}",
            "revision": REVISION,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.tz = pytz.timezone(timezone)
        self._metric_cache: dict = {}

    def _get(self, path: str, params: dict = None) -> dict:
        r = requests.get(f"{BASE_URL}/{path}", headers=self.headers, params=params or {})
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> dict:
        r = requests.post(f"{BASE_URL}/{path}", headers=self.headers, json=body)
        r.raise_for_status()
        return r.json()

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
        url = "metrics"
        while url:
            data = self._get(url)
            for m in data.get("data", []):
                metrics[m["attributes"]["name"]] = m["id"]
            next_link = data.get("links", {}).get("next")
            # next_link is a full URL; strip base for _get
            url = next_link.replace(f"{BASE_URL}/", "") if next_link else None

        self._metric_cache = metrics
        return metrics

    def _aggregate(self, metric_name: str, measurement: str, start: str, end: str) -> float:
        metric_id = self._load_metrics().get(metric_name)
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
        data = self._get("profiles", {
            "page[size]": 1,
            "filter": "equals(subscriptions.email.marketing.can_receive_email_marketing,true)",
        })
        return data.get("meta", {}).get("total", 0)

    def get_send_type(self, start: str, end: str) -> str:
        """Returns Campaign, Flow, or Both based on what sent emails yesterday."""
        data = self._get("campaigns", {
            "filter": (
                f"greater-or-equal(scheduled_at,{start}),"
                f"less-than(scheduled_at,{end}),"
                "equals(status,'Sent')"
            ),
            "fields[campaign]": "id",
            "page[size]": 1,
        })
        had_campaign = len(data.get("data", [])) > 0

        # Flows always run, so check if flow emails were sent via metric
        flow_sent = self._aggregate(METRIC_SENT_EMAIL, "count", start, end)
        had_flow = flow_sent > 0 and not had_campaign  # simplistic; refine if needed

        if had_campaign and had_flow:
            return "Both"
        elif had_campaign:
            return "Campaign"
        elif had_flow:
            return "Flow"
        return "—"

    def fetch(self) -> dict:
        start, end = self.yesterday_range()

        sent = self._aggregate(METRIC_SENT_EMAIL, "count", start, end)
        delivered = self._aggregate(METRIC_DELIVERED_EMAIL, "count", start, end)
        opened = self._aggregate(METRIC_OPENED_EMAIL, "count", start, end)
        clicked = self._aggregate(METRIC_CLICKED_EMAIL, "count", start, end)
        revenue = self._aggregate(METRIC_PLACED_ORDER, "sum_value", start, end)
        gained = self._aggregate(METRIC_SUBSCRIBED, "count", start, end)
        lost = self._aggregate(METRIC_UNSUBSCRIBED, "count", start, end)
        total_list = self.get_total_email_list()
        send_type = self.get_send_type(start, end)

        deliverability = round(delivered / sent * 100, 2) if sent else 0.0
        open_rate = round(opened / delivered * 100, 2) if delivered else 0.0
        click_rate = round(clicked / delivered * 100, 2) if delivered else 0.0

        return {
            "email_revenue": round(revenue, 2),
            "emails_sent": int(sent),
            "deliverability": deliverability,
            "open_rate": open_rate,
            "click_rate": click_rate,
            "total_email_list": total_list,
            "email_gain": int(gained),
            "email_lost": int(lost),
            "email_net": int(gained - lost),
            "type": send_type,
        }
