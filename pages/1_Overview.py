"""
Overview page — live price metrics, 1-year price chart with Nifty comparison,
volume chart, and key stats table.
"""
from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import get_stock_info, get_price_history

st.set_page_config(page_title="Overview | India Stock Analyzer", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_mcap(v: float) -> str:
    """Format market cap in ₹Cr with B/T suffixes."""
    if v is None:
        return "N/A"
    cr = v / 1e7
    if cr >= 1_00_000:
        return f"₹{cr/1_00_000:.2f}L Cr"
    if cr >= 1_000:
        return f"₹{cr/1_000:.2f}K Cr"
    return f"₹{cr:.0f} Cr"


def build_price_chart(hist: pd.DataFrame, nifty: pd.DataFrame, ticker: str) -> go.Figure:
    """Return a dual-series normalised price chart (stock vs. Nifty)."""
    fig = go.Figure()

    # Normalise both to 100 at start
    if not hist.empty:
        norm_stock = hist["Close"] / hist["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=hist.index, y=norm_stock,
            name=ticker, mode="lines",
            line=dict(color="#1976D2", width=2),
        ))

    if not nifty.empty:
        norm_nifty = nifty["Close"] / nifty["Close"].iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=nifty.index, y=norm_nifty,
            name="Nifty 50 (^NSEI)", mode="lines",
            line=dict(color="#FF6F00", width=1.5, dash="dot"),
        ))

    fig.update_layout(
        title="1-Year Price Performance (Indexed to 100)",
        yaxis_title="Indexed Price",
        xaxis_title="Date",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=380,
        margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#EEEEEE")
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    return fig


def build_volume_chart(hist: pd.DataFrame, ticker: str) -> go.Figure:
    """Return a volume bar chart."""
    if hist.empty:
        return go.Figure()

    colors_list = ["#2E7D32" if c >= o else "#C62828"
                   for c, o in zip(hist["Close"], hist["Open"])]

    fig = go.Figure(go.Bar(
        x=hist.index, y=hist["Volume"],
        marker_color=colors_list, name="Volume",
    ))
    fig.update_layout(
        title="Daily Trading Volume",
        yaxis_title="Volume",
        height=220,
        margin=dict(l=0, r=0, t=35, b=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    return fig


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

ticker = st.session_state.get("ticker", "RELIANCE.NS")

st.title(f"Overview — {ticker}")

with st.spinner("Fetching live data…"):
    info = get_stock_info(ticker)

if info.get("error"):
    st.error(info["error"])
    st.stop()

# ---- Metric cards ----
price = info["currentPrice"] or 0.0
prev = info["previousClose"] or 0.0
chg_pts = info["changePts"]
chg_pct = info["changePercent"]
mcap = info["marketCap"] or 0
pe = info["trailingPE"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Price (₹)", f"₹{price:,.2f}", f"₹{chg_pts:+,.2f}")
col2.metric(
    "1D Change",
    f"{chg_pct:+.2f}%",
    delta_color="normal" if chg_pct >= 0 else "inverse",
)
col3.metric("Market Cap", fmt_mcap(mcap))
col4.metric("P/E (Trailing)", f"{pe:.1f}" if pe else "N/A")

st.divider()

# ---- Price history ----
period_map = {"1 Month": "1mo", "3 Months": "3mo", "6 Months": "6mo",
              "1 Year": "1y", "2 Years": "2y", "5 Years": "5y"}
period_label = st.selectbox("Chart period", list(period_map.keys()), index=3)
period = period_map[period_label]

with st.spinner("Loading chart data…"):
    hist = get_price_history(ticker, period)
    nifty = get_price_history("^NSEI", period)

if hist.empty:
    st.warning("Price history unavailable for this ticker.")
else:
    st.plotly_chart(build_price_chart(hist, nifty, ticker), use_container_width=True)
    st.plotly_chart(build_volume_chart(hist, ticker), use_container_width=True)

st.divider()

# ---- Key stats table ----
st.subheader("Key Statistics")

def pct(v):
    return f"{float(v)*100:.2f}%" if v is not None else "N/A"

stats = {
    "Company Name": info["longName"],
    "Sector": info["sector"],
    "Industry": info["industry"],
    "Exchange": info["exchange"],
    "Currency": info["currency"],
    "52-Week High": f"₹{info['fiftyTwoWeekHigh']:,.2f}" if info["fiftyTwoWeekHigh"] else "N/A",
    "52-Week Low": f"₹{info['fiftyTwoWeekLow']:,.2f}" if info["fiftyTwoWeekLow"] else "N/A",
    "EPS (TTM)": f"₹{info['trailingEps']:,.2f}" if info["trailingEps"] else "N/A",
    "Forward P/E": f"{info['forwardPE']:.2f}" if info["forwardPE"] else "N/A",
    "Price/Book": f"{info['priceToBook']:.2f}" if info["priceToBook"] else "N/A",
    "Dividend Yield": pct(info["dividendYield"]),
    "Beta": f"{info['beta']:.2f}" if info["beta"] else "N/A",
    "Volume": f"{info['volume']:,}" if info["volume"] else "N/A",
    "Avg Volume": f"{info['averageVolume']:,}" if info["averageVolume"] else "N/A",
    "Revenue Growth": pct(info["revenueGrowth"]),
    "Earnings Growth": pct(info["earningsGrowth"]),
    "ROE": pct(info["returnOnEquity"]),
    "Debt/Equity": f"{info['debtToEquity']:.2f}" if info["debtToEquity"] else "N/A",
    "Current Ratio": f"{info['currentRatio']:.2f}" if info["currentRatio"] else "N/A",
    "Operating Margin": pct(info["operatingMargins"]),
    "Net Profit Margin": pct(info["profitMargins"]),
}

half = len(stats) // 2
items = list(stats.items())
left_col, right_col = st.columns(2)
with left_col:
    st.table(pd.DataFrame(items[:half], columns=["Metric", "Value"]).set_index("Metric"))
with right_col:
    st.table(pd.DataFrame(items[half:], columns=["Metric", "Value"]).set_index("Metric"))
