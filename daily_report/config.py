import os
from dotenv import load_dotenv

load_dotenv()

TIMEZONE = os.getenv("TIMEZONE", "America/Chicago")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

BRANDS = [
    {
        "name": os.getenv(f"BRAND{i}_NAME"),
        "klaviyo_key": os.getenv(f"BRAND{i}_KLAVIYO_KEY"),
        "postscript_key": os.getenv(f"BRAND{i}_POSTSCRIPT_KEY"),
        "sheet_tab": os.getenv(f"BRAND{i}_SHEET_TAB"),
    }
    for i in range(1, 6)
    if os.getenv(f"BRAND{i}_KLAVIYO_KEY")
]

# Column order must match your Google Sheet exactly
SHEET_COLUMNS = [
    "Date",
    "Email Rev",
    "SMS Rev",
    "Total Rev",
    "Deliverability",
    "Open Rate",
    "Click Rate",
    "Total Email List",
    "Total SMS List",
    "Email Gain",
    "Email Lost",
    "Email Net",
    "SMS Gain",
    "SMS Lost",
    "SMS Net",
    "Emails Sent",
    "Type",
    "Pop Up Opt In",
]
