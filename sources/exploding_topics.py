#!/usr/bin/env python3
"""
Exploding Topics Scraper

Discovers trending topics with growth metrics from explodingtopics.com.
This is a DISCOVERY source - finds keywords we don't know about.

Output: data/processed/exploding_topics.csv
"""
import json
import time
import re
import argparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Constants
BASE_URL = "https://explodingtopics.com"
RAW_DIR = config.RAW_DIR / "exploding"
OUTPUT_FILE = config.PROCESSED_DIR / "exploding_topics.csv"

# Rate limiting
REQUEST_DELAY = 2  # seconds between requests

# Categories to scrape (empty = all from main page)
CATEGORIES = [
    "",  # Main trending page
    "/topic/beauty",
    "/topic/business",
    "/topic/design",
    "/topic/ecommerce",
    "/topic/fashion",
    "/topic/finance",
    "/topic/fitness",
    "/topic/food",
    "/topic/gaming",
    "/topic/health",
    "/topic/lifestyle",
    "/topic/marketing",
    "/topic/pets",
    "/topic/social-media",
    "/topic/software",
    "/topic/sports",
    "/topic/tech",
    "/topic/travel",
]


def get_headers():
    """Get browser-like headers."""
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def fetch_page(url: str, save_name: str = None) -> BeautifulSoup:
    """Fetch a page with rate limiting."""
    print(f"  Fetching: {url[:60]}...")

    try:
        response = requests.get(url, headers=get_headers(), timeout=30)
        response.raise_for_status()

        # Save raw HTML if requested
        if save_name:
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            raw_path = RAW_DIR / f"{save_name}.html"
            raw_path.write_text(response.text, encoding="utf-8")

        time.sleep(REQUEST_DELAY)
        return BeautifulSoup(response.text, "lxml")

    except requests.exceptions.RequestException as e:
        print(f"  ERROR: {e}")
        time.sleep(REQUEST_DELAY)
        return None


def extract_topics_from_page(soup: BeautifulSoup, category: str) -> list:
    """Extract topic data from an Exploding Topics page."""
    topics = []

    # Exploding Topics uses various structures - try multiple selectors
    # Look for topic cards/rows
    selectors = [
        'div[class*="topic"]',
        'tr[class*="topic"]',
        'a[href*="/topic/"]',
        '.trend-card',
        'div[class*="trend"]',
        'div[class*="card"]',
    ]

    items = []
    for selector in selectors:
        items = soup.select(selector)
        if len(items) > 5:  # Found a good set
            break

    for item in items:
        try:
            topic = extract_single_topic(item, category)
            if topic and topic.get("keyword"):
                topics.append(topic)
        except Exception as e:
            continue

    return topics


def extract_single_topic(item, category: str) -> dict:
    """Extract data from a single topic element."""
    topic = {
        "keyword": None,
        "category": category or "trending",
        "growth_pct": None,
        "growth_status": None,  # e.g., "Exploding", "Regular", "Peaked"
        "search_volume": None,
        "months_trending": None,
        "url": None,
    }

    # Get topic name - usually in a link or heading
    name_selectors = [
        'a[href*="/topic/"]',
        'h2', 'h3', 'h4',
        '.topic-name',
        '.trend-name',
        'span[class*="name"]',
    ]
    for selector in name_selectors:
        elem = item.select_one(selector)
        if elem:
            name = elem.get_text(strip=True)
            # Clean up name
            if name and len(name) > 1 and len(name) < 100:
                topic["keyword"] = name
                # Get URL if it's a link
                if elem.name == 'a':
                    href = elem.get("href", "")
                    if href.startswith("/"):
                        topic["url"] = BASE_URL + href
                    elif href.startswith("http"):
                        topic["url"] = href
                break

    # Get growth percentage
    growth_patterns = [
        r'(\d+(?:,\d+)?)\s*%',  # "234%" or "1,234%"
        r'\+(\d+(?:,\d+)?)',    # "+234"
    ]

    # Look for growth in various elements
    growth_selectors = [
        'span[class*="growth"]',
        'span[class*="percent"]',
        'div[class*="growth"]',
        '.growth',
        '.change',
    ]

    for selector in growth_selectors:
        elem = item.select_one(selector)
        if elem:
            text = elem.get_text(strip=True)
            for pattern in growth_patterns:
                match = re.search(pattern, text)
                if match:
                    topic["growth_pct"] = int(match.group(1).replace(",", ""))
                    break
            if topic["growth_pct"]:
                break

    # If no growth found in specific elements, search entire item text
    if not topic["growth_pct"]:
        item_text = item.get_text()
        for pattern in growth_patterns:
            match = re.search(pattern, item_text)
            if match:
                topic["growth_pct"] = int(match.group(1).replace(",", ""))
                break

    # Get growth status (Exploding, Regular, Peaked)
    status_keywords = ["exploding", "regular", "peaked", "trending", "growing"]
    item_text_lower = item.get_text().lower()
    for status in status_keywords:
        if status in item_text_lower:
            topic["growth_status"] = status.capitalize()
            break

    # Get search volume if available
    volume_match = re.search(r'(\d+(?:,\d+)?(?:K|M)?)\s*(?:searches?|volume)', item.get_text(), re.I)
    if volume_match:
        vol_str = volume_match.group(1).replace(",", "")
        if 'K' in vol_str:
            topic["search_volume"] = int(float(vol_str.replace('K', '')) * 1000)
        elif 'M' in vol_str:
            topic["search_volume"] = int(float(vol_str.replace('M', '')) * 1000000)
        else:
            topic["search_volume"] = int(vol_str)

    return topic


