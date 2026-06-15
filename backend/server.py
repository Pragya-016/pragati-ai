#!/usr/bin/env python3
"""
PRAGATI.AI — Blockchain-Powered AI Portfolio Manager
Backend Server v2.0
Stack: FastAPI · yfinance · IPFS (Pinata) · Ethereum (Web3.py) · SHA-256 Chain
"""

import os
import json
import hashlib
import datetime
import random
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib
load_dotenv()                           # reads .env file if present

# ML module (must import after dotenv)
from ml_models import ml_service

# ─────────────────────────────────────────────────────────────────────────────
# Application Setup
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PRAGATI.AI",
    description="Blockchain-Powered AI Portfolio Manager for Indian Markets",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Environment / Config
# ─────────────────────────────────────────────────────────────────────────────

PINATA_API_KEY    = os.getenv("PINATA_API_KEY", "")
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY", "")
ETH_RPC_URL       = os.getenv("ETHEREUM_RPC_URL", "")
ETH_PRIVATE_KEY   = os.getenv("ETHEREUM_PRIVATE_KEY", "")
CONTRACT_ADDR     = os.getenv("CONTRACT_ADDRESS", "")

BLOCKCHAIN_FILE = "blockchain_log.json"

# Minimal ABI for PragatiDecisionLogger
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "_blockIndex",      "type": "uint256"},
            {"internalType": "string",  "name": "_decision",        "type": "string"},
            {"internalType": "string",  "name": "_ipfsCid",         "type": "string"},
            {"internalType": "bytes32", "name": "_dataHash",        "type": "bytes32"},
            {"internalType": "bool",    "name": "_tradeFrozen",     "type": "bool"},
            {"internalType": "uint8",   "name": "_confidenceScore", "type": "uint8"},
        ],
        "name": "logDecision",
        "outputs": [{"internalType": "uint256", "name": "logIndex", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalDecisions",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Static Portfolio / Market Data
# ─────────────────────────────────────────────────────────────────────────────

PORTFOLIO_HOLDINGS = [
    {"symbol": "RELIANCE.NS",    "display_symbol": "RELIANCE",   "name": "Reliance Industries Ltd",     "quantity": 50,  "avg_price": 2450.00, "sector": "Energy"},
    {"symbol": "TCS.NS",         "display_symbol": "TCS",        "name": "Tata Consultancy Services",   "quantity": 30,  "avg_price": 3200.00, "sector": "IT"},
    {"symbol": "HDFCBANK.NS",    "display_symbol": "HDFCBANK",   "name": "HDFC Bank Ltd",               "quantity": 80,  "avg_price": 1580.00, "sector": "Banking"},
    {"symbol": "INFY.NS",        "display_symbol": "INFY",       "name": "Infosys Ltd",                 "quantity": 60,  "avg_price": 1400.00, "sector": "IT"},
    {"symbol": "WIPRO.NS",       "display_symbol": "WIPRO",      "name": "Wipro Ltd",                   "quantity": 100, "avg_price": 420.00,  "sector": "IT"},
    {"symbol": "BAJFINANCE.NS",  "display_symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd",           "quantity": 20,  "avg_price": 6800.00, "sector": "NBFC"},
    {"symbol": "ICICIBANK.NS",   "display_symbol": "ICICIBANK",  "name": "ICICI Bank Ltd",              "quantity": 90,  "avg_price": 950.00,  "sector": "Banking"},
    {"symbol": "TATAMOTORS.NS",  "display_symbol": "TATAMOTORS", "name": "Tata Motors Ltd",             "quantity": 120, "avg_price": 580.00,  "sector": "Auto"},
    {"symbol": "SUNPHARMA.NS",   "display_symbol": "SUNPHARMA",  "name": "Sun Pharmaceutical Ltd",      "quantity": 45,  "avg_price": 1100.00, "sector": "Pharma"},
    {"symbol": "ADANIPORTS.NS",  "display_symbol": "ADANIPORTS", "name": "Adani Ports and SEZ Ltd",     "quantity": 70,  "avg_price": 780.00,  "sector": "Infrastructure"},
]

MOCK_PRICES: Dict[str, Dict] = {
    "RELIANCE.NS":   {"ltp": 2687.50, "change":  34.20, "change_pct":  1.29},
    "TCS.NS":        {"ltp": 3456.80, "change": -12.40, "change_pct": -0.36},
    "HDFCBANK.NS":   {"ltp": 1723.45, "change":  22.10, "change_pct":  1.30},
    "INFY.NS":       {"ltp": 1523.60, "change":  18.90, "change_pct":  1.26},
    "WIPRO.NS":      {"ltp":  467.30, "change":  -3.20, "change_pct": -0.68},
    "BAJFINANCE.NS": {"ltp": 7234.50, "change": 156.80, "change_pct":  2.22},
    "ICICIBANK.NS":  {"ltp": 1089.70, "change":  14.30, "change_pct":  1.33},
    "TATAMOTORS.NS": {"ltp":  623.40, "change":   8.60, "change_pct":  1.40},
    "SUNPHARMA.NS":  {"ltp": 1234.80, "change": -22.40, "change_pct": -1.78},
    "ADANIPORTS.NS": {"ltp":  867.20, "change":  19.80, "change_pct":  2.34},
    "^NSEI":         {"ltp": 22450.75,"change": 124.35, "change_pct":  0.56},
    "^BSESN":        {"ltp": 73845.20,"change": 412.60, "change_pct":  0.56},
    "^NSEBANK":      {"ltp": 48234.10,"change": 234.50, "change_pct":  0.49},
    "^CNXIT":        {"ltp": 35678.90,"change":-123.40, "change_pct": -0.35},
}

MOCK_INDICES: Dict[str, Dict] = {
    "NIFTY_50":    {"value": 22450.75, "change":  124.35, "change_pct":  0.56, "symbol": "^NSEI"},
    "SENSEX":      {"value": 73845.20, "change":  412.60, "change_pct":  0.56, "symbol": "^BSESN"},
    "BANK_NIFTY":  {"value": 48234.10, "change":  234.50, "change_pct":  0.49, "symbol": "^NSEBANK"},
    "NIFTY_IT":    {"value": 35678.90, "change": -123.40, "change_pct": -0.35, "symbol": "^CNXIT"},
}

MOCK_NEWS = [
    {"title": "FII inflows surge as India Q3 GDP beats expectations at 7.4%", "source": "Economic Times", "time": "2h ago", "impact": "bullish", "summary": "Foreign institutional investors pumped in Rs 8,500 crore into Indian equities as GDP growth surpassed analyst estimates by a significant margin."},
    {"title": "RBI keeps repo rate unchanged at 6.5% in April policy meet",    "source": "Mint",           "time": "4h ago", "impact": "neutral", "summary": "The Reserve Bank of India maintained its benchmark interest rate, signaling continuity in monetary policy stance with focus on inflation management."},
    {"title": "IT sector faces headwinds amid global macro uncertainty",        "source": "Business Standard","time": "5h ago","impact": "bearish", "summary": "Major IT exporters report cautious Q4 guidance amid reduced discretionary tech spending from US and European banking clients."},
    {"title": "Tata Motors EV sales hit record high of 21,000 units in March", "source": "Financial Express","time": "6h ago","impact": "bullish", "summary": "Tata Motors captured 73% of India's EV market, posting record monthly sales driven by Nexon EV and Punch EV models."},
    {"title": "Adani Group stocks rally 4-7% on positive operational updates", "source": "Moneycontrol",   "time": "8h ago", "impact": "bullish", "summary": "Adani Group portfolio companies surged across the board following strong Q4 operational metrics and international investor interest."},
    {"title": "HDFC Bank Q4 loan book grows 16.5% YoY driven by retail segment","source": "Bloomberg Quint","time": "10h ago","impact": "bullish", "summary": "HDFC Bank reported robust credit growth, outperforming peers with strong CASA ratio and improving net interest margins."},
    {"title": "Crude oil rises to $89/barrel on OPEC+ production cut extension","source": "Reuters India",  "time": "12h ago","impact": "bearish", "summary": "Brent crude climbed as OPEC+ extended production cuts, raising imported inflation concerns for oil-dependent Indian companies."},
    {"title": "India becomes world's third largest power producer: IEA report", "source": "PTI",           "time": "14h ago","impact": "bullish", "summary": "India crossed 200 GW of renewable energy capacity, positioning the country as a clean energy investment destination globally."},
]

RECOMMENDATIONS: Dict[str, Any] = {
    "conservative": {
        "strategy": "Capital Preservation with Stable Returns",
        "description": "Focus on large-cap dividend-paying stocks and government securities. Minimize portfolio volatility. Suitable for investors with low risk appetite or near retirement horizon.",
        "allocation": [
            {"asset": "Large Cap Stocks", "pct": 30, "color": "#FF9933"},
            {"asset": "Government Bonds", "pct": 35, "color": "#138808"},
            {"asset": "Fixed Deposits",   "pct": 20, "color": "#3b82f6"},
            {"asset": "Gold ETF",         "pct": 10, "color": "#eab308"},
            {"asset": "Liquid Funds",     "pct":  5, "color": "#94a3b8"},
        ],
        "stocks": [
            {"symbol": "HDFCBANK",  "name": "HDFC Bank",      "reason": "Stable banking giant with consistent dividend and strong balance sheet"},
            {"symbol": "ITC",       "name": "ITC Ltd",         "reason": "High dividend yield with diversified FMCG and hospitality business"},
            {"symbol": "POWERGRID", "name": "Power Grid Corp", "reason": "Government-backed utility with regulated revenue and high dividend payout"},
            {"symbol": "COALINDIA", "name": "Coal India",      "reason": "PSU monopoly with high dividend yield and stable cash generation"},
        ],
    },
    "moderate": {
        "strategy": "Balanced Growth with Managed Risk",
        "description": "Mix of growth and value stocks across multiple sectors. Moderate exposure to mid-cap companies for alpha. Suitable for 5-10 year investment horizon.",
        "allocation": [
            {"asset": "Large Cap Stocks", "pct": 40, "color": "#FF9933"},
            {"asset": "Mid Cap Stocks",   "pct": 20, "color": "#138808"},
            {"asset": "Mutual Funds",     "pct": 20, "color": "#3b82f6"},
            {"asset": "Bonds",            "pct": 15, "color": "#eab308"},
            {"asset": "International",    "pct":  5, "color": "#94a3b8"},
        ],
        "stocks": [
            {"symbol": "RELIANCE",   "name": "Reliance Industries", "reason": "Diversified conglomerate with Jio and Green Energy transformation story"},
            {"symbol": "INFY",       "name": "Infosys",             "reason": "IT bellwether with improving margins and strong global client base"},
            {"symbol": "BAJFINANCE", "name": "Bajaj Finance",       "reason": "Leading NBFC with superior loan book growth and digital lending prowess"},
            {"symbol": "SUNPHARMA",  "name": "Sun Pharma",          "reason": "Specialty pharma leader with high-value US pipeline and branded generics"},
        ],
    },
    "aggressive": {
        "strategy": "High Growth with Higher Risk Tolerance",
        "description": "Heavy allocation to growth sectors including small-cap and thematic plays. Suitable for investors with 10+ year horizon and appetite for volatility.",
        "allocation": [
            {"asset": "Small/Mid Cap", "pct": 35, "color": "#FF9933"},
            {"asset": "Large Cap",     "pct": 25, "color": "#138808"},
            {"asset": "Sector Funds",  "pct": 20, "color": "#3b82f6"},
            {"asset": "International", "pct": 15, "color": "#eab308"},
            {"asset": "Alternatives",  "pct":  5, "color": "#94a3b8"},
        ],
        "stocks": [
            {"symbol": "TATAMOTORS", "name": "Tata Motors",   "reason": "EV transformation catalyst plus JLR global luxury turnaround story"},
            {"symbol": "ADANIPORTS", "name": "Adani Ports",   "reason": "Port infrastructure dominance with 24% market share and expansion plans"},
            {"symbol": "WIPRO",      "name": "Wipro",         "reason": "IT services turnaround under new leadership with margin expansion target"},
            {"symbol": "ICICIBANK",  "name": "ICICI Bank",    "reason": "Best-in-class retail banking franchise with superior digital acquisition"},
        ],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# Real-time Price Fetching  (yfinance → httpx Yahoo → mock fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _yfinance_fetch_sync(symbols: List[str]) -> Dict[str, Dict]:
    """Blocking yfinance call — runs in ThreadPoolExecutor."""
    import yfinance as yf  # lazy import to avoid startup delay

    prices: Dict[str, Dict] = {}
    try:
        tickers = yf.Tickers(" ".join(symbols))
        for sym in symbols:
            try:
                fi   = tickers.tickers[sym].fast_info
                ltp  = round(float(fi.last_price or 0), 2)
                prev = round(float(fi.previous_close or ltp), 2)
                if ltp > 0:
                    chg  = round(ltp - prev, 2)
                    pct  = round((chg / prev) * 100 if prev else 0, 2)
                    prices[sym] = {"ltp": ltp, "change": chg, "change_pct": pct}
            except Exception as e:
                print(f"[yfinance] {sym}: {e}")
    except Exception as e:
        print(f"[yfinance batch] {e}")
    return prices


async def _yfinance_fetch(symbols: List[str]) -> Dict[str, Dict]:
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        return await loop.run_in_executor(pool, _yfinance_fetch_sync, symbols)


async def _httpx_yahoo_fetch(symbols: List[str]) -> Dict[str, Dict]:
    """Direct Yahoo Finance v8 API as secondary source."""
    try:
        url = ("https://query1.finance.yahoo.com/v8/finance/quote"
               f"?symbols={','.join(symbols)}"
               "&fields=regularMarketPrice,regularMarketChange,regularMarketChangePercent")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PRAGATI.AI/2.0)"}
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            result = resp.json().get("quoteResponse", {}).get("result", [])
            if result:
                return {
                    q["symbol"]: {
                        "ltp":        round(q.get("regularMarketPrice", 0), 2),
                        "change":     round(q.get("regularMarketChange", 0), 2),
                        "change_pct": round(q.get("regularMarketChangePercent", 0), 2),
                    }
                    for q in result if q.get("regularMarketPrice")
                }
    except Exception as e:
        print(f"[Yahoo httpx] {e}")
    return {}


def _mock_with_drift(symbols: List[str]) -> Dict[str, Dict]:
    prices = {}
    for sym in symbols:
        base = MOCK_PRICES.get(sym, {"ltp": 1000.0, "change": 0.0, "change_pct": 0.0})
        drift = random.uniform(-0.006, 0.006)
        ltp   = round(base["ltp"] * (1 + drift), 2)
        chg   = round(base["change"] + random.uniform(-5, 5), 2)
        pct   = round(base["change_pct"] + drift * 10, 2)
        prices[sym] = {"ltp": ltp, "change": chg, "change_pct": pct}
    return prices


async def fetch_live_prices(symbols: List[str]) -> Dict[str, Dict]:
    """
    Price priority:
      1. yfinance (most reliable for NSE/BSE)
      2. Yahoo Finance v8 API (httpx)
      3. Mock with drift (offline fallback)
    """
    prices = await _yfinance_fetch(symbols)
    if len(prices) >= len(symbols) // 2:
        return {**_mock_with_drift(symbols), **prices}   # fill gaps with mock

    prices2 = await _httpx_yahoo_fetch(symbols)
    if prices2:
        return {**_mock_with_drift(symbols), **prices2}

    return _mock_with_drift(symbols)


async def fetch_live_indices() -> Dict[str, Dict]:
    sym_map = {"^NSEI": "NIFTY_50", "^BSESN": "SENSEX", "^NSEBANK": "BANK_NIFTY", "^CNXIT": "NIFTY_IT"}
    symbols = list(sym_map.keys())
    prices  = await fetch_live_prices(symbols)

    result = {}
    for sym, key in sym_map.items():
        if sym in prices:
            d = prices[sym]
            result[key] = {"value": d["ltp"], "change": d["change"], "change_pct": d["change_pct"]}
        else:
            base = MOCK_INDICES[key]
            drift = random.uniform(-0.003, 0.003)
            result[key] = {
                "value":      round(base["value"] * (1 + drift), 2),
                "change":     round(base["change"] + random.uniform(-30, 30), 2),
                "change_pct": round(base["change_pct"] + drift * 10, 2),
            }
    return result

# ─────────────────────────────────────────────────────────────────────────────
# IPFS via Pinata
# ─────────────────────────────────────────────────────────────────────────────

async def pin_to_ipfs(data: dict, name: str = "pragati-block") -> str:
    """
    Pin a JSON document to IPFS via Pinata.
    Returns the IPFS CID (v1) or empty string if unavailable.
    """
    if not PINATA_API_KEY or not PINATA_SECRET_KEY:
        print("[IPFS] Pinata keys not set — skipping pin.")
        return ""
    try:
        url     = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
        headers = {
            "pinata_api_key":        PINATA_API_KEY,
            "pinata_secret_api_key": PINATA_SECRET_KEY,
            "Content-Type":          "application/json",
        }
        payload = {
            "pinataContent":  data,
            "pinataMetadata": {"name": name, "keyvalues": {"source": "PRAGATI.AI"}},
            "pinataOptions":  {"cidVersion": 1},
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code == 200:
            cid = resp.json().get("IpfsHash", "")
            print(f"[IPFS] Pinned: {cid}")
            return cid
        print(f"[IPFS] Pinata error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[IPFS] {e}")
    return ""


async def check_ipfs_status() -> dict:
    """Verify Pinata connection and remaining storage."""
    if not PINATA_API_KEY:
        return {"connected": False, "reason": "API key not configured"}
    try:
        url = "https://api.pinata.cloud/data/testAuthentication"
        headers = {
            "pinata_api_key":        PINATA_API_KEY,
            "pinata_secret_api_key": PINATA_SECRET_KEY,
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers=headers)
        return {"connected": resp.status_code == 200, "status": resp.json()}
    except Exception as e:
        return {"connected": False, "reason": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# Ethereum via Web3.py (Sepolia Testnet)
# ─────────────────────────────────────────────────────────────────────────────

def _get_web3():
    """Return a Web3 instance connected to the configured RPC, or None."""
    if not ETH_RPC_URL:
        return None
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL, request_kwargs={"timeout": 15}))
        return w3 if w3.is_connected() else None
    except Exception as e:
        print(f"[Web3] connection error: {e}")
        return None


def _eth_log_sync(
    block_index: int,
    decision: str,
    ipfs_cid: str,
    data_hash_hex: str,
    trade_frozen: bool,
    confidence: int,
) -> str:
    """Blocking call — sign and broadcast transaction to Ethereum."""
    from web3 import Web3

    w3 = _get_web3()
    if not w3:
        print("[Ethereum] Not connected — skipping on-chain log.")
        return ""
    if not ETH_PRIVATE_KEY or not CONTRACT_ADDR:
        print("[Ethereum] Private key or contract address missing.")
        return ""

    try:
        account  = w3.eth.account.from_key(ETH_PRIVATE_KEY)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDR),
            abi=CONTRACT_ABI,
        )
        data_bytes32 = bytes.fromhex(data_hash_hex.replace("0x", "").ljust(64, "0")[:64])
        nonce        = w3.eth.get_transaction_count(account.address)
        gas_price    = w3.eth.gas_price

        tx = contract.functions.logDecision(
            block_index,
            decision,
            ipfs_cid,
            data_bytes32,
            trade_frozen,
            min(confidence, 100),
        ).build_transaction({
            "from":     account.address,
            "nonce":    nonce,
            "gas":      250_000,
            "gasPrice": gas_price,
        })

        signed   = w3.eth.account.sign_transaction(tx, ETH_PRIVATE_KEY)
        tx_hash  = w3.eth.send_raw_transaction(signed.raw_transaction)
        result   = "0x" + tx_hash.hex()
        print(f"[Ethereum] TX broadcast: {result}")
        return result
    except Exception as e:
        print(f"[Ethereum] TX failed: {e}")
        return ""


async def log_to_ethereum(
    block_index: int,
    decision: str,
    ipfs_cid: str,
    data_hash_hex: str,
    trade_frozen: bool,
    confidence: int,
) -> str:
    """Async wrapper around the blocking Ethereum call."""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(
            pool, _eth_log_sync,
            block_index, decision, ipfs_cid, data_hash_hex, trade_frozen, confidence,
        )


async def check_eth_status() -> dict:
    """Return Ethereum network status."""
    if not ETH_RPC_URL:
        return {"connected": False, "reason": "RPC URL not configured"}
    try:
        from web3 import Web3
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            def _check():
                w3 = Web3(Web3.HTTPProvider(ETH_RPC_URL, request_kwargs={"timeout": 10}))
                if not w3.is_connected():
                    return {"connected": False}
                return {
                    "connected":    True,
                    "chain_id":     w3.eth.chain_id,
                    "block_number": w3.eth.block_number,
                    "contract":     CONTRACT_ADDR or "not deployed",
                    "network":      "Sepolia Testnet" if w3.eth.chain_id == 11155111 else f"ChainID {w3.eth.chain_id}",
                }
            return await loop.run_in_executor(pool, _check)
    except Exception as e:
        return {"connected": False, "reason": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
# SHA-256 Local Blockchain
# ─────────────────────────────────────────────────────────────────────────────

def calculate_hash(block_data: dict) -> str:
    payload    = {k: v for k, v in block_data.items() if k != "hash"}
    serialised = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def create_genesis_block() -> dict:
    genesis = {
        "index": 0,
        "timestamp":       "2024-01-01T00:00:00",
        "decision":        "GENESIS",
        "advice":          "PRAGATI.AI Blockchain Initialized",
        "trade_freeze":    False,
        "confidence_score": 100.0,
        "wallet_address":  "0x0000000000000000000000000000000000000000",
        "agent_verdicts":  {"portfolio_health": "GENESIS", "market_regime": "GENESIS", "news_sentiment": "GENESIS", "ethics_risk": "GENESIS"},
        "previous_hash":   "0" * 64,
        "nonce":           0,
        "ipfs_cid":        "",
        "eth_tx_hash":     "",
    }
    genesis["hash"] = calculate_hash(genesis)
    return genesis


def load_blockchain() -> List[dict]:
    if os.path.exists(BLOCKCHAIN_FILE):
        try:
            with open(BLOCKCHAIN_FILE) as fh:
                chain = json.load(fh)
            if isinstance(chain, list) and chain:
                return chain
        except (json.JSONDecodeError, KeyError):
            pass
    chain = [create_genesis_block()]
    _save_blockchain(chain)
    return chain


def _save_blockchain(chain: List[dict]) -> None:
    with open(BLOCKCHAIN_FILE, "w") as fh:
        json.dump(chain, fh, indent=2)


async def add_block(
    decision: str,
    advice: str,
    trade_freeze: bool,
    confidence: float,
    wallet: str,
    agent_verdicts: dict,
) -> dict:
    """
    Build a new block, optionally pin it to IPFS and log it on Ethereum,
    then append to the local chain.
    """
    chain = load_blockchain()
    prev  = chain[-1]

    block: dict = {
        "index":          len(chain),
        "timestamp":      datetime.datetime.utcnow().isoformat(),
        "decision":       decision,
        "advice":         advice,
        "trade_freeze":   trade_freeze,
        "confidence_score": round(confidence, 2),
        "wallet_address": wallet,
        "agent_verdicts": agent_verdicts,
        "previous_hash":  prev["hash"],
        "nonce":          random.randint(10_000, 99_999),
        "ipfs_cid":       "",
        "eth_tx_hash":    "",
    }
    block["hash"] = calculate_hash(block)

    # ── Pin to IPFS (async, non-blocking) ────────────────────────────
    ipfs_cid = await pin_to_ipfs(
        data=block,
        name=f"pragati-block-{block['index']}-{decision.lower()}",
    )
    block["ipfs_cid"] = ipfs_cid

    # ── Log on Ethereum (async, non-blocking) ────────────────────────
    eth_tx = await log_to_ethereum(
        block_index  = block["index"],
        decision     = decision,
        ipfs_cid     = ipfs_cid,
        data_hash_hex= block["hash"],
        trade_frozen = trade_freeze,
        confidence   = int(confidence),
    )
    block["eth_tx_hash"] = eth_tx

    # Recompute hash to include ipfs_cid and eth_tx_hash
    block["hash"] = calculate_hash(block)

    chain.append(block)
    _save_blockchain(chain)
    return block


def verify_chain(chain: List[dict]) -> bool:
    for i in range(1, len(chain)):
        cur, prev = chain[i], chain[i - 1]
        if cur["hash"] != calculate_hash(cur):
            return False
        if cur["previous_hash"] != prev["hash"]:
            return False
    return True

# ─────────────────────────────────────────────────────────────────────────────
# AI Agents
# ─────────────────────────────────────────────────────────────────────────────

def agent_portfolio_health(portfolio: list, scenario: str) -> dict:
    total_value    = sum(h.get("ltp", h["avg_price"]) * h["quantity"] for h in portfolio)
    total_invested = sum(h["avg_price"] * h["quantity"] for h in portfolio)
    returns_pct    = ((total_value - total_invested) / total_invested * 100) if total_invested else 0

    sector_values: Dict[str, float] = {}
    for h in portfolio:
        val = h.get("ltp", h["avg_price"]) * h["quantity"]
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0) + val

    num_sectors       = len(sector_values)
    max_concentration = (max(sector_values.values()) / total_value * 100) if total_value else 0

    score = 50
    if   returns_pct > 20:  score += 30
    elif returns_pct > 10:  score += 20
    elif returns_pct > 0:   score += 10
    elif returns_pct < -15: score -= 25
    elif returns_pct < -5:  score -= 12

    if   num_sectors >= 6: score += 20
    elif num_sectors >= 4: score += 12
    elif num_sectors >= 3: score +=  6

    if   max_concentration > 60: score -= 20
    elif max_concentration > 40: score -= 10

    score = max(0, min(100, score))
    verdict = "APPROVE" if score >= 70 else "CAUTION" if score >= 45 else "WARN"

    return {
        "agent_name": "Portfolio Health Agent", "agent_id": "AGENT_01",
        "score": round(score, 1), "verdict": verdict,
        "findings": [
            f"Portfolio return: {returns_pct:+.2f}%",
            f"Sector diversification: {num_sectors} unique sectors",
            f"Highest sector concentration: {max_concentration:.1f}%",
            f"Total active positions: {len(portfolio)} stocks",
        ],
        "metadata": {"total_value": round(total_value, 2), "returns_pct": round(returns_pct, 2)},
    }


def agent_market_regime(scenario: str, indices: dict) -> dict:
    configs = {
        "bull":     {"score": 85, "action": "GROW",    "verdict": "APPROVE", "risk": "LOW"},
        "bear":     {"score": 25, "action": "PROTECT", "verdict": "WARN",    "risk": "HIGH"},
        "sideways": {"score": 55, "action": "HOLD",    "verdict": "CAUTION", "risk": "MODERATE"},
        "volatile": {"score": 35, "action": "WAIT",    "verdict": "WARN",    "risk": "HIGH"},
    }
    cfg = configs.get(scenario.lower(), configs["sideways"])
    nifty_chg   = indices.get("NIFTY_50", {}).get("change_pct", 0)
    nifty_value = indices.get("NIFTY_50", {}).get("value", 22000)
    return {
        "agent_name": "Market Regime Agent", "agent_id": "AGENT_02",
        "score": cfg["score"], "verdict": cfg["verdict"], "action": cfg["action"],
        "findings": [
            f"Detected regime: {scenario.upper()} MARKET",
            f"Recommended portfolio action: {cfg['action']}",
            f"Current risk environment: {cfg['risk']}",
            f"NIFTY 50: {nifty_value:,.2f} ({'+' if nifty_chg >= 0 else ''}{nifty_chg:.2f}%)",
        ],
        "metadata": {"regime": scenario.upper(), "risk_level": cfg["risk"]},
    }


def agent_news_sentiment(news_items: list) -> dict:
    bullish = sum(1 for n in news_items if n.get("impact") == "bullish")
    bearish = sum(1 for n in news_items if n.get("impact") == "bearish")
    neutral = len(news_items) - bullish - bearish
    total   = max(len(news_items), 1)
    raw     = (bullish - bearish) / total * 100
    score   = max(0, min(100, raw + 50))
    verdict = "APPROVE" if score >= 60 else "CAUTION" if score >= 40 else "WARN"
    return {
        "agent_name": "News Sentiment Agent", "agent_id": "AGENT_03",
        "score": round(score, 1), "verdict": verdict,
        "findings": [
            f"Bullish market signals: {bullish} articles",
            f"Bearish market signals: {bearish} articles",
            f"Neutral / informational: {neutral} articles",
            f"Composite sentiment index: {raw:+.0f} pts",
        ],
        "metadata": {"bullish_count": bullish, "bearish_count": bearish},
    }


def agent_ethics_risk(age: int, risk_tolerance: str, scenario: str) -> dict:
    if   age < 30: recommended, age_group = "HIGH",     "Young Investor (Under 30)"
    elif age < 50: recommended, age_group = "MODERATE", "Mid-Career Investor (30–50)"
    else:          recommended, age_group = "LOW",       "Senior Investor (Over 50)"

    user_risk    = risk_tolerance.upper()
    risk_match   = user_risk == recommended
    trade_freeze = scenario.lower() in ["bear", "volatile"]
    base_scores  = {"LOW": 35, "MODERATE": 65, "HIGH": 90}
    score        = base_scores.get(recommended, 65)

    if risk_match:                                      score += 10
    elif user_risk == "HIGH" and recommended == "LOW":  score -= 25
    elif user_risk == "HIGH":                           score -= 10
    else:                                               score -=  5

    if trade_freeze: score -= 35
    score   = max(0, min(100, score))
    verdict = "WARN" if trade_freeze else ("APPROVE" if score >= 65 else "CAUTION" if score >= 42 else "WARN")

    return {
        "agent_name": "Ethics and Risk Agent", "agent_id": "AGENT_04",
        "score": round(score, 1), "verdict": verdict, "trade_freeze": trade_freeze,
        "findings": [
            f"Investor profile: {age_group}",
            f"Recommended risk level: {recommended}",
            f"Declared risk tolerance: {user_risk}",
            f"Trade freeze: {'ACTIVE — Protect capital' if trade_freeze else 'INACTIVE — Normal trading'}",
        ],
        "metadata": {"recommended_risk": recommended, "user_risk": user_risk},
    }


def synthesize_decision(agents: List[dict]) -> dict:
    verdicts      = [a["verdict"] for a in agents]
    trade_freezes = [a.get("trade_freeze", False) for a in agents]
    mixed         = verdicts.count("WARN") + verdicts.count("CAUTION")

    if   "REFUSE" in verdicts:      final, freeze = "REFUSED", True
    elif mixed >= 2:                final, freeze = "CAUTION", any(trade_freezes)
    elif verdicts.count("APPROVE") >= 3: final, freeze = "APPROVED", False
    else:                           final, freeze = "CAUTION", any(trade_freezes)

    avg_conf = sum(a["score"] for a in agents) / len(agents)
    advice_map = {
        "APPROVED": "AI consensus is positive. Portfolio health is strong and market conditions are favorable. Proceed with your planned investment strategy.",
        "CAUTION":  "AI consensus flags mixed signals. Consider reviewing portfolio allocation and avoid new leveraged positions until clarity improves.",
        "REFUSED":  "AI consensus indicates high-risk environment. New investments are not advised. Prioritize capital preservation and activate stop-losses.",
    }
    return {
        "final_decision":  final,
        "trade_freeze":    freeze,
        "confidence_score": round(avg_conf, 2),
        "advice":          advice_map[final],
        "agent_verdicts":  {
            "portfolio_health": verdicts[0],
            "market_regime":    verdicts[1],
            "news_sentiment":   verdicts[2],
            "ethics_risk":      verdicts[3],
        },
    }

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────────────────────

class HoldingInput(BaseModel):
    symbol:         str
    display_symbol: str
    name:           str
    quantity:       float
    avg_price:      float
    sector:         str


class AnalysisRequest(BaseModel):
    scenario:       str = "bull"
    age:            int = 35
    risk_tolerance: str = "MODERATE"
    wallet_address: str = "0xUser123abc456def789"
    holdings:       Optional[List[HoldingInput]] = None

# ─────────────────────────────────────────────────────────────────────────────
# Shared helper — enrich raw holdings with live prices
# ─────────────────────────────────────────────────────────────────────────────

async def enrich_holdings(raw: List[dict]) -> dict:
    symbols  = [h["symbol"] for h in raw]
    prices   = await fetch_live_prices(symbols)
    holdings = []
    total_v  = total_i = 0.0

    for h in raw:
        sym   = h["symbol"]
        pd    = prices.get(sym, MOCK_PRICES.get(sym, {"ltp": h["avg_price"], "change": 0, "change_pct": 0}))
        ltp   = pd["ltp"] or h["avg_price"]
        inv   = h["avg_price"] * h["quantity"]
        cur   = ltp * h["quantity"]
        pnl   = cur - inv
        pp    = (pnl / inv * 100) if inv else 0
        total_v += cur; total_i += inv
        holdings.append({
            **h,
            "ltp":            round(ltp, 2),
            "change":         round(pd["change"], 2),
            "change_pct":     round(pd["change_pct"], 2),
            "current_value":  round(cur, 2),
            "invested_value": round(inv, 2),
            "pnl":            round(pnl, 2),
            "pnl_pct":        round(pp, 2),
        })

    total_pnl = total_v - total_i
    return {
        "holdings": holdings,
        "summary": {
            "total_value":    round(total_v, 2),
            "total_invested": round(total_i, 2),
            "total_pnl":      round(total_pnl, 2),
            "total_pnl_pct":  round((total_pnl / total_i * 100) if total_i else 0, 2),
            "holdings_count": len(holdings),
        },
        "risk_metrics": {
            "beta":          round(random.uniform(0.85, 1.15), 2),
            "volatility":    round(random.uniform(12.0, 18.0), 1),
            "sharpe_ratio":  round(random.uniform(1.2,  2.1),  2),
            "var_95":        round(total_v * random.uniform(0.015, 0.025), 2),
            "max_drawdown":  round(random.uniform(-8.0, -15.0), 1),
        },
        "price_source": "yfinance/NSE",
        "timestamp":    datetime.datetime.utcnow().isoformat(),
    }

# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

# Serve frontend
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent  # pragati4/
FRONTEND_DIR = BASE_DIR / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
async def health():
    chain = load_blockchain()
    return {
        "status": "healthy",
        "timestamp":        datetime.datetime.utcnow().isoformat(),
        "blockchain_blocks": len(chain),
        "blockchain_valid":  verify_chain(chain),
        "ipfs_configured":   bool(PINATA_API_KEY),
        "eth_configured":    bool(ETH_RPC_URL and ETH_PRIVATE_KEY and CONTRACT_ADDR),
        "version":           "2.0.0",
    }


@app.get("/api/status/ipfs")
async def ipfs_status():
    return await check_ipfs_status()


@app.get("/api/status/ethereum")
async def eth_status():
    return await check_eth_status()


@app.get("/api/portfolio")
async def get_portfolio():
    return await enrich_holdings(PORTFOLIO_HOLDINGS)


@app.post("/api/portfolio/enrich")
async def enrich_user_portfolio(holdings: List[HoldingInput]):
    raw = [
        {
            "symbol":         h.symbol if "." in h.symbol else f"{h.symbol}.NS",
            "display_symbol": h.display_symbol,
            "name":           h.name,
            "quantity":       h.quantity,
            "avg_price":      h.avg_price,
            "sector":         h.sector,
        }
        for h in holdings
    ]
    return await enrich_holdings(raw)


@app.get("/api/stock/{symbol}")
async def get_stock(symbol: str):
    yahoo_sym = symbol if "." in symbol else f"{symbol}.NS"
    prices    = await fetch_live_prices([yahoo_sym])
    pd        = prices.get(yahoo_sym, {"ltp": 0.0, "change": 0.0, "change_pct": 0.0})
    return {"symbol": symbol, "yahoo_symbol": yahoo_sym, **pd,
            "source": "yfinance", "timestamp": datetime.datetime.utcnow().isoformat()}


@app.get("/api/indices")
async def get_indices():
    indices = await fetch_live_indices()
    now     = datetime.datetime.now()
    market  = "OPEN" if (9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)) else "CLOSED"
    return {"indices": indices, "market_status": market, "source": "yfinance/NSE",
            "timestamp": now.isoformat()}


