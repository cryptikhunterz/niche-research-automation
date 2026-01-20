#!/usr/bin/env python3
"""
Category Discovery Script
Explores Google Trends across multiple categories to find high-growth niches.
Uses suggestions endpoint (not rate limited) + batched trend analysis.
"""

import pandas as pd
import time
import os
from datetime import datetime
from pytrends.request import TrendReq

# ═══════════════════════════════════════════════════════════════
# DISCOVERY SEEDS - Broad terms to explore across categories
# ═══════════════════════════════════════════════════════════════

DISCOVERY_SEEDS = {
    # Keep existing health (already validated)
    "health_supplements": [
        "supplement", "vitamin", "magnesium", "adaptogen", "probiotic"
    ],

    # NEW CATEGORIES
    "home_kitchen": [
        "kitchen gadget", "air fryer", "food storage", "organization",
        "home decor", "cleaning product", "smart home"
    ],
    "pet_products": [
        "dog toy", "cat food", "pet supplement", "pet grooming",
        "dog training", "pet bed", "aquarium"
    ],
    "outdoor_camping": [
        "camping gear", "hiking", "outdoor cooking", "survival gear",
        "fishing", "hunting", "backpack"
    ],
    "baby_parenting": [
        "baby product", "toddler", "baby food", "stroller",
        "nursery", "baby monitor", "teething"
    ],
    "hobby_craft": [
        "craft supplies", "knitting", "painting", "3d printing",
        "woodworking", "sewing", "resin art"
    ],
    "fitness_equipment": [
        "home gym", "resistance band", "yoga mat", "kettlebell",
        "massage gun", "fitness tracker", "recovery"
    ],
    "tech_accessories": [
        "phone accessory", "laptop stand", "cable organizer",
        "portable charger", "webcam", "microphone", "ring light"
    ],
    "automotive": [
        "car accessory", "car cleaning", "dash cam", "car organizer",
        "phone mount", "car charger", "seat cover"
    ],
    "fashion_accessories": [
        "jewelry", "watch", "sunglasses", "bag", "wallet",
        "hair accessory", "belt"
    ],
    "gaming": [
        "gaming chair", "gaming mouse", "gaming headset", "controller",
        "gaming desk", "stream deck", "gaming glasses"
    ],
    "office_wfh": [
        "standing desk", "ergonomic chair", "desk organizer",
        "monitor arm", "keyboard", "desk lamp", "whiteboard"
    ]
}

# Rate limiting for trends queries (suggestions don't need this)
TRENDS_DELAY = 20  # Seconds between trend requests
MAX_TRENDS_PER_SESSION = 30  # Stop after this many to avoid bans

# Output
OUTPUT_FILE = "discovered_keywords.csv"
TRENDS_OUTPUT = "discovered_trends.csv"


# ═══════════════════════════════════════════════════════════════
# PHASE 1: SUGGESTIONS DISCOVERY (Not rate limited)
# ═══════════════════════════════════════════════════════════════

def discover_keywords_via_suggestions(pytrends: TrendReq) -> list:
    """Use suggestions endpoint to find product keywords."""

    print("=" * 60)
    print("PHASE 1: KEYWORD DISCOVERY VIA SUGGESTIONS")
    print("=" * 60)

    all_discoveries = []

    for category, seeds in DISCOVERY_SEEDS.items():
        print(f"\n[{category.upper()}]")

        for seed in seeds:
            try:
                suggestions = pytrends.suggestions(seed)

                # Filter for product-like suggestions
                for s in suggestions:
                    stype = s.get('type', '')
                    title = s.get('title', '')
                    mid = s.get('mid', '')

                    # Keep products, topics, and some specific types
                    if stype in ['Product', 'Topic', 'Product line', 'Brand',
                                 'Consumer product', 'Type of product']:
                        discovery = {
                            'keyword': title,
                            'seed': seed,
                            'category': category,
                            'type': stype,
                            'mid': mid
                        }
                        all_discoveries.append(discovery)
                        print(f"  + {title} ({stype})")

                time.sleep(0.5)  # Light delay for suggestions

            except Exception as e:
                print(f"  ! Error with '{seed}': {e}")

    # Deduplicate by keyword
    seen = set()
    unique = []
    for d in all_discoveries:
        if d['keyword'].lower() not in seen:
            seen.add(d['keyword'].lower())
            unique.append(d)

    print(f"\n{'=' * 60}")
    print(f"Discovered {len(unique)} unique keywords from {len(all_discoveries)} total")

    return unique


