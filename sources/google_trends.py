#!/usr/bin/env python3
"""
Google Trends via SerpAPI

Two functions:
1. DISCOVERY: Get Rising Queries - keywords with biggest growth %
2. VALIDATION: Get Interest Over Time - calculate 5yr/1yr/3mo/1wk growth

Output: data/processed/google_trends.csv

Requires: SERPAPI_KEY in .env
"""
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from serpapi import GoogleSearch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Constants
RAW_DIR = config.RAW_DIR / "serpapi"
OUTPUT_FILE = config.PROCESSED_DIR / "google_trends.csv"

# Rate limiting - SerpAPI has limits
REQUEST_DELAY = 1  # seconds between requests

# Categories to discover from (Google Trends category IDs)
# https://serpapi.com/google-trends-categories
DISCOVERY_CATEGORIES = {
    "all": 0,           # All categories
    "shopping": 18,     # Shopping
    "beauty": 44,       # Beauty & Fitness
    "health": 45,       # Health
    "food": 71,         # Food & Drink
    "home": 11,         # Home & Garden
    "sports": 20,       # Sports
    "tech": 5,          # Computers & Electronics
    "travel": 67,       # Travel
    "pets": 66,         # Pets & Animals
    "business": 12,     # Business & Industrial
    "hobbies": 64,      # Hobbies & Leisure
}


def get_api_key():
    """Get SerpAPI key from config."""
    if not config.SERPAPI_KEY:
        raise ValueError("SERPAPI_KEY not found in .env file")
    return config.SERPAPI_KEY


# Seed keywords for discovery - BROAD categories, NOT health-focused
# These are category triggers to find what's trending ACROSS all product types
SEED_KEYWORDS = [
    # Home & Living
    "home decor", "furniture", "kitchen appliance", "cleaning product",
    # Tech & Electronics
    "phone accessory", "laptop stand", "wireless charger", "smart device",
    # Outdoor & Sports
    "camping gear", "fishing equipment", "golf accessory", "bike accessory",
    # Pets
    "dog product", "cat product", "pet accessory", "aquarium",
    # Kids & Baby
    "baby gear", "kids toy", "stroller", "nursery",
    # Fashion & Accessories
    "handbag", "watch", "sunglasses", "jewelry",
    # Automotive
    "car accessory", "car organizer", "dash cam", "car charger",
    # Garden & Outdoor
    "garden tool", "patio furniture", "grill accessory", "plant pot",
    # Hobbies & Crafts
    "craft supplies", "sewing machine", "art supplies", "3d printer",
    # Office & Productivity
    "desk organizer", "ergonomic chair", "monitor stand", "planner",
]


