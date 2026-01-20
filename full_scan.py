#!/usr/bin/env python3
"""
Full Keyword Scan - All 158 keywords across all categories
Combines health seeds + discovered keywords
"""

import pandas as pd
import time
import os
from datetime import datetime
from pytrends.request import TrendReq

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Health seeds (original 47)
HEALTH_KEYWORDS = {
    "supplements": [
        "magnesium glycinate", "magnesium threonate", "ashwagandha",
        "l-theanine", "vitamin d3", "zinc", "omega 3", "probiotics",
        "berberine", "creatine"
    ],
    "womens_health": [
        "hormone balance", "cycle syncing", "PCOS", "spearmint tea",
        "myo-inositol", "seed cycling", "DIM supplement", "vitex"
    ],
    "gut_health": [
        "gut health", "bloating relief", "digestive enzymes", "bone broth",
        "l-glutamine", "leaky gut", "SIBO", "castor oil pack"
    ],
    "sleep_stress": [
        "nervous system regulation", "cortisol", "burnout recovery",
        "sleep supplements", "melatonin alternatives", "GABA", "adaptogens"
    ],
    "natural_beauty": [
        "gua sha", "face massage", "natural botox", "retinol alternative",
        "hyaluronic acid", "collagen peptides", "red light therapy"
    ],
    "mens_optimization": [
        "tongkat ali", "fadogia agrestis", "testosterone booster",
        "alpha gpc", "l-tyrosine", "shilajit", "turkesterone"
    ]
}

# Rate limiting
REQUEST_DELAY = 18  # Increased for safety
MAX_RETRIES = 3
RETRY_DELAY = 45  # Longer backoff

# Scoring weights
WEIGHTS = {'1mo': 0.30, '3mo': 0.25, '6mo': 0.20, '1yr': 0.15, '5yr': 0.10}

# Thresholds
MIN_GROWTH_THRESHOLD = 300
MAX_GROWTH_CAP = 10000

# Output
OUTPUT_FILE = "full_scan_results.csv"
CHECKPOINT_FILE = "full_scan_checkpoint.csv"
CHECKPOINT_INTERVAL = 5


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def calculate_growth(current: float, past: float) -> float:
    if past <= 0:
        return MAX_GROWTH_CAP if current > 0 else 0
    growth = ((current - past) / past) * 100
    return min(growth, MAX_GROWTH_CAP)


def get_time_periods(df: pd.DataFrame, keyword: str) -> dict:
    if df.empty:
        return None
    current = df[keyword].iloc[-1]
    return {
        'current': current,
        '1mo_ago': df[keyword].iloc[-5] if len(df) > 5 else df[keyword].iloc[0],
        '3mo_ago': df[keyword].iloc[-13] if len(df) > 13 else df[keyword].iloc[0],
        '6mo_ago': df[keyword].iloc[-26] if len(df) > 26 else df[keyword].iloc[0],
        '1yr_ago': df[keyword].iloc[-52] if len(df) > 52 else df[keyword].iloc[0],
        '5yr_ago': df[keyword].iloc[0]
    }


def calculate_score(g: dict) -> float:
    return round(
        g.get('growth_1mo', 0) * WEIGHTS['1mo'] +
        g.get('growth_3mo', 0) * WEIGHTS['3mo'] +
        g.get('growth_6mo', 0) * WEIGHTS['6mo'] +
        g.get('growth_1yr', 0) * WEIGHTS['1yr'] +
        g.get('growth_5yr', 0) * WEIGHTS['5yr'], 2
    )


def passes_threshold(r: dict) -> bool:
    if r.get('error'):
        return False
    return any([
        r['growth_5yr'] >= MIN_GROWTH_THRESHOLD,
        r['growth_1yr'] >= MIN_GROWTH_THRESHOLD,
        r['growth_6mo'] >= MIN_GROWTH_THRESHOLD,
        r['growth_3mo'] >= MIN_GROWTH_THRESHOLD,
        r['growth_1mo'] >= MIN_GROWTH_THRESHOLD
    ])


def load_checkpoint() -> tuple:
    if os.path.exists(CHECKPOINT_FILE):
        df = pd.read_csv(CHECKPOINT_FILE)
        results = df.to_dict('records')
        processed = set(df['keyword'].str.lower().tolist())
        return results, processed
    return [], set()


def save_checkpoint(results: list):
    if results:
        pd.DataFrame(results).to_csv(CHECKPOINT_FILE, index=False)