# ═══════════════════════════════════════════════════════════════
# PHASE 2: TREND ANALYSIS (Rate limited - careful!)
# ═══════════════════════════════════════════════════════════════

def analyze_keyword_trends(pytrends: TrendReq, keywords: list, max_keywords: int = 30) -> list:
    """Get trend data for discovered keywords. RATE LIMITED."""

    print("\n" + "=" * 60)
    print("PHASE 2: TREND ANALYSIS (Rate Limited)")
    print(f"Analyzing top {max_keywords} keywords")
    print("=" * 60)

    results = []

    # Take a sample to avoid rate limits
    sample = keywords[:max_keywords]

    for i, kw_data in enumerate(sample):
        keyword = kw_data['keyword']
        print(f"\n({i+1}/{len(sample)}) {keyword}...", end=" ", flush=True)

        try:
            pytrends.build_payload([keyword], timeframe='today 5-y', geo='US')
            df = pytrends.interest_over_time()

            if df.empty:
                print("No data")
                continue

            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])

            # Calculate growth
            current = df[keyword].iloc[-1]
            yr1_ago = df[keyword].iloc[-52] if len(df) > 52 else df[keyword].iloc[0]
            yr5_ago = df[keyword].iloc[0]

            growth_1yr = calculate_growth(current, yr1_ago)
            growth_5yr = calculate_growth(current, yr5_ago)

            result = {
                **kw_data,
                'current_interest': current,
                'growth_1yr': growth_1yr,
                'growth_5yr': growth_5yr,
                'score': (growth_1yr * 0.6) + (growth_5yr * 0.4)
            }
            results.append(result)

            print(f"Interest: {current}, 1yr: {growth_1yr:.0f}%, 5yr: {growth_5yr:.0f}%")

        except Exception as e:
            if '429' in str(e):
                print(f"RATE LIMITED - stopping early")
                break
            print(f"Error: {e}")

        time.sleep(TRENDS_DELAY)

    return results


def calculate_growth(current: float, past: float) -> float:
    """Calculate growth percentage."""
    if past <= 0:
        return 10000 if current > 0 else 0
    growth = ((current - past) / past) * 100
    return min(growth, 10000)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("CATEGORY DISCOVERY SCRIPT")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    pytrends = TrendReq(hl='en-US', tz=360)

    # Phase 1: Discover keywords (fast, not rate limited)
    discoveries = discover_keywords_via_suggestions(pytrends)

    # Save discoveries
    df_disc = pd.DataFrame(discoveries)
    df_disc.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved discoveries to: {OUTPUT_FILE}")

    # Phase 2: Analyze trends (slow, rate limited)
    print("\n" + "-" * 60)
    proceed = input("Proceed with trend analysis? (y/n): ").strip().lower()

    if proceed == 'y':
        trends = analyze_keyword_trends(pytrends, discoveries, MAX_TRENDS_PER_SESSION)

        if trends:
            df_trends = pd.DataFrame(trends)
            df_trends = df_trends.sort_values('score', ascending=False)
            df_trends.to_csv(TRENDS_OUTPUT, index=False)
            print(f"\nSaved trends to: {TRENDS_OUTPUT}")

            # Print top results
            print("\n" + "=" * 60)
            print("TOP DISCOVERIES BY GROWTH")
            print("=" * 60)
            for _, row in df_trends.head(20).iterrows():
                print(f"\n{row['keyword']} ({row['category']})")
                print(f"  Interest: {row['current_interest']}, 1yr: {row['growth_1yr']:.0f}%, 5yr: {row['growth_5yr']:.0f}%")
    else:
        print("\nSkipped trend analysis. Run later with discovered keywords.")

    print("\n" + "=" * 60)
    print(f"COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
