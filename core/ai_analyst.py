"""
Claude API integration for AI-generated morning notes and Q&A.
Reads ANTHROPIC_API_KEY from environment — never hardcoded.
"""
from __future__ import annotations

import os
from typing import Generator, Optional
import anthropic


MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_morning_note_prompt(stock_data: dict) -> str:
    """Build the structured prompt for morning note generation."""
    name = stock_data.get("longName", stock_data.get("ticker", "Unknown"))
    ticker = stock_data.get("ticker", "")
    price = stock_data.get("currentPrice", "N/A")
    chg = stock_data.get("changePercent", 0)
    pe = stock_data.get("trailingPE", "N/A")
    fpe = stock_data.get("forwardPE", "N/A")
    eps = stock_data.get("trailingEps", "N/A")
    pb = stock_data.get("priceToBook", "N/A")
    div = stock_data.get("dividendYield", "N/A")
    roe = stock_data.get("returnOnEquity", "N/A")
    mcap = stock_data.get("marketCap", 0)
    mcap_cr = round(mcap / 1e7, 0) if mcap else "N/A"
    sector = stock_data.get("sector", "N/A")
    rev_growth = stock_data.get("revenueGrowth", "N/A")
    earn_growth = stock_data.get("earningsGrowth", "N/A")
    op_margin = stock_data.get("operatingMargins", "N/A")
    net_margin = stock_data.get("profitMargins", "N/A")
    beta = stock_data.get("beta", "N/A")
    wk52_hi = stock_data.get("fiftyTwoWeekHigh", "N/A")
    wk52_lo = stock_data.get("fiftyTwoWeekLow", "N/A")
    dte = stock_data.get("debtToEquity", "N/A")
    cr = stock_data.get("currentRatio", "N/A")

    def fmt_pct(v):
        try:
            return f"{float(v)*100:.1f}%"
        except Exception:
            return str(v)

    return f"""You are a senior equity research analyst at a top Indian brokerage.
Write a professional morning research note for the stock below.
The note will be read by portfolio managers and institutional investors.

STOCK DATA (as of today):
- Company: {name} ({ticker})
- Sector: {sector}
- Current Price: ₹{price} ({chg:+.2f}% today)
- Market Cap: ₹{mcap_cr} Cr
- 52-Week Range: ₹{wk52_lo} – ₹{wk52_hi}
- Trailing P/E: {pe} | Forward P/E: {fpe}
- Price-to-Book: {pb}
- EPS (TTM): ₹{eps}
- Dividend Yield: {fmt_pct(div)}
- Beta: {beta}
- Revenue Growth (YoY): {fmt_pct(rev_growth)}
- Earnings Growth (YoY): {fmt_pct(earn_growth)}
- Operating Margin: {fmt_pct(op_margin)}
- Net Profit Margin: {fmt_pct(net_margin)}
- Return on Equity: {fmt_pct(roe)}
- Debt-to-Equity: {dte}
- Current Ratio: {cr}

Write a structured morning note with EXACTLY these sections (use markdown headers):

## Top Call
[BUY / HOLD / SELL] — One punchy sentence with the core thesis and target price range.

## Overnight Developments
2–3 bullet points on likely market-moving news, sector trends, or macro factors relevant to this stock today. If not available, infer from sector and recent price action.

## Key Metrics at a Glance
A concise table or bullet list covering: valuation (P/E vs. sector peers), growth trajectory, margin quality, and balance sheet strength.

## Trade Idea
Entry zone, stop-loss level, and target price. Include a brief rationale (technical or fundamental trigger).

## Risks
2–3 key risks that could invalidate the thesis — be specific (not generic).

## Analyst Note
One short paragraph of context that a CEO would find useful before a board meeting.

Keep the tone authoritative, data-driven, and concise. Avoid waffle. Total length: ~400–500 words."""


def _build_qa_prompt(question: str, stock_data: dict) -> str:
    """Build the Q&A prompt given a follow-up question and context."""
    name = stock_data.get("longName", stock_data.get("ticker", "the stock"))
    sector = stock_data.get("sector", "unknown sector")
    price = stock_data.get("currentPrice", "N/A")
    pe = stock_data.get("trailingPE", "N/A")

    return f"""You are a senior equity research analyst.
Context: {name} ({sector}), current price ₹{price}, P/E {pe}.
The user has been reviewing this stock and has a follow-up question.

Question: {question}

Answer concisely and professionally, using the data context above.
If you don't have enough data, say so and explain what information would help.
Keep your response under 200 words unless depth is required."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_morning_note(stock_data: dict) -> Generator[str, None, None]:
    """
    Stream a professional morning note from Claude for the given stock.

    Args:
        stock_data: dict returned by core/fetcher.get_stock_info()

    Yields:
        str chunks as they arrive from the Claude streaming API.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        yield "**Error:** ANTHROPIC_API_KEY is not set. Please add it to your .env file."
        return

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_morning_note_prompt(stock_data)

    try:
        with client.messages.stream(
            model=MODEL,
            max_tokens=1024,
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

    Args:
        question: User's question string.
        stock_data: dict returned by core/fetcher.get_stock_info()
        conversation_history: Optional list of prior {"role", "content"} dicts.

    Yields:
        str chunks from Claude streaming API.
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
            max_tokens=512,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as exc:
        yield f"**Error:** {exc}"
