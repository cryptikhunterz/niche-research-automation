# Agent Handoff: Niche Research Automation

## Project Location
`~/Desktop/niche-research-automation`

## Goal
Build a tool that DISCOVERS trending product niches Omar doesn't know about. NOT validation of existing keywords.

**The question to answer:** "What products are growing that I've never heard of?"

## Current State: BROKEN

### What Was Built
- GitHub repo: https://github.com/cryptikhunterz/niche-research-automation
- Google Trends module via SerpAPI (sources/google_trends.py)
- Streamlit UI (ui/app.py) - runs at localhost:8501
- Data merger (analysis/merger.py)

### Why It Sucks
The current approach uses "seed keywords" to find related queries. This is fundamentally wrong:

```
Seed: "home decor" → Results: "home decor ai", "ramadan home decor", "2025 home decor trends"
```

**This is NOT discovery.** It's finding synonyms of words I picked. Omar explicitly said:
> "The 111 seed keywords are DELETED from scope. They anchor me to health/wellness."
> "Sources tell me what's growing across ALL categories"
> "I discover keywords I never would have guessed"

## The Core Problem

Google Trends Related Queries REQUIRES a seed keyword. Whatever seed you give, it returns variations of that seed. You're always anchored to your starting point.

**True discovery requires seedless sources:**
1. Google Trends Trending Now (daily trending) - SerpAPI deprecated this endpoint
2. Exploding Topics - curated trends, no seeds - but JS-rendered (needs Playwright)
3. Amazon Movers & Shakers - sales surge data - but blocked by CAPTCHA

## What's Blocked

| Source | Why Blocked | Fix |
|--------|-------------|-----|
| Amazon Movers | CAPTCHA on every request | Proxy service or SerpAPI Amazon endpoint |
| Exploding Topics | JavaScript rendered | Playwright browser automation |
| Google Trends Trending Now | SerpAPI deprecated the endpoint | Try new endpoint format or different API |

## Files That Matter

```
sources/
├── google_trends.py    # Works but wrong approach (seed-based)
├── amazon_movers.py    # Built but blocked by CAPTCHA
├── exploding_topics.py # Built but blocked by JS rendering

analysis/merger.py      # Works, combines sources
ui/app.py              # Works, Streamlit dashboard

config.py              # Has SERPAPI_KEY loaded from .env
.env                   # Contains: SERPAPI_KEY=cdc1f621680e7937f92a42f1c428cbd0cd34ab177059a33ce176efbc9bac9db2
```

## What Needs to Happen

### Option A: Fix Exploding Topics with Playwright
```bash
pip install playwright
playwright install chromium
```
Then rewrite sources/exploding_topics.py to use browser automation.

Exploding Topics shows curated trending topics with growth % - no seeds needed. This is real discovery.

### Option B: Try SerpAPI's New Trending Endpoint
The error said: "See the new version here: https://serpapi.com/google-trends-trending-now"

May need different params. Research and test.

### Option C: Different Data Source
- Glimpse (glimpse.com) - trending products API
- Treendly - trend detection
- Google Shopping trending (via SerpAPI)

## Context for Omar
- Sprint Day 86 of 90
- Allen meeting needs 10-20 niche recommendations
- Original pytrends approach hit rate limits
- Pivoted to multi-source but hit blocking issues

## To Test Current State
```bash
cd ~/Desktop/niche-research-automation

# Run Google Trends (seed-based, not great but works)
python3 -m sources.google_trends --test

# Launch UI
python3 -m streamlit run ui/app.py
```

## Bottom Line
The infrastructure is built. The approach is wrong. Need a TRUE discovery source that doesn't require seed keywords.
