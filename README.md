# India Stock Analyzer 📈

A production-ready Streamlit web app for live NSE/BSE stock research, AI-powered analysis,
and interactive DCF valuation — powered by the Claude API.

## Screenshot Placeholders

> _Screenshots will be added after first deployment_

| Overview | Fundamentals |
|----------|-------------|
| ![Overview](docs/screenshots/overview.png) | ![Fundamentals](docs/screenshots/fundamentals.png) |

| AI Morning Note | DCF Valuation |
|----------------|---------------|
| ![AI Note](docs/screenshots/morning_note.png) | ![DCF](docs/screenshots/dcf.png) |

---

## Features

- **Live Data** — Real-time NSE/BSE prices via yfinance, refreshed every 5 minutes
- **Interactive Charts** — Plotly price history with Nifty 50 overlay, volume bars, margin trends
- **AI Morning Note** — Claude-generated professional equity research note with streaming output
- **Q&A Chat** — Ask follow-up questions about any stock, answered by Claude in context
- **DCF Valuation** — Interactive sliders for WACC, growth rates, margins; sensitivity matrix
- **Sector Screener** — Live table of 15 NSE blue-chips with 1-click ticker switching
- **PDF Export** — Download a branded PDF research note with one click

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/india-stock-analyzer.git
cd india-stock-analyzer
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

`.env` contents:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Get your API key at [console.anthropic.com](https://console.anthropic.com).

### 4. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Usage

1. Enter any NSE ticker in the sidebar (e.g. `RELIANCE.NS`, `TCS.NS`, `HDFCBANK.NS`)
2. Navigate pages using the sidebar menu
3. Click **Refresh Data** to force a live update
4. On the AI Morning Note page, click **Generate Morning Note** for a Claude-powered analysis
5. Use the DCF sliders to model different scenarios

### Supported ticker formats

| Exchange | Suffix | Example |
|----------|--------|---------|
| NSE | `.NS` | `RELIANCE.NS` |
| BSE | `.BO` | `RELIANCE.BO` |

---

## Deployment to Streamlit Community Cloud

1. Push your repo to GitHub (do **not** include `.env`)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Set `ANTHROPIC_API_KEY` in the **Secrets** section:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
4. Deploy — Streamlit Cloud will install `requirements.txt` automatically

---

## Project Structure

```
india-stock-analyzer/
├── app.py                     # Main entry point + sidebar
├── pages/
│   ├── 1_Overview.py          # Live price, charts, key stats
│   ├── 2_Fundamentals.py      # Financial statements & ratios
│   ├── 3_AI_Morning_Note.py   # Claude API morning note + Q&A
│   ├── 4_Valuation.py         # Interactive DCF model
│   └── 5_Sector_Screener.py   # NSE stock screener table
├── core/
│   ├── fetcher.py             # yfinance data fetching (cached 5 min)
│   ├── ratios.py              # Financial ratio calculations
│   ├── dcf.py                 # DCF model logic
│   └── ai_analyst.py          # Claude API integration
├── reports/
│   └── pdf_builder.py         # ReportLab PDF generation
├── .env.example               # Environment variable template
└── requirements.txt
```

---

## Built with

| Tool | Purpose |
|------|---------|
| [Streamlit](https://streamlit.io) | Web UI framework |
| [Claude API (claude-sonnet-4-6)](https://www.anthropic.com) | AI analysis & morning notes |
| [yfinance](https://github.com/ranaroussi/yfinance) | Live NSE/BSE stock data |
| [Plotly](https://plotly.com/python/) | Interactive charts |
| [ReportLab](https://www.reportlab.com) | PDF generation |
| [pandas / numpy](https://pandas.pydata.org) | Data processing |

---

## License

MIT License. See [LICENSE](LICENSE) for details.

> **Disclaimer:** This tool is for informational and educational purposes only. 
> It does not constitute investment advice. Always consult a SEBI-registered investment advisor.
