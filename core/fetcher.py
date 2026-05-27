"""
Live NSE/BSE data fetching via yfinance and nsepython.
All functions are cached for 5 minutes to avoid API rate limits.
"""
from __future__ import annotations

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_val(info: dict, key: str, default=None):
    """Return info[key] if present and not NaN, else default."""
    val = info.get(key, default)
    if val is None:
        return default
    try:
        if np.isnan(float(val)):
            return default
    except (TypeError, ValueError):
        pass
    return val


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_stock_info(ticker: str) -> dict:
    """
    Fetch summary fundamentals for a single NSE/BSE ticker.

    Args:
        ticker: e.g. "RELIANCE.NS" or "TCS.NS"

    Returns:
        dict with keys: currentPrice, previousClose, marketCap, trailingPE,
        forwardPE, priceToBook, trailingEps, dividendYield,
        fiftyTwoWeekHigh, fiftyTwoWeekLow, volume, sector, longName,
        error (str | None)
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}

        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            return {"error": f"No data found for ticker '{ticker}'. Check the symbol (e.g. RELIANCE.NS)."}

        result = {
            "ticker": ticker,
            "longName": _safe_val(info, "longName", ticker),
            "sector": _safe_val(info, "sector", "N/A"),
            "industry": _safe_val(info, "industry", "N/A"),
            "currentPrice": _safe_val(info, "currentPrice") or _safe_val(info, "regularMarketPrice", 0.0),
            "previousClose": _safe_val(info, "previousClose", 0.0),
            "marketCap": _safe_val(info, "marketCap", 0),
            "trailingPE": _safe_val(info, "trailingPE"),
            "forwardPE": _safe_val(info, "forwardPE"),
            "priceToBook": _safe_val(info, "priceToBook"),
            "trailingEps": _safe_val(info, "trailingEps"),
            "dividendYield": _safe_val(info, "dividendYield"),
            "fiftyTwoWeekHigh": _safe_val(info, "fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": _safe_val(info, "fiftyTwoWeekLow"),
            "volume": _safe_val(info, "volume", 0),
            "averageVolume": _safe_val(info, "averageVolume", 0),
            "beta": _safe_val(info, "beta"),
            "revenueGrowth": _safe_val(info, "revenueGrowth"),
            "earningsGrowth": _safe_val(info, "earningsGrowth"),
            "returnOnEquity": _safe_val(info, "returnOnEquity"),
            "returnOnAssets": _safe_val(info, "returnOnAssets"),
            "debtToEquity": _safe_val(info, "debtToEquity"),
            "currentRatio": _safe_val(info, "currentRatio"),
            "operatingMargins": _safe_val(info, "operatingMargins"),
            "profitMargins": _safe_val(info, "profitMargins"),
            "grossMargins": _safe_val(info, "grossMargins"),
            "totalRevenue": _safe_val(info, "totalRevenue"),
            "ebitda": _safe_val(info, "ebitda"),
            "freeCashflow": _safe_val(info, "freeCashflow"),
            "currency": _safe_val(info, "currency", "INR"),
            "exchange": _safe_val(info, "exchange", "NSE"),
            "error": None,
        }

        # Compute 1-day change %
        cur = result["currentPrice"] or 0.0
        prev = result["previousClose"] or 0.0
        result["changePercent"] = ((cur - prev) / prev * 100) if prev else 0.0
        result["changePts"] = cur - prev

        return result

    except Exception as exc:
        return {"error": f"Failed to fetch data for '{ticker}': {exc}", "ticker": ticker}


@st.cache_data(ttl=300)
def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV price history for the given ticker and period.

    Args:
        ticker: e.g. "RELIANCE.NS"
        period: yfinance period string — "1mo", "3mo", "6mo", "1y", "2y", "5y"

    Returns:
        DataFrame with columns [Open, High, Low, Close, Volume] indexed by Date.
        Returns empty DataFrame on error.
    """
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_financials(ticker: str) -> dict:
    """
    Fetch income statement, balance sheet, and cash flow statement.

    Returns:
        dict with keys 'income_stmt', 'balance_sheet', 'cashflow' (DataFrames)
        and 'error' (None or str).
    """
    try:
        t = yf.Ticker(ticker)
        income = t.financials          # annual income statement
        balance = t.balance_sheet      # annual balance sheet
        cashflow = t.cashflow          # annual cash flow

        return {
            "income_stmt": income if income is not None and not income.empty else pd.DataFrame(),
            "balance_sheet": balance if balance is not None and not balance.empty else pd.DataFrame(),
            "cashflow": cashflow if cashflow is not None and not cashflow.empty else pd.DataFrame(),
            "error": None,
        }
    except Exception as exc:
        return {
            "income_stmt": pd.DataFrame(),
            "balance_sheet": pd.DataFrame(),
            "cashflow": pd.DataFrame(),
            "error": str(exc),
        }


@st.cache_data(ttl=300)
def get_nifty50_data() -> pd.DataFrame:
    """
    Fetch live price and fundamentals for a curated list of NSE blue-chips.

    Returns:
        DataFrame with columns:
        Company, Ticker, Price, Change%, P/E, EPS, MarketCap(Cr), Sector
    """
    tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
        "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
        "LT.NS", "AXISBANK.NS", "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS",
    ]

    rows = []
    for t in tickers:
        info = get_stock_info(t)
        if info.get("error"):
            continue
        mcap_cr = (info["marketCap"] or 0) / 1e7  # convert to crores
        rows.append({
            "Company": info["longName"] or t,
            "Ticker": t,
            "Price (₹)": round(info["currentPrice"] or 0, 2),
            "1D Change%": round(info["changePercent"] or 0, 2),
            "P/E": round(info["trailingPE"], 2) if info["trailingPE"] else None,
            "EPS (₹)": round(info["trailingEps"], 2) if info["trailingEps"] else None,
            "Mkt Cap (₹Cr)": round(mcap_cr, 0),
            "Sector": info["sector"] or "N/A",
        })

    return pd.DataFrame(rows)
