#!/usr/bin/env python3
"""
Extract company keywords from Workday CSV files for batch database queries.
Workday URLs require different extraction logic than other ATS platforms.
Outputs keywords in JSON format, grouped in batches of 500 for API compatibility.
"""

import pandas as pd
from urllib.parse import urlparse
import json
import math
import os

# === 1. Read input file ===
# TODO: Update file_path to your specific Workday CSV file
file_path = "C:/Users/GJX/Desktop/submission/workday.csv"
df = pd.read_csv(file_path)

# === 2. Extract Workday company keywords: take first domain segment ===
# Examples:
#   https://3m.wd1.myworkdayjobs.com/Search           → "3m"
#   https://nvidia.wd5.myworkdayjobs.com/Careers      → "nvidia"
#   https://apple.wd3.myworkdayjobs.com/en-US/Jobs    → "apple"

def extract_keyword(url: str) -> str:
    """
    Extract company keyword from Workday URL by taking the first domain segment.
    
    Args:
        url: Workday career page URL
    
    Returns:
        Company keyword (first domain segment, lowercase)
    """
    parsed = urlparse(str(url))
    netloc = parsed.netloc or ""
    if not netloc:
        return ""
    # Extract first segment before the first dot
    first_part = netloc.split(".")[0]
    return first_part.lower().strip()

# Apply extraction function to all career_urls
keywords_series = df["career_url"].apply(extract_keyword)

# Remove empty values, deduplicate, and sort
keywords = sorted(set(k for k in keywords_series if k))

print(f"Total keywords extracted: {len(keywords)}")

# === 3. Group keywords in batches of 500, write to text files ===
batch_size = 500
num_batches = math.ceil(len(keywords) / batch_size)

# TODO: Update output directory as needed
output_dir = "C:/Users/GJX/Desktop/submission/"
os.makedirs(output_dir, exist_ok=True)

for i in range(num_batches):
    batch = keywords[i * batch_size : (i + 1) * batch_size]
    
    # Convert to JSON list format for easy copying or loading
    list_str = json.dumps(batch, ensure_ascii=False)
    
    # Output filename with 1-based numbering
    output_path = os.path.join(output_dir, f"workday_keywords{i+1}.txt")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(list_str)
    
    print(f"Written {output_path} (contains {len(batch)} keywords)")

print("\nProcessing complete!")