def get_keyword_data(pytrends: TrendReq, keyword: str, category: str) -> dict:
    result = {
        'keyword': keyword,
        'category': category,
        'current_interest': 0,
        'growth_5yr': 0, 'growth_1yr': 0, 'growth_6mo': 0,
        'growth_3mo': 0, 'growth_1mo': 0,
        'related_queries': '', 'rising_queries': '',
        'recommendation_score': 0, 'error': None
    }

    for attempt in range(MAX_RETRIES):
        try:
            pytrends.build_payload([keyword], timeframe='today 5-y', geo='US')
            df = pytrends.interest_over_time()

            if df.empty:
                result['error'] = 'No data'
                return result

            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])

            periods = get_time_periods(df, keyword)
            if periods:
                result['current_interest'] = periods['current']
                result['growth_5yr'] = calculate_growth(periods['current'], periods['5yr_ago'])
                result['growth_1yr'] = calculate_growth(periods['current'], periods['1yr_ago'])
                result['growth_6mo'] = calculate_growth(periods['current'], periods['6mo_ago'])
                result['growth_3mo'] = calculate_growth(periods['current'], periods['3mo_ago'])
                result['growth_1mo'] = calculate_growth(periods['current'], periods['1mo_ago'])

            time.sleep(2)

            try:
                related = pytrends.related_queries()
                if keyword in related:
                    if related[keyword]['top'] is not None:
                        result['related_queries'] = '; '.join(
                            related[keyword]['top']['query'].head(5).tolist()
                        )
                    if related[keyword]['rising'] is not None:
                        result['rising_queries'] = '; '.join(
                            related[keyword]['rising']['query'].head(5).tolist()
                        )
            except:
                pass

            result['recommendation_score'] = calculate_score({
                'growth_1mo': result['growth_1mo'],
                'growth_3mo': result['growth_3mo'],
                'growth_6mo': result['growth_6mo'],
                'growth_1yr': result['growth_1yr'],
                'growth_5yr': result['growth_5yr']
            })

            return result

        except Exception as e:
            if '429' in str(e) or 'rate' in str(e).lower():
                print(f" [Rate limit, waiting {RETRY_DELAY}s...]", end="", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                result['error'] = str(e)[:50]
                return result

    result['error'] = 'Max retries'
    return result


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("FULL KEYWORD SCAN - 158 Keywords")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Build keyword list
    all_keywords = []

    # Add health keywords
    for category, keywords in HEALTH_KEYWORDS.items():
        for kw in keywords:
            all_keywords.append({'keyword': kw, 'category': category})

    # Add discovered keywords
    if os.path.exists('discovered_keywords.csv'):
        discovered = pd.read_csv('discovered_keywords.csv')
        for _, row in discovered.iterrows():
            all_keywords.append({
                'keyword': row['keyword'],
                'category': row['category']
            })

    # Deduplicate
    seen = set()
    unique = []
    for kw in all_keywords:
        key = kw['keyword'].lower()
        if key not in seen:
            seen.add(key)
            unique.append(kw)
    all_keywords = unique

    print(f"\nTotal unique keywords: {len(all_keywords)}")

    # Load checkpoint
    results, processed = load_checkpoint()
    remaining = [k for k in all_keywords if k['keyword'].lower() not in processed]

    print(f"Already processed: {len(processed)}")
    print(f"Remaining: {len(remaining)}")
    print(f"Request delay: {REQUEST_DELAY}s")
    print(f"Estimated time: {len(remaining) * REQUEST_DELAY // 60} minutes")
    print("-" * 60)

    if not remaining:
        print("All keywords already processed!")
    else:
        pytrends = TrendReq(hl='en-US', tz=360)

        for i, kw_data in enumerate(remaining):
            keyword = kw_data['keyword']
            category = kw_data['category']
            total_done = len(processed) + i + 1

            print(f"({total_done}/{len(all_keywords)}) {keyword[:40]}...", end=" ", flush=True)

            result = get_keyword_data(pytrends, keyword, category)
            results.append(result)

            if result['error']:
                print(f"ERROR: {result['error']}")
            else:
                flag = "***" if passes_threshold(result) else ""
                print(f"5yr:{result['growth_5yr']:.0f}% 1yr:{result['growth_1yr']:.0f}% Score:{result['recommendation_score']} {flag}")

            # Checkpoint
            if (i + 1) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(results)
                print(f"  [Checkpoint: {len(results)} saved]")

            time.sleep(REQUEST_DELAY)

        save_checkpoint(results)

    # Final output
    print("\n" + "=" * 60)
    print("PROCESSING RESULTS")
    print("=" * 60)

    df = pd.DataFrame(results)

    # Filter passing threshold
    passing = df[df.apply(lambda r: passes_threshold(r.to_dict()), axis=1)]
    print(f"\nTotal scanned: {len(df)}")
    print(f"Passed 300%+ threshold: {len(passing)}")
    print(f"Errors: {len(df[df['error'].notna()])}")

    # Sort and save
    df = df.sort_values('recommendation_score', ascending=False)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved to: {OUTPUT_FILE}")

    # Cleanup checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    # Print top results
    print("\n" + "=" * 60)
    print("TOP 25 KEYWORDS BY SCORE")
    print("=" * 60)

    for i, row in df.head(25).iterrows():
        if row.get('error'):
            continue
        passes = "***" if passes_threshold(row.to_dict()) else ""
        print(f"\n{row['keyword'][:35]} ({row['category']})")
        print(f"  Interest: {row['current_interest']} | Score: {row['recommendation_score']} {passes}")
        print(f"  Growth: 5yr={row['growth_5yr']:.0f}% | 1yr={row['growth_1yr']:.0f}% | 6mo={row['growth_6mo']:.0f}% | 3mo={row['growth_3mo']:.0f}% | 1mo={row['growth_1mo']:.0f}%")

    # Category breakdown
    print("\n" + "=" * 60)
    print("PASSING KEYWORDS BY CATEGORY")
    print("=" * 60)

    if len(passing) > 0:
        for cat in passing['category'].unique():
            cat_kws = passing[passing['category'] == cat]['keyword'].tolist()
            print(f"\n{cat}: {len(cat_kws)}")
            for kw in cat_kws[:5]:
                print(f"  - {kw}")

    print("\n" + "=" * 60)
    print(f"COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted! Checkpoint saved. Re-run to resume.")
