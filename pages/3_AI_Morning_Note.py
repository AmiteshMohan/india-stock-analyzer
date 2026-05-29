"""
AI Morning Note page — streams a Claude-generated professional research note
and supports follow-up Q&A.
"""
from __future__ import annotations

import sys
import os
from datetime import date

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.fetcher import get_stock_info, get_financials
from core.ai_analyst import generate_morning_note, answer_question
from reports.pdf_builder import build_pdf

st.set_page_config(page_title="AI Morning Note | India Stock Analyzer", layout="wide")

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

ticker = st.session_state.get("ticker", "RELIANCE.NS")
st.title(f"AI Morning Note — {ticker}")
st.caption(f"Powered by Claude Sonnet 4.6 | {date.today():%d %B %Y}")

# API key check
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY not set.** "
        "Add your key to a `.env` file in the project root and restart the app."
    )
    st.stop()

# Load stock data + financial statements
with st.spinner("Fetching live data and financial statements…"):
    info = get_stock_info(ticker)
    fins = get_financials(ticker)

if info.get("error"):
    st.error(info["error"])
    st.stop()

# Display quick context strip
c1, c2, c3, c4 = st.columns(4)
c1.metric("Price", f"₹{info['currentPrice']:,.2f}" if info["currentPrice"] else "N/A")
c2.metric("1D Change", f"{info['changePercent']:+.2f}%" if info.get("changePercent") is not None else "N/A")
c3.metric("P/E", f"{info['trailingPE']:.1f}" if info["trailingPE"] else "N/A")
c4.metric("Sector", info["sector"] or "N/A")

st.divider()

# ---------------------------------------------------------------------------
# Morning note generation
# ---------------------------------------------------------------------------

col_a, col_b = st.columns([1, 2])
with col_a:
    note_type = st.radio(
        "Note type",
        ["Quick Snapshot", "Detailed Research Note"],
        index=1,
        help="Quick: ~10 sec, ~$0.02 — key stats + 3-bullet thesis.\n\nDetailed: ~30-60 sec, ~$0.10 — full institutional note with web search.",
    )

is_short = note_type == "Quick Snapshot"

with col_b:
    if is_short:
        st.info(
            "**Quick Snapshot** — price, key ratios, 3-bullet investment case, and what to watch. "
            "No web search. ~10 seconds.",
            icon="⚡",
        )
    else:
        st.info(
            "**Detailed Research Note** — full institutional note with income trend, balance sheet, "
            "cash flow projections, valuation scenarios, peer comparison, risk matrix, and recommendation. "
            "Uses live web search for sourced data. ~30–60 seconds.",
            icon="📊",
        )

btn_label = "⚡ Generate Quick Snapshot" if is_short else "✨ Generate Detailed Research Note"
generate_btn = st.button(btn_label, type="primary", use_container_width=True)

# Use separate session-state keys so switching type doesn't show stale note
note_key = "morning_note_short" if is_short else "morning_note_text"

if generate_btn or note_key in st.session_state:
    note_container = st.empty()

    if generate_btn:
        st.session_state.pop(note_key, None)
        full_note = ""
        spinner_msg = "Claude is writing your quick snapshot (~10 seconds)…" if is_short else "Claude is writing your detailed research note (~30-60 seconds)…"
        with note_container.container():
            with st.spinner(spinner_msg):
                note_box = st.empty()
                for chunk in generate_morning_note(info, fins, short=is_short):
                    full_note += chunk
                    note_box.markdown(full_note + "▌")
                note_box.markdown(full_note)

        st.session_state[note_key] = full_note

    else:
        full_note = st.session_state[note_key]
        with note_container.container():
            st.markdown(full_note)

    # ---- PDF download ----
    st.divider()
    try:
        pdf_bytes = build_pdf(st.session_state[note_key], info)
        st.download_button(
            label="📄 Download as PDF",
            data=pdf_bytes,
            file_name=f"{ticker}_morning_note_{date.today():%Y%m%d}.pdf",
            mime="application/pdf",
            type="secondary",
        )
    except Exception as e:
        st.warning(f"PDF generation failed: {e}")

else:
    st.info("Select a note type above and click **Generate** to create an AI-powered research note for this stock.")

st.divider()

# ---------------------------------------------------------------------------
# Q&A section
# ---------------------------------------------------------------------------

st.subheader("Ask the Analyst")
st.caption("Ask any follow-up question about this stock. Claude will answer using live data context.")

if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []

# Display chat history
for msg in st.session_state["qa_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("e.g. What are the main risks in the next quarter?")

if question:
    st.session_state["qa_history"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        answer_box = st.empty()
        full_answer = ""
        for chunk in answer_question(question, info, st.session_state["qa_history"]):
            full_answer += chunk
            answer_box.markdown(full_answer + "▌")
        answer_box.markdown(full_answer)

    st.session_state["qa_history"].append({"role": "assistant", "content": full_answer})
