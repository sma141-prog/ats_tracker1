# ATS Company Discovery Tool

A comprehensive toolset for discovering companies that use Applicant Tracking Systems (ATS) by querying Common Crawl archives. This toolset helps data analysts collect and process company data from various ATS platforms for further analysis and integration.

## Project Overview

This project provides a pipeline for:
1. **Discovering** companies using ATS platforms through Common Crawl queries
2. **Processing** and normalizing the discovered URLs
3. **Validating** and filtering the results
4. **Preparing** data for external database queries and analysis

The primary goal is to regularly collect up-to-date company data from ATS platforms, making it easy for data analysts to query, filter, and analyze which companies use which ATS systems.

## Supported ATS Platforms

Currently supports the following ATS platforms:
- **Greenhouse**: `boards.greenhouse.io/{company}`
- **Lever**: `jobs.lever.co/{company}`
- **Ashby**: `jobs.ashbyhq.com/{company}`
- **Workday**: `{tenant}.wd{N}.myworkdayjobs.com/{site}`
- **SmartRecruiters**: `careers.smartrecruiters.com/{company}`

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Installation
```bash
# Clone or download the project files
# Navigate to the project directory

# Install required packages
pip install requests pandas
```

### Project Structure
```
.
├── company_from_ats.py          # Main discovery script
├── company_keywords.py          # Keyword extraction for most ATS
├── company_keywords_for_workday.py  # Workday-specific keyword extraction
├── deduplicate_companies.py     # Remove duplicate companies
├── validate_urls.py             # Validate URLs accessibility
├── README.md                    # This documentation
└── *.csv                        # Output CSV files
```

## Quick Start Guide

### Basic Discovery (Single ATS)
```bash
# Discover Greenhouse companies from Common Crawl
python company_from_ats.py --providers greenhouse --out greenhouse_companies.csv
```

### Discover Multiple ATS Platforms
```bash
# Discover Greenhouse and Lever companies
python company_from_ats.py --providers greenhouse lever --out companies.csv
```

## Detailed Workflow

### Step 1: Discover Companies from Common Crawl
Use `company_from_ats.py` to query Common Crawl for company career pages:

```bash
# Advanced discovery with specific Common Crawl snapshots
python company_from_ats.py \
  --providers greenhouse \
  --limit-per-ats 2000 \
  --max-validate 0 \
  --skip-validation \
  --cc-index CC-MAIN-2023-40 CC-MAIN-2023-23 CC-MAIN-2023-10 CC-MAIN-2022-49 CC-MAIN-2021-31 \
  --cc-start-page 0 \
  --cc-max-pages 1 \
  --out greenhouse_p0.csv
```

**Key Parameters:**
- `--providers`: ATS platforms to query (or "all" for all)
- `--limit-per-ats`: Maximum URLs to collect per ATS (soft limit)
- `--skip-validation`: Skip live URL validation (faster but less accurate)
- `--cc-index`: Specific Common Crawl snapshots to query
- `--cc-start-page`: Start page for pagination (0-based)
- `--cc-max-pages`: Maximum pages to fetch per snapshot

**Common Crawl Snapshots:**
- Find available snapshots at: https://data.commoncrawl.org/
- Recommended snapshots with good ATS coverage: 2021-2023 ranges

### Step 2: Extract Company Keywords
Prepare company names for batch database queries:

```bash
# For Greenhouse, Lever, Ashby, SmartRecruiters
python company_keywords.py

# For Workday (special handling)
python company_keywords_for_workday.py
```

**Before running:**
- Update the file paths in each script
- Outputs are saved as `*_keywords{number}.txt` files in batches of 500

**Keyword Extraction Rules:**
- **Most ATS**: Extract the last segment of the URL path (e.g., `https://boards.greenhouse.io/2kczech` → `"2kczech"`)
- **Workday**: Extract the first domain segment (e.g., `https://aes.wd1.myworkdayjobs.com/AES_ANDES` → `"aes"`)

### Step 3: External Database Query
1. Use the generated keyword files to query your external database/API
2. Save query results as JSON files (e.g., `greenhouse.json`)

### Step 4: Deduplicate Companies
Remove companies already present in your database:

```bash
python deduplicate_companies.py
```

**Before running:**
- Update the file paths in the script
- Input: CSV file from Step 1 and JSON file from Step 3
- Outputs: CSV files with and without duplicate flags

### Step 5: Validate URLs
Filter out inaccessible URLs:

```bash
python validate_urls.py
```

**Validation Criteria:**
- URLs returning HTTP status 200-399 are kept
- URLs with redirects (301/302) are followed and validated
- SSL certificate errors are ignored
- Timeout after 10 seconds

## Script Reference

### `company_from_ats.py`
The main discovery script with the following features:
- **Multi-ATS support**: Query multiple ATS platforms in one run
- **Pagination**: Supports paginated Common Crawl queries
- **URL normalization**: Standardizes URLs for each ATS type
- **Validation**: Optional live URL validation
- **Seed URLs**: Fallback to predefined URLs if Common Crawl queries fail

**Full Command Reference:**
```bash
python company_from_ats.py --help
```

### `company_keywords.py` & `company_keywords_for_workday.py`
Extract company names from URLs for batch database queries:
- **Batch processing**: Groups companies in batches of 500
- **Platform-specific handling**: Different extraction logic for different ATS
- **JSON output**: Outputs as JSON arrays for easy API integration

