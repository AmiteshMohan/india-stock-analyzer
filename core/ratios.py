"""
Financial ratio calculations derived from raw yfinance DataFrames.
All functions accept DataFrames returned by core/fetcher.get_financials().
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional


def _row(df: pd.DataFrame, *labels: str) -> Optional[pd.Series]:
    """Return the first matching row from a DataFrame by any of the given labels."""
    for label in labels:
        if label in df.index:
            return df.loc[label]
    return None


def extract_income_summary(income_stmt: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Revenue, Net Income, and EPS for the last 4 annual periods.

    Args:
        income_stmt: raw yfinance annual financials DataFrame (rows = line items, cols = dates)

    Returns:
        DataFrame with index = year labels, columns = [Revenue, Net Income, EPS]
    """
    if income_stmt.empty:
        return pd.DataFrame()

    cols = income_stmt.columns[:4]  # most recent 4 years
    rev = _row(income_stmt, "Total Revenue", "Revenue") or pd.Series([np.nan] * len(cols), index=cols)
    net = _row(income_stmt, "Net Income", "Net Income Common Stockholders") or pd.Series([np.nan] * len(cols), index=cols)
    eps = _row(income_stmt, "Basic EPS", "Diluted EPS") or pd.Series([np.nan] * len(cols), index=cols)

    labels = [str(c.year) if hasattr(c, "year") else str(c)[:4] for c in cols]

    df = pd.DataFrame({
        "Revenue (₹Cr)": (rev[cols].values / 1e7).round(2),
        "Net Income (₹Cr)": (net[cols].values / 1e7).round(2),
        "EPS (₹)": eps[cols].values.round(2) if not eps.isnull().all() else [np.nan] * len(cols),
    }, index=labels)
    return df


def extract_margins(income_stmt: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Operating Margin % and Net Profit Margin % for the last 4 years.

    Returns:
        DataFrame with index = year labels, columns = [Operating Margin%, Net Margin%]
    """
    if income_stmt.empty:
        return pd.DataFrame()

    cols = income_stmt.columns[:4]
    rev = _row(income_stmt, "Total Revenue", "Revenue")
    ebit = _row(income_stmt, "EBIT", "Operating Income", "Ebit")
    net = _row(income_stmt, "Net Income", "Net Income Common Stockholders")

    if rev is None or rev[cols].isnull().all():
        return pd.DataFrame()

    rev_vals = rev[cols].values.astype(float)
    ebit_vals = ebit[cols].values.astype(float) if ebit is not None else np.full(len(cols), np.nan)
    net_vals = net[cols].values.astype(float) if net is not None else np.full(len(cols), np.nan)

    op_margin = np.where(rev_vals != 0, ebit_vals / rev_vals * 100, np.nan)
    net_margin = np.where(rev_vals != 0, net_vals / rev_vals * 100, np.nan)

    labels = [str(c.year) if hasattr(c, "year") else str(c)[:4] for c in cols]
    return pd.DataFrame({
        "Operating Margin%": op_margin.round(2),
        "Net Margin%": net_margin.round(2),
    }, index=labels)


def extract_cashflow_summary(cashflow: pd.DataFrame) -> pd.DataFrame:
    """
    Extract Operating CF, CapEx, and Free Cash Flow for the last 4 years.

    Returns:
        DataFrame with index = year labels, columns = [Operating CF, CapEx, FCF] in ₹Cr
    """
    if cashflow.empty:
        return pd.DataFrame()

    cols = cashflow.columns[:4]
    ocf = _row(cashflow, "Operating Cash Flow", "Cash From Operations")
    capex = _row(cashflow, "Capital Expenditure", "Capital Expenditures", "Purchase Of Property Plant And Equipment")

    ocf_vals = ocf[cols].values.astype(float) if ocf is not None else np.zeros(len(cols))
    capex_vals = capex[cols].values.astype(float) if capex is not None else np.zeros(len(cols))
    # CapEx is typically negative in yfinance; FCF = OCF + CapEx
    fcf_vals = ocf_vals + capex_vals

    labels = [str(c.year) if hasattr(c, "year") else str(c)[:4] for c in cols]
    return pd.DataFrame({
        "Operating CF (₹Cr)": (ocf_vals / 1e7).round(2),
        "CapEx (₹Cr)": (capex_vals / 1e7).round(2),
        "FCF (₹Cr)": (fcf_vals / 1e7).round(2),
    }, index=labels)


def health_color(value: Optional[float], metric: str) -> str:
    """
    Return 'green', 'amber', or 'red' color label based on metric health thresholds.

    Args:
        value: the numeric value
        metric: one of 'roe', 'current_ratio', 'debt_to_equity'
    """
    if value is None or np.isnan(value):
        return "grey"

    thresholds = {
        "roe":              {"green": 15, "amber": 8},        # % — higher is better
        "current_ratio":    {"green": 1.5, "amber": 1.0},     # higher is better
        "debt_to_equity":   {"green": 50, "amber": 100},      # lower is better (D/E in %)
    }

    t = thresholds.get(metric)
    if not t:
        return "grey"

    if metric == "debt_to_equity":
        return "green" if value <= t["green"] else ("amber" if value <= t["amber"] else "red")
    else:
        return "green" if value >= t["green"] else ("amber" if value >= t["amber"] else "red")
