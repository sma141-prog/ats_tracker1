#!/usr/bin/env python3
import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse
import pdb
import requests

REQUEST_TIMEOUT = 10
RETRY_BACKOFFS = [0.5, 1.0, 2.0]
HEADERS = {"User-Agent": "ats-discover/1.0 (+https://example.com)"}

# ATS definitions: how to extract company slug and validate a career page.
class ATS:
    def __init__(
        self,
        name: str,
        cc_host_pattern: str,
        url_normalizer,
        validator,
        description: str,
    ):
        self.name = name
        self.cc_host_pattern = cc_host_pattern  # For Common Crawl query
        self.url_normalizer = url_normalizer    # (parsed_url) -> normalized_url or None
        self.validator = validator              # (url) -> bool
        self.description = description

def http_get(url: str) -> Optional[requests.Response]:
    for backoff in [0.0] + RETRY_BACKOFFS:
        if backoff:
            time.sleep(backoff)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            return resp
        except requests.RequestException:
            continue
    return None

def is_status_ok(resp: Optional[requests.Response]) -> bool:
    return bool(resp and 200 <= resp.status_code < 300)

ALLOWED_BLOCK_STATUSES = {301, 302, 303, 307, 308, 401, 403, 429}


def response_accessible(resp: Optional[requests.Response]) -> bool:
    """
    Determine whether a response indicates the URL is a live ATS board.
    Treats most non-404 client statuses as acceptable because many boards
    block anonymous scraping with 403/429 or rely on redirects.
    """
    if resp is None:
        return False
    status = resp.status_code
    if status in (404, 410):
        return False
    if 200 <= status < 400:
        return True
    return status in ALLOWED_BLOCK_STATUSES


def response_has_keyword(resp: Optional[requests.Response], *keywords: str) -> bool:
    if resp is None or not resp.text:
        #pdb.set_trace()
        return False
    text = resp.text.lower()
    return any(keyword in text for keyword in keywords)

def normalize_greenhouse(parsed) -> Optional[str]:
    # Expect host boards.greenhouse.io or job-boards.greenhouse.io
    if parsed.netloc not in ("boards.greenhouse.io", "job-boards.greenhouse.io"):
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    company = parts[0]
    return f"https://boards.greenhouse.io/{company}"