def discover_trending_now(geo: str = "US") -> list:
    """
    DISCOVERY: Get trending searches from Google Trends Trending Now.

    Uses the new SerpAPI endpoint format.
    """
    params = {
        "engine": "google_trends_trending_now",
        "geo": geo,
        "api_key": get_api_key(),
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        # Save raw response
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = RAW_DIR / f"trending_now_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        raw_path.write_text(json.dumps(results, indent=2))

        keywords = []

        # Try different response formats
        trending = results.get("trending_searches", []) or results.get("daily_searches", [])

        for item in trending:
            if isinstance(item, dict):
                # Handle nested structure
                searches = item.get("searches", [item])
                for search_item in searches:
                    query = search_item.get("query", search_item.get("title", ""))
                    if isinstance(query, dict):
                        query = query.get("text", "")
                    if query:
                        keywords.append({
                            "keyword": str(query),
                            "traffic": search_item.get("traffic", search_item.get("formattedTraffic", "")),
                            "source": "google_trends_trending",
                        })
            elif isinstance(item, str):
                keywords.append({
                    "keyword": item,
                    "source": "google_trends_trending",
                })

        time.sleep(REQUEST_DELAY)
        return keywords

    except Exception as e:
        print(f"    ERROR in discover_trending_now: {e}")
        return []


def discover_from_seeds(seeds: list = None, geo: str = "US") -> list:
    """
    DISCOVERY: Get rising related queries for seed keywords.

    More reliable than trending_now - finds keywords related to product categories.
    """
    if seeds is None:
        seeds = SEED_KEYWORDS

    all_keywords = []
    seen = set()

    for seed in seeds:
        print(f"    Seed: {seed}...")
        related = discover_related_queries(seed, geo=geo)

        for kw in related:
            keyword = kw.get("keyword", "").lower()
            if keyword and keyword not in seen and len(keyword) > 2:
                seen.add(keyword)
                kw["seed"] = seed
                all_keywords.append(kw)

    return all_keywords


def discover_related_queries(seed_keyword: str, geo: str = "US") -> list:
    """
    DISCOVERY: Get related rising queries for a seed keyword.

    Finds keywords related to a topic that are growing.
    """
    params = {
        "engine": "google_trends",
        "q": seed_keyword,
        "geo": geo,
        "data_type": "RELATED_QUERIES",
        "api_key": get_api_key(),
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        # Save raw response
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        safe_kw = seed_keyword.replace(" ", "_")[:20]
        raw_path = RAW_DIR / f"related_{safe_kw}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        raw_path.write_text(json.dumps(results, indent=2))

        keywords = []

        # Get rising queries (biggest growth)
        rising = results.get("related_queries", {}).get("rising", [])
        for item in rising:
            keywords.append({
                "keyword": item.get("query", ""),
                "growth_pct": parse_growth(item.get("value", "")),
                "source": "google_trends_related",
                "seed": seed_keyword,
            })

        # Get top queries (most searched)
        top = results.get("related_queries", {}).get("top", [])
        for item in top:
            keywords.append({
                "keyword": item.get("query", ""),
                "relevance": item.get("value", 0),
                "source": "google_trends_top",
                "seed": seed_keyword,
            })

        time.sleep(REQUEST_DELAY)
        return keywords

    except Exception as e:
        print(f"    ERROR in discover_related_queries: {e}")
        return []


def parse_growth(value) -> int:
    """Parse growth value from SerpAPI (e.g., '+2,400%' or 'Breakout')."""
    if not value:
        return None
    if isinstance(value, int):
        return value
    value_str = str(value)
    if "breakout" in value_str.lower():
        return 5000  # Breakout = massive growth, use 5000%
    # Extract number
    import re
    match = re.search(r'[\+]?([\d,]+)', value_str)
    if match:
        return int(match.group(1).replace(",", ""))
    return None


def get_interest_over_time(keyword: str, geo: str = "US", timeframe: str = "today 5-y") -> dict:
    """
    VALIDATION: Get interest over time for a keyword.

    Returns interest values that can be used to calculate growth.
    """
    params = {
        "engine": "google_trends",
        "q": keyword,
        "geo": geo,
        "date": timeframe,
        "data_type": "TIMESERIES",
        "api_key": get_api_key(),
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        # Save raw response
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        safe_kw = keyword.replace(" ", "_")[:20]
        raw_path = RAW_DIR / f"timeseries_{safe_kw}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        raw_path.write_text(json.dumps(results, indent=2))

        time.sleep(REQUEST_DELAY)
        return results.get("interest_over_time", {})

    except Exception as e:
        print(f"    ERROR getting interest for '{keyword}': {e}")
        return {}


def calculate_growth_metrics(interest_data: dict) -> dict:
    """
    Calculate growth percentages from interest over time data.

    Returns: {gt_5yr_pct, gt_1yr_pct, gt_3mo_pct, gt_1wk_pct, gt_current}
    """
    metrics = {
        "gt_current": None,
        "gt_5yr_pct": None,
        "gt_1yr_pct": None,
        "gt_3mo_pct": None,
        "gt_1wk_pct": None,
    }

    timeline = interest_data.get("timeline_data", [])
    if not timeline:
        return metrics

    # Get values with dates
    data_points = []
    for point in timeline:
        try:
            date_str = point.get("date", "")
            values = point.get("values", [])
            if values:
                value = values[0].get("value", 0) if isinstance(values[0], dict) else values[0]
                data_points.append({
                    "date": date_str,
                    "value": int(value) if value else 0
                })
        except:
            continue

    if len(data_points) < 2:
        return metrics

    # Current value (most recent)
    current = data_points[-1]["value"]
    metrics["gt_current"] = current

    # Calculate growth for different periods
    now = datetime.now()
    periods = {
        "gt_5yr_pct": timedelta(days=5*365),
        "gt_1yr_pct": timedelta(days=365),
        "gt_3mo_pct": timedelta(days=90),
        "gt_1wk_pct": timedelta(days=7),
    }

    # For 5-year data, estimate dates based on position
    total_points = len(data_points)

    for metric_name, delta in periods.items():
        try:
            # Estimate which index corresponds to this time period
            days_back = delta.days
            # Assuming 5 years of data = ~260 weekly points or ~1825 daily points
            # Rough estimate: position = total_points * (1 - days_back / (5*365))
            fraction = days_back / (5 * 365)
            index = int(total_points * (1 - fraction))
            index = max(0, min(index, total_points - 1))

            past_value = data_points[index]["value"]

            if past_value > 0:
                growth = ((current - past_value) / past_value) * 100
                metrics[metric_name] = round(growth, 1)
            elif current > 0:
                metrics[metric_name] = 100  # Went from 0 to something = 100% growth (conservative)

        except:
            continue

    return metrics


def validate_keywords(keywords: list, max_keywords: int = None) -> pd.DataFrame:
    """
    VALIDATION: Get growth metrics for a list of keywords.

    For each keyword, calculates 5yr/1yr/3mo/1wk growth from Google Trends.
    """
    if max_keywords:
        keywords = keywords[:max_keywords]

    print(f"\n  Validating {len(keywords)} keywords with Google Trends...")

    validated = []
    for i, kw_data in enumerate(keywords, 1):
        keyword = kw_data.get("keyword", "") if isinstance(kw_data, dict) else str(kw_data)
        if not keyword:
            continue

        print(f"    [{i}/{len(keywords)}] {keyword[:40]}...")

        # Get interest over time (5 years)
        interest = get_interest_over_time(keyword, geo="US", timeframe="today 5-y")
        metrics = calculate_growth_metrics(interest)

        # Combine discovery data with validation metrics
        result = kw_data.copy() if isinstance(kw_data, dict) else {"keyword": keyword}
        result.update(metrics)
        validated.append(result)

    return pd.DataFrame(validated)


def discover_all(max_seeds: int = 10, geo: str = "US") -> list:
    """
    Run discovery using seed keywords to find related rising queries.

    This approach is more reliable than the trending_now endpoint.
    """
    seeds = SEED_KEYWORDS[:max_seeds]

    print(f"\n  Discovering from {len(seeds)} seed keywords...")

    all_keywords = []
    seen = set()

    for i, seed in enumerate(seeds, 1):
        print(f"\n    [{i}/{len(seeds)}] Seed: '{seed}'")

        # Get related rising queries
        keywords = discover_related_queries(seed, geo=geo)
        new_count = 0

        for kw in keywords:
            keyword = kw.get("keyword", "").lower()
            if keyword and keyword not in seen and len(keyword) > 2:
                seen.add(keyword)
                kw["seed"] = seed
                all_keywords.append(kw)
                new_count += 1

        print(f"        → Found {new_count} new keywords ({len(all_keywords)} total)")

    print(f"\n  Total unique keywords discovered: {len(all_keywords)}")
    return all_keywords


def run_full_pipeline(max_discover: int = 100, max_validate: int = 50) -> pd.DataFrame:
    """
    Full pipeline: Discover → Validate → Output.
    """
    print("\n" + "=" * 50)
    print("GOOGLE TRENDS PIPELINE")
    print("=" * 50)

    # Step 1: Discovery
    print("\n[1/2] DISCOVERY - Finding trending keywords...")
    keywords = discover_all(max_per_category=max_discover // len(DISCOVERY_CATEGORIES))

    if not keywords:
        print("ERROR: No keywords discovered")
        return pd.DataFrame()

    # Step 2: Validation
    print(f"\n[2/2] VALIDATION - Getting growth metrics for top {max_validate}...")
    df = validate_keywords(keywords, max_keywords=max_validate)

    if len(df) > 0:
        # Add metadata
        df["source"] = "google_trends"
        df["validated_at"] = datetime.now().isoformat()

        # Sort by current interest (descending)
        if "gt_current" in df.columns:
            df = df.sort_values("gt_current", ascending=False, na_position="last")

        # Save
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n  Saved {len(df)} keywords to {OUTPUT_FILE}")

    return df


def test_pipeline():
    """Test with limited data."""
    print("\n[TEST MODE] Limited discovery and validation")

    # Test with 3 seeds, validate only 5 keywords
    keywords = discover_all(max_seeds=3, geo="US")
    df = validate_keywords(keywords, max_keywords=5)

    if len(df) > 0:
        df.to_csv(OUTPUT_FILE, index=False)
        print("\n" + "=" * 50)
        print("SAMPLE OUTPUT:")
        print("=" * 50)
        cols = ["keyword", "growth_pct", "gt_current", "gt_1yr_pct", "gt_3mo_pct"]
        available_cols = [c for c in cols if c in df.columns]
        print(df[available_cols].to_string())

    return df


def main():
    """Run full pipeline."""
    df = run_full_pipeline(max_discover=200, max_validate=100)

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total keywords: {len(df)}")
    print(f"Output: {OUTPUT_FILE}")

    if len(df) > 0 and "gt_1yr_pct" in df.columns:
        print("\nTop 10 by 1-year growth:")
        top = df.nlargest(10, "gt_1yr_pct", "all")
        print(top[["keyword", "gt_current", "gt_1yr_pct", "gt_3mo_pct"]].to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Trends Discovery & Validation")
    parser.add_argument("--test", action="store_true", help="Test with limited data")
    parser.add_argument("--discover-only", action="store_true", help="Only run discovery")
    parser.add_argument("--max-validate", type=int, default=100, help="Max keywords to validate")
    args = parser.parse_args()

    if args.test:
        test_pipeline()
    elif args.discover_only:
        keywords = discover_all()
        df = pd.DataFrame(keywords)
        df.to_csv(OUTPUT_FILE.with_name("discovered_keywords.csv"), index=False)
        print(f"Saved {len(df)} discovered keywords")
    else:
        main()
