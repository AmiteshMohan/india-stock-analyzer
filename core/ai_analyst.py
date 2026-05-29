"""
Claude API integration for AI-generated morning notes and Q&A.
Reads ANTHROPIC_API_KEY from environment — never hardcoded.
"""
from __future__ import annotations

import os
from typing import Generator, Optional
import pandas as pd
import numpy as np
import anthropic


MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Financial data formatter
# ---------------------------------------------------------------------------

def _fmt_cr(val, divisor=1e7, decimals=1):
    """Convert raw rupee value to ₹ Crore string."""
    try:
        v = float(val)
        if np.isnan(v):
            return "N/A"
        return f"{v / divisor:,.{decimals}f}"
    except Exception:
        return "N/A"


def _row(df: pd.DataFrame, *labels: str):
    for label in labels:
        if df is not None and not df.empty and label in df.index:
            return df.loc[label]
    return None


def _extract_financials_context(income: pd.DataFrame, balance: pd.DataFrame,
                                  cashflow: pd.DataFrame, shares: float) -> str:
    """
    Convert yfinance financial DataFrames into a compact text block
    that Claude can use as ground-truth numbers for the note.
    """
    if income is None:
        income = pd.DataFrame()
    if balance is None:
        balance = pd.DataFrame()
    if cashflow is None:
        cashflow = pd.DataFrame()

    lines = []

    # ---- Income Statement ----
    if not income.empty:
        cols = income.columns[:4]
        years = [str(c.year) if hasattr(c, 'year') else str(c)[:4] for c in cols]

        def _inc_row(labels):
            r = _row(income, *labels)
            if r is None:
                return ["N/A"] * len(cols)
            return [_fmt_cr(r.iloc[i]) for i in range(len(cols))]

        rev   = _inc_row(["Total Revenue", "Revenue"])
        ebit  = _inc_row(["Operating Income", "EBIT", "Ebit"])
        net   = _inc_row(["Net Income", "Net Income Common Stockholders"])
        eps_r = _inc_row(["Basic EPS", "Diluted EPS"])

        lines.append("=== INCOME STATEMENT (₹ Crore) ===")
        lines.append(f"Year:             {' | '.join(years)}")
        lines.append(f"Revenue:          {' | '.join(rev)}")
        lines.append(f"Operating Income: {' | '.join(ebit)}")
        lines.append(f"Net Profit:       {' | '.join(net)}")
        lines.append(f"EPS (₹):          {' | '.join(eps_r)}")

    # ---- Balance Sheet ----
    if not balance.empty:
        cols = balance.columns[:2]
        years = [str(c.year) if hasattr(c, 'year') else str(c)[:4] for c in cols]

        def _bs_row(labels):
            r = _row(balance, *labels)
            if r is None:
                return ["N/A"] * len(cols)
            return [_fmt_cr(r.iloc[i]) for i in range(len(cols))]

        equity   = _bs_row(["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"])
        debt     = _bs_row(["Total Debt", "Long Term Debt"])
        cash     = _bs_row(["Cash And Cash Equivalents", "Cash"])
        assets   = _bs_row(["Total Assets"])
        curr_a   = _bs_row(["Current Assets"])
        curr_l   = _bs_row(["Current Liabilities"])

        lines.append("\n=== BALANCE SHEET (₹ Crore) ===")
        lines.append(f"Year:              {' | '.join(years)}")
        lines.append(f"Total Assets:      {' | '.join(assets)}")
        lines.append(f"Equity:            {' | '.join(equity)}")
        lines.append(f"Total Debt:        {' | '.join(debt)}")
        lines.append(f"Cash & Equiv:      {' | '.join(cash)}")
        lines.append(f"Current Assets:    {' | '.join(curr_a)}")
        lines.append(f"Current Liab:      {' | '.join(curr_l)}")

    # ---- Cash Flow ----
    if not cashflow.empty:
        cols = cashflow.columns[:3]
        years = [str(c.year) if hasattr(c, 'year') else str(c)[:4] for c in cols]

        def _cf_row(labels):
            r = _row(cashflow, *labels)
            if r is None:
                return ["N/A"] * len(cols)
            return [_fmt_cr(r.iloc[i]) for i in range(len(cols))]

        ocf   = _cf_row(["Operating Cash Flow", "Cash Flow From Operations"])
        capex = _cf_row(["Capital Expenditure", "Purchase Of Property Plant And Equipment"])
        inv   = _cf_row(["Investing Cash Flow", "Net PPE Purchase And Sale"])
        fin   = _cf_row(["Financing Cash Flow"])
        div   = _cf_row(["Common Stock Dividend Paid", "Dividends Paid"])

        lines.append("\n=== CASH FLOW (₹ Crore) ===")
        lines.append(f"Year:               {' | '.join(years)}")
        lines.append(f"Operating CF:       {' | '.join(ocf)}")
        lines.append(f"CapEx:              {' | '.join(capex)}")
        lines.append(f"Investing CF:       {' | '.join(inv)}")
        lines.append(f"Financing CF:       {' | '.join(fin)}")
        lines.append(f"Dividends Paid:     {' | '.join(div)}")

    return "\n".join(lines) if lines else "Financial statement data not available."


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_morning_note_prompt(stock_data: dict, fins: Optional[dict] = None) -> str:
    """Build the comprehensive research note prompt."""
    name    = stock_data.get("longName", stock_data.get("ticker", "Unknown"))
    ticker  = stock_data.get("ticker", "")
    price   = stock_data.get("currentPrice", "N/A")
    chg     = stock_data.get("changePercent", 0) or 0
    pe      = stock_data.get("trailingPE", "N/A")
    fpe     = stock_data.get("forwardPE", "N/A")
    eps     = stock_data.get("trailingEps", "N/A")
    pb      = stock_data.get("priceToBook", "N/A")
    div     = stock_data.get("dividendYield", "N/A")
    roe     = stock_data.get("returnOnEquity", "N/A")
    roa     = stock_data.get("returnOnAssets", "N/A")
    mcap    = stock_data.get("marketCap", 0) or 0
    mcap_cr = round(mcap / 1e7, 0) if mcap else "N/A"
    sector  = stock_data.get("sector", "N/A")
    ind     = stock_data.get("industry", "N/A")
    rev_g   = stock_data.get("revenueGrowth", "N/A")
    earn_g  = stock_data.get("earningsGrowth", "N/A")
    op_m    = stock_data.get("operatingMargins", "N/A")
    net_m   = stock_data.get("profitMargins", "N/A")
    beta    = stock_data.get("beta", "N/A")
    hi52    = stock_data.get("fiftyTwoWeekHigh", "N/A")
    lo52    = stock_data.get("fiftyTwoWeekLow", "N/A")
    dte     = stock_data.get("debtToEquity", "N/A")
    cr_r    = stock_data.get("currentRatio", "N/A")
    shares  = stock_data.get("sharesOutstanding", "N/A")
    revenue = stock_data.get("totalRevenue", "N/A")
    exch    = stock_data.get("exchange", "NSE")
    currency = stock_data.get("currency", "INR")

    def pct(v):
        try:
            return f"{float(v)*100:.2f}%"
        except Exception:
            return str(v) if v not in (None, "N/A") else "N/A"

    def fmt(v, decimals=2):
        try:
            return f"{float(v):,.{decimals}f}"
        except Exception:
            return str(v) if v not in (None, "N/A") else "N/A"

    rev_cr = _fmt_cr(revenue) if revenue not in ("N/A", None) else "N/A"
    shares_cr = f"{float(shares)/1e7:.3f} cr ({float(shares)/1e5:.1f}M)" if shares not in ("N/A", None) else "N/A"

    # Extract financial statement text
    fins_text = ""
    income = balance = cashflow = pd.DataFrame()
    if fins:
        income   = fins.get("income_stmt", pd.DataFrame())
        balance  = fins.get("balance_sheet", pd.DataFrame())
        cashflow = fins.get("cashflow", pd.DataFrame())
        shares_f = float(shares) if shares not in ("N/A", None) else 1.0
        fins_text = _extract_financials_context(income, balance, cashflow, shares_f)

    return f"""You are Amitesh, a senior equity research analyst at an Indian brokerage, writing a DETAILED RESEARCH NOTE for institutional investors and portfolio managers.

Today's date for this note: use current date context.
Analyst: Amitesh | Indian Equities Coverage

COMPANY: {name}
TICKER: {ticker} ({exch})
SECTOR: {sector} | INDUSTRY: {ind}
CURRENCY: {currency}

LIVE MARKET DATA (from yfinance):
- Current Price: ₹{price} ({chg:+.2f}% today)
- Market Cap: ₹{mcap_cr} Cr
- 52-Week High: ₹{hi52} | 52-Week Low: ₹{lo52}
- Trailing P/E: {fmt(pe)} | Forward P/E: {fmt(fpe)}
- Price-to-Book: {fmt(pb)}
- EPS (TTM): ₹{fmt(eps)}
- Dividend Yield: {pct(div)}
- Beta: {fmt(beta)}
- Revenue (TTM): ₹{rev_cr} Cr
- Revenue Growth (YoY): {pct(rev_g)}
- Earnings Growth (YoY): {pct(earn_g)}
- Operating Margin: {pct(op_m)}
- Net Profit Margin: {pct(net_m)}
- Return on Equity: {pct(roe)}
- Return on Assets: {pct(roa)}
- Debt-to-Equity: {fmt(dte)}
- Current Ratio: {fmt(cr_r)}
- Shares Outstanding: {shares_cr}

FINANCIAL STATEMENTS DATA (from NSE filings via yfinance):
{fins_text}

---

IMPORTANT RULES FOR THIS NOTE:
1. Use the FINANCIAL STATEMENTS DATA above as ground truth for all historical figures. Do NOT make up numbers that contradict the provided data.
2. For forward estimates (FY27E, FY28E), derive them from stated CAGR assumptions — clearly label as estimates.
3. Cite every key data point with its source (e.g., "Source: yfinance/NSE filings", "Source: Screener.in", "Source: StockAnalysis.com", etc.)
4. All monetary figures in ₹ Crore unless stated otherwise.
5. Use Indian fiscal year convention: FY26 = April 2025 – March 2026.
6. The most recent fiscal year in the data above is the latest completed FY.
7. Be specific and opinionated — this is read by portfolio managers at 7am, not retail investors.
8. If data is unavailable, say "N/A" or "not available" — do not hallucinate numbers.

---

Write the note using EXACTLY this structure with markdown:

---
# DETAILED RESEARCH NOTE
## {name} ({ticker})
**{exch} | Sector: {sector} | Date: [today's date]**
**Analyst: Amitesh | Rating: [BUY/HOLD/SELL] | PT Range: ₹[low]–₹[high] | CMP: ₹{price}**

> **INVESTMENT SUMMARY:** [3-4 bold sentences covering: what the company does, key financial quality metrics from the data above, current valuation context, and your core thesis/recommendation with specific numbers]

---

### 1. FUNDAMENTALS SNAPSHOT

| METRIC | VALUE | METRIC | VALUE |
|--------|-------|--------|-------|
| Stock Price | ₹{price} | Market Cap | ₹[X] Cr |
| 52-Week High | ₹{hi52} | 52-Week Low | ₹{lo52} |
| P/E Ratio (TTM) | [X]x | Forward P/E (FY27E) | ~[X]x |
| P/B Ratio | [X]x | EV/EBITDA | [X]x |
| EPS — Latest FY (reported) | ₹[X] | EPS — Prev FY (reported) | ₹[X] |
| TTM EPS | ₹{fmt(eps)} | EV/FCF | [X]x |
| Revenue Latest FY | ₹[X] Cr ([+X]% YoY) | Revenue Prev FY | ₹[X] Cr |
| Net Profit Latest FY | ₹[X] Cr | Net Profit Prev FY | ₹[X] Cr |
| Operating Margin (TTM) | {pct(op_m)} | Net Profit Margin | {pct(net_m)} |
| ROE | {pct(roe)} | 1-Year Price Return | [X]% |
| Debt-to-Equity | {fmt(dte)} | Shares Outstanding | {shares_cr} |

*Source: yfinance/NSE filings, StockAnalysis.com*

---

### 2. INCOME STATEMENT TREND (₹ CRORE)

| METRIC | FY[year-2] | FY[year-1] | FY[latest] | YoY CHANGE | TREND |
|--------|-----------|-----------|-----------|------------|-------|
[Use the financial statement data provided above. Calculate YoY % changes. Add trend color labels: Accelerating / Stable / Steady / Declining]

*Source: NSE filings via yfinance. FY[latest] = year ended March [year].*

---

### 3. BALANCE SHEET & LIQUIDITY

| BALANCE SHEET ITEM | FY[latest] | FY[prev] | ASSESSMENT |
|--------------------|-----------|---------|------------|
[Use balance sheet data provided above. Add one-line assessment for each item.]

---

### 4. CASH FLOW ANALYSIS (ACTUAL + PROJECTIONS)

| CASH FLOW ITEM | FY[prev] Actual | FY[latest] Actual | FY[+1]E | FY[+2]E | BASIS |
|----------------|----------------|------------------|---------|---------|-------|
[Use cash flow data provided. For projections, use [X]% revenue CAGR assumption and stable margins. Label projections clearly as estimates.]

*FY[+1]E/FY[+2]E projections based on [X]% revenue CAGR assumption and maintained operating margins. These are analyst estimates, not company guidance.*

---

### 5. CONSENSUS EPS ESTIMATES & VALUATION BRIDGE

[Explain that formal sell-side consensus coverage may be limited. Below are analyst-derived estimates based on actuals + stated growth assumptions.]

| METRIC | FY[year-2]E | FY[prev]A | FY[latest]A | FY[+1]E | FY[+2]E | CAGR FY[latest]-[+2]E |
|--------|------------|----------|------------|---------|---------|----------------------|
| Revenue (₹ cr) | | | | | | |
| EBITDA (₹ cr) | | | | | | |
| EBITDA Margin | | | | | | |
| Net Profit ex-exc. (₹ cr) | | | | | | |
| EPS ex-exceptional (₹) | | | | | | |
| EPS reported (₹) | | | | | | |
| P/E at CMP ₹{price} | | | | | | |
| EPS Growth YoY | | | | | | |

---

### 6. VALUATION SCENARIOS

| VALUATION SCENARIO | FY[+1]E EPS | MULTIPLE | IMPLIED PRICE | UPSIDE/(DOWNSIDE) | BASIS |
|--------------------|------------|---------|--------------|-------------------|-------|
| Bear — P/E compression | ₹[X] | [X]x | ₹[X] | [X]% | [reason] |
| Base — P/E at [X]x | ₹[X] | [X]x | ₹[X] | [X]% | [analyst PT / sector multiple] |
| Bull — P/E re-rating | ₹[X] | [X]x | ₹[X] | [X]% | [reason] |
| DCF-implied ([X]% WACC, [X]% terminal) | FCF ₹[X] cr | — | ~₹[X] | [X]% | [X]-yr DCF |

---

### 7. BUSINESS OVERVIEW & KEY PRODUCTS/SEGMENTS

[2-3 paragraphs: what the company does, key business segments/products, competitive moat, geographic mix if relevant, recent strategic developments. Be specific to this company's actual business.]

---

### 8. SHAREHOLDING PATTERN & OWNERSHIP

| CATEGORY | STAKE | CHANGE QoQ | IMPLICATION |
|----------|-------|-----------|-------------|
| Promoter / Parent | [X]% | Stable/Rising/Falling | [one-line implication] |
| Domestic Institutional (DII) | [X]% | | |
| Foreign Institutional (FII) | [X]% | | |
| Public / Retail | [X]% | | |

*Source: BSE/NSE shareholding disclosures (Screener.in / ChoiceIndia.com)*

[One paragraph on float quality and institutional ownership implications]

---

### 9. SECTOR CONTEXT

[3-4 bullet points on the sector/industry environment relevant to this stock: index performance, macro tailwinds/headwinds, regulatory environment, competitive dynamics. Be specific and current.]

---

### 10. PEER COMPARISON

| COMPANY | NIFTY WT. | CMP (₹) | P/E TTM | Revenue (₹ cr) | NET MARGIN | 1-YR RETURN |
|---------|----------|---------|--------|---------------|-----------|------------|
[List 4-5 direct peers in the same sector. Use approximate numbers sourced from public data. Bold {name} row.]

*Source: StockAnalysis.com NSE data, approximate figures*

[2-3 sentences on where {name} sits in the peer set — premium/discount, why, and whether it is justified]

---

### 11. RISK FACTORS

| RISK | SEVERITY | PROBABILITY | DETAIL |
|------|---------|------------|--------|
[List 5-7 specific risks relevant to this company and sector. Not generic platitudes — be specific to this company's actual risk profile.]

---

### 12. TRADE IDEA & FINAL RECOMMENDATION

**[STRONG BUY / BUY / HOLD / SELL / STRONG SELL] — [Entry range] | [X]-month horizon**
**Current: ₹{price} | Base PT: ₹[X] | Bull PT: ₹[X] | Implied upside: [X]–[X]%**

- **Why [rating]:** [2-3 sentences with the core quantitative thesis]
- **Why watch list (if HOLD):** [what makes this high-quality despite valuation constraint]
- **Key catalysts to upgrade:** [specific triggers — product launches, policy changes, earnings beats]
- **Key risk to monitor:** [the one thing that would change the rating]
- **Entry zone:** ₹[X]–₹[X] | **Stop-loss:** ₹[X] | **Target:** ₹[X] (base) / ₹[X] (bull)

---

### SOURCES & DATA VERIFICATION

- {name} Annual Results — NSE/BSE filings (Revenue ₹[X] cr; PAT ₹[X] cr; EPS ₹[X])
- {name} Quarterly Results — TradeBrains.in / NSE (Q[X] FY[XX] revenue ₹[X] cr)
- {name} Fundamentals — Screener.in (Market cap ₹[X] cr; P/E [X]x; P/B [X]x)
- StockAnalysis.com NSE:{ticker} (Trailing P/E [X]x; Forward P/E [X]x; EPS TTM ₹[X])
- Shareholding — Screener.in / ChoiceIndia.com (Promoter [X]%; DII [X]%; FII [X]%)
- 52-Week high/low — NSE / NirmalBang.com (High ₹[X] / Low ₹[X])
- Analyst Targets — [broker names and targets if publicly known]
- Sector data — NSE Index data, BusinessToday, SEBI disclosures

*DISCLAIMER: This report is produced for informational purposes only and does not constitute investment advice or a solicitation to buy/sell securities. Forward estimates (FY[+1]E/FY[+2]E) are analyst-derived from published growth assumptions and are not company guidance. All data sourced from publicly available information. Past performance is not indicative of future results. Verify all data with primary sources before making any investment decision. Analyst: Amitesh | Indian Equities Coverage.*

---

Now write the full note following the structure above. Fill in all [placeholders] with actual data from the financial statements provided, or clearly-labelled estimates. The note should be comprehensive, professional, opinionated, and sourced."""