def validate_greenhouse(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "greenhouse", "window.gh", "boards.greenhouse"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_lever(parsed) -> Optional[str]:
    if parsed.netloc != "jobs.lever.co":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    company = parts[0]
    return f"https://jobs.lever.co/{company}"

def validate_lever(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "lever", "lever.co"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_smartrecruiters(parsed) -> Optional[str]:
    if parsed.netloc != "careers.smartrecruiters.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    company = parts[0]
    return f"https://careers.smartrecruiters.com/{company}"

def validate_smartrecruiters(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "smartrecruiters", "sr-company-name"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_ashby(parsed) -> Optional[str]:
    if parsed.netloc != "jobs.ashbyhq.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    company = parts[0]
    return f"https://jobs.ashbyhq.com/{company}"

def validate_ashby(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "ashby", "ashbyhq"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_breezy(parsed) -> Optional[str]:
    if not parsed.netloc.endswith(".breezy.hr"):
        return None
    host_parts = parsed.netloc.split(".")
    if len(host_parts) < 3:
        return None 
    company = host_parts[0]
    if not company:
        return None
    return f"https://{company}.breezy.hr"

def validate_breezy(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "breezy", "breezy.hr"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_workable(parsed) -> Optional[str]:
    if parsed.netloc != "apply.workable.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    company = parts[0]   
    return f"https://apply.workable.com/{company}"

def validate_workable(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "workable", "workable.com"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_ycombinator(parsed) -> Optional[str]:
    if parsed.netloc != "www.ycombinator.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        return None
    if parts[0] != "companies":  
        return None
    company = parts[1]
    return f"https://www.ycombinator.com/companies/{company}"

def validate_ycombinator(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "ycombinator", "ycombinator.com"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_rippling(parsed) -> Optional[str]:
    if parsed.netloc != "ats.rippling.com":
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    company = parts[0]
    return f"https://ats.rippling.com/{company}"

def validate_rippling(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "rippling", "ats.rippling.com"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

def normalize_workday(parsed) -> Optional[str]:
    """
    Normalize Workday URLs to extract company tenant and site key.
    Accepts any *.myworkdayjobs.com domain.
    Example: stripe.wd1.myworkdayjobs.com/StripeCareers -> https://stripe.wd1.myworkdayjobs.com/StripeCareers
    """
    # Accept any domain ending with .myworkdayjobs.com
    if not parsed.netloc.endswith(".myworkdayjobs.com"):
        return None

    # Extract tenant from domain, e.g., stripe.wd1.myworkdayjobs.com -> stripe
    host_parts = parsed.netloc.split(".")
    if len(host_parts) < 3:
        return None  # Domain format is too unusual, skip

    # Use the first valid path segment as site key
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        # No path, return root URL
        return f"https://{parsed.netloc}"

    # Some URLs have language code as first segment, e.g., /en-US/External
    if re.match(r"^[a-z]{2}-[A-Z]{2}$", parts[0]) and len(parts) >= 2:
        site_key = parts[1]  # Skip language code
    else:
        site_key = parts[0]

    return f"https://{parsed.netloc}/{site_key}"


def validate_workday(url: str) -> bool:
    resp = http_get(url)
    if not response_accessible(resp):
        return False
    if response_has_keyword(resp, "myworkdayjobs", "/wday/", "workday"):
        return True
    return resp.status_code in ALLOWED_BLOCK_STATUSES

ATS_PROVIDERS = {
    "greenhouse": ATS(
        name="Greenhouse",
        cc_host_pattern="boards.greenhouse.io",
        url_normalizer=normalize_greenhouse,
        validator=validate_greenhouse,
        description="boards.greenhouse.io/{company}",
    ),
    "lever": ATS(
        name="Lever",
        cc_host_pattern="jobs.lever.co",
        url_normalizer=normalize_lever,
        validator=validate_lever,
        description="jobs.lever.co/{company}",
    ),
    "smartrecruiters": ATS(
        name="SmartRecruiters",
        cc_host_pattern="careers.smartrecruiters.com",
        url_normalizer=normalize_smartrecruiters,
        validator=validate_smartrecruiters,
        description="careers.smartrecruiters.com/{Company}",
    ),
    "ashby": ATS(
        name="Ashby",
        cc_host_pattern="jobs.ashbyhq.com",
        url_normalizer=normalize_ashby,
        validator=validate_ashby,
        description="jobs.ashbyhq.com/{Company}",
    ),
    "workday": ATS(
        name="Workday",
        cc_host_pattern="*.myworkdayjobs.com",
        url_normalizer=normalize_workday,
        validator=validate_workday,
        description="{tenant}.wd{N}.myworkdayjobs.com/{site}",
    ),
    "breezy": ATS(
        name="Breezy",
        cc_host_pattern="*.breezy.hr",
        url_normalizer=normalize_breezy,
        validator=validate_breezy, 
        description="{company}.breezy.hr",
    ),
    "workable": ATS(
        name="Workable",    
        cc_host_pattern="apply.workable.com",
        url_normalizer=normalize_workable,
        validator=validate_workable,
        description="apply.workable.com/{company}",
    ),
    "ycombinator": ATS(
        name="Y Combinator",    
        cc_host_pattern="www.ycombinator.com",
        url_normalizer=normalize_ycombinator,
        validator=validate_ycombinator,
        description="www.ycombinator.com/companies/{company}",
    ),
    "rippling": ATS(
    name="Rippling",
    cc_host_pattern="ats.rippling.com",
    url_normalizer=normalize_rippling,
    validator=validate_rippling,
    description="ats.rippling.com/{company}",
),
}

ATS_SEED_CANDIDATES: Dict[str, List[str]] = {
    "greenhouse": [
        "https://boards.greenhouse.io/hubspot",
        "https://boards.greenhouse.io/notion",
        "https://boards.greenhouse.io/wayfair",
    ],
    "lever": [
        "https://jobs.lever.co/gusto",
        "https://jobs.lever.co/robinhood",
        "https://jobs.lever.co/discord",
    ],
    "smartrecruiters": [
        "https://careers.smartrecruiters.com/UbiSoft",
        "https://careers.smartrecruiters.com/Vodafone",
        "https://careers.smartrecruiters.com/TwitterCareers",
    ],
    "ashby": [
        "https://jobs.ashbyhq.com/Notion",
        "https://jobs.ashbyhq.com/Figma",
        "https://jobs.ashbyhq.com/Anthropic",
    ],
    "workday": [
        "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "https://stripe.wd1.myworkdayjobs.com/StripeCareers",
        "https://levistraussandco.wd5.myworkdayjobs.com/External",
    ],
    "breezy": [
        "https://Notion.breezy.hr",
        "https://Figma.breezy.hr",
        "https://Anthropic.breezy.hr",
    ],
     "workable": [
        "https://apply.workable.com/workable/",
        "https://apply.workable.com/zoom/",
        "https://apply.workable.com/notion/",
    ],
    "ycombinator": [
        "https://www.ycombinator.com/companies/metriport",
        "https://www.ycombinator.com/companies/stripe",
        "https://www.ycombinator.com/companies/airbnb",
    ],
    "rippling": [
    "https://ats.rippling.com/rippling",
    "https://ats.rippling.com/Newjobs",
    "https://ats.rippling.com/Notion",
],
}

def get_latest_cc_index() -> Optional[str]:
    try:
        resp = requests.get("https://index.commoncrawl.org/collinfo.json", headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        cols = resp.json()
        if not cols:
            return None
        # Choose newest snapshot (last entry typically newest)
        return cols[-1]["cdx-api"]
    except Exception:
        return None

def build_cc_patterns(host_pattern: str) -> List[str]:
    patterns: List[str] = []
    base = host_pattern
    wildcard = False
    if host_pattern.startswith("*."):
        wildcard = True
        base = host_pattern[2:]
        patterns.append(host_pattern)
    if "://" in host_pattern:
        patterns.append(host_pattern)
    else:
        patterns.append(base)
        patterns.append(f"https://{base}")
        patterns.append(f"http://{base}")
        if not wildcard:
            patterns.append(f"*.{base}")
    seen: Set[str] = set()
    ordered: List[str] = []
    for pattern in patterns:
        if pattern in seen:
            continue
        seen.add(pattern)
        ordered.append(pattern)
    return ordered

# 🔁 New version: Support paginated Common Crawl queries
def query_cc_index(
    cdx_api: str,
    host_pattern: str,
    limit: int,
    start_page: int = 0,
    max_pages: Optional[int] = None,
) -> Iterable[str]:
    """
    Query Common Crawl CDX index for URLs with pagination support.
    
    Args:
        cdx_api: Common Crawl CDX API endpoint
        host_pattern: Host pattern to query (e.g., "boards.greenhouse.io")
        limit: Scale parameter used to determine page size (not a hard limit)
        start_page: Starting page for pagination (0-based)
        max_pages: Maximum number of pages to fetch per pattern (None = until empty)
    
    Yields:
        Unique URLs matching the host pattern
    """
    seen_urls: Set[str] = set()

    for pattern in build_cc_patterns(host_pattern):
        page = start_page
        pages_seen = 0

        while True:
            params = {
                "url": f"{pattern}/*",
                "output": "json",
                # Keep original pageSize logic but no longer truncate with emitted
                "pageSize": str(max(2000, min(8000, limit * 10))),
                "page": str(page),
            }

            try:
                resp = requests.get(
                    cdx_api,
                    params=params,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    stream=True,
                )
                resp.raise_for_status()
            except Exception:
                # Request for this page failed, break out of current pattern
                break

            count_this_page = 0

            try:
                for line in resp.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        url = obj.get("url")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)
                        yield url
                        count_this_page += 1
                    except Exception:
                        continue
            except Exception:
                break

            # No new data on current page, assume we've reached the end for this pattern
            if count_this_page == 0:
                break

            page += 1
            pages_seen += 1

            if max_pages is not None and pages_seen >= max_pages:
                # Reached user-defined maximum pages
                break


def discover_for_ats(
    ats: ATS,
    cdx_api: str,
    limit: int,
    start_page: int = 0,
    max_pages: Optional[int] = None,
) -> List[str]:
    """
    Discover career URLs for a specific ATS from Common Crawl index.
    
    Args:
        ats: ATS provider configuration
        cdx_api: Common Crawl CDX API endpoint
        limit: Maximum number of normalized URLs to return
        start_page: Starting page for pagination (passed to query_cc_index)
        max_pages: Maximum pages to fetch (passed to query_cc_index)
    
    Returns:
        List of normalized career URLs
    """
    seen: Set[str] = set()
    results: List[str] = []
    for raw_url in query_cc_index(
        cdx_api,
        ats.cc_host_pattern,
        limit=limit,
        start_page=start_page,
        max_pages=max_pages,
    ):
        parsed = urlparse(raw_url)
        normalized = ats.url_normalizer(parsed)
        if not normalized:
            continue
        normalized = normalized.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
        if len(results) >= limit:
            break
    return results

def validate_urls(ats: ATS, urls: List[str], max_checks: int) -> List[str]:
    validated: List[str] = []
    for url in urls[:max_checks]:
        try:
            if ats.validator(url):
                validated.append(url)
        except Exception:
            continue
    return validated

def extract_company_key(ats_key: str, url: str) -> str:
    parsed = urlparse(url)
    if ats_key in ("greenhouse", "lever", "smartrecruiters", "ashby", "workable"):
        # company slug is first path segment
        parts = [p for p in parsed.path.split("/") if p]
        return parts[0] if parts else ""
    if ats_key == "workday":
        sub = parsed.netloc.split(".")[0]
        company = re.sub(r"wd\d+$", "", sub)
        return company
    if ats_key == "breezy":
        host = (parsed.netloc or "").lower().split(":", 1)[0]
        if host.endswith(".breezy.hr"):
            return host[: -len(".breezy.hr")]
        return ""
    if ats_key == "ycombinator":
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "companies":
            return parts[1]
        return ""
    if ats_key == "rippling":
        parts = [p for p in parsed.path.split("/") if p]
        if not parts:
            return ""
        if re.match(r"^[a-z]{2}-[A-Z]{2}$", parts[0]) and len(parts) >= 2:
            return parts[1]
        return parts[0]

    # fallback
    return parsed.netloc

def run(
    providers: List[str],
    limit_per_ats: int,
    out_path: str,
    max_validate: int,
    skip_validation: bool = False,
    debug: bool = False,
    cc_indexes: Optional[List[str]] = None,
    cc_start_page: int = 0,
    cc_max_pages: Optional[int] = 1,
):
    # If user provided --cc-index, use that; otherwise use defaults
    if cc_indexes:
        cdx_apis = [f"https://index.commoncrawl.org/{name}-index" for name in cc_indexes]
    else:
        # Default recommended CC snapshots (strong ATS coverage)
        default_cc = [
            "CC-MAIN-2023-40",
            "CC-MAIN-2023-23",
            "CC-MAIN-2023-10",
            "CC-MAIN-2022-49",
            "CC-MAIN-2021-31",
        ]
        cdx_apis = [f"https://index.commoncrawl.org/{name}-index" for name in default_cc]

    print("Using Common Crawl indexes:", file=sys.stderr)
    for api in cdx_apis:
        print(f"  {api}", file=sys.stderr)
    print(
        f"Pagination settings: start_page={cc_start_page}, max_pages={cc_max_pages}",
        file=sys.stderr,
    )

    rows: List[Tuple[str, str, str]] = []
    for key in providers:
        ats = ATS_PROVIDERS[key]
        print(f"Discovering {ats.name} ({ats.description}) ...", file=sys.stderr)
        if debug:
            patterns = ", ".join(build_cc_patterns(ats.cc_host_pattern))
            print(f"    CC query patterns: {patterns}", file=sys.stderr)
        candidates: List[str] = []
        for api in cdx_apis:
            candidates.extend(
                discover_for_ats(
                    ats,
                    api,
                    limit=limit_per_ats * 3,
                    start_page=cc_start_page,
                    max_pages=cc_max_pages,
                )
            )

        if debug:
            sample = ", ".join(candidates[:5])
            print(f"    Sample candidates: {sample or 'none'}", file=sys.stderr)
        if not candidates:
            print("    No candidates found in Common Crawl for this ATS.", file=sys.stderr)
            seeds = ATS_SEED_CANDIDATES.get(key, [])
            if seeds:
                print(f"    Falling back to {len(seeds)} seed URLs.", file=sys.stderr)
                candidates = seeds[: limit_per_ats * 3]
            else:
                print("    No seed URLs configured; continuing.", file=sys.stderr)
        if skip_validation:
            valid = candidates[:limit_per_ats]
            print(f"  Skipping validation; taking {len(valid)} candidates.", file=sys.stderr)
        else:
            print(f"  Candidates found: {len(candidates)}; validating up to {max_validate}", file=sys.stderr)
            valid = validate_urls(ats, candidates, max_checks=max_validate)
            print(f"  Validated: {len(valid)}", file=sys.stderr)
        for url in valid:
            company = extract_company_key(key, url)
            rows.append((company, ats.name, url))

    # Deduplicate by (company, ats)
    dedup: Dict[Tuple[str, str], str] = {}
    for company, ats_name, url in rows:
        key = (company.lower(), ats_name.lower())
        if key not in dedup:
            dedup[key] = url

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["company", "ats", "career_url"])
        for (company_l, ats_l), url in sorted(dedup.items()):
            writer.writerow([company_l, ats_l, url])

    print(f"Wrote {len(dedup)} rows to {out_path}", file=sys.stderr)

def parse_args():
    parser = argparse.ArgumentParser(description="Discover companies using ATS career sites via Common Crawl.")
    parser.add_argument(
        "--providers",
        nargs="+",
        default=["all"],
        choices=["all"] + list(ATS_PROVIDERS.keys()),
        help="ATS providers to include"
    )
    parser.add_argument("--limit-per-ats", type=int, default=300, help="Target validated URLs per ATS (soft)")
    parser.add_argument("--max-validate", type=int, default=600, help="Maximum URLs to live-validate per ATS")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--skip-validation", action="store_true", help="Do not perform live validation; keep Common Crawl candidates")
    parser.add_argument("--debug", action="store_true", help="Print debug information such as candidate samples")
    parser.add_argument(
        "--cc-index",
        nargs="+",
        default=None,
        help="Specify one or more Common Crawl index names, e.g. CC-MAIN-2023-10 CC-MAIN-2022-49",
    )
    # ⭐ New pagination parameters
    parser.add_argument(
        "--cc-start-page",
        type=int,
        default=0,
        help="Start page for Common Crawl query (per index, 0-based)",
    )
    parser.add_argument(
        "--cc-max-pages",
        type=int,
        default=1,
        help="Max pages to fetch per index (use -1 for no limit)",
    )

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    if args.providers == ["all"]:
        providers = list(ATS_PROVIDERS.keys())
    else:
        providers = args.providers

    cc_max_pages = None if args.cc_max_pages < 0 else args.cc_max_pages

    run(
        providers=providers,
        limit_per_ats=args.limit_per_ats,
        out_path=args.out,
        max_validate=args.max_validate,
        skip_validation=args.skip_validation,
        debug=args.debug,
        cc_indexes=args.cc_index,
        cc_start_page=args.cc_start_page,
        cc_max_pages=cc_max_pages,
    )
