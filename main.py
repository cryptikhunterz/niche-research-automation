#!/usr/bin/env python3
"""
Niche Research Pipeline - Main Orchestrator

Runs all data collection modules and merges results.
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import config


def run_serpapi():
    """Run SerpAPI trends collection."""
    print("\n[1/4] SerpAPI Trends...")
    try:
        from sources import serpapi_trends
        serpapi_trends.main()
        print("  ✓ SerpAPI complete")
        return True
    except ImportError:
        print("  ✗ Not implemented yet")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def run_amazon():
    """Run Amazon Movers scraper."""
    print("\n[2/4] Amazon Movers & Shakers...")
    try:
        from sources import amazon_movers
        amazon_movers.main()
        print("  ✓ Amazon complete")
        return True
    except ImportError:
        print("  ✗ Not implemented yet")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def run_exploding():
    """Run Exploding Topics scraper."""
    print("\n[3/4] Exploding Topics...")
    try:
        from sources import exploding_topics
        exploding_topics.main()
        print("  ✓ Exploding Topics complete")
        return True
    except ImportError:
        print("  ✗ Not implemented yet")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def run_merger():
    """Merge all data sources."""
    print("\n[4/4] Merging data...")
    try:
        from analysis import merger
        merger.main()
        print("  ✓ Merge complete")
        print(f"\n  Output: {config.MERGED_OUTPUT}")
        return True
    except ImportError:
        print("  ✗ Not implemented yet")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Niche Research Pipeline")
    parser.add_argument("--serpapi", action="store_true", help="Run only SerpAPI")
    parser.add_argument("--amazon", action="store_true", help="Run only Amazon")
    parser.add_argument("--exploding", action="store_true", help="Run only Exploding Topics")
    parser.add_argument("--merge", action="store_true", help="Run only merger")
    args = parser.parse_args()

    print("=" * 50)
    print("NICHE RESEARCH PIPELINE")
    print("=" * 50)

    # If specific module requested, run only that
    if args.serpapi:
        run_serpapi()
        return
    if args.amazon:
        run_amazon()
        return
    if args.exploding:
        run_exploding()
        return
    if args.merge:
        run_merger()
        return

    # Run full pipeline
    results = {
        "serpapi": run_serpapi(),
        "amazon": run_amazon(),
        "exploding": run_exploding(),
        "merger": run_merger(),
    }

    print("\n" + "=" * 50)
    print("PIPELINE COMPLETE")
    print("=" * 50)

    successful = sum(results.values())
    print(f"\nModules completed: {successful}/4")

    if results["merger"]:
        print(f"\nView results: streamlit run ui/app.py")
        print(f"Or open: {config.MERGED_OUTPUT}")


if __name__ == "__main__":
    main()
