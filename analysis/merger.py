#!/usr/bin/env python3
"""
Data Merger

Combines data from all sources into a single output file.
Currently: Google Trends only (Amazon and Exploding Topics skipped)

Output: data/processed/all_niches_raw.csv
"""
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Input files
GOOGLE_TRENDS_FILE = config.PROCESSED_DIR / "google_trends.csv"
AMAZON_FILE = config.PROCESSED_DIR / "amazon_movers.csv"
EXPLODING_FILE = config.PROCESSED_DIR / "exploding_topics.csv"

# Output
OUTPUT_FILE = config.MERGED_OUTPUT


def load_google_trends() -> pd.DataFrame:
    """Load Google Trends data."""
    if not GOOGLE_TRENDS_FILE.exists():
        print("  Google Trends: No data file found")
        return pd.DataFrame()

    df = pd.read_csv(GOOGLE_TRENDS_FILE)
    print(f"  Google Trends: {len(df)} keywords loaded")
    return df


def load_amazon() -> pd.DataFrame:
    """Load Amazon Movers data."""
    if not AMAZON_FILE.exists():
        print("  Amazon Movers: No data file found (skipped)")
        return pd.DataFrame()

    df = pd.read_csv(AMAZON_FILE)
    print(f"  Amazon Movers: {len(df)} products loaded")
    return df


def load_exploding() -> pd.DataFrame:
    """Load Exploding Topics data."""
    if not EXPLODING_FILE.exists():
        print("  Exploding Topics: No data file found (skipped)")
        return pd.DataFrame()

    df = pd.read_csv(EXPLODING_FILE)
    print(f"  Exploding Topics: {len(df)} topics loaded")
    return df


def merge_all() -> pd.DataFrame:
    """
    Merge all data sources.

    For now, just uses Google Trends since others are skipped.
    Future: merge by keyword with fuzzy matching.
    """
    print("\n[Data Merger]")
    print("=" * 50)
    print("\n  Loading sources...")

    # Load all available data
    gt_df = load_google_trends()
    amz_df = load_amazon()
    et_df = load_exploding()

    # For now, Google Trends is the only source
    if len(gt_df) == 0:
        print("\nERROR: No data to merge")
        return pd.DataFrame()

    # Standardize columns
    df = gt_df.copy()

    # Ensure required columns exist
    required_cols = [
        "keyword",
        "gt_current",
        "gt_5yr_pct",
        "gt_1yr_pct",
        "gt_3mo_pct",
        "gt_1wk_pct",
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    # Add source tracking
    df["sources"] = "google_trends"
    df["sources_count"] = 1

    # Add Amazon data if available
    if len(amz_df) > 0:
        # Future: merge on keyword with fuzzy matching
        df["sources_count"] += 1
        df["sources"] += ",amazon"

    # Add Exploding Topics if available
    if len(et_df) > 0:
        # Future: merge on keyword with fuzzy matching
        df["sources_count"] += 1
        df["sources"] += ",exploding"

    # Clean up
    df["merged_at"] = datetime.now().isoformat()

    # Select and order columns for output
    output_cols = [
        "keyword",
        "seed",
        "growth_pct",          # From related queries (discovery)
        "gt_current",          # Current interest
        "gt_5yr_pct",          # 5-year growth
        "gt_1yr_pct",          # 1-year growth
        "gt_3mo_pct",          # 3-month growth
        "gt_1wk_pct",          # 1-week growth
        "sources",
        "sources_count",
        "merged_at",
    ]

    # Only include columns that exist
    output_cols = [c for c in output_cols if c in df.columns]
    df = df[output_cols]

    # Sort by discovery growth (rising queries)
    if "growth_pct" in df.columns:
        df = df.sort_values("growth_pct", ascending=False, na_position="last")

    # Save
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n  Merged {len(df)} keywords to {OUTPUT_FILE}")

    return df


def main():
    """Run merger."""
    df = merge_all()

    if len(df) > 0:
        print("\n" + "=" * 50)
        print("TOP 20 KEYWORDS BY GROWTH")
        print("=" * 50)

        display_cols = ["keyword", "growth_pct", "gt_current", "gt_1yr_pct", "gt_3mo_pct"]
        display_cols = [c for c in display_cols if c in df.columns]
        print(df[display_cols].head(20).to_string())


if __name__ == "__main__":
    main()
