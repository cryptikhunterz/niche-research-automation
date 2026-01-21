#!/usr/bin/env python3
"""
Niche Research UI - Streamlit Dashboard

Displays discovered keywords with growth metrics.
Sortable, filterable, exportable.

Run: streamlit run ui/app.py
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

# Page config
st.set_page_config(
    page_title="Niche Research",
    page_icon="📈",
    layout="wide",
)

# Data file
DATA_FILE = config.MERGED_OUTPUT
GT_FILE = config.PROCESSED_DIR / "google_trends.csv"


@st.cache_data(ttl=60)
def load_data():
    """Load the merged data file."""
    # Try merged file first, fall back to Google Trends
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE)
    elif GT_FILE.exists():
        return pd.read_csv(GT_FILE)
    return pd.DataFrame()


def main():
    st.title("📈 Niche Research Dashboard")
    st.markdown("*Discover trending keywords across ALL categories*")

    # Load data
    df = load_data()

    if len(df) == 0:
        st.error("No data found. Run the pipeline first:")
        st.code("python3 -m sources.google_trends")
        st.code("python3 -m analysis.merger")
        return

    # Sidebar filters
    st.sidebar.header("Filters")

    # Seed category filter (if available)
    if "seed" in df.columns:
        seeds = ["All"] + sorted(df["seed"].dropna().unique().tolist())
        selected_seed = st.sidebar.selectbox("Seed Category", seeds)
        if selected_seed != "All":
            df = df[df["seed"] == selected_seed]

    # Growth filters
    st.sidebar.subheader("Growth Thresholds")

    if "growth_pct" in df.columns:
        min_growth = st.sidebar.slider(
            "Min Discovery Growth %",
            min_value=0,
            max_value=5000,
            value=100,
            step=50,
        )
        df = df[df["growth_pct"].fillna(0) >= min_growth]

    if "gt_1yr_pct" in df.columns:
        min_1yr = st.sidebar.slider(
            "Min 1-Year Growth %",
            min_value=-100,
            max_value=500,
            value=-100,
            step=10,
        )
        df = df[df["gt_1yr_pct"].fillna(-999) >= min_1yr]

    # Current interest filter
    if "gt_current" in df.columns:
        min_interest = st.sidebar.slider(
            "Min Current Interest",
            min_value=0,
            max_value=100,
            value=0,
            step=5,
        )
        df = df[df["gt_current"].fillna(0) >= min_interest]

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Keywords", len(df))
    with col2:
        if "seed" in df.columns:
            st.metric("Categories", df["seed"].nunique())
    with col3:
        if "growth_pct" in df.columns:
            breakouts = len(df[df["growth_pct"] >= 5000])
            st.metric("Breakouts (5000%+)", breakouts)
    with col4:
        if "gt_1yr_pct" in df.columns:
            sustained = len(df[df["gt_1yr_pct"].fillna(0) >= 50])
            st.metric("Sustained Growth (1yr 50%+)", sustained)

    # Data table
    st.subheader("Keywords")

    # Select columns to display
    display_cols = []
    priority_cols = ["keyword", "seed", "growth_pct", "gt_current", "gt_5yr_pct", "gt_1yr_pct", "gt_3mo_pct", "gt_1wk_pct"]
    for col in priority_cols:
        if col in df.columns:
            display_cols.append(col)

    # Add any remaining columns
    for col in df.columns:
        if col not in display_cols and col not in ["merged_at", "validated_at", "source", "sources"]:
            display_cols.append(col)

    # Sort options
    sort_col = st.selectbox(
        "Sort by",
        display_cols,
        index=display_cols.index("growth_pct") if "growth_pct" in display_cols else 0,
    )
    sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
    ascending = sort_order == "Ascending"

    # Sort and display
    df_display = df[display_cols].sort_values(sort_col, ascending=ascending, na_position="last")

    # Rename columns for display
    column_labels = {
        "keyword": "Keyword",
        "seed": "Category",
        "growth_pct": "Discovery Growth %",
        "gt_current": "Current Interest",
        "gt_5yr_pct": "5yr Growth %",
        "gt_1yr_pct": "1yr Growth %",
        "gt_3mo_pct": "3mo Growth %",
        "gt_1wk_pct": "1wk Growth %",
    }

    df_display = df_display.rename(columns={k: v for k, v in column_labels.items() if k in df_display.columns})

    # Display table
    st.dataframe(
        df_display,
        use_container_width=True,
        height=600,
    )

    # Export
    st.subheader("Export")
    col1, col2 = st.columns(2)

    with col1:
        csv = df_display.to_csv(index=False)
        st.download_button(
            "📥 Download Filtered CSV",
            csv,
            f"niche_research_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "text/csv",
        )

    with col2:
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

    # Data freshness
    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Info")
    if DATA_FILE.exists():
        mtime = datetime.fromtimestamp(DATA_FILE.stat().st_mtime)
        st.sidebar.text(f"Last updated:\n{mtime.strftime('%Y-%m-%d %H:%M')}")
    st.sidebar.text(f"Total rows: {len(load_data())}")


if __name__ == "__main__":
    main()
