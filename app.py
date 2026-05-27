"""
India Stock Analyzer — main Streamlit entry point.
Run with: streamlit run app.py
"""
from __future__ import annotations

import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="India Stock Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        "<div style='font-size:52px;line-height:1;margin-bottom:4px'>📈</div>"
        "<div style='font-size:18px;font-weight:700;margin-bottom:2px'>India Stock Analyzer</div>"
        "<div style='font-size:12px;opacity:0.65'>Live NSE/BSE Research Platform</div>",
        unsafe_allow_html=True,
    )
    st.divider()

    ticker_input = st.text_input(
        "Stock Ticker",
        value=st.session_state.get("ticker", "RELIANCE.NS"),
        placeholder="e.g. TCS.NS, HDFCBANK.NS",
        help="Use NSE suffix (.NS) or BSE suffix (.BO). Example: RELIANCE.NS",
    ).strip().upper()

    if ticker_input:
        st.session_state["ticker"] = ticker_input

    refresh = st.button("🔄 Refresh Data", use_container_width=True)
    if refresh:
        st.cache_data.clear()
        st.rerun()

    st.divider()

    # Dark/Light mode hint (Streamlit manages theme via config; we provide a toggle that writes to config)
    mode = st.radio("Theme", ["Light", "Dark"], horizontal=True, index=0)
    if mode == "Dark":
        st.markdown(
            """<style>
            .stApp { background-color: #0e1117; color: #fafafa; }
            </style>""",
            unsafe_allow_html=True,
        )

    st.divider()
    st.caption(f"Last updated: {datetime.now():%H:%M:%S, %d %b %Y}")
    st.caption("Data: yfinance / NSE")
    st.caption("AI: Claude Sonnet 4.6")

# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

st.title("📈 India Stock Analyzer")
st.subheader("Live NSE/BSE Research Dashboard")

ticker = st.session_state.get("ticker", "RELIANCE.NS")
st.info(
    f"**Active ticker:** `{ticker}` — Navigate the pages in the sidebar to explore "
    "Overview, Fundamentals, AI Morning Note, DCF Valuation, and Sector Screener."
)

col1, col2, col3 = st.columns(3)
col1.metric("Platform", "NSE / BSE Live Data")
col2.metric("AI Engine", "Claude Sonnet 4.6")
col3.metric("Refresh Rate", "Every 5 minutes")

st.markdown("""
### How to use
1. **Enter a ticker** in the sidebar (e.g. `RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS`)
2. **Overview** — live price, 1-year chart, key metrics
3. **Fundamentals** — income statement, margins, balance sheet
4. **AI Morning Note** — Claude-generated research note + Q&A
5. **Valuation** — interactive DCF model with sensitivity table
6. **Sector Screener** — compare top NSE stocks

> Tip: Click **Refresh Data** in the sidebar to force a live data update.
""")

# API key warning
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.warning(
        "**ANTHROPIC_API_KEY not set.** "
        "The AI Morning Note page requires an API key. "
        "Add `ANTHROPIC_API_KEY=your_key` to a `.env` file in the project root.",
        icon="⚠️",
    )
