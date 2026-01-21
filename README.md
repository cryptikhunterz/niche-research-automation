# Niche Research Automation

Multi-source niche research pipeline for e-commerce product discovery. Aggregates data from multiple sources to identify high-growth product opportunities.

## Data Sources

| Source | Type | What It Provides |
|--------|------|------------------|
| SerpAPI | API | Google Trends interest over time |
| Amazon Movers & Shakers | Scrape | Products with biggest rank changes |
| Exploding Topics | Scrape | Trending topics with growth metrics |

## Quick Start

```bash
# Clone the repo
git clone https://github.com/cryptikhunterz/niche-research-automation.git
cd niche-research-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and add your API keys
cp .env.example .env
# Edit .env with your SERPAPI_KEY

# Run the pipeline
python main.py

# Launch the UI
streamlit run ui/app.py
```

## Project Structure

```
niche-research-automation/
├── sources/              # Data collection modules
│   ├── serpapi_trends.py     # Google Trends via SerpAPI
│   ├── amazon_movers.py      # Amazon Movers & Shakers scraper
│   └── exploding_topics.py   # Exploding Topics scraper
├── analysis/             # Processing modules
│   └── merger.py             # Combines all sources
├── ui/                   # Web interface
│   └── app.py                # Streamlit dashboard
├── data/
│   ├── raw/                  # Raw API responses (gitignored)
│   └── processed/            # Final CSVs
├── seeds/                # Input keywords
│   └── keywords.csv
├── docs/                 # Documentation
│   ├── PROGRESS.md           # Current status
│   └── phases/               # Phase documentation
└── main.py               # Pipeline orchestrator
```

## Output

The pipeline produces `data/processed/all_niches_raw.csv` with columns:

| Column | Source | Description |
|--------|--------|-------------|
| keyword | Input | Search term |
| category | Input | Product category |
| gt_interest_now | SerpAPI | Current Google Trends interest |
| gt_change_1yr_pct | SerpAPI | % change vs 1 year ago |
| gt_change_5yr_pct | SerpAPI | % change vs 5 years ago |
| amz_rank | Amazon | Current best seller rank |
| amz_rank_change_pct | Amazon | Rank movement % |
| et_growth_pct | Exploding Topics | Topic growth % |
| et_months_trending | Exploding Topics | Months on trend |
| sources_with_data | Calculated | How many sources returned data |

## API Keys Required

- **SERPAPI_KEY**: Get from [serpapi.com](https://serpapi.com) (has free tier)

## Legacy Files

The following files are from the original Google Trends approach (kept for reference):
- `niche_scanner.py` - Original pytrends scanner
- `category_discovery.py` - Keyword discovery via pytrends
- `full_scan.py` - Full keyword scan script
