#!/usr/bin/env python3
"""
Extract company keywords from ATS CSV files for batch database queries.
This script processes Greenhouse, Lever, Ashby, and SmartRecruiters URLs.
Outputs keywords in JSON format, grouped in batches of 500 for API compatibility.
"""

import pandas as pd
from urllib.parse import urlparse
import json
import math
import os

# === 1. Read input file ===
# TODO: Update file_path to your specific CSV file
file_path = "C:/Users/super/Downloads/get_ats_company/get_ats_company/test.csv"
df = pd.read_csv(file_path)

# === 2. Extract keywords from career_url (last path segment) ===
def extract_keyword(url):
    """
    Extract company keyword from URL by taking the last path segment.
    
    Example:
        https://boards.greenhouse.io/2kczech -> "2kczech"
        https://jobs.lever.co/discord -> "discord"
    """
    path = urlparse(url).path
    return path.rstrip("/").split("/")[-1]

# Apply extraction function to all career_urls and get unique keywords
keywords = sorted(set(df["career_url"].apply(extract_keyword)))

print(f"Total keywords extracted: {len(keywords)}")

# === 3. Group keywords in batches of 500 for API compatibility ===
batch_size = 500
num_batches = math.ceil(len(keywords) / batch_size)

# TODO: Update output directory as needed
output_dir = "C/Users/super/Downloads/get_ats_company/get_ats_company"
os.makedirs(output_dir, exist_ok=True)

for i in range(num_batches):
    batch = keywords[i * batch_size : (i + 1) * batch_size]
    
    # Convert to JSON list format for easy API consumption
    list_str = json.dumps(batch, ensure_ascii=False)
    
    # Output filename with batch number
    output_path = os.path.join(output_dir, f"greenhouse_keywords{i+1}.txt")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(list_str)
    
    print(f"Written {output_path} (contains {len(batch)} keywords)")

print("\nProcessing complete!")
