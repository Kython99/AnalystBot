"""
Report tool — generate structured sales summaries and recommendations.
"""
import json
import os
import pandas as pd
from pathlib import Path


DATA_DIR = os.getenv("ANALYSTBOT_DATA_DIR", "/root/analystbot-data")


def generate_report(tenant_id: str, **kwargs) -> str:
    """
    Generate a structured sales performance report from the tenant's data.

    Looks at all uploaded files and Google Sheets, analyses them,
    and returns a formatted summary with key metrics and recommendations.

    Returns a structured report string.
    """
    tenant_dir = Path(DATA_DIR) / f"tenant_{tenant_id}"
    uploads_dir = tenant_dir / "uploads"

    if not uploads_dir.exists() or not any(uploads_dir.iterdir()):
        return "No data available. Upload a CSV or connect a Google Sheet first."

    reports = []

    # Read all CSV/Excel files
    for f in uploads_dir.iterdir():
        if f.suffix.lower() in [".csv"]:
            try:
                df = pd.read_csv(f)
                report = _analyse_dataframe(df, f.name)
                reports.append(report)
            except Exception as e:
                reports.append(f"Error reading {f.name}: {e}")

        elif f.suffix.lower() in [".xlsx", ".xls"]:
            try:
                df = pd.read_excel(f, engine="openpyxl")
                report = _analyse_dataframe(df, f.name)
                reports.append(report)
            except Exception as e:
                reports.append(f"Error reading {f.name}: {e}")

    if not reports:
        return "Could not generate report. Make sure your files are CSV or Excel format."

    return "\n\n".join(reports)


def _analyse_dataframe(df: pd.DataFrame, filename: str) -> str:
    """Analyse a dataframe and return a formatted report."""
    lines = [f"📊 Report: {filename}"]
    lines.append("=" * 40)

    # Try to detect common sales columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    date_cols = [c for c in df.columns if any(k in c.lower() for k in ["date", "time", "month", "year", "day"])]
    text_cols = [c for c in df.columns if c not in numeric_cols and c not in date_cols]

    # Basic stats
    if numeric_cols:
        total_row = None
        for col in numeric_cols:
            if any(k in col.lower() for k in ["total", "revenue", "sales", "amount", "qty", "quantity"]):
                total_col = col
                break
        else:
            total_col = numeric_cols[0]

        total = df[total_col].sum()
        avg = df[total_col].mean()
        max_val = df[total_col].max()
        min_val = df[total_col].min()

        lines.append(f"\n📈 Sales Column: {total_col}")
        lines.append(f"  Total:  ${total:,.2f}")
        lines.append(f"  Average: ${avg:,.2f}")
        lines.append(f"  Highest: ${max_val:,.2f}")
        lines.append(f"  Lowest: ${min_val:,.2f}")
        lines.append(f"  Records: {len(df)}")

    # Column overview
    lines.append(f"\n📋 Columns ({len(df.columns)}):")
    for col in df.columns.tolist():
        dtype = str(df[col].dtype)
        nulls = df[col].isnull().sum()
        lines.append(f"  • {col} ({dtype}) — {nulls} nulls")

    # Top values
    if numeric_cols:
        lines.append(f"\n🏆 Top 5 by {total_col}:")
        top5 = df.nlargest(5, total_col)
        for _, row in top5.iterrows():
            label = str(row.iloc[0]) if text_cols else "—"
            val = row[total_col]
            lines.append(f"  {label}: ${val:,.2f}")

    # Recommendations (basic)
    lines.append(f"\n💡 Recommendations:")
    if len(df) > 100:
        lines.append("  • Large dataset — consider filtering by date range for deeper analysis")
    if any(df[total_col] < 0 for col in numeric_cols if total_col in df.columns):
        lines.append("  • ⚠️ Negative values detected — review for refunds or corrections")
    if numeric_cols:
        cv = df[total_col].std() / df[total_col].mean() if df[total_col].mean() != 0 else 0
        if cv > 1:
            lines.append("  • High variability in sales — investigate outliers for patterns")
        else:
            lines.append("  • Sales are relatively stable — consistent performance")
    lines.append("  • Upload more data files to compare periods or segments")

    return "\n".join(lines)
