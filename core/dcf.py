"""
DCF valuation model logic.
Takes user-supplied assumptions and live financials, returns projected cash flows
and implied intrinsic value per share.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional


def run_dcf(
    base_revenue: float,
    shares_outstanding: float,
    net_debt: float,
    revenue_growth: float = 0.10,
    ebit_margin: float = 0.25,
    tax_rate: float = 0.25,
    capex_pct_revenue: float = 0.05,
    nwc_change_pct: float = 0.02,
    wacc: float = 0.11,
    terminal_growth: float = 0.04,
    projection_years: int = 10,
) -> dict:
    """
    Compute a 2-stage DCF valuation.

    Args:
        base_revenue:      Latest annual revenue in ₹ (absolute).
        shares_outstanding: Total shares outstanding.
        net_debt:          Net debt = Total Debt − Cash (can be negative).
        revenue_growth:    Annual revenue CAGR during projection period (decimal).
        ebit_margin:       EBIT as fraction of revenue (decimal).
        tax_rate:          Effective tax rate (decimal).
        capex_pct_revenue: CapEx as fraction of revenue (decimal).
        nwc_change_pct:    Change in net working capital as fraction of revenue (decimal).
        wacc:              Weighted average cost of capital (decimal).
        terminal_growth:   Gordon Growth Model terminal rate (decimal).
        projection_years:  Number of explicit forecast years.

    Returns:
        dict with keys:
          projections  — DataFrame with Year, Revenue, EBIT, NOPAT, FCF, PV_FCF
          terminal_value  — float
          pv_terminal     — float
          enterprise_value — float
          equity_value    — float
          intrinsic_price — float (per share)
    """
    revenues, ebit_vals, nopat_vals, fcf_vals, pv_fcfs = [], [], [], [], []

    for yr in range(1, projection_years + 1):
        rev = base_revenue * (1 + revenue_growth) ** yr
        ebit = rev * ebit_margin
        nopat = ebit * (1 - tax_rate)
        capex = rev * capex_pct_revenue
        nwc = rev * nwc_change_pct
        fcf = nopat - capex - nwc
        pv = fcf / (1 + wacc) ** yr

        revenues.append(rev)
        ebit_vals.append(ebit)
        nopat_vals.append(nopat)
        fcf_vals.append(fcf)
        pv_fcfs.append(pv)

    projections = pd.DataFrame({
        "Year": list(range(1, projection_years + 1)),
        "Revenue (₹Cr)": [r / 1e7 for r in revenues],
        "EBIT (₹Cr)": [e / 1e7 for e in ebit_vals],
        "NOPAT (₹Cr)": [n / 1e7 for n in nopat_vals],
        "FCF (₹Cr)": [f / 1e7 for f in fcf_vals],
        "PV of FCF (₹Cr)": [p / 1e7 for p in pv_fcfs],
    })

    terminal_fcf = fcf_vals[-1] * (1 + terminal_growth)
    terminal_value = terminal_fcf / (wacc - terminal_growth) if wacc > terminal_growth else 0.0
    pv_terminal = terminal_value / (1 + wacc) ** projection_years

    sum_pv_fcf = sum(pv_fcfs)
    enterprise_value = sum_pv_fcf + pv_terminal
    equity_value = enterprise_value - net_debt
    intrinsic_price = equity_value / shares_outstanding if shares_outstanding > 0 else 0.0

    return {
        "projections": projections,
        "terminal_value": terminal_value / 1e7,    # ₹Cr
        "pv_terminal": pv_terminal / 1e7,
        "sum_pv_fcf": sum_pv_fcf / 1e7,
        "enterprise_value": enterprise_value / 1e7,
        "equity_value": equity_value / 1e7,
        "intrinsic_price": intrinsic_price,
    }


def sensitivity_table(
    base_revenue: float,
    shares_outstanding: float,
    net_debt: float,
    wacc_range: list[float],
    tg_range: list[float],
    **kwargs,
) -> pd.DataFrame:
    """
    Build a sensitivity matrix of implied price per share vs. WACC and terminal growth.

    Args:
        base_revenue: Latest annual revenue in ₹.
        shares_outstanding: Total shares outstanding.
        net_debt: Net debt in ₹.
        wacc_range: List of WACC values (decimal).
        tg_range: List of terminal growth values (decimal).
        **kwargs: Passed through to run_dcf (ebit_margin, tax_rate, etc.)

    Returns:
        DataFrame where rows = WACC, columns = terminal growth rate, values = ₹/share.
    """
    rows = {}
    for w in wacc_range:
        row = {}
        for tg in tg_range:
            if w <= tg:
                row[f"{tg:.0%}"] = float("nan")
                continue
            result = run_dcf(
                base_revenue=base_revenue,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                wacc=w,
                terminal_growth=tg,
                **kwargs,
            )
            row[f"{tg:.0%}"] = round(result["intrinsic_price"], 2)
        rows[f"{w:.0%}"] = row

    df = pd.DataFrame(rows).T
    df.index.name = "WACC \\ Term. Growth"
    return df
