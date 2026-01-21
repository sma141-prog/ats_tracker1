#!/usr/bin/env python3
"""
Deduplicate companies by comparing against existing database records.
Removes companies already present in external database/API query results.
Outputs both flagged (all records) and deduplicated CSV files.
"""

import json
import pandas as pd
from urllib.parse import urlparse

# ======== CONFIGURATION: Update these paths for your specific files ========
EXCEL_FILE = "C:/Users/super/Downloads/get_ats_company/get_ats_company/test.csv"
JSON_FILE = "C:/Users/super/Downloads/get_ats_company/get_ats_company/greenhouse_keywords1.json"  # Existing database records JSON
OUTPUT_WITH_FLAG = "C:/Users/super/Downloads/get_ats_company/get_ats_company/ashby_comp_with_flag.csv"   # Output with duplicate flags
OUTPUT_DEDUP = "C:/Users/super/Downloads/get_ats_company/get_ats_company/ashby_comp_deduped.csv"         # Deduplicated output
# ===========================================================================

# 1. Read CSV file (use pd.read_excel for XLSX files)
df = pd.read_csv(EXCEL_FILE)

# 2. Read JSON database records
with open(JSON_FILE, "r", encoding="utf-8") as f:
    json_data = json.load(f)

results = json_data.get("data", {}).get("results", [])

# Build keyword -> record index for fast lookup
keyword_to_record = {str(item["keyword"]): item for item in results}


def extract_keyword_from_url(url: str) -> str:
    """
    Extract the last path segment from URL as keyword.
    
    Example:
        https://jobs.ashbyhq.com/aerovect -> "aerovect"
        https://boards.greenhouse.io/2kczech -> "2kczech"
    
    Args:
        url: Career page URL
    
    Returns:
        Extracted keyword or empty string
    """
    try:
        parsed = urlparse(str(url))
        path = parsed.path.rstrip("/")  # Remove trailing slash
        if not path:
            return ""
        return path.split("/")[-1]
    except Exception:
        return ""


def check_exists_in_db(career_url: str) -> bool:
    """
    Check if a company already exists in the database based on JSON records.
    
    Logic:
    1. URL must contain 'workday' (adjust for other ATS as needed)
    2. Extract keyword from URL (last path segment)
    3. Find matching record in JSON
    4. If matchCount == 0 or dataSources is empty -> treat as not existing
    5. Otherwise check if any siteUrl contains both 'workday' and keyword
    
    Args:
        career_url: Career page URL to check
    
    Returns:
        True if company exists in database, False otherwise
    """
    url_str = str(career_url)

    # Only process URLs containing 'workday' (adjust for different ATS)
    if "workday" not in url_str:
        return False

    keyword = extract_keyword_from_url(url_str)
    if not keyword:
        return False

    # First try exact case-sensitive match
    record = keyword_to_record.get(keyword)

    # If not found, try case-insensitive match
    if record is None:
        kw_lower = keyword.lower()
        for k, rec in keyword_to_record.items():
            if k.lower() == kw_lower:
                record = rec
                break

    # No record found in JSON for this keyword
    if record is None:
        return False

    # Special case: matchCount == 0 and dataSources == [] means no results, not considered existing
    if record.get("matchCount", 0) == 0 or not record.get("dataSources"):
        return False

    # At least one siteUrl must contain both 'workday' and keyword
    for ds in record.get("dataSources", []):
        site_url = str(ds.get("siteUrl", ""))
        if "workday" in site_url and keyword in site_url:
            return True

    return False


# 3. Apply duplicate check to each career_url, add exists_in_db column
df["exists_in_db"] = df["career_url"].apply(check_exists_in_db)

# 4. Save complete table with flags (for manual inspection)
df.to_csv(OUTPUT_WITH_FLAG, index=False, encoding="utf-8-sig")

# 5. Generate deduplicated table: keep only records not in existing database
df_dedup = df[~df["exists_in_db"]].copy()
df_dedup.to_csv(OUTPUT_DEDUP, index=False, encoding="utf-8-sig")

print("Total rows:", len(df))
print("Rows identified as existing in database:", df["exists_in_db"].sum())
print("Rows after deduplication:", len(df_dedup))
print("Flagged results saved to:", OUTPUT_WITH_FLAG)
print("Deduplicated results saved to:", OUTPUT_DEDUP)