### `deduplicate_companies.py`
Remove duplicate companies based on external database results:
- **Flexible matching**: Case-insensitive keyword matching
- **Database integration**: Checks against external query results
- **Dual output**: Produces both flagged and deduplicated CSV files

### `validate_urls.py`
Validate URL accessibility:
- **HTTP validation**: Checks actual HTTP responses
- **Error tolerance**: Ignores SSL errors and follows redirects
- **Performance**: Sequential validation with progress reporting

## Data Analysis & Querying

For data analysts, here's how to work with the output:

### Querying Discovered Companies
```python
import pandas as pd

# Load discovered companies
df = pd.read_csv('greenhouse_companies_valid.csv')

# Filter by specific criteria
active_companies = df[df['status'] == 'active']
specific_ats = df[df['ats'] == 'greenhouse']

# Group and analyze
ats_distribution = df.groupby('ats').size()
company_count = len(df)
```

### Common Analysis Questions
1. **Which companies use which ATS?** - Group by ATS platform
2. **How has ATS adoption changed over time?** - Compare across Common Crawl snapshots
3. **Which URLs are most active?** - Analyze validation results
4. **Are there duplicate companies across ATS?** - Cross-reference company names

### Data Schema
The output CSV contains:
- `company`: Extracted company identifier/slug
- `ats`: ATS platform name
- `career_url`: Normalized career page URL

## Extending the System

### Adding New ATS Providers
To add support for a new ATS platform:

1. **Add URL normalization function** in `company_from_ats.py`:
   ```python
   def normalize_new_ats(parsed) -> Optional[str]:
       if parsed.netloc != "newats.example.com":
           return None
       parts = [p for p in parsed.path.split("/") if p]
       if not parts:
           return None
       company = parts[0]
       return f"https://newats.example.com/{company}"
   ```

2. **Add validation function**:
   ```python
   def validate_new_ats(url: str) -> bool:
       resp = http_get(url)
       if not response_accessible(resp):
           return False
       if response_has_keyword(resp, "newats", "newats-keyword"):
           return True
       return resp.status_code in ALLOWED_BLOCK_STATUSES
   ```

3. **Register the ATS provider**:
   ```python
   ATS_PROVIDERS["newats"] = ATS(
       name="NewATS",
       cc_host_pattern="newats.example.com",
       url_normalizer=normalize_new_ats,
       validator=validate_new_ats,
       description="newats.example.com/{company}",
   )
   ```

4. **Add seed candidates** (optional):
   ```python
   ATS_SEED_CANDIDATES["newats"] = [
       "https://newats.example.com/example1",
       "https://newats.example.com/example2",
   ]
   ```

### Modifying Validation Logic
Adjust the validation criteria in `company_from_ats.py`:
- Modify `ALLOWED_BLOCK_STATUSES` for different status code handling
- Update `response_has_keyword()` with platform-specific keywords
- Change `REQUEST_TIMEOUT` and `RETRY_BACKOFFS` for network behavior

### Cross-Platform Compatibility
The scripts are designed to work on both Windows and Linux:
- Use relative paths or configuration files for file locations
- All scripts use standard Python libraries with cross-platform support
- Path handling uses `os.path` or `pathlib` for compatibility

## Troubleshooting

### Common Issues

**Issue**: No companies found in Common Crawl
**Solution**:
- Try different Common Crawl snapshots (`--cc-index`)
- Increase pagination (`--cc-max-pages`)
- Check if the ATS host pattern is correct

**Issue**: URL validation fails for accessible sites
**Solution**:
- Check if the site blocks automated requests
- Try with `--skip-validation` to bypass validation
- Adjust `ALLOWED_BLOCK_STATUSES` in the code

**Issue**: Database query returns no matches
**Solution**:
- Verify keyword extraction logic matches your database
- Check if company names need normalization
- Ensure JSON output format matches expected schema

**Issue**: Performance is slow
**Solution**:
- Use `--skip-validation` for faster discovery
- Reduce `--max-validate` for fewer validations
- Process ATS platforms separately

### Debug Mode
Enable debug output for detailed logging:
```bash
python company_from_ats.py --debug --out debug_output.csv
```

This shows:
- Common Crawl query patterns
- Sample candidate URLs
- Validation progress and results

## Contributing

### Development Guidelines
1. **Code Style**: Follow PEP 8 conventions
2. **Type Hints**: Use type annotations for function parameters and returns
3. **Documentation**: Update this README when adding new features
4. **Testing**: Test changes with different ATS platforms

### Adding Features
When adding new features:
1. Update the command-line interface in `parse_args()`
2. Add corresponding logic in the `run()` function
3. Update documentation in this README
4. Test with existing ATS providers

### Reporting Issues
Include the following when reporting issues:
1. Command used and full output/error
2. Python version (`python --version`)
3. Operating system
4. Any relevant CSV/JSON file snippets

---

## License & Credits

This toolset is designed for data collection and analysis purposes. Use responsibly and in accordance with Common Crawl's terms of service and the target websites' robots.txt policies.

Common Crawl data is available at: https://commoncrawl.org/
ATS platform information is collected from publicly accessible career pages.
