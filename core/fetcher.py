"""
Live NSE/BSE data fetching via yfinance.
All functions are cached for 10 minutes to reduce API load on cloud.
"""
from __future__ import annotations

import time
import requests
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Known company names — fallback when t.info is unavailable on cloud
# ---------------------------------------------------------------------------

_KNOWN_NAMES = {
    "RELIANCE.NS": "Reliance Industries Limited",
    "TCS.NS": "Tata Consultancy Services",
    "HDFCBANK.NS": "HDFC Bank Limited",
    "INFY.NS": "Infosys Limited",
    "ICICIBANK.NS": "ICICI Bank Limited",
    "HINDUNILVR.NS": "Hindustan Unilever Limited",
    "ITC.NS": "ITC Limited",
    "SBIN.NS": "State Bank of India",
    "BHARTIARTL.NS": "Bharti Airtel Limited",
    "KOTAKBANK.NS": "Kotak Mahindra Bank Limited",
    "LT.NS": "Larsen & Toubro Limited",
    "AXISBANK.NS": "Axis Bank Limited",
    "SUNPHARMA.NS": "Sun Pharmaceutical Industries",
    "DRREDDY.NS": "Dr. Reddy's Laboratories",
    "CIPLA.NS": "Cipla Limited",
    "WIPRO.NS": "Wipro Limited",
    "MARUTI.NS": "Maruti Suzuki India Limited",
    "BAJFINANCE.NS": "Bajaj Finance Limited",
    "ASIANPAINT.NS": "Asian Paints Limited",
    "TITAN.NS": "Titan Company Limited",
}

_KNOWN_SECTORS = {
    "RELIANCE.NS": "Energy", "TCS.NS": "Technology", "HDFCBANK.NS": "Financial Services",
    "INFY.NS": "Technology", "ICICIBANK.NS": "Financial Services",
    "HINDUNILVR.NS": "Consumer Defensive", "ITC.NS": "Consumer Defensive",
    "SBIN.NS": "Financial Services", "BHARTIARTL.NS": "Communication Services",
    "KOTAKBANK.NS": "Financial Services", "LT.NS": "Industrials",
    "AXISBANK.NS": "Financial Services", "SUNPHARMA.NS": "Healthcare",
    "DRREDDY.NS": "Healthcare", "CIPLA.NS": "Healthcare",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    return session


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol, session=_make_session())


def _safe_val(info: dict, key: str, default=None):
    val = info.get(key, default)
    if val is None:
        return default
    try:
        if np.isnan(float(val)):
            return default
    except (TypeError, ValueError):
        pass
    return val


def _retry(fn, retries: int = 3, delay: float = 2.0):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:
            msg = str(exc).lower()
            if attempt < retries - 1 and any(k in msg for k in ("429", "too many", "rate", "connection")):
                time.sleep(delay * (attempt + 1))
                continue
            raise


def _row(df: pd.DataFrame, *labels: str):
    """Return first matching row from a DataFrame by label."""
    for label in labels:
        if df is not None and not df.empty and label in df.index:
            return df.loc[label]
    return None


def _val(series, idx: int = 0):
    if series is None:
        return None
    try:
        v = float(series.iloc[idx])
        return None if np.isnan(v) else v
    except Exception:
        return None


