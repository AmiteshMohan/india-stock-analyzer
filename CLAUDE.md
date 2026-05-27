# India Stock Analyzer — Claude Code Context

This file gives Claude Code full context about the project so future sessions can pick up immediately.

## What this project does

A Streamlit web app that:
1. Fetches live NSE/BSE stock data via yfinance
2. Displays price charts, fundamentals, and financial ratios
3. Generates AI-powered morning research notes using the Claude API (claude-sonnet-4-6)
4. Runs an interactive DCF valuation model with sliders
5. Shows a sector screener for 15 NSE blue-chip stocks
6. Exports branded PDF research reports via ReportLab

Target user: a CEO or portfolio manager who opens a URL, types a ticker, and gets institutional-quality research instantly.

## File structure

```
app.py                      # Entry point: sidebar (ticker, refresh, theme), navigation
pages/
  1_Overview.py             # Metric cards, 1-year Plotly chart vs Nifty, volume bars, stats table
  2_Fundamentals.py         # Income stmt, margin trend, balance sheet health, cash flow
  3_AI_Morning_Note.py      # Claude streaming morning note + Q&A chat + PDF download
  4_Valuation.py            # DCF with sliders, waterfall chart, sensitivity matrix
  5_Sector_Screener.py      # Sortable screener table with sector filter
core/
  fetcher.py                # All yfinance calls; all functions @st.cache_data(ttl=300)
  ratios.py                 # Pure-function ratio extraction from yfinance DataFrames
  dcf.py                    # run_dcf() + sensitivity_table() — no Streamlit imports
  ai_analyst.py             # generate_morning_note() and answer_question() — streaming generators
reports/
  pdf_builder.py            # build_pdf(note_text, stock_data) → bytes using ReportLab
```

## Key design decisions

- **5-minute cache**: All `fetcher.py` functions use `@st.cache_data(ttl=300)`. The "Refresh Data" button calls `st.cache_data.clear()` to force an immediate update.
- **Session state for ticker**: Active ticker lives in `st.session_state["ticker"]`. All pages read from it; the sidebar writes to it.
- **Streaming AI**: `generate_morning_note()` and `answer_question()` are generators that yield string chunks. Pages use them with a `for chunk in ...` loop to update a `st.empty()` box in real-time.
- **No Streamlit in core/dcf.py**: DCF logic is pure Python so it can be unit-tested or imported outside Streamlit.
- **Graceful degradation**: Every external API call is wrapped in try/except. If data is missing, a meaningful "N/A" or warning is shown — the app never crashes on bad data.
- **API key**: Always loaded from `os.environ.get("ANTHROPIC_API_KEY")`. Never hardcoded.

## Common tasks

### Add a new page
1. Create `pages/N_PageName.py`
2. Add `sys.path.insert(0, ...)` at top so `core/` imports work
3. Call `st.set_page_config(...)` as first Streamlit call
4. Read ticker from `st.session_state.get("ticker", "RELIANCE.NS")`
5. Streamlit auto-discovers pages in the `pages/` folder alphabetically by filename prefix

### Add a new stock to the screener
In `core/fetcher.py`, add the `.NS` ticker to the `tickers` list inside `get_nifty50_data()`.

### Change the Claude model
In `core/ai_analyst.py`, update the `MODEL = "claude-sonnet-4-6"` constant at the top of the file.

### Modify the morning note prompt
Edit `_build_morning_note_prompt()` in `core/ai_analyst.py`. The function returns a plain string that is sent as the user message to Claude.

### Modify the PDF layout
Edit `reports/pdf_builder.py`. The `build_pdf()` function builds a ReportLab `BaseDocTemplate` story. The `_header_footer()` callback draws the branded header/footer on every page.

### Change the DCF defaults
Edit the default slider values in `pages/4_Valuation.py` (`st.slider(..., value=DEFAULT)`). The model logic lives in `core/dcf.py`.

### Deploy to Streamlit Cloud
1. Push to GitHub (no `.env` file — add key in Streamlit Cloud Secrets)
2. In Streamlit Cloud: connect repo, set main file to `app.py`
3. Add secret: `ANTHROPIC_API_KEY = "sk-ant-..."`

## Dependencies
See `requirements.txt`. Key pinned versions:
- streamlit==1.35.0
- yfinance==0.2.40
- anthropic==0.28.0
- plotly==5.22.0
- reportlab==4.2.2

## Environment variables
| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes (for AI pages) | Claude API authentication |
