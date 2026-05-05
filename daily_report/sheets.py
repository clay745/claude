import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_ID, SHEET_COLUMNS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsClient:
    def __init__(self):
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
        self._client = gspread.authorize(creds)
        self._workbook = self._client.open_by_key(GOOGLE_SHEET_ID)

    def append_row(self, tab_name: str, row_data: dict):
        """Append one row to the named tab. row_data keys must match SHEET_COLUMNS."""
        sheet = self._workbook.worksheet(tab_name)
        row = [row_data.get(col, "") for col in SHEET_COLUMNS]
        sheet.append_row(row, value_input_option="USER_ENTERED")