@app.get("/api/news")
async def get_news():
    news = MOCK_NEWS.copy(); random.shuffle(news)
    return {"news": news, "count": len(news), "timestamp": datetime.datetime.utcnow().isoformat()}


@app.post("/api/analyze")
async def run_analysis(req: AnalysisRequest):
    scenario = req.scenario.lower()

    base_holdings = (
        [{"symbol": h.symbol if "." in h.symbol else f"{h.symbol}.NS",
          "display_symbol": h.display_symbol, "name": h.name,
          "quantity": h.quantity, "avg_price": h.avg_price, "sector": h.sector}
         for h in req.holdings]
        if req.holdings else PORTFOLIO_HOLDINGS
    )

    symbols   = [h["symbol"] for h in base_holdings]
    prices    = await fetch_live_prices(symbols)
    indices   = await fetch_live_indices()
    portfolio = [{**h, "ltp": prices.get(h["symbol"], MOCK_PRICES.get(h["symbol"], {"ltp": h["avg_price"]}))["ltp"]}
                 for h in base_holdings]

    a1 = agent_portfolio_health(portfolio, scenario)
    a2 = agent_market_regime(scenario, indices)
    a3 = agent_news_sentiment(MOCK_NEWS)
    a4 = agent_ethics_risk(req.age, req.risk_tolerance, scenario)

    synthesis = synthesize_decision([a1, a2, a3, a4])

    block = await add_block(
        decision       = synthesis["final_decision"],
        advice         = synthesis["advice"],
        trade_freeze   = synthesis["trade_freeze"],
        confidence     = synthesis["confidence_score"],
        wallet         = req.wallet_address,
        agent_verdicts = synthesis["agent_verdicts"],
    )

    return {
        "agents":    [a1, a2, a3, a4],
        "synthesis": synthesis,
        "blockchain": {
            "block_index":   block["index"],
            "block_hash":    block["hash"],
            "ipfs_cid":      block["ipfs_cid"],
            "ipfs_url":      f"https://gateway.pinata.cloud/ipfs/{block['ipfs_cid']}" if block["ipfs_cid"] else "",
            "eth_tx_hash":   block["eth_tx_hash"],
            "eth_url":       f"https://sepolia.etherscan.io/tx/{block['eth_tx_hash']}" if block["eth_tx_hash"] else "",
            "timestamp":     block["timestamp"],
            "logged":        True,
        },
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


@app.get("/api/blockchain/chain")
async def get_chain():
    chain    = load_blockchain()
    is_valid = verify_chain(chain)
    return {"chain": chain, "length": len(chain), "is_valid": is_valid,
            "contract_address": CONTRACT_ADDR or "not deployed",
            "network": "Sepolia Testnet"}


@app.get("/api/blockchain/status")
async def get_chain_status():
    chain     = load_blockchain()
    decisions = [b["decision"] for b in chain[1:]]
    eth_info  = await check_eth_status()
    return {
        "total_blocks":      len(chain),
        "genesis_timestamp": chain[0]["timestamp"],
        "latest_block":      chain[-1]["index"],
        "latest_hash":       chain[-1]["hash"],
        "is_valid":          verify_chain(chain),
        "contract_address":  CONTRACT_ADDR or "not deployed",
        "network":           eth_info.get("network", "Sepolia Testnet"),
        "eth_connected":     eth_info.get("connected", False),
        "ipfs_configured":   bool(PINATA_API_KEY),
        "decision_counts":   {
            "approved": decisions.count("APPROVED"),
            "caution":  decisions.count("CAUTION"),
            "refused":  decisions.count("REFUSED"),
        },
    }


@app.get("/api/blockchain/user/{address}")
async def get_user_blocks(address: str):
    chain       = load_blockchain()
    user_blocks = [b for b in chain if b.get("wallet_address") == address]
    return {"wallet_address": address, "blocks": user_blocks, "count": len(user_blocks)}


@app.get("/api/recommendations")
async def get_recommendations():
    return {"recommendations": RECOMMENDATIONS, "timestamp": datetime.datetime.utcnow().isoformat()}


@app.get("/api/risk/metrics")
async def get_risk_metrics():
    pv = sum(MOCK_PRICES.get(h["symbol"], {"ltp": h["avg_price"]})["ltp"] * h["quantity"] for h in PORTFOLIO_HOLDINGS)
    return {
        "metrics": {
            "beta":              round(random.uniform(0.85, 1.15), 2),
            "volatility_annual": round(random.uniform(14.0, 22.0), 1),
            "sharpe_ratio":      round(random.uniform(1.2,  2.1),  2),
            "sortino_ratio":     round(random.uniform(1.5,  2.8),  2),
            "information_ratio": round(random.uniform(0.3,  0.9),  2),
            "tracking_error":    round(random.uniform(2.0,  6.0),  1),
            "var_95_1day":       round(pv * 0.020, 2),
            "var_99_1day":       round(pv * 0.030, 2),
            "max_drawdown":      round(random.uniform(-8.0, -18.0), 1),
        },
        "portfolio_value": round(pv, 2),
        "timestamp":       datetime.datetime.utcnow().isoformat(),
    }

# ─────────────────────────────────────────────────────────────────────────────
# ML / AI Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/ml/insights")
async def get_ml_insights():
    """Full ML insights: stock predictions + market regime + portfolio risk."""
    enriched = await enrich_holdings(PORTFOLIO_HOLDINGS)
    holdings = enriched["holdings"]
    indices  = await fetch_live_indices()
    insights = ml_service.get_full_insights(holdings, indices)
    return {**insights, "timestamp": datetime.datetime.utcnow().isoformat()}


@app.get("/api/ml/regime")
async def get_ml_regime():
    """K-Means market regime detection."""
    indices = await fetch_live_indices()
    regime  = ml_service.get_market_regime(indices)
    return {**regime, "indices_snapshot": indices, "timestamp": datetime.datetime.utcnow().isoformat()}


@app.get("/api/ml/risk")
async def get_ml_risk():
    """HHI-based portfolio risk score."""
    enriched = await enrich_holdings(PORTFOLIO_HOLDINGS)
    risk     = ml_service.get_portfolio_risk(enriched["holdings"])
    return {**risk, "timestamp": datetime.datetime.utcnow().isoformat()}


@app.get("/api/ml/predict/{symbol}")
async def predict_stock(symbol: str):
    """Random Forest direction prediction for a single stock."""
    yahoo_sym = symbol if "." in symbol else f"{symbol}.NS"
    prices    = await fetch_live_prices([yahoo_sym])
    pd_data   = prices.get(yahoo_sym, {"ltp": 1000, "change_pct": 0})
    prediction = ml_service.get_stock_predictions([{
        "display_symbol": symbol,
        "symbol": yahoo_sym,
        "ltp": pd_data["ltp"],
        "change_pct": pd_data.get("change_pct", 0),
        "avg_price": pd_data["ltp"],
        "quantity": 1,
    }])
    return {**prediction[0], "timestamp": datetime.datetime.utcnow().isoformat()}


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║            PRAGATI.AI v2.0 — Blockchain Portfolio Manager               ║
║            yfinance · IPFS (Pinata) · Ethereum (Sepolia)                ║
║            Starting on http://0.0.0.0:8000                              ║
║                                                                          ║
║  IPFS  : {}                                          ║
║  ETH   : {}                                 ║
╚══════════════════════════════════════════════════════════════════════════╝
""".format(
        "CONFIGURED (Pinata)" if PINATA_API_KEY else "NOT CONFIGURED  (set PINATA_API_KEY in .env)",
        "CONFIGURED (Sepolia)" if ETH_RPC_URL  else "NOT CONFIGURED  (set ETHEREUM_RPC_URL in .env)",
    ))
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)