#!/usr/bin/env python3
"""
Google Trends Niche Scanner
Finds high-growth keywords for e-commerce product research.
"""

import pandas as pd
import time
import os
from datetime import datetime
from pytrends.request import TrendReq

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

SEED_KEYWORDS = {
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
REQUEST_DELAY = 15  # Seconds between requests (safe for pytrends)
MAX_RETRIES = 3
RETRY_DELAY = 30  # Seconds to wait on rate limit

# Scoring weights (recent growth weighted higher)
WEIGHTS = {
    '1mo': 0.30,
    '3mo': 0.25,
    '6mo': 0.20,
    '1yr': 0.15,
    '5yr': 0.10
}

# Thresholds
MIN_GROWTH_THRESHOLD = 300  # % growth on ANY horizon to include
MAX_GROWTH_CAP = 10000  # Cap growth at 10000% to avoid infinity

# Output
OUTPUT_FILE = "niche_trends_results.csv"
CHECKPOINT_FILE = "checkpoint_results.csv"


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def calculate_growth(current: float, past: float) -> float:
    """Calculate growth percentage with safeguards."""
    if past <= 0:
        if current > 0:
            return MAX_GROWTH_CAP  # From 0 to something = max growth
        return 0  # 0 to 0 = no growth

    growth = ((current - past) / past) * 100
    return min(growth, MAX_GROWTH_CAP)  # Cap at max


def get_time_periods(df: pd.DataFrame) -> dict:
    """Extract values at different time horizons from interest_over_time data."""
    if df.empty:
        return None

    keyword = df.columns[0]  # First column is the keyword

    # Get current (most recent)
    current = df[keyword].iloc[-1]

    # Get values at different horizons
    # Data is weekly, so: 4 weeks = 1 month, 13 = 3mo, 26 = 6mo, 52 = 1yr, 260 = 5yr
    periods = {
        'current': current,
        '1mo_ago': df[keyword].iloc[-5] if len(df) > 5 else df[keyword].iloc[0],
        '3mo_ago': df[keyword].iloc[-13] if len(df) > 13 else df[keyword].iloc[0],
        '6mo_ago': df[keyword].iloc[-26] if len(df) > 26 else df[keyword].iloc[0],
        '1yr_ago': df[keyword].iloc[-52] if len(df) > 52 else df[keyword].iloc[0],
        '5yr_ago': df[keyword].iloc[0]  # First data point
    }

    return periods


def calculate_recommendation_score(growth_dict: dict) -> float:
    """Calculate weighted recommendation score."""
    score = (
        growth_dict.get('growth_1mo', 0) * WEIGHTS['1mo'] +
        growth_dict.get('growth_3mo', 0) * WEIGHTS['3mo'] +
        growth_dict.get('growth_6mo', 0) * WEIGHTS['6mo'] +
        growth_dict.get('growth_1yr', 0) * WEIGHTS['1yr'] +
        growth_dict.get('growth_5yr', 0) * WEIGHTS['5yr']
    )
    return round(score, 2)


def get_keyword_data(pytrends: TrendReq, keyword: str, category: str) -> dict:
    """Fetch all data for a single keyword with retry logic."""
    result = {
        'keyword': keyword,
        'category': category,
        'current_interest': 0,
        'growth_5yr': 0,
        'growth_1yr': 0,
        'growth_6mo': 0,
        'growth_3mo': 0,
        'growth_1mo': 0,
        'related_queries': '',
        'rising_queries': '',
        'recommendation_score': 0,
        'error': None
    }

    for attempt in range(MAX_RETRIES):
        try:
            # Build payload
            pytrends.build_payload([keyword], timeframe='today 5-y', geo='US')

            # Get interest over time
            df = pytrends.interest_over_time()

            if df.empty:
                result['error'] = 'No data'
                return result

            # Remove isPartial column if present
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])

            # Calculate growth metrics
            periods = get_time_periods(df)
            if periods:
                result['current_interest'] = periods['current']
                result['growth_5yr'] = calculate_growth(periods['current'], periods['5yr_ago'])
                result['growth_1yr'] = calculate_growth(periods['current'], periods['1yr_ago'])
                result['growth_6mo'] = calculate_growth(periods['current'], periods['6mo_ago'])
                result['growth_3mo'] = calculate_growth(periods['current'], periods['3mo_ago'])
                result['growth_1mo'] = calculate_growth(periods['current'], periods['1mo_ago'])

            # Small delay before related queries
            time.sleep(2)

            # Get related queries
            try:
                related = pytrends.related_queries()
                if keyword in related and related[keyword]['top'] is not None:
                    top_queries = related[keyword]['top']['query'].head(5).tolist()
                    result['related_queries'] = '; '.join(top_queries)

                if keyword in related and related[keyword]['rising'] is not None:
                    rising = related[keyword]['rising']['query'].head(5).tolist()
                    result['rising_queries'] = '; '.join(rising)
            except Exception as e:
                # Related queries sometimes fail - not critical
                pass

            # Calculate recommendation score
            growth_dict = {
                'growth_1mo': result['growth_1mo'],
                'growth_3mo': result['growth_3mo'],
                'growth_6mo': result['growth_6mo'],
                'growth_1yr': result['growth_1yr'],
                'growth_5yr': result['growth_5yr']
            }
            result['recommendation_score'] = calculate_recommendation_score(growth_dict)

            return result

        except Exception as e:
            error_msg = str(e)
            if '429' in error_msg or 'rate' in error_msg.lower():
                print(f"    Rate limited. Waiting {RETRY_DELAY}s before retry {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(RETRY_DELAY)
            else:
                result['error'] = error_msg
                return result

    result['error'] = 'Max retries exceeded'
    return result


def passes_threshold(result: dict) -> bool:
    """Check if keyword passes the 300%+ growth threshold on any horizon."""
    if result.get('error'):
        return False

    return (
        result['growth_5yr'] >= MIN_GROWTH_THRESHOLD or
        result['growth_1yr'] >= MIN_GROWTH_THRESHOLD or
        result['growth_6mo'] >= MIN_GROWTH_THRESHOLD or
        result['growth_3mo'] >= MIN_GROWTH_THRESHOLD or
        result['growth_1mo'] >= MIN_GROWTH_THRESHOLD
    )


def save_checkpoint(results: list, filename: str):
    """Save intermediate results to checkpoint file."""
    if not results:
        return

    df = pd.DataFrame(results)
    df.to_csv(filename, index=False)
    print(f"  [Checkpoint saved: {len(results)} keywords]")


def load_checkpoint(filename: str) -> tuple:
    """Load checkpoint if exists. Returns (results_list, processed_keywords_set)."""
    if os.path.exists(filename):
        df = pd.read_csv(filename)
        results = df.to_dict('records')
        processed = set(df['keyword'].tolist())
        print(f"  [Loaded checkpoint: {len(results)} keywords already processed]")
        return results, processed
    return [], set()


# ═══════════════════════════════════════════════════════════════
# MAIN SCANNER
# ═══════════════════════════════════════════════════════════════

def scan_all_keywords():
    """Main function to scan all keywords."""
    print("=" * 60)
    print("GOOGLE TRENDS NICHE SCANNER")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Initialize pytrends
    pytrends = TrendReq(hl='en-US', tz=360)

    # Load checkpoint if exists
    all_results, processed_keywords = load_checkpoint(CHECKPOINT_FILE)

    # Count total keywords
    total_keywords = sum(len(kws) for kws in SEED_KEYWORDS.values())
    remaining = total_keywords - len(processed_keywords)
    print(f"\nTotal keywords: {total_keywords}")
    print(f"Already processed: {len(processed_keywords)}")
    print(f"Remaining: {remaining}")
    print(f"Request delay: {REQUEST_DELAY}s between requests")
    print("-" * 60)

    processed_count = len(processed_keywords)

    for category, keywords in SEED_KEYWORDS.items():
        print(f"\n[CATEGORY: {category.upper()}]")

        for keyword in keywords:
            # Skip if already processed
            if keyword in processed_keywords:
                continue

            processed_count += 1
            print(f"  ({processed_count}/{total_keywords}) {keyword}...", end=" ", flush=True)

            # Get data
            result = get_keyword_data(pytrends, keyword, category)

            if result['error']:
                print(f"ERROR: {result['error']}")
            else:
                # Show key metrics
                print(f"Interest: {result['current_interest']}, " +
                      f"5yr: {result['growth_5yr']:.0f}%, " +
                      f"1yr: {result['growth_1yr']:.0f}%, " +
                      f"Score: {result['recommendation_score']}")

            all_results.append(result)

            # Save checkpoint every 10 keywords
            if processed_count % 10 == 0:
                save_checkpoint(all_results, CHECKPOINT_FILE)

            # Rate limit delay
            time.sleep(REQUEST_DELAY)

    # Final save
    save_checkpoint(all_results, CHECKPOINT_FILE)

    return all_results


def save_final_results(results: list):
    """Save final results, filtered and sorted."""
    print("\n" + "=" * 60)
    print("PROCESSING RESULTS")
    print("=" * 60)

    # Filter for keywords passing threshold
    passing = [r for r in results if passes_threshold(r)]
    failed = [r for r in results if r.get('error')]

    print(f"\nTotal scanned: {len(results)}")
    print(f"Passed 300%+ threshold: {len(passing)}")
    print(f"Failed/no data: {len(failed)}")

    if not passing:
        print("\nNo keywords passed the threshold. Saving all results anyway.")
        passing = [r for r in results if not r.get('error')]

    # Create DataFrame and sort
    df = pd.DataFrame(passing)

    # Reorder columns
    columns = [
        'keyword', 'category', 'current_interest',
        'growth_5yr', 'growth_1yr', 'growth_6mo', 'growth_3mo', 'growth_1mo',
        'related_queries', 'rising_queries', 'recommendation_score'
    ]
    df = df[[c for c in columns if c in df.columns]]

    # Sort by recommendation score
    df = df.sort_values('recommendation_score', ascending=False)

    # Save to CSV
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved to: {OUTPUT_FILE}")

    # Clean up checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        print("Checkpoint file cleaned up.")

    return df


def print_top_results(df: pd.DataFrame, n: int = 20):
    """Print top N results to console."""
    print("\n" + "=" * 60)
    print(f"TOP {n} HIGH-GROWTH KEYWORDS")
    print("=" * 60)

    for i, row in df.head(n).iterrows():
        print(f"\n{df.index.get_loc(i) + 1}. {row['keyword'].upper()} ({row['category']})")
        print(f"   Current Interest: {row['current_interest']}")
        print(f"   Growth: 5yr={row['growth_5yr']:.0f}% | 1yr={row['growth_1yr']:.0f}% | " +
              f"6mo={row['growth_6mo']:.0f}% | 3mo={row['growth_3mo']:.0f}% | 1mo={row['growth_1mo']:.0f}%")
        print(f"   Recommendation Score: {row['recommendation_score']}")
        if row['rising_queries']:
            print(f"   Rising: {row['rising_queries'][:80]}...")


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        # Run scanner
        results = scan_all_keywords()

        # Save and display results
        df = save_final_results(results)
        print_top_results(df)

        print("\n" + "=" * 60)
        print(f"COMPLETE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nInterrupted! Checkpoint saved. Re-run to resume.")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        raise
