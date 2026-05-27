"""
Sector Screener page — sortable table of NSE blue-chip stocks with live data.
Clicking a row updates the sidebar ticker.
"""
from __future__ import annotations

import sys
import os

import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import get_nifty50_data

st.set_page_config(page_title="Sector Screener | India Stock Analyzer", layout="wide")

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.title("Sector Screener — NSE Blue Chips")
st.caption("Live data for top NSE-listed companies. Click any row to set it as your active ticker.")

# ---- Sector filter ----
sector_map = {
    "All": None,
    "Banking": ["Financial Services", "Banks", "Banking"],
    "IT / Technology": ["Technology", "Information Technology"],
    "Pharma": ["Healthcare", "Pharmaceutical", "Drug Manufacturers"],
    "Energy": ["Energy", "Oil & Gas"],
    "FMCG": ["Consumer Defensive", "Consumer Staples", "FMCG"],
    "Telecom": ["Communication Services", "Telecom"],
}

selected_sector = st.selectbox("Filter by Sector", list(sector_map.keys()), index=0)

with st.spinner("Loading screener data… (this may take ~15 seconds on first load)"):
    df = get_nifty50_data()

if df.empty:
    st.error("Could not load screener data. Check your internet connection.")
    st.stop()

# Apply sector filter
if selected_sector != "All":
    allowed = sector_map[selected_sector]
    df = df[df["Sector"].apply(lambda s: any(a.lower() in s.lower() for a in allowed))]
    if df.empty:
        st.info(f"No stocks found for sector '{selected_sector}' in the current data.")

# ---- Color coding helper ----
def color_change(val):
    """Style positive green, negative red for 1D Change% column."""
    try:
        v = float(val)
        if v > 0:
            return "color: #2E7D32; font-weight: bold"
        if v < 0:
            return "color: #C62828; font-weight: bold"
    except Exception:
        pass
    return ""


styled = (
    df.style
    .map(color_change, subset=["1D Change%"])
    .format({
        "Price (₹)": "{:,.2f}",
        "1D Change%": "{:+.2f}%",
        "P/E": lambda v: f"{v:.1f}" if pd.notna(v) else "N/A",
        "EPS (₹)": lambda v: f"₹{v:.2f}" if pd.notna(v) else "N/A",
        "Mkt Cap (₹Cr)": "{:,.0f}",
    })
)

st.dataframe(styled, use_container_width=True, height=500)

st.divider()

# ---- Ticker selector ----
st.subheader("Switch Active Ticker")
col1, col2 = st.columns([3, 1])
with col1:
    selected_ticker = st.selectbox(
        "Select stock to analyze",
        options=df["Ticker"].tolist(),
        format_func=lambda t: f"{df.loc[df['Ticker']==t,'Company'].values[0]}  ({t})" if not df[df['Ticker']==t].empty else t,
    )
with col2:
    st.write("")
    st.write("")
    if st.button("Set as Active Ticker", type="primary"):
        st.session_state["ticker"] = selected_ticker
        st.success(f"Active ticker set to **{selected_ticker}**. Navigate to Overview to see details.")

st.divider()

# ---- Summary stats ----
st.subheader("Screener Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Stocks Shown", len(df))

gainers = df[df["1D Change%"] > 0]
losers  = df[df["1D Change%"] < 0]
c2.metric("Gainers", len(gainers), delta=f"+{len(gainers)}", delta_color="normal")
c3.metric("Losers", len(losers), delta=f"-{len(losers)}", delta_color="inverse")

avg_pe = df["P/E"].dropna().mean()
c4.metric("Avg P/E", f"{avg_pe:.1f}" if not pd.isna(avg_pe) else "N/A")
