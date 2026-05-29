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
    # Nifty 50 + popular large/mid-caps
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
    "HCLTECH.NS": "HCL Technologies Limited",
    "ULTRACEMCO.NS": "UltraTech Cement Limited",
    "BAJAJFINSV.NS": "Bajaj Finserv Limited",
    "NESTLEIND.NS": "Nestle India Limited",
    "TATAMOTORS.NS": "Tata Motors Limited",
    "ONGC.NS": "Oil and Natural Gas Corporation",
    "NTPC.NS": "NTPC Limited",
    "POWERGRID.NS": "Power Grid Corporation of India",
    "COALINDIA.NS": "Coal India Limited",
    "TATASTEEL.NS": "Tata Steel Limited",
    "JSWSTEEL.NS": "JSW Steel Limited",
    "HINDALCO.NS": "Hindalco Industries Limited",
    "DIVISLAB.NS": "Divi's Laboratories Limited",
    "APOLLOHOSP.NS": "Apollo Hospitals Enterprise Limited",
    "TECHM.NS": "Tech Mahindra Limited",
    "GRASIM.NS": "Grasim Industries Limited",
    "ADANIENT.NS": "Adani Enterprises Limited",
    "ADANIPORTS.NS": "Adani Ports and SEZ Limited",
    "ADANIGREEN.NS": "Adani Green Energy Limited",
    "TATACONSUM.NS": "Tata Consumer Products Limited",
    "BRITANNIA.NS": "Britannia Industries Limited",
    "EICHERMOT.NS": "Eicher Motors Limited",
    "HEROMOTOCO.NS": "Hero MotoCorp Limited",
    "BAJAJ-AUTO.NS": "Bajaj Auto Limited",
    "M&M.NS": "Mahindra & Mahindra Limited",
    "INDUSINDBK.NS": "IndusInd Bank Limited",
    "BPCL.NS": "Bharat Petroleum Corporation Limited",
    "VEDL.NS": "Vedanta Limited",
    "SAIL.NS": "Steel Authority of India Limited",
    "SBILIFE.NS": "SBI Life Insurance Company Limited",
    "HDFCLIFE.NS": "HDFC Life Insurance Company Limited",
    "ICICIGI.NS": "ICICI Lombard General Insurance",
    "SHRIRAMFIN.NS": "Shriram Finance Limited",
    "LUPIN.NS": "Lupin Limited",
    "AUROPHARMA.NS": "Aurobindo Pharma Limited",
    "TORNTPHARM.NS": "Torrent Pharmaceuticals Limited",
    "ALKEM.NS": "Alkem Laboratories Limited",
    "ZOMATO.NS": "Zomato Limited",
    "NYKAA.NS": "FSN E-Commerce Ventures (Nykaa)",
    "PAYTM.NS": "One 97 Communications (Paytm)",
    "DMART.NS": "Avenue Supermarts Limited",
    "PERSISTENT.NS": "Persistent Systems Limited",
    "MPHASIS.NS": "Mphasis Limited",
    "COFORGE.NS": "Coforge Limited",
    "LTTS.NS": "L&T Technology Services Limited",
    "PIDILITIND.NS": "Pidilite Industries Limited",
    "MARICO.NS": "Marico Limited",
    "DABUR.NS": "Dabur India Limited",
    "GODREJCP.NS": "Godrej Consumer Products Limited",
    "HAVELLS.NS": "Havells India Limited",
    "SIEMENS.NS": "Siemens Limited",
    "ABB.NS": "ABB India Limited",
    "POLYCAB.NS": "Polycab India Limited",
    "PFIZER.NS": "Pfizer Limited",
    "SANOFI.NS": "Sanofi India Limited",
    "ABBOTINDIA.NS": "Abbott India Limited",
    "MANKIND.NS": "Mankind Pharma Limited",
    "BANKBARODA.NS": "Bank of Baroda",
    "PNB.NS": "Punjab National Bank",
    "CANARABANK.NS": "Canara Bank",
    "UNIONBANK.NS": "Union Bank of India",
    "BANDHANBNK.NS": "Bandhan Bank Limited",
    "FEDERALBNK.NS": "The Federal Bank Limited",
    "IDFCFIRSTB.NS": "IDFC First Bank Limited",
    "YESBANK.NS": "Yes Bank Limited",
    "TATAPOWER.NS": "Tata Power Company Limited",
    "NHPC.NS": "NHPC Limited",
    "IRFC.NS": "Indian Railway Finance Corporation",
    "HAL.NS": "Hindustan Aeronautics Limited",
    "BEL.NS": "Bharat Electronics Limited",
    "IRCTC.NS": "Indian Railway Catering and Tourism Corporation",
    "NMDC.NS": "NMDC Limited",
    "GAIL.NS": "GAIL India Limited",
    "IOC.NS": "Indian Oil Corporation Limited",
    "HINDPETRO.NS": "Hindustan Petroleum Corporation Limited",
    "MRF.NS": "MRF Limited",
    "APOLLOTYRE.NS": "Apollo Tyres Limited",
    "BALKRISIND.NS": "Balkrishna Industries Limited",
    "PAGEIND.NS": "Page Industries Limited",
    "MUTHOOTFIN.NS": "Muthoot Finance Limited",
    "CHOLAFIN.NS": "Cholamandalam Investment and Finance",
    "LTFH.NS": "L&T Finance Holdings Limited",
    "LICHSGFIN.NS": "LIC Housing Finance Limited",
    "RECLTD.NS": "REC Limited",
    "PFC.NS": "Power Finance Corporation Limited",
}

