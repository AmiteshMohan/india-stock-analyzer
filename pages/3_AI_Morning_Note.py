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
from core.fetcher import get_stock_info
from core.ai_analyst import generate_morning_note, answer_question
from reports.pdf_builder import build_pdf

st.set_page_config(page_title="AI Morning Note | India Stock Analyzer", layout="wide")

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

ticker = st.session_state.get("ticker", "RELIANCE.NS")
st.title(f"AI Morning Note — {ticker}")
st.caption(f"Powered by Claude claude-sonnet-4-6 | {date.today():%d %B %Y}")

# API key check
if not os.environ.get("ANTHROPIC_API_KEY"):
    st.error(
        "**ANTHROPIC_API_KEY not set.** "
        "Add your key to a `.env` file in the project root and restart the app."
    )
    st.stop()

# Load stock data
with st.spinner("Fetching live data…"):
    info = get_stock_info(ticker)

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

col_left, col_right = st.columns([2, 1])

with col_left:
    generate_btn = st.button("✨ Generate Morning Note", type="primary", use_container_width=True)

with col_right:
    style_hint = st.selectbox(
        "Note style",
        ["Institutional (default)", "Short briefing", "Detailed deep-dive"],
        label_visibility="collapsed",
    )

if generate_btn or "morning_note_text" in st.session_state:
    note_container = st.empty()

    if generate_btn:
        # Stream fresh note
        full_note = ""
        with note_container.container():
            with st.spinner("Claude is writing your note…"):
                note_box = st.empty()
                for chunk in generate_morning_note(info):
                    full_note += chunk
                    note_box.markdown(full_note + "▌")
                note_box.markdown(full_note)

        st.session_state["morning_note_text"] = full_note

    else:
        # Show previously generated note
        full_note = st.session_state["morning_note_text"]
        with note_container.container():
            st.markdown(full_note)

    # ---- PDF download ----
    st.divider()
    try:
        pdf_bytes = build_pdf(st.session_state["morning_note_text"], info)
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
    st.info("Click **Generate Morning Note** to create an AI-powered research note for this stock.")

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