def try_api_approach() -> pd.DataFrame:
    """Try to get data via any available API endpoints."""
    print("\n  Trying API approach...")

    # Exploding Topics might have API endpoints
    api_urls = [
        f"{BASE_URL}/api/trends",
        f"{BASE_URL}/api/topics",
        f"{BASE_URL}/api/v1/trends",
    ]

    for url in api_urls:
        try:
            response = requests.get(url, headers=get_headers(), timeout=15)
            if response.status_code == 200:
                data = response.json()
                print(f"  Found API: {url}")
                return pd.DataFrame(data)
        except:
            continue

    return None


def scrape_all_categories(max_categories: int = None) -> pd.DataFrame:
    """Scrape Exploding Topics across all categories."""
    print("\n[Exploding Topics Scraper]")
    print("=" * 50)

    # Ensure raw directory exists
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Try API first
    api_df = try_api_approach()
    if api_df is not None and len(api_df) > 0:
        print(f"  Got {len(api_df)} topics from API")
        return api_df

    # Fall back to scraping
    categories = CATEGORIES
    if max_categories:
        categories = categories[:max_categories]

    print(f"\n  Scraping {len(categories)} category pages...")

    all_topics = []
    seen_keywords = set()

    for i, cat_path in enumerate(categories, 1):
        cat_name = cat_path.replace("/topic/", "") if cat_path else "main"
        print(f"\n  [{i}/{len(categories)}] {cat_name}")

        url = BASE_URL + cat_path if cat_path else BASE_URL
        soup = fetch_page(url, f"category_{cat_name}")

        if soup:
            topics = extract_topics_from_page(soup, cat_name)
            # Deduplicate
            for t in topics:
                if t["keyword"] and t["keyword"].lower() not in seen_keywords:
                    seen_keywords.add(t["keyword"].lower())
                    all_topics.append(t)
            print(f"      → Found {len(topics)} topics ({len(all_topics)} total unique)")
        else:
            print(f"      → Failed to fetch")

    # Convert to DataFrame
    df = pd.DataFrame(all_topics)

    if len(df) > 0:
        # Add metadata
        df["source"] = "exploding_topics"
        df["scraped_at"] = datetime.now().isoformat()

        # Sort by growth
        df = df.sort_values("growth_pct", ascending=False, na_position="last")

        # Save to CSV
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n  Saved {len(df)} topics to {OUTPUT_FILE}")
    else:
        print("\nWARNING: No topics extracted")

    return df


def test_scraper():
    """Test with limited categories."""
    print("\n[TEST MODE] Scraping 3 categories only")
    df = scrape_all_categories(max_categories=3)

    if len(df) > 0:
        print("\n" + "=" * 50)
        print("SAMPLE OUTPUT:")
        print("=" * 50)
        cols = ["keyword", "category", "growth_pct", "growth_status"]
        available_cols = [c for c in cols if c in df.columns]
        print(df[available_cols].head(15).to_string())

    return df


def main():
    """Run full scrape."""
    df = scrape_all_categories()

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total topics: {len(df)}")
    print(f"Categories: {df['category'].nunique() if len(df) > 0 else 0}")
    print(f"Output: {OUTPUT_FILE}")

    if len(df) > 0:
        print("\nTop 15 by growth:")
        cols = ["keyword", "category", "growth_pct"]
        available_cols = [c for c in cols if c in df.columns]
        print(df[available_cols].head(15).to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exploding Topics Scraper")
    parser.add_argument("--test", action="store_true", help="Test with 3 categories only")
    args = parser.parse_args()

    if args.test:
        test_scraper()
    else:
        main()