_KNOWN_SECTORS = {
    # Banks
    "HDFCBANK.NS": "Financial Services", "ICICIBANK.NS": "Financial Services",
    "SBIN.NS": "Financial Services", "KOTAKBANK.NS": "Financial Services",
    "AXISBANK.NS": "Financial Services", "INDUSINDBK.NS": "Financial Services",
    "BANDHANBNK.NS": "Financial Services", "FEDERALBNK.NS": "Financial Services",
    "IDFCFIRSTB.NS": "Financial Services", "YESBANK.NS": "Financial Services",
    "BANKBARODA.NS": "Financial Services", "PNB.NS": "Financial Services",
    "CANARABANK.NS": "Financial Services", "UNIONBANK.NS": "Financial Services",
    # Finance / NBFC
    "BAJFINANCE.NS": "Financial Services", "BAJAJFINSV.NS": "Financial Services",
    "SBILIFE.NS": "Financial Services", "HDFCLIFE.NS": "Financial Services",
    "ICICIGI.NS": "Financial Services", "SHRIRAMFIN.NS": "Financial Services",
    "MUTHOOTFIN.NS": "Financial Services", "CHOLAFIN.NS": "Financial Services",
    "LTFH.NS": "Financial Services", "LICHSGFIN.NS": "Financial Services",
    "RECLTD.NS": "Financial Services", "PFC.NS": "Financial Services",
    # IT / Technology
    "TCS.NS": "Technology", "INFY.NS": "Technology", "WIPRO.NS": "Technology",
    "HCLTECH.NS": "Technology", "TECHM.NS": "Technology", "PERSISTENT.NS": "Technology",
    "MPHASIS.NS": "Technology", "COFORGE.NS": "Technology", "LTTS.NS": "Technology",
    # Healthcare / Pharma
    "SUNPHARMA.NS": "Healthcare", "DRREDDY.NS": "Healthcare", "CIPLA.NS": "Healthcare",
    "DIVISLAB.NS": "Healthcare", "LUPIN.NS": "Healthcare", "AUROPHARMA.NS": "Healthcare",
    "TORNTPHARM.NS": "Healthcare", "ALKEM.NS": "Healthcare", "APOLLOHOSP.NS": "Healthcare",
    "PFIZER.NS": "Healthcare", "SANOFI.NS": "Healthcare", "ABBOTINDIA.NS": "Healthcare",
    "MANKIND.NS": "Healthcare",
    # Energy / Oil & Gas
    "RELIANCE.NS": "Energy", "ONGC.NS": "Energy", "BPCL.NS": "Energy",
    "IOC.NS": "Energy", "HINDPETRO.NS": "Energy", "GAIL.NS": "Energy",
    # Power / Utilities
    "NTPC.NS": "Utilities", "POWERGRID.NS": "Utilities", "TATAPOWER.NS": "Utilities",
    "ADANIGREEN.NS": "Utilities", "NHPC.NS": "Utilities",
    # Consumer Defensive / FMCG
    "HINDUNILVR.NS": "Consumer Defensive", "ITC.NS": "Consumer Defensive",
    "NESTLEIND.NS": "Consumer Defensive", "BRITANNIA.NS": "Consumer Defensive",
    "MARICO.NS": "Consumer Defensive", "DABUR.NS": "Consumer Defensive",
    "GODREJCP.NS": "Consumer Defensive", "TATACONSUM.NS": "Consumer Defensive",
    # Consumer Cyclical / Auto
    "MARUTI.NS": "Consumer Cyclical", "TATAMOTORS.NS": "Consumer Cyclical",
    "M&M.NS": "Consumer Cyclical", "BAJAJ-AUTO.NS": "Consumer Cyclical",
    "HEROMOTOCO.NS": "Consumer Cyclical", "EICHERMOT.NS": "Consumer Cyclical",
    "MRF.NS": "Consumer Cyclical", "APOLLOTYRE.NS": "Consumer Cyclical",
    "BALKRISIND.NS": "Consumer Cyclical", "TITAN.NS": "Consumer Cyclical",
    "PAGEIND.NS": "Consumer Cyclical", "DMART.NS": "Consumer Cyclical",
    "ZOMATO.NS": "Consumer Cyclical", "NYKAA.NS": "Consumer Cyclical",
    # Industrials
    "LT.NS": "Industrials", "SIEMENS.NS": "Industrials", "ABB.NS": "Industrials",
    "HAVELLS.NS": "Industrials", "POLYCAB.NS": "Industrials",
    "HAL.NS": "Industrials", "BEL.NS": "Industrials", "IRCTC.NS": "Industrials",
    "ADANIPORTS.NS": "Industrials", "ADANIENT.NS": "Industrials",
    # Telecom
    "BHARTIARTL.NS": "Communication Services",
    # Materials / Metals
    "TATASTEEL.NS": "Basic Materials", "JSWSTEEL.NS": "Basic Materials",
    "HINDALCO.NS": "Basic Materials", "VEDL.NS": "Basic Materials",
    "SAIL.NS": "Basic Materials", "NMDC.NS": "Basic Materials",
    "COALINDIA.NS": "Basic Materials", "ULTRACEMCO.NS": "Basic Materials",
    "GRASIM.NS": "Basic Materials", "ASIANPAINT.NS": "Basic Materials",
    "PIDILITIND.NS": "Basic Materials",
    # Finance / Infrastructure
    "IRFC.NS": "Financial Services", "RECLTD.NS": "Financial Services",
    "PFC.NS": "Financial Services",
    # Fintech
    "PAYTM.NS": "Technology",
}

