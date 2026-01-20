# Niche Research Automation - Roadmap

## Milestone 1: MVP Pipeline (v1.0)

Goal: Automated niche discovery pipeline that outputs actionable recommendations for Allen meeting.

### Phases

#### Phase 1: Google Trends Scanner [COMPLETE]
**Status:** Built, needs full run
**Goal:** Scan seed keywords, calculate growth metrics, output ranked CSV

Deliverables:
- [x] `niche_scanner.py` - Main scanner script (263 lines)
- [ ] `niche_trends_results.csv` - Full scan output
- [ ] Top 20 keywords printed with metrics

Key Features:
- Scans 47 seed keywords across 6 categories
- Calculates growth % across 5 time horizons
- Weighted recommendation scoring
- Rate limit handling (15s delay, 30s retry backoff)
- Checkpoint/resume capability

Research: No (using known library)

---

#### Phase 2: Keyword Expansion
**Status:** Not started
**Goal:** Expand initial results using related/rising queries

Deliverables:
- [ ] Expanded keyword list (target: 100-200 keywords)
- [ ] Second scan pass on expanded keywords
- [ ] Merged results CSV

Dependencies: Phase 1 complete scan

Research: No

---

#### Phase 3: YouTube Transcript Mining
**Status:** Not started
**Goal:** Collect transcripts from top YouTube videos for high-growth keywords

Deliverables:
- [ ] `transcript_collector.py` - YouTube API integration
- [ ] Raw transcripts for top 20-50 keywords
- [ ] Organized by keyword/niche

Dependencies: Phase 1 or 2 results (need keywords to search)

Research: Likely (YouTube API quotas, transcript extraction methods)

---

#### Phase 4: LLM Analysis
**Status:** Not started
**Goal:** Extract pain points, opportunities, and recommendations from transcripts

Deliverables:
- [ ] `transcript_analyzer.py` - LLM integration
- [ ] Structured analysis per keyword
- [ ] Final recommendations report

Dependencies: Phase 3 transcripts

Research: Likely (prompt engineering, cost optimization)

---

#### Phase 5: Final Report
**Status:** Not started
**Goal:** Consolidate findings into actionable format for Allen

Deliverables:
- [ ] Top 10-20 niche recommendations
- [ ] Growth data + transcript insights per niche
- [ ] Prioritized action list

Dependencies: Phase 4 analysis

Research: No

---

## Success Criteria (Milestone 1)

- [ ] 50+ keywords scanned with growth metrics
- [ ] Top 20 keywords have YouTube transcript analysis
- [ ] Clear recommendations ready for Allen meeting
- [ ] Reproducible pipeline (can run again for new keywords)

## Domain Expertise

None required - standard Python, APIs, data processing.

---
*Last updated: 2026-01-20*
