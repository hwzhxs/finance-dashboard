#!/usr/bin/env python3
"""Fetch recent SEC Form 4 / 13D/G filings for tracked experts.

Uses SEC EDGAR EFTS (full-text search) API.
Output: data/sec-filings.json

Rate limit: SEC requires ≤10 req/s and a User-Agent with contact info.
"""

import json, os, sys, time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_PATH = DATA_DIR.parent / "config" / "tickers.json"
EXPERT_PATH = DATA_DIR / "expert-holdings.json"
OUTPUT_PATH = DATA_DIR / "sec-filings.json"

HEADERS = {
    "User-Agent": "FinanceDashboard research@example.com",
    "Accept": "application/json",
}

EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"


def load_expert_ciks():
    """Load expert names from expert-holdings.json for matching."""
    if not EXPERT_PATH.exists():
        return []
    with open(EXPERT_PATH) as f:
        data = json.load(f)
    return [e.get("name", "").split("/")[-1].strip() for e in data.get("experts", []) if e.get("name")]


def load_consensus_symbols():
    """Get symbols held by 2+ experts."""
    if not EXPERT_PATH.exists():
        return []
    with open(EXPERT_PATH) as f:
        data = json.load(f)
    ticker_count = {}
    for expert in data.get("experts", []):
        for h in expert.get("topHoldings", []) + expert.get("notableMoves", []):
            sym = h.get("symbol")
            if sym:
                ticker_count[sym] = ticker_count.get(sym, 0) + 1
    return [s for s, c in ticker_count.items() if c >= 2]


def fetch_edgar(forms="4,SC 13D,SC 13G", days_back=14, size=50):
    """Fetch recent filings from SEC EDGAR full-text search."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    url = (
        f"{EDGAR_SEARCH}?q=&forms={forms.replace(' ', '+')}"
        f"&dateRange=custom&startdt={start}&enddt={end}"
        f"&from=0&size={size}"
    )
    
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (HTTPError, URLError) as e:
        print(f"EDGAR fetch failed: {e}", file=sys.stderr)
        return None


def fetch_form4_for_symbol(symbol, days_back=14):
    """Search Form 4 filings mentioning a specific ticker."""
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    url = (
        f"{EDGAR_SEARCH}?q=%22{symbol}%22&forms=4"
        f"&dateRange=custom&startdt={start}&enddt={end}"
        f"&from=0&size=10"
    )
    
    req = Request(url, headers=HEADERS)
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except (HTTPError, URLError):
        return None


def main():
    print("Updating SEC filings data...")
    consensus_symbols = load_consensus_symbols()
    print(f"Consensus symbols (2+ experts): {len(consensus_symbols)}")
    
    # Fetch general Form 4 / 13D/G
    general = fetch_edgar(days_back=14, size=100)
    
    # Fetch symbol-specific Form 4 for top consensus stocks
    symbol_filings = {}
    for sym in consensus_symbols[:10]:  # Top 10 to respect rate limits
        time.sleep(0.15)  # SEC rate limit
        result = fetch_form4_for_symbol(sym)
        if result and (result.get("hits") or result.get("filings")):
            hits = result.get("hits", result.get("filings", []))
            if hits:
                symbol_filings[sym] = [
                    {
                        "form": h.get("form_type", h.get("formType", "4")),
                        "filer": h.get("entity_name", h.get("companyName", "")),
                        "date": h.get("file_date", h.get("filedAt", "")),
                        "url": h.get("file_url", ""),
                    }
                    for h in (hits[:5] if isinstance(hits, list) else [])
                ]
    
    output = {
        "generatedAt": datetime.now().isoformat(),
        "consensusSymbols": consensus_symbols[:20],
        "symbolFilings": symbol_filings,
        "recentFilings": [],
    }
    
    if general:
        hits = general.get("hits", general.get("filings", []))
        if isinstance(hits, list):
            output["recentFilings"] = [
                {
                    "form": h.get("form_type", h.get("formType", "")),
                    "filer": h.get("entity_name", h.get("companyName", "")),
                    "date": h.get("file_date", h.get("filedAt", "")),
                    "url": h.get("file_url", ""),
                }
                for h in hits[:30]
            ]
    
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(output['recentFilings'])} general filings, {len(symbol_filings)} symbol-specific to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
