"""
Centralized configuration for niche research pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SEEDS_DIR = PROJECT_ROOT / "seeds"

# API Keys
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Rate limiting
SERPAPI_DELAY = 2  # seconds between requests
AMAZON_DELAY = 3   # seconds between requests (be respectful)
EXPLODING_DELAY = 2  # seconds between requests

# Thresholds
GROWTH_THRESHOLD_PCT = 300  # Minimum growth % to flag as "high growth"

# Output files
SERPAPI_OUTPUT = PROCESSED_DIR / "serpapi_trends.csv"
AMAZON_OUTPUT = PROCESSED_DIR / "amazon_movers.csv"
EXPLODING_OUTPUT = PROCESSED_DIR / "exploding_topics.csv"
MERGED_OUTPUT = PROCESSED_DIR / "all_niches_raw.csv"
KEYWORDS_FILE = SEEDS_DIR / "keywords.csv"

# Ensure directories exist
for dir_path in [RAW_DIR / "serpapi", RAW_DIR / "amazon", RAW_DIR / "exploding", PROCESSED_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
