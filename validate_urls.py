#!/usr/bin/env python3
"""
Validate URL accessibility by checking HTTP responses.
Filters out inaccessible URLs, keeping only those returning 200-399 status codes.
Outputs a cleaned CSV with only valid, accessible URLs.
"""

import os
import csv
import requests

# Configuration: Update these paths for your specific files
input_csv = r"C:\Users\GJX\Desktop\submission\greenhouse_companies_deduped.csv"
output_csv = r"C:\Users\GJX\Desktop\submission\greenhouse_companies_valid.csv"


def url_is_valid(url):
    """
    Check if a URL is accessible and returns a valid HTTP response.
    
    Criteria:
    - Allows redirects (301/302)
    - Ignores SSL certificate errors
    - Returns True for status codes 200-399
    - Timeout after 10 seconds
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL is accessible, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        response = requests.get(
            url,
            timeout=10,
            allow_redirects=True,
            verify=False  # Ignore SSL errors
        )
        # Consider 200-399 status codes as valid accessible pages
        return 200 <= response.status_code < 400

    except Exception:
        return False


def filter_valid_urls(input_path, output_path):
    """
    Filter CSV file to keep only rows with accessible URLs.
    
    Args:
        input_path: Path to input CSV file
        output_path: Path for output CSV file with valid URLs only
    """
    if not os.path.exists(input_path):
        print(f"❌ File does not exist: {input_path}")
        return
    
    valid_rows = []

    with open(input_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        total = len(rows)

        for i, row in enumerate(rows):
            # Automatically identify URL field from common column names
            url = (
                row.get("url")
                or row.get("career_url")
                or row.get("siteUrl")
                or row.get("start_url")
            )
            
            print(f"[{i+1}/{total}] Checking: {url}")

            if url_is_valid(url):
                print("   ✔️ Accessible (keeping)")
                valid_rows.append(row)
            else:
                print("   ❌ Not accessible (removing)")

    # Write new CSV with only valid URLs
    if valid_rows:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=valid_rows[0].keys())
            writer.writeheader()
            writer.writerows(valid_rows)
        print(f"\n✅ Complete! New file with only accessible URLs:\n{output_path}")
    else:
        print("\n⚠️ No accessible URLs found, file not generated.")


# Direct execution
if __name__ == "__main__":
    filter_valid_urls(input_csv, output_csv)
