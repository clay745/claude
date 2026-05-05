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

            total_rev = round(email_data["email_revenue"] + sms_data["sms_revenue"], 2)

            row = {
                "Date": date_label,
                "Email Rev": email_data["email_revenue"],
                "SMS Rev": sms_data["sms_revenue"],
                "Total Rev": total_rev,
                "Deliverability": f"{email_data['deliverability']}%",
                "Open Rate": f"{email_data['open_rate']}%",
                "Click Rate": f"{email_data['click_rate']}%",
                "Total Email List": email_data["total_email_list"],
                "Total SMS List": sms_data["total_sms_list"],
                "Email Gain": email_data["email_gain"],
                "Email Lost": email_data["email_lost"],
                "Email Net": email_data["email_net"],
                "SMS Gain": sms_data["sms_gain"],
                "SMS Lost": sms_data["sms_lost"],
                "SMS Net": sms_data["sms_net"],
                "Emails Sent": email_data["emails_sent"],
                "Type": email_data["type"],
                "Pop Up Opt In": f"{sms_data['popup_opt_in']}%",
            }

            print(f"  Writing to sheet tab: {brand['sheet_tab']}")
            sheets.append_row(brand["sheet_tab"], row)

            print(f"  ✓ Done — Email Rev: ${row['Email Rev']} | SMS Rev: ${row['SMS Rev']} | Total: ${total_rev}")

        except Exception as e:
            print(f"  ✗ Failed for {name}: {e}")
            traceback.print_exc()

    print(f"\n{'─' * 50}")
    print("All brands processed.")


if __name__ == "__main__":
    run()
