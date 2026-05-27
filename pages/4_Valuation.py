"""
Valuation page — interactive DCF model with sliders, waterfall chart,
implied price vs. market price, and sensitivity table.
"""
from __future__ import annotations

import sys
import os

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import get_stock_info, get_financials
from core.dcf import run_dcf, sensitivity_table

st.set_page_config(page_title="Valuation | India Stock Analyzer", layout="wide")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def waterfall_chart(result: dict) -> go.Figure:
    """Render a waterfall: PV of FCFs → PV Terminal → EV → Equity Value."""
    sum_pv = result["sum_pv_fcf"]
    pv_tv = result["pv_terminal"]
    ev = result["enterprise_value"]
    eq = result["equity_value"]

    labels = ["PV of FCFs", "PV Terminal Value", "Enterprise Value", "Equity Value"]
    values = [sum_pv, pv_tv, 0, 0]
    measures = ["relative", "relative", "total", "total"]
    text = [f"₹{v:,.0f} Cr" for v in [sum_pv, pv_tv, ev, eq]]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measures,
        x=labels,
        y=values + [ev, eq],
        text=text,
        textposition="outside",
        connector=dict(line=dict(color="#9E9E9E")),
        increasing=dict(marker=dict(color="#1976D2")),
        decreasing=dict(marker=dict(color="#C62828")),
        totals=dict(marker=dict(color="#1565C0")),
    ))
    fig.update_layout(
        title="DCF Value Bridge (₹ Crore)",
        height=380,
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def color_upside(upside: float) -> str:
    if upside >= 20:
        return "#2E7D32"
    if upside >= 0:
        return "#F57F17"
    return "#C62828"


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

ticker = st.session_state.get("ticker", "RELIANCE.NS")
st.title(f"DCF Valuation — {ticker}")

with st.spinner("Fetching data…"):
    info = get_stock_info(ticker)
    fins = get_financials(ticker)

if info.get("error"):
    st.error(info["error"])
    st.stop()

# Attempt to pull base revenue and shares from yfinance
base_revenue = info.get("totalRevenue") or 0.0
shares = 0.0
net_debt = 0.0

try:
    bs = fins["balance_sheet"]
    if not bs.empty:
        total_debt = 0.0
        cash = 0.0
        for lbl in ["Total Debt", "Long Term Debt"]:
            if lbl in bs.index:
                total_debt = float(bs.loc[lbl].iloc[0]) if not pd.isna(bs.loc[lbl].iloc[0]) else 0.0
                break
        for lbl in ["Cash And Cash Equivalents", "Cash"]:
            if lbl in bs.index:
                cash = float(bs.loc[lbl].iloc[0]) if not pd.isna(bs.loc[lbl].iloc[0]) else 0.0
                break
        net_debt = total_debt - cash

    # sharesOutstanding comes from fast_info via get_stock_info — works on cloud
    shares = info.get("sharesOutstanding") or 1.0
except Exception:
    shares = 1.0

if base_revenue == 0:
    st.warning(
        "Revenue data unavailable — using a placeholder of ₹10,000 Cr. "
        "Adjust assumptions below to model the stock."
    )
    base_revenue = 1e11  # 10,000 Cr as placeholder

current_price = info.get("currentPrice") or 0.0

# ---------------------------------------------------------------------------
# Sliders
# ---------------------------------------------------------------------------

st.subheader("Model Assumptions")
c1, c2, c3 = st.columns(3)

with c1:
    rev_growth = st.slider("Revenue Growth Rate (%)", 5, 30, 10, step=1) / 100
    ebit_margin = st.slider("EBIT Margin (%)", 10, 40, 25, step=1) / 100

with c2:
    wacc = st.slider("WACC (%)", 8, 15, 11, step=1) / 100
    tg = st.slider("Terminal Growth Rate (%)", 2, 6, 4, step=1) / 100

with c3:
    proj_years = st.slider("Projection Years", 5, 15, 10, step=1)
    tax_rate = st.slider("Tax Rate (%)", 15, 35, 25, step=1) / 100

st.divider()

# ---------------------------------------------------------------------------
# DCF computation
# ---------------------------------------------------------------------------

result = run_dcf(
    base_revenue=base_revenue,
    shares_outstanding=shares,
    net_debt=net_debt,
    revenue_growth=rev_growth,
    ebit_margin=ebit_margin,
    tax_rate=tax_rate,
    wacc=wacc,
    terminal_growth=tg,
    projection_years=proj_years,
)

intrinsic = result["intrinsic_price"]
upside = ((intrinsic - current_price) / current_price * 100) if current_price else 0.0

# ---- Summary metrics ----
m1, m2, m3, m4 = st.columns(4)
m1.metric("Intrinsic Price (₹)", f"₹{intrinsic:,.2f}")
m2.metric("Current Market Price", f"₹{current_price:,.2f}")
m3.metric("Enterprise Value (₹Cr)", f"₹{result['enterprise_value']:,.0f}")
m4.metric("Equity Value (₹Cr)", f"₹{result['equity_value']:,.0f}")

upside_color = color_upside(upside)
st.markdown(
    f"""<div style="background:{upside_color};padding:16px;border-radius:8px;
    color:white;text-align:center;margin:12px 0">
    <div style="font-size:13px">Implied Upside / Downside vs. Market Price</div>
    <div style="font-size:32px;font-weight:800">{upside:+.1f}%</div>
    <div style="font-size:11px;opacity:0.85">Intrinsic ₹{intrinsic:,.2f} vs. Market ₹{current_price:,.2f}</div>
    </div>""",
    unsafe_allow_html=True,
)

st.divider()

# ---- Charts + table ----
col_chart, col_tbl = st.columns([2, 3])

with col_chart:
    st.plotly_chart(waterfall_chart(result), use_container_width=True)

with col_tbl:
    st.caption("Projected Free Cash Flows")
    proj = result["projections"].set_index("Year")
    st.dataframe(proj.style.format("{:,.1f}"), use_container_width=True)

st.divider()

# ---- Sensitivity table ----
st.subheader("Sensitivity Analysis — Implied Price (₹)")
st.caption("Implied price per share across WACC (rows) × Terminal Growth (columns)")

wacc_range = [w / 100 for w in range(8, 16)]
tg_range = [g / 100 for g in range(2, 7)]

with st.spinner("Computing sensitivity…"):
    sens = sensitivity_table(
        base_revenue=base_revenue,
        shares_outstanding=shares,
        net_debt=net_debt,
        wacc_range=wacc_range,
        tg_range=tg_range,
        revenue_growth=rev_growth,
        ebit_margin=ebit_margin,
        tax_rate=tax_rate,
        projection_years=proj_years,
    )

def highlight_closest(val):
    """Highlight cells closest to current market price."""
    if pd.isna(val):
        return "background-color: #EEEEEE; color: #9E9E9E"
    diff = abs(val - current_price) / current_price if current_price else 1
    if diff < 0.05:
        return "background-color: #C8E6C9; color: #1B5E20; font-weight: bold"
    if val > current_price:
        return "background-color: #E8F5E9; color: #2E7D32"
    return "background-color: #FFEBEE; color: #B71C1C"

st.dataframe(
    sens.style.format("{:,.0f}").map(highlight_closest),
    use_container_width=True,
)
st.caption("Green = above current price (upside) | Red = below current price (downside) | Bold = within 5% of market price")
