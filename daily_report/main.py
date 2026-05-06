#!/usr/bin/env python3
"""
Daily reporting script — pulls yesterday's data from Klaviyo + Postscript
and appends one row per brand to the configured Google Sheet.

Run manually:   python main.py
Schedule via cron (runs at 8am daily):
  0 8 * * * cd /path/to/daily_report && python main.py >> logs/report.log 2>&1
"""

from datetime import datetime, timedelta
import pytz
import traceback

import time
from config import BRANDS, TIMEZONE
from klaviyo import KlaviyoClient
from postscript import PostscriptClient
from sheets import SheetsClient


def yesterday_label(timezone: str) -> str:
    tz = pytz.timezone(timezone)
    yesterday = datetime.now(tz) - timedelta(days=1)
    return yesterday.strftime("%m/%d/%Y")


def run():
    sheets = SheetsClient()
    date_label = yesterday_label(TIMEZONE)

    for brand in BRANDS:
        name = brand["name"]
        print(f"\n{'─' * 50}")
        print(f"Processing: {name}")

        try:
            print(f"  Fetching Klaviyo data...")
            klaviyo = KlaviyoClient(brand["klaviyo_key"], TIMEZONE)
            email_data = klaviyo.fetch()

            print(f"  Fetching Postscript data...")
            postscript = PostscriptClient(brand["postscript_key"], TIMEZONE)
            sms_data = postscript.fetch()

            row = {
                "Date": date_label,
                "Email Rev": email_data["email_revenue"],
                "SMS Rev": "",           # fill in manually from Postscript
                "Total Rev": "",         # fill in manually after SMS Rev
                "Deliverability": f"{email_data['deliverability']}%",
                "Open Rate": f"{email_data['open_rate']}%",
                "Click Rate": f"{email_data['click_rate']}%",
                "Total Email List": email_data["total_email_list"],
                "Total SMS List": "",    # fill in manually from Postscript
                "Email Gain": email_data["email_gain"],
                "Email Lost": email_data["email_lost"],
                "Email Net": email_data["email_net"],
                "SMS Gain": "",          # fill in manually from Postscript
                "SMS Lost": "",          # fill in manually from Postscript
                "SMS Net": "",           # fill in manually from Postscript
                "Emails Sent": email_data["emails_sent"],
                "Type": email_data["type"],
                "Pop Up Opt In": "",     # fill in manually from Postscript
            }

            print(f"  Writing to sheet tab: {brand['sheet_tab']}")
            sheets.append_row(brand["sheet_tab"], row)

            print(f"  ✓ Done — Email Rev: ${row['Email Rev']} | Deliverability: {row['Deliverability']} | Open Rate: {row['Open Rate']}")

        except Exception as e:
            print(f"  ✗ Failed for {name}: {e}")
            traceback.print_exc()

        time.sleep(2)  # pause between brands to avoid rate limits

    print(f"\n{'─' * 50}")
    print("All brands processed.")


if __name__ == "__main__":
    run()
