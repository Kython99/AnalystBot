"""
Excel/CSV tool — read and parse CSV and Excel files from tenant uploads.
"""
import io
import pandas as pd
import os
from pathlib import Path


DATA_DIR = os.getenv("ANALYSTBOT_DATA_DIR", "/root/analystbot-data")


def _get_upload_path(tenant_id: str, filename: str) -> str:
    return f"{DATA_DIR}/tenant_{tenant_id}/uploads/{filename}"


def read_csv(tenant_id: str, filename: str, **kwargs) -> str:
    """
    Read a CSV file from the tenant's uploads folder.
    Returns a preview of the data as a string.
    """
    path = _get_upload_path(tenant_id, filename)
    if not os.path.exists(path):
        return f"Error: file '{filename}' not found in uploads. Upload it first."

    try:
        df = pd.read_csv(path, **kwargs)
        preview = df.head(20).to_string(index=False)
        shape = f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n\n"
        columns = f"Columns: {', '.join(df.columns.tolist())}\n\n"
        return shape + columns + preview
    except Exception as e:
        return f"Error reading CSV: {e}"


def read_excel(tenant_id: str, filename: str, sheet_name: str = None, **kwargs) -> str:
    """
    Read an Excel (.xlsx) file from the tenant's uploads folder.
    Optionally specify a sheet name or index.
    """
    path = _get_upload_path(tenant_id, filename)
    if not os.path.exists(path):
        return f"Error: file '{filename}' not found in uploads. Upload it first."

    try:
        if sheet_name:
            df = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl", **kwargs)
        else:
            # Read first sheet
            df = pd.read_excel(path, engine="openpyxl", **kwargs)

        preview = df.head(20).to_string(index=False)
        shape = f"Shape: {df.shape[0]} rows × {df.shape[1]} columns\n\n"
        columns = f"Columns: {', '.join(df.columns.tolist())}\n\n"
        return shape + columns + preview
    except Exception as e:
        return f"Error reading Excel: {e}"


def list_files(tenant_id: str, **kwargs) -> str:
    """List all files in the tenant's uploads folder."""
    upload_dir = f"{DATA_DIR}/tenant_{tenant_id}/uploads"
    if not os.path.exists(upload_dir):
        return "No uploads yet."

    files = os.listdir(upload_dir)
    if not files:
        return "No uploaded files."
    return "Uploaded files:\n" + "\n".join(f"- {f}" for f in files)
