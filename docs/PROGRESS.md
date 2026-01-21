# Niche Research Pipeline - Progress

## Current Status

- **Phase:** 1 of 6
- **Last Updated:** 2026-01-21
- **Blockers:** None

## Phase Checklist

- [x] Phase 1: Project Setup
- [ ] Phase 2: SerpAPI Integration
- [ ] Phase 3: Amazon Movers & Shakers
- [ ] Phase 4: Exploding Topics
- [ ] Phase 5: Data Merger
- [ ] Phase 6: Local Web UI

## Quick Start

```bash
# Current state: Project initialized, no data collection yet
python main.py  # Will show "not implemented" for each source

# After Phase 2:
python -m sources.serpapi_trends --test

# After all phases:
streamlit run ui/app.py
```

## Data Sources Status

| Source | Status | Last Run | Records |
|--------|--------|----------|---------|
| SerpAPI | Not Started | - | - |
| Amazon | Not Started | - | - |
| Exploding Topics | Not Started | - | - |

## Notes

- Reddit removed from scope (API complexity)
- Preserving legacy Google Trends code for reference
- 111 keywords from previous work available in seeds/
