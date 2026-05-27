"""
Fundamentals page — Income statement trends, margins, balance sheet health,
and cash flow analysis.
"""
from __future__ import annotations

import sys
import os

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import get_stock_info, get_financials
from core.ratios import (
    extract_income_summary,
    extract_margins,
    extract_cashflow_summary,
    health_color,
)

st.set_page_config(page_title="Fundamentals | India Stock Analyzer", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COLOR_MAP = {"green": "#2E7D32", "amber": "#F57F17", "red": "#C62828", "grey": "#9E9E9E"}


def color_metric(label: str, value, metric_key: str, unit: str = ""):
    """Render a metric card with health-coded color."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        display = "N/A"
        color = COLOR_MAP["grey"]
    else:
        display = f"{value:.2f}{unit}"
        color = COLOR_MAP[health_color(float(value), metric_key)]

    st.markdown(
        f"""<div style="background:{color};padding:12px 16px;border-radius:8px;color:white;margin:4px 0">
        <div style="font-size:11px;opacity:0.85">{label}</div>
        <div style="font-size:22px;font-weight:700">{display}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def bar_chart(df: pd.DataFrame, cols: list[str], title: str, yaxis: str = "") -> go.Figure:
    """Grouped bar chart for multi-column DataFrames."""
    fig = go.Figure()
    palette = ["#1976D2", "#43A047", "#FB8C00", "#E53935"]
    for i, col in enumerate(cols):
        if col in df.columns:
            fig.add_trace(go.Bar(
                x=df.index, y=df[col], name=col,
                marker_color=palette[i % len(palette)],
            ))
    fig.update_layout(
        title=title,
        barmode="group",
        yaxis_title=yaxis,
        height=320,
        margin=dict(l=0, r=0, t=60, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    return fig


def line_chart(df: pd.DataFrame, cols: list[str], title: str, yaxis: str = "") -> go.Figure:
    """Multi-line trend chart."""
    fig = go.Figure()
    palette = ["#1976D2", "#43A047"]
    for i, col in enumerate(cols):
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=col, mode="lines+markers",
                line=dict(color=palette[i % len(palette)], width=2),
                marker=dict(size=6),
            ))
    fig.update_layout(
        title=title,
        yaxis_title=yaxis,
        height=280,
        margin=dict(l=0, r=0, t=60, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    return fig


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

ticker = st.session_state.get("ticker", "RELIANCE.NS")
st.title(f"Fundamentals — {ticker}")

with st.spinner("Loading financial statements…"):
    info = get_stock_info(ticker)
    fins = get_financials(ticker)

if info.get("error"):
    st.error(info["error"])
    st.stop()

income = fins["income_stmt"]
balance = fins["balance_sheet"]
cashflow = fins["cashflow"]

if fins.get("error"):
    st.warning(f"Partial data warning: {fins['error']}")

# ---- Section 1: Income Statement ----
st.subheader("Income Statement")
inc_df = extract_income_summary(income)

if inc_df.empty:
    st.info("Income statement data unavailable for this ticker.")
else:
    c1, c2 = st.columns([3, 2])
    with c1:
        fig = bar_chart(inc_df, ["Revenue (₹Cr)", "Net Income (₹Cr)"],
                        "Revenue & Net Income (₹ Crore)", "₹ Crore")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.caption("Annual Data (₹ Crore)")
        st.dataframe(inc_df.style.format("{:.2f}"), use_container_width=True)

st.divider()

# ---- Section 2: Margins ----
st.subheader("Profitability Margins")
margin_df = extract_margins(income)

if margin_df.empty:
    st.info("Margin data unavailable.")
else:
    c1, c2 = st.columns([3, 2])
    with c1:
        fig = line_chart(margin_df, ["Operating Margin%", "Net Margin%"],
                         "Margin Trend (%)", "%")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.caption("Margin History (%)")
        st.dataframe(margin_df.style.format("{:.2f}%"), use_container_width=True)

st.divider()

# ---- Section 3: Balance Sheet Health ----
st.subheader("Balance Sheet Health")

roe = (info.get("returnOnEquity") or 0) * 100  # convert to %
dte = info.get("debtToEquity")       # already in % in yfinance
cr  = info.get("currentRatio")

c1, c2, c3, c4 = st.columns(4)
with c1:
    color_metric("Return on Equity (ROE)", roe if roe else None, "roe", "%")
with c2:
    color_metric("Debt-to-Equity", dte, "debt_to_equity", "")
with c3:
    color_metric("Current Ratio", cr, "current_ratio", "x")
with c4:
    roa = (info.get("returnOnAssets") or 0) * 100
    st.metric("Return on Assets", f"{roa:.2f}%" if roa else "N/A")

st.caption("Color coding — Green: healthy | Amber: watch | Red: concern")
st.divider()

# ---- Section 4: Cash Flow ----
st.subheader("Cash Flow Analysis")
cf_df = extract_cashflow_summary(cashflow)

if cf_df.empty:
    st.info("Cash flow data unavailable.")
else:
    c1, c2 = st.columns([3, 2])
    with c1:
        fig = bar_chart(cf_df, ["Operating CF (₹Cr)", "CapEx (₹Cr)", "FCF (₹Cr)"],
                        "Cash Flow Summary (₹ Crore)", "₹ Crore")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.caption("Annual Cash Flow (₹ Crore)")
        st.dataframe(cf_df.style.format("{:.2f}"), use_container_width=True)
