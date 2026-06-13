# PRAGATI.AI — Intelligent Portfolio Manager

An AI-powered portfolio manager for Indian retail investors that knows when to grow, when to protect, and when to stay out.

---

## Live Demo

**Deployment:** https://pragati-ai-a5wx.onrender.com/app  
**GitHub:** https://github.com/Pragya-016/pragati-ai

---

## Overview

PRAGATI.AI addresses a critical gap in the Indian retail investment ecosystem. Over 90% of retail investors consistently underperform the market due to emotionally driven decisions, social media hype, and a lack of contextual market intelligence.

PRAGATI.AI solves this by combining multi-agent AI reasoning, custom machine learning models, and blockchain-backed audit logging to deliver ethical, explainable investment guidance — not just recommendations, but decisions on whether to act at all.

---

## Key Features

- **Multi-Agent AI System** — Four parallel agents analyse portfolio health, market regime, news sentiment, and ethical risk simultaneously via an MCP backbone
- **Random Forest Stock Predictor** — Computes RSI, MACD, and Bollinger Bands to predict 5-day price direction per holding
- **K-Means Market Regime Detector** — Classifies the current market as BULL, BEAR, SIDEWAYS, or HIGH VOLATILITY using NIFTY return, breadth, and VIX proxy signals
- **HHI Portfolio Risk Scorer** — Uses the Herfindahl-Hirschman Index to score concentration risk across stocks and sectors
- **Ethical Refusal Engine** — Can pause trading, refuse recommendations, and switch to capital-protection mode with plain-English reasoning
- **Blockchain Audit Log** — Every AI decision is recorded on Ethereum Sepolia via Solidity smart contracts for full transparency
- **Live Market Data** — Real-time NSE/BSE prices via yfinance with a scrolling stock ticker
- **ML Insights Dashboard** — Dedicated tab showing all three ML model outputs with confidence scores and feature breakdowns

---

## Tech Stack

**Core AI**
- Anthropic Claude API (multi-agent reasoning)
- MCP Server (shared context backbone)
- Groq LLM (free-tier AI synthesis)
- FastAPI + Uvicorn (backend)

**Machine Learning**
- Random Forest Classifier (scikit-learn)
- K-Means Clustering (scikit-learn)
- HHI Concentration Index (NumPy)
- Technical indicators: RSI, MACD, Bollinger Bands

**Blockchain**
- Ethereum Sepolia testnet
- Solidity smart contracts
- IPFS via Pinata
- MetaMask Web3 wallet integration

**Frontend**
- Vanilla JavaScript + HTML
- Chart.js for portfolio visualisation
- Lucide icons
- Responsive dark UI

---

## Project Structure

```
pragati4/
├── backend/
│   ├── server.py          # FastAPI backend + all API endpoints
│   ├── ml_models.py       # Random Forest, K-Means, HHI models
│   ├── requirements.txt   # Python dependencies
│   ├── .env.example       # Environment variable template
│   └── blockchain_log.json
├── frontend/
│   └── index.html         # Full frontend (single file)
├── contracts/
│   └── DecisionLogger.sol # Solidity smart contract
├── .gitignore
└── README.md
```

---

## Setup Instructions

### Prerequisites
- Python 3.10 or above
- pip
- A modern browser (Chrome recommended)

### 1. Clone the repository

```
git clone https://github.com/Pragya-016/pragati-ai.git
cd pragati-ai/pragati4
```

### 2. Install dependencies

```
pip install -r backend/requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your keys:

```
copy backend\.env.example backend\.env
```

Open `backend/.env` and add:

```
GROQ_API_KEY=your_groq_api_key_here
ETHEREUM_RPC_URL=https://sepolia.infura.io/v3/your_infura_project_id
ETHEREUM_PRIVATE_KEY=your_64_char_private_key_no_0x
PINATA_API_KEY=your_pinata_api_key_here
PINATA_SECRET_KEY=your_pinata_secret_key_here
```

Free API keys:
- Groq: https://console.groq.com
- Infura: https://infura.io
- Pinata: https://pinata.cloud

### 4. Run the backend

```
python -m uvicorn backend.server:app --reload --port 8000
```

### 5. Open the frontend

```
start frontend\index.html
```

The application will be available at `http://localhost:8000/app`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Server health check |
| GET | /api/portfolio | Portfolio holdings with live prices |
| GET | /api/indices | Live NIFTY, SENSEX, BANK NIFTY data |
| POST | /api/analyze | Run full 4-agent AI analysis |
| GET | /api/ml/insights | All three ML model outputs |
| GET | /api/ml/regime | K-Means market regime detection |
| GET | /api/ml/risk | HHI portfolio risk score |
| GET | /api/ml/predict/{symbol} | Random Forest prediction for a stock |
| GET | /api/recommendations | AI-generated investment recommendations |
| GET | /api/blockchain/chain | Full blockchain audit log |
| GET | /docs | Interactive API documentation |

---

## How It Works

1. **Data Ingestion** — User profile, live market data, and news signals are loaded
2. **Parallel Agent Reasoning** — Four agents run simultaneously via the MCP context server
3. **ML Signal Generation** — Random Forest, K-Means, and HHI models generate structured signals
4. **MCP Aggregation** — Conflicting signals are resolved with confidence weighting
5. **Ethical Validation** — The Ethics and Risk agent validates every decision
6. **Output Generation** — Plain-English advice with explicit warnings or refusals
7. **Blockchain Logging** — Every decision is recorded immutably on Ethereum Sepolia

---

## ML Models

### Random Forest — Stock Direction Predictor
Predicts 5-day price direction (UP / DOWN / NEUTRAL) for each portfolio holding using RSI (14-period), MACD (12/26/9 EMA), Bollinger Bands (20-day), and momentum signals.

### K-Means Clustering — Market Regime Detector
Classifies the current market regime into one of four states using NIFTY 50 return, market breadth score, and a VIX proxy indicator mapped against four hand-calibrated centroids.

### HHI Risk Scorer — Portfolio Concentration Risk
Scores portfolio concentration risk from 0 to 100 using the Herfindahl-Hirschman Index across individual stocks and sectors, penalising for drawdown exposure and insufficient diversification.

---

## Team

**Pragya Yadav**  
Lead Developer and Integration — Full-stack architecture, API design, frontend UI, ML Insights dashboard, GitHub deployment

**Shivali Upadhyay** 
ML Engineer and Analytics — Random Forest stock predictor, K-Means regime detector, HHI portfolio risk scoring engine

---

## Ethical Commitment

PRAGATI.AI is built around one principle: the investor's financial safety comes before returns. The system can and will refuse to make recommendations when market conditions are uncertain, manipulated, or unsuitable for the investor's risk profile. This is not a limitation — it is the core feature.