def _build_qa_prompt(question: str, stock_data: dict) -> str:
    name   = stock_data.get("longName", stock_data.get("ticker", "the stock"))
    sector = stock_data.get("sector", "unknown sector")
    price  = stock_data.get("currentPrice", "N/A")
    pe     = stock_data.get("trailingPE", "N/A")
    ticker = stock_data.get("ticker", "")

    return f"""You are Amitesh, a senior equity research analyst covering Indian equities (NSE/BSE).
Context: {name} ({ticker}), {sector}, current price ₹{price}, trailing P/E {pe}.
The user has been reviewing a detailed research note on this stock and has a follow-up question.

Question: {question}

Answer professionally and with specificity. Cite data sources where relevant.
If you need more data to answer accurately, say so. Keep under 300 words unless depth is required."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_morning_note(
    stock_data: dict,
    fins: Optional[dict] = None,
) -> Generator[str, None, None]:
    """
    Stream a detailed research note from Claude for the given stock.

    Args:
        stock_data: dict returned by core/fetcher.get_stock_info()
        fins: dict returned by core/fetcher.get_financials()

    Yields:
        str chunks as they arrive from the Claude streaming API.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield "**Error:** ANTHROPIC_API_KEY is not set. Please add it to your .env file."
        return

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_morning_note_prompt(stock_data, fins)

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.AuthenticationError:
        yield "**Error:** Invalid API key. Please check your ANTHROPIC_API_KEY in .env."
    except anthropic.RateLimitError:
        yield "**Error:** Claude API rate limit hit. Please wait a moment and try again."
    except Exception as exc:
        yield f"**Error generating note:** {exc}"


def answer_question(
    question: str,
    stock_data: dict,
    conversation_history: Optional[list] = None,
) -> Generator[str, None, None]:
    """
    Stream an answer to a follow-up question about the stock.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield "**Error:** ANTHROPIC_API_KEY is not set."
        return

    client = anthropic.Anthropic(api_key=api_key)
    messages = list(conversation_history or [])
    messages.append({"role": "user", "content": _build_qa_prompt(question, stock_data)})

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as exc:
        yield f"**Error:** {exc}"
