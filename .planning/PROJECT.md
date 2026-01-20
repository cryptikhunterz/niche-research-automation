# Niche Research Automation

## What This Is

An automated niche discovery pipeline for e-commerce product research. Uses Google Trends data to identify high-growth keywords (300%+), then validates opportunities through YouTube transcript mining and LLM analysis. Built for Omar to find product niches like "magnesium glycinate" (+550% growth) for Allen partnership.

## Core Value

**Find 10-20 exploding product niches programmatically before big brands capture them.**

Everything else (UI, database, reports) is secondary to surfacing high-growth opportunities fast.

## Requirements

### Validated

- [x] Google Trends scanner via pytrends — Phase 1 (built)
- [x] Growth calculation across 5 time horizons (5yr, 1yr, 6mo, 3mo, 1mo) — Phase 1
- [x] Weighted recommendation scoring (recent growth > old growth) — Phase 1
- [x] Rate limit handling with retries — Phase 1
- [x] CSV output sorted by score — Phase 1

### Active

- [ ] Run full keyword scan (47 seeds across 6 categories)
- [ ] Related query expansion for additional keywords
- [ ] YouTube transcript collection for top keywords
- [ ] LLM analysis of transcripts for pain points/opportunities
- [ ] Supplier research integration

### Out of Scope

- Web UI or dashboard — CLI/CSV sufficient for now
- Database storage — CSV files for this sprint
- Real-time monitoring — batch analysis only
- Multi-region analysis — US market focus

## Context

**Validated template:** Magnesium glycinate showed +550% growth, validated through manual transcript mining. This tool automates that discovery process.

**Seed categories:** Supplements, Women's Health, Gut Health, Sleep/Stress, Natural Beauty, Men's Optimization

**Timeline:** Sprint Day 86 of 90. Allen meeting next week needs 10-20 niche recommendations.

**Technical:** Python 3.12, pytrends 4.9.2 (unofficial Google Trends API). Rate limits require 15s+ delays between requests.

## Constraints

- **API Rate Limits**: pytrends gets rate-limited aggressively. 15s delays, 30s retry backoff required.
- **No Official API**: Google Trends has no official API. pytrends is best available option.
- **Timeline**: Must have actionable output before Allen meeting (end of 90-day sprint)
- **Growth Threshold**: 300%+ growth on any time horizon = worth investigating

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| pytrends over scraping | Stable library, handles rate limits | -- Pending |
| 15s request delay | Balance speed vs rate limits | -- Pending |
| Weighted scoring (recent > old) | Prioritize emerging trends over established | -- Pending |
| CSV output (not DB) | Speed to value, easy to share | -- Pending |
| 300% growth threshold | High bar filters noise, matches magnesium template | -- Pending |

---
*Last updated: 2026-01-20 after Phase 1 implementation*
