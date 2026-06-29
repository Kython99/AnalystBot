"""
Google Sheets tool — read data from a shareable Google Sheets link.
No OAuth needed for public/anyone-with-link sheets.
"""
import pandas as pd
import requests
import io
import re


def _extract_sheet_id(url: str) -> str | None:
    """
    Extract the sheet ID from various Google Sheets URL formats.
    Supports:
    - https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
    - https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=<GID>
    - https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>
    """
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None


def _extract_gid(url: str) -> str | None:
    """Extract gid (sheet ID) from URL if present."""
    gid_match = re.search(r'[?&]gid=(\d+)', url)
    if gid_match:
        return gid_match.group(1)
    return None


def read_sheets(tenant_id: str, url: str, sheet_name: str = None, **kwargs) -> str:
    """
    Read data from a Google Sheets shareable link.

    Exports as CSV via Google's export URL.
    No authentication required if the sheet is set to "Anyone with the link can view".

    Args:
        tenant_id: The tenant ID (for future caching/context)
        url: The full Google Sheets shareable URL
        sheet_name: Optional sheet name or index (default: first sheet)

    Returns:
        Data as a formatted string preview
    """
    sheet_id = _extract_sheet_id(url)
    if not sheet_id:
        return f"Error: Could not extract sheet ID from URL. Make sure you paste the full Google Sheets URL (e.g. https://docs.google.com/spreadsheets/d/.../edit)."

    # Try to get CSV export
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"

    # Add gid if specified
    gid = _extract_gid(url)
    if gid:
        export_url += f"&gid={gid}"

    try:
        response = requests.get(export_url, timeout=15)
        if response.status_code == 429:
            return "Error: Too many requests to Google Sheets. Please wait a moment and try again."
        if response.status_code == 403:
            return "Error: Access denied. Make sure the sheet is set to 'Anyone with the link can view' (not 'Restricted')."
        if response.status_code != 200:
            return f"Error: Google Sheets returned status {response.status_code}. Make sure the link is correct and the sheet is publicly accessible."

        content = response.content.decode("utf-8", errors="replace")
        if not content.strip():
            return "Error: The sheet appears to be empty."

        df = pd.read_csv(io.StringIO(content), **kwargs)
        preview = df.head(20).to_string(index=False)
        shape = f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n\n"
        columns = f"Columns: {', '.join(df.columns.tolist())}\n\n"
        return shape + columns + preview

    except requests.exceptions.Timeout:
        return "Error: Google Sheets request timed out. Try again or use a smaller data range."
    except Exception as e:
        return f"Error reading Google Sheets: {e}"