_KNOWN_INDUSTRIES = {
    # Banks
    "HDFCBANK.NS": "Banks - Regional", "ICICIBANK.NS": "Banks - Regional",
    "SBIN.NS": "Banks - Regional", "KOTAKBANK.NS": "Banks - Regional",
    "AXISBANK.NS": "Banks - Regional", "INDUSINDBK.NS": "Banks - Regional",
    "BANDHANBNK.NS": "Banks - Regional", "FEDERALBNK.NS": "Banks - Regional",
    "IDFCFIRSTB.NS": "Banks - Regional", "YESBANK.NS": "Banks - Regional",
    "BANKBARODA.NS": "Banks - Regional", "PNB.NS": "Banks - Regional",
    "CANARABANK.NS": "Banks - Regional", "UNIONBANK.NS": "Banks - Regional",
    # Finance / NBFC / Insurance
    "BAJFINANCE.NS": "Financial Services", "BAJAJFINSV.NS": "Financial Conglomerates",
    "SBILIFE.NS": "Insurance - Life", "HDFCLIFE.NS": "Insurance - Life",
    "ICICIGI.NS": "Insurance - Property & Casualty",
    "SHRIRAMFIN.NS": "Financial Services", "MUTHOOTFIN.NS": "Financial Services",
    "CHOLAFIN.NS": "Financial Services", "LTFH.NS": "Financial Services",
    "LICHSGFIN.NS": "Mortgage Finance", "RECLTD.NS": "Financial Services",
    "PFC.NS": "Financial Services", "IRFC.NS": "Financial Services",
    # IT
    "TCS.NS": "Information Technology Services",
    "INFY.NS": "Information Technology Services",
    "WIPRO.NS": "Information Technology Services",
    "HCLTECH.NS": "Information Technology Services",
    "TECHM.NS": "Information Technology Services",
    "PERSISTENT.NS": "Software - Application",
    "MPHASIS.NS": "Information Technology Services",
    "COFORGE.NS": "Information Technology Services",
    "LTTS.NS": "Information Technology Services",
    # Pharma / Healthcare
    "SUNPHARMA.NS": "Drug Manufacturers", "DRREDDY.NS": "Drug Manufacturers",
    "CIPLA.NS": "Drug Manufacturers", "DIVISLAB.NS": "Drug Manufacturers",
    "LUPIN.NS": "Drug Manufacturers", "AUROPHARMA.NS": "Drug Manufacturers",
    "TORNTPHARM.NS": "Drug Manufacturers", "ALKEM.NS": "Drug Manufacturers",
    "APOLLOHOSP.NS": "Medical Facilities", "PFIZER.NS": "Drug Manufacturers",
    "SANOFI.NS": "Drug Manufacturers", "ABBOTINDIA.NS": "Drug Manufacturers",
    "MANKIND.NS": "Drug Manufacturers",
    # Energy
    "RELIANCE.NS": "Oil & Gas Refining & Marketing",
    "ONGC.NS": "Oil & Gas Exploration & Production",
    "BPCL.NS": "Oil & Gas Refining & Marketing",
    "IOC.NS": "Oil & Gas Refining & Marketing",
    "HINDPETRO.NS": "Oil & Gas Refining & Marketing",
    "GAIL.NS": "Gas Distribution",
    # Power
    "NTPC.NS": "Utilities - Regulated Electric",
    "POWERGRID.NS": "Utilities - Regulated Electric",
    "TATAPOWER.NS": "Utilities - Independent Power Producers",
    "ADANIGREEN.NS": "Utilities - Renewable",
    "NHPC.NS": "Utilities - Regulated Electric",
    # FMCG / Consumer
    "HINDUNILVR.NS": "Household & Personal Products",
    "ITC.NS": "Tobacco", "NESTLEIND.NS": "Packaged Foods",
    "BRITANNIA.NS": "Packaged Foods", "MARICO.NS": "Household & Personal Products",
    "DABUR.NS": "Household & Personal Products",
    "GODREJCP.NS": "Household & Personal Products",
    "TATACONSUM.NS": "Packaged Foods",
    # Auto
    "MARUTI.NS": "Auto Manufacturers", "TATAMOTORS.NS": "Auto Manufacturers",
    "M&M.NS": "Auto Manufacturers", "BAJAJ-AUTO.NS": "Auto Manufacturers",
    "HEROMOTOCO.NS": "Auto Manufacturers", "EICHERMOT.NS": "Auto Manufacturers",
    "MRF.NS": "Auto Parts", "APOLLOTYRE.NS": "Auto Parts",
    "BALKRISIND.NS": "Auto Parts",
    # Consumer Retail / Luxury
    "TITAN.NS": "Luxury Goods", "PAGEIND.NS": "Apparel Manufacturing",
    "DMART.NS": "Discount Stores", "ZOMATO.NS": "Internet Retail",
    "NYKAA.NS": "Internet Retail", "PAYTM.NS": "Software - Application",
    # Industrials
    "LT.NS": "Engineering & Construction",
    "SIEMENS.NS": "Specialty Industrial Machinery",
    "ABB.NS": "Specialty Industrial Machinery",
    "HAVELLS.NS": "Electrical Equipment & Parts",
    "POLYCAB.NS": "Electrical Equipment & Parts",
    "HAL.NS": "Aerospace & Defense", "BEL.NS": "Aerospace & Defense",
    "IRCTC.NS": "Railroads", "ADANIPORTS.NS": "Marine Shipping",
    "ADANIENT.NS": "Conglomerates",
    # Telecom
    "BHARTIARTL.NS": "Telecom Services",
    # Materials / Metals / Cement
    "TATASTEEL.NS": "Steel", "JSWSTEEL.NS": "Steel",
    "HINDALCO.NS": "Aluminum", "VEDL.NS": "Other Industrial Metals & Mining",
    "SAIL.NS": "Steel", "NMDC.NS": "Other Industrial Metals & Mining",
    "COALINDIA.NS": "Thermal Coal",
    "ULTRACEMCO.NS": "Building Materials", "GRASIM.NS": "Conglomerates",
    "ASIANPAINT.NS": "Specialty Chemicals", "PIDILITIND.NS": "Specialty Chemicals",
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

        # Prefer net0/shares (always in INR) over the "Basic EPS" row which
        # may be in USD for cross-listed stocks (e.g. INFY), causing wrong P/E.
        if net0 is not None and shares and shares > 1e6:
            out["trailingEps"] = net0 / shares
        elif eps_r is not None:
            eps_val = _val(eps_r, 0)
            if eps_val:
                out["trailingEps"] = eps_val

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
                out["debtToEquity"] = round(debt / abs(equity), 4)
            if net0 is not None:
                out["returnOnEquity"] = net0 / equity

        if assets and assets != 0 and net0 is not None:
            out["returnOnAssets"] = net0 / assets

        if curr_assets and curr_liab and curr_liab != 0:
            out["currentRatio"] = curr_assets / curr_liab

        if equity and equity > 0 and shares and shares > 1e6 and price:
            book_per_share = equity / shares
            if book_per_share > 0:
                out["priceToBook"] = price / book_per_share

    return out


# ---------------------------------------------------------------------------
# Normalizers — fix yfinance format inconsistencies
# ---------------------------------------------------------------------------

def _norm_dte(from_info, from_computed):
    """
    yfinance t.info returns debtToEquity as (debt/equity)*100.
    Our _compute_ratios returns actual ratio. Normalize everything to actual ratio.
    """
    raw = from_info if from_info is not None else from_computed
    if raw is None:
        return None
    try:
        v = float(raw)
        # Values from t.info are ×100 format; computed is already actual ratio.
        # Heuristic: if raw came from t.info (from_info is not None) it needs ÷100.
        if from_info is not None:
            return round(v / 100, 4)
        return round(v, 4)
    except Exception:
        return None


def _norm_div_yield(from_info, from_computed):
    """
    yfinance t.info returns dividendYield in % format for Indian tickers
    (e.g., 5.43 means 5.43%). Our computed value is decimal (0.054).
    Normalize everything to decimal so pct() displays correctly.
    """
    if from_info is not None:
        try:
            v = float(from_info)
            # If > 0.20 it's almost certainly already in % format — divide by 100.
            # Handles both 5.43 (TCS) and 0.41 (Reliance) which are both in % format.
            return v / 100
        except Exception:
            pass
    return from_computed  # already decimal from t.dividends / price


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
        market_cap = getattr(fi, "market_cap", None) or 0

        # shares: prefer fast_info, fall back to market_cap/price (reliable on cloud)
        shares = getattr(fi, "shares", None)
        if not shares or shares < 1000:
            shares = (market_cap / price) if (market_cap and price) else 1.0
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

        # 3. Dividend yield from trailing 12-month dividends (works on cloud)
        dividend_yield_computed = None
        try:
            divs = _retry(lambda: t.dividends)
            if divs is not None and not divs.empty:
                tz = divs.index.tz
                cutoff = pd.Timestamp.now(tz=tz) - pd.DateOffset(years=1)
                trailing = float(divs[divs.index >= cutoff].sum())
                if trailing > 0 and price:
                    dividend_yield_computed = trailing / price
        except Exception:
            pass

        # 4. Beta vs Nifty 50 computed from 1-year price history
        beta_computed = None
        try:
            s_hist = _retry(lambda: t.history(period="1y"))
            n_hist = _retry(lambda: yf.Ticker("^NSEI", session=_make_session()).history(period="1y"))
            if not s_hist.empty and not n_hist.empty:
                s_close = s_hist["Close"].copy()
                n_close = n_hist["Close"].copy()
                s_close.index = pd.to_datetime(s_close.index).tz_localize(None)
                n_close.index = pd.to_datetime(n_close.index).tz_localize(None)
                combined = pd.concat([s_close, n_close], axis=1, join="inner")
                combined.columns = ["stock", "nifty"]
                rets = combined.pct_change().dropna()
                if len(rets) >= 30:
                    cov_mat = rets.cov()
                    beta_computed = cov_mat.loc["stock", "nifty"] / cov_mat.loc["nifty", "nifty"]
        except Exception:
            pass

        # 5. t.info — try for fields we can't compute (sector, longName, etc.)
        #    Falls back silently if blocked on cloud
        try:
            info = _retry(lambda: t.info, retries=2, delay=1.0) or {}
        except Exception:
            info = {}

        avg_vol = getattr(fi, "three_month_average_volume", None)

        result = {
            "ticker":           ticker,
            "longName":         _safe_val(info, "longName") or _KNOWN_NAMES.get(ticker, ticker),
            "sector":           _safe_val(info, "sector")   or _KNOWN_SECTORS.get(ticker, "N/A"),
            "industry":         _safe_val(info, "industry") or _KNOWN_INDUSTRIES.get(ticker, "N/A"),
            "currentPrice":     price,
            "previousClose":    prev_close,
            "marketCap":        market_cap,
            "trailingPE":       _safe_val(info, "trailingPE")       or computed.get("trailingPE"),
            "forwardPE":        _safe_val(info, "forwardPE"),
            "priceToBook":      _safe_val(info, "priceToBook")      or computed.get("priceToBook"),
            "trailingEps":      _safe_val(info, "trailingEps")      or computed.get("trailingEps"),
            "dividendYield":    _norm_div_yield(_safe_val(info, "dividendYield"), dividend_yield_computed),
            "fiftyTwoWeekHigh": wk52_high or _safe_val(info, "fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow":  wk52_low  or _safe_val(info, "fiftyTwoWeekLow"),
            "volume":           avg_vol or _safe_val(info, "volume", 0),
            "averageVolume":    avg_vol or _safe_val(info, "averageVolume", 0),
            "beta":             _safe_val(info, "beta")             or beta_computed,
            "revenueGrowth":    _safe_val(info, "revenueGrowth")    or computed.get("revenueGrowth"),
            "earningsGrowth":   _safe_val(info, "earningsGrowth")   or computed.get("earningsGrowth"),
            "returnOnEquity":   _safe_val(info, "returnOnEquity")   or computed.get("returnOnEquity"),
            "returnOnAssets":   _safe_val(info, "returnOnAssets")   or computed.get("returnOnAssets"),
            "debtToEquity":     _norm_dte(_safe_val(info, "debtToEquity"), computed.get("debtToEquity")),
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
