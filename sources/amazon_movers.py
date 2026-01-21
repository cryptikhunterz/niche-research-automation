#!/usr/bin/env python3
"""
Amazon Movers & Shakers Scraper

Discovers products with biggest sales rank improvements across ALL categories.
This is a DISCOVERY source - finds keywords we don't know about.

Output: data/processed/amazon_movers.csv
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
from fake_useragent import UserAgent

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Constants
BASE_URL = "https://www.amazon.com"
MOVERS_URL = f"{BASE_URL}/gp/movers-and-shakers"
RAW_DIR = config.RAW_DIR / "amazon"
OUTPUT_FILE = config.PROCESSED_DIR / "amazon_movers.csv"

# Rate limiting
REQUEST_DELAY = 3  # seconds between requests


# Global session to maintain cookies
_session = None


def get_session():
    """Get or create a requests session with browser-like settings."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "Cache-Control": "max-age=0",
        })
        # Warm up session by hitting amazon.com first
        try:
            print("  Warming up session...")
            _session.get("https://www.amazon.com", timeout=15)
            time.sleep(2)
        except:
            pass
    return _session


def fetch_page(url: str, save_name: str = None, retries: int = 2) -> BeautifulSoup:
    """Fetch a page with rate limiting, retries, and optional raw save."""
    print(f"  Fetching: {url[:80]}...")
    session = get_session()

    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=30)

            # Check for blocking
            if response.status_code == 429:
                wait_time = REQUEST_DELAY * (attempt + 2) * 2
                print(f"  Rate limited (429). Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue

            if response.status_code == 503:
                print(f"  Service unavailable (503). Attempt {attempt + 1}/{retries + 1}")
                time.sleep(REQUEST_DELAY * 3)
                continue

            response.raise_for_status()

            # Check for CAPTCHA
            if "captcha" in response.text.lower() or "robot" in response.text.lower():
                print(f"  CAPTCHA detected. Attempt {attempt + 1}/{retries + 1}")
                time.sleep(REQUEST_DELAY * 5)
                continue

            # Save raw HTML if requested
            if save_name:
                raw_path = RAW_DIR / f"{save_name}.html"
                raw_path.write_text(response.text, encoding="utf-8")

            time.sleep(REQUEST_DELAY)
            return BeautifulSoup(response.text, "lxml")

        except requests.exceptions.RequestException as e:
            print(f"  ERROR: {e}")
            if attempt < retries:
                time.sleep(REQUEST_DELAY * (attempt + 2))
            continue

    print(f"  Failed after {retries + 1} attempts")
    return None


def get_category_links(soup: BeautifulSoup) -> list:
    """Extract all category links from Movers & Shakers main page."""
    categories = []

    # Look for department links in the sidebar or main content
    # Amazon uses various class names, try multiple selectors
    selectors = [
        'a[href*="/gp/movers-and-shakers/"]',
        '.zg_homeWidget a',
        '#zg_browseRoot a',
        'div[role="treeitem"] a',
    ]

    for selector in selectors:
        links = soup.select(selector)
        for link in links:
            href = link.get("href", "")
            text = link.get_text(strip=True)

            # Filter to actual category pages
            if "/gp/movers-and-shakers/" in href and text and len(text) > 1:
                # Build full URL
                if href.startswith("/"):
                    href = BASE_URL + href

                # Skip duplicates and the main page itself
                if href != MOVERS_URL and href not in [c["url"] for c in categories]:
                    categories.append({
                        "name": text,
                        "url": href
                    })

    return categories


def extract_products(soup: BeautifulSoup, category: str) -> list:
    """Extract product data from a Movers & Shakers category page."""
    products = []

    # Find product containers - Amazon uses various structures
    # Try multiple selectors
    item_selectors = [
        'div[data-asin]',
        '.zg-item-immersion',
        '#zg-ordered-list li',
        '.a-carousel-card',
    ]

    items = []
    for selector in item_selectors:
        items = soup.select(selector)
        if items:
            break

    for item in items:
        try:
            product = extract_single_product(item, category)
            if product and product.get("name"):
                products.append(product)
        except Exception as e:
            continue  # Skip problematic items

    return products


def extract_single_product(item, category: str) -> dict:
    """Extract data from a single product item."""
    product = {
        "category": category,
        "name": None,
        "asin": None,
        "rank": None,
        "rank_change_pct": None,
        "price": None,
        "reviews_count": None,
        "rating": None,
        "url": None,
    }

    # ASIN
    product["asin"] = item.get("data-asin", "")

    # Product name - try multiple selectors
    name_selectors = [
        '.p13n-sc-truncate',
        '.a-link-normal span',
        'a.a-link-normal',
        '.zg-text-center-align',
        'span.a-size-small',
    ]
    for selector in name_selectors:
        name_elem = item.select_one(selector)
        if name_elem:
            name = name_elem.get_text(strip=True)
            if name and len(name) > 3:
                product["name"] = name[:200]  # Truncate long names
                break

    # Rank change percentage - look for the green/red percentage
    rank_selectors = [
        '.zg-percent-change',
        '.a-size-small.a-color-success',
        '.a-color-success',
        'span[class*="percent"]',
    ]
    for selector in rank_selectors:
        rank_elem = item.select_one(selector)
        if rank_elem:
            rank_text = rank_elem.get_text(strip=True)
            # Extract number from text like "+234%" or "234%"
            match = re.search(r'[\+\-]?(\d+(?:,\d+)?)', rank_text)
            if match:
                product["rank_change_pct"] = int(match.group(1).replace(",", ""))
                break

    # Rank number
    rank_num_selectors = [
        '.zg-badge-text',
        '.zg-rank',
        'span.a-badge-text',
    ]
    for selector in rank_num_selectors:
        rank_elem = item.select_one(selector)
        if rank_elem:
            rank_text = rank_elem.get_text(strip=True)
            match = re.search(r'#?(\d+)', rank_text)
            if match:
                product["rank"] = int(match.group(1))
                break

    # Price
    price_selectors = [
        '.p13n-sc-price',
        '.a-price .a-offscreen',
        'span.a-price',
    ]
    for selector in price_selectors:
        price_elem = item.select_one(selector)
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
            if match:
                product["price"] = float(match.group(1).replace(",", ""))
                break

    # Reviews count
    review_selectors = [
        'span.a-size-small[aria-label*="stars"]',
        '.a-icon-alt',
    ]
    for selector in review_selectors:
        review_elem = item.select_one(selector)
        if review_elem:
            review_text = review_elem.get("aria-label", "") or review_elem.get_text()
            # Extract rating
            rating_match = re.search(r'([\d.]+)\s*out of\s*5', review_text)
            if rating_match:
                product["rating"] = float(rating_match.group(1))
            # Extract count
            count_match = re.search(r'([\d,]+)\s*(?:ratings?|reviews?)', review_text, re.I)
            if count_match:
                product["reviews_count"] = int(count_match.group(1).replace(",", ""))
            break

    # Product URL
    link = item.select_one('a.a-link-normal[href*="/dp/"]')
    if link:
        href = link.get("href", "")
        if href.startswith("/"):
            href = BASE_URL + href
        product["url"] = href.split("?")[0]  # Remove query params

    return product


def scrape_all_categories(max_categories: int = None) -> pd.DataFrame:
    """Scrape Movers & Shakers across all categories."""
    print("\n[Amazon Movers & Shakers Scraper]")
    print("=" * 50)

    # Ensure raw directory exists
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Get main page
    print("\n1. Fetching main Movers & Shakers page...")
    main_soup = fetch_page(MOVERS_URL, "main_page")

    if not main_soup:
        print("ERROR: Could not fetch main page")
        return pd.DataFrame()

    # Extract category links
    categories = get_category_links(main_soup)
    print(f"   Found {len(categories)} categories")

    if max_categories:
        categories = categories[:max_categories]
        print(f"   (Limited to {max_categories} for testing)")

    # Scrape each category
    all_products = []
    print(f"\n2. Scraping {len(categories)} categories...")

    for i, cat in enumerate(categories, 1):
        print(f"\n   [{i}/{len(categories)}] {cat['name']}")

        soup = fetch_page(cat["url"], f"category_{i}_{cat['name'][:20]}")
        if soup:
            products = extract_products(soup, cat["name"])
            print(f"       → Found {len(products)} products")
            all_products.extend(products)
        else:
            print(f"       → Failed to fetch")

    # Convert to DataFrame
    df = pd.DataFrame(all_products)

    if len(df) > 0:
        # Add metadata
        df["source"] = "amazon_movers"
        df["scraped_at"] = datetime.now().isoformat()

        # Create keyword column from product name
        df["keyword"] = df["name"].apply(extract_keyword)

        # Sort by rank change
        df = df.sort_values("rank_change_pct", ascending=False, na_position="last")

        # Save to CSV
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n3. Saved {len(df)} products to {OUTPUT_FILE}")
    else:
        print("\nWARNING: No products extracted")

    return df


def extract_keyword(name: str) -> str:
    """Extract a searchable keyword from product name."""
    if not name:
        return ""

    # Remove common suffixes and clean up
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name)  # Remove parentheticals
    name = re.sub(r'\s*-\s*.*$', '', name)  # Remove everything after dash
    name = re.sub(r'\s*,\s*.*$', '', name)  # Remove everything after comma
    name = re.sub(r'\d+\s*(pack|count|oz|ml|lb|kg|inch|cm)\b.*$', '', name, flags=re.I)

    # Take first 5 words max
    words = name.split()[:5]
    return " ".join(words).strip()


def test_scraper():
    """Test with limited categories."""
    print("\n[TEST MODE] Scraping 3 categories only")
    df = scrape_all_categories(max_categories=3)

    if len(df) > 0:
        print("\n" + "=" * 50)
        print("SAMPLE OUTPUT:")
        print("=" * 50)
        print(df[["keyword", "category", "rank_change_pct", "price"]].head(10).to_string())

    return df


def main():
    """Run full scrape."""
    df = scrape_all_categories()

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total products: {len(df)}")
    print(f"Categories: {df['category'].nunique() if len(df) > 0 else 0}")
    print(f"Output: {OUTPUT_FILE}")

    if len(df) > 0:
        print("\nTop 10 by rank change:")
        print(df[["keyword", "category", "rank_change_pct"]].head(10).to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Amazon Movers & Shakers Scraper")
    parser.add_argument("--test", action="store_true", help="Test with 3 categories only")
    args = parser.parse_args()

    if args.test:
        test_scraper()
    else:
        main()