def _compute_ratios(income: pd.DataFrame, balance: pd.DataFrame, price: float, shares: float) -> dict:
    """
    Derive key financial ratios from income statement and balance sheet.
    Used as primary source when t.info is unavailable on cloud IPs.
    """
    out: dict = {}

    # --- Income statement ---
    if income is not None and not income.empty:
        rev   = _row(income, "Total Revenue", "Revenue")
        net   = _row(income, "Net Income", "Net Income Common Stockholders")
        ebit  = _row(income, "EBIT", "Operating Income", "Ebit")
        eps_r = _row(income, "Basic EPS", "Diluted EPS")

        rev0, rev1 = _val(rev, 0), _val(rev, 1)
        net0, net1 = _val(net, 0), _val(net, 1)
        ebit0      = _val(ebit, 0)

        if rev0:
            out["totalRevenue"] = rev0
            if ebit0 is not None:
                out["operatingMargins"] = ebit0 / rev0
            if net0 is not None:
                out["profitMargins"] = net0 / rev0
            if rev1 and rev1 != 0:
                out["revenueGrowth"] = (rev0 - rev1) / abs(rev1)

        if net0 is not None and net1 is not None and net1 != 0:
            out["earningsGrowth"] = (net0 - net1) / abs(net1)

        if eps_r is not None:
            eps_val = _val(eps_r, 0)
            if eps_val:
                out["trailingEps"] = eps_val
        elif net0 and shares and shares > 1:
            out["trailingEps"] = net0 / shares

        eps_val = out.get("trailingEps")
        if eps_val and price and eps_val != 0:
            out["trailingPE"] = price / eps_val

        # Store net0 for balance sheet ratios below
        out["_net0"] = net0

    # --- Balance sheet ---
    if balance is not None and not balance.empty:
        equity = _val(_row(balance,
            "Stockholders Equity", "Common Stock Equity",
            "Total Equity Gross Minority Interest", "Ordinary Shares Number"), 0)
        debt        = _val(_row(balance, "Total Debt", "Long Term Debt"), 0)
        assets      = _val(_row(balance, "Total Assets"), 0)
        curr_assets = _val(_row(balance, "Current Assets"), 0)
        curr_liab   = _val(_row(balance, "Current Liabilities"), 0)
        net0        = out.pop("_net0", None)

        if equity and equity != 0:
            if debt is not None:
                # Match yfinance format: D/E expressed as (debt/equity)*100
                out["debtToEquity"] = round((debt / abs(equity)) * 100, 2)
            if net0 is not None:
                out["returnOnEquity"] = net0 / equity

        if assets and assets != 0 and net0 is not None:
            out["returnOnAssets"] = net0 / assets

        if curr_assets and curr_liab and curr_liab != 0:
            out["currentRatio"] = curr_assets / curr_liab

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def get_stock_info(ticker: str) -> dict:
    """
    Fetch summary fundamentals for a single NSE/BSE ticker.
    Uses fast_info + financial statements as primary sources so the app
    works reliably on Streamlit Cloud where t.info is often rate-limited.
    """
    try:
        t = _ticker(ticker)

        # 1. fast_info — lightweight, always works on cloud
        fi = _retry(lambda: t.fast_info)
        price = getattr(fi, "last_price", None) or getattr(fi, "previous_close", None)
        if not price:
            return {"error": f"No data found for ticker '{ticker}'. Check the symbol (e.g. RELIANCE.NS)."}
        prev_close = getattr(fi, "previous_close", None) or price
        shares     = getattr(fi, "shares", None) or 1.0
        market_cap = getattr(fi, "market_cap", None) or 0
        wk52_high  = getattr(fi, "year_high", None) or getattr(fi, "fifty_two_week_high", None)
        wk52_low   = getattr(fi, "year_low", None)  or getattr(fi, "fifty_two_week_low", None)
        currency   = getattr(fi, "currency", "INR") or "INR"
        exchange   = getattr(fi, "exchange", "NSE") or "NSE"

        # 2. Financial statements — work reliably, compute all ratios from them
        try:
            income  = _retry(lambda: t.financials)
            balance = _retry(lambda: t.balance_sheet)
        except Exception:
            income  = pd.DataFrame()
            balance = pd.DataFrame()

        computed = _compute_ratios(income, balance, price, shares)

        # 3. t.info — try for fields we can't compute (sector, longName, beta, etc.)
        #    Falls back silently if blocked on cloud
        try:
            info = _retry(lambda: t.info, retries=2, delay=1.0) or {}
        except Exception:
            info = {}

        result = {
            "ticker":           ticker,
            "longName":         _safe_val(info, "longName") or _KNOWN_NAMES.get(ticker, ticker),
            "sector":           _safe_val(info, "sector")   or _KNOWN_SECTORS.get(ticker, "N/A"),
            "industry":         _safe_val(info, "industry", "N/A"),
            "currentPrice":     price,
            "previousClose":    prev_close,
            "marketCap":        market_cap,
            "trailingPE":       _safe_val(info, "trailingPE")       or computed.get("trailingPE"),
            "forwardPE":        _safe_val(info, "forwardPE"),
            "priceToBook":      _safe_val(info, "priceToBook"),
            "trailingEps":      _safe_val(info, "trailingEps")      or computed.get("trailingEps"),
            "dividendYield":    _safe_val(info, "dividendYield"),
            "fiftyTwoWeekHigh": wk52_high or _safe_val(info, "fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow":  wk52_low  or _safe_val(info, "fiftyTwoWeekLow"),
            "volume":           getattr(fi, "three_month_average_volume", None) or _safe_val(info, "volume", 0),
            "averageVolume":    _safe_val(info, "averageVolume", 0),
            "beta":             _safe_val(info, "beta"),
            "revenueGrowth":    _safe_val(info, "revenueGrowth")    or computed.get("revenueGrowth"),
            "earningsGrowth":   _safe_val(info, "earningsGrowth")   or computed.get("earningsGrowth"),
            "returnOnEquity":   _safe_val(info, "returnOnEquity")   or computed.get("returnOnEquity"),
            "returnOnAssets":   _safe_val(info, "returnOnAssets")   or computed.get("returnOnAssets"),
            "debtToEquity":     _safe_val(info, "debtToEquity")     or computed.get("debtToEquity"),
            "currentRatio":     _safe_val(info, "currentRatio")     or computed.get("currentRatio"),
            "operatingMargins": _safe_val(info, "operatingMargins") or computed.get("operatingMargins"),
            "profitMargins":    _safe_val(info, "profitMargins")    or computed.get("profitMargins"),
            "grossMargins":     _safe_val(info, "grossMargins"),
            "totalRevenue":     _safe_val(info, "totalRevenue")     or computed.get("totalRevenue"),
            "ebitda":           _safe_val(info, "ebitda"),
            "freeCashflow":     _safe_val(info, "freeCashflow"),
            "currency":         _safe_val(info, "currency") or currency,
            "exchange":         _safe_val(info, "exchange") or exchange,
            "sharesOutstanding": shares,
            "error": None,
        }

        cur  = result["currentPrice"]  or 0.0
        prev = result["previousClose"] or 0.0
        result["changePercent"] = ((cur - prev) / prev * 100) if prev else 0.0
        result["changePts"]     = cur - prev

        return result

    except Exception as exc:
        return {"error": f"Failed to fetch data for '{ticker}': {exc}", "ticker": ticker}


@st.cache_data(ttl=600)
def get_price_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        t  = _ticker(ticker)
        df = _retry(lambda: t.history(period=period))
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_financials(ticker: str) -> dict:
    try:
        t        = _ticker(ticker)
        income   = _retry(lambda: t.financials)
        balance  = _retry(lambda: t.balance_sheet)
        cashflow = _retry(lambda: t.cashflow)
        return {
            "income_stmt":   income   if income   is not None and not income.empty   else pd.DataFrame(),
            "balance_sheet": balance  if balance  is not None and not balance.empty  else pd.DataFrame(),
            "cashflow":      cashflow if cashflow is not None and not cashflow.empty else pd.DataFrame(),
            "error": None,
        }
    except Exception as exc:
        return {
            "income_stmt": pd.DataFrame(), "balance_sheet": pd.DataFrame(),
            "cashflow": pd.DataFrame(), "error": str(exc),
        }


@st.cache_data(ttl=600)
def get_nifty50_data() -> pd.DataFrame:
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
        mcap_cr = (info["marketCap"] or 0) / 1e7
        rows.append({
            "Company":       info["longName"] or t,
            "Ticker":        t,
            "Price (₹)":     round(info["currentPrice"] or 0, 2),
            "1D Change%":    round(info["changePercent"] or 0, 2),
            "P/E":           round(info["trailingPE"], 2) if info["trailingPE"] else None,
            "EPS (₹)":       round(info["trailingEps"], 2) if info["trailingEps"] else None,
            "Mkt Cap (₹Cr)": round(mcap_cr, 0),
            "Sector":        info["sector"] or "N/A",
        })
    return pd.DataFrame(rows)
