#!/usr/bin/env python3
"""Fetch upcoming earnings dates for watchlist stocks using yfinance.
Outputs to finance/data/earnings-calendar.json
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCHLIST = ROOT / "config" / "watchlist.json"
OUTPUT = ROOT / "data" / "earnings-calendar.json"

def main():
    try:
        import yfinance as yf
    except ImportError:
        print("Installing yfinance...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
        import yfinance as yf

    with open(WATCHLIST) as f:
        config = json.load(f)

    tickers = [t["symbol"] for t in config.get("tickers", [])
               if not t["symbol"] in ("SPY", "QQQ", "VOO", "VTI", "SGOV")]

    calendar = []
    for symbol in tickers:
        try:
            stock = yf.Ticker(symbol)
            # Get next earnings date
            cal = stock.calendar
            if cal is not None:
                if isinstance(cal, dict):
                    earnings_date = cal.get("Earnings Date", [None])
                    if isinstance(earnings_date, list) and len(earnings_date) > 0:
                        calendar.append({
                            "symbol": symbol,
                            "earningsDate": str(earnings_date[0])[:10],
                            "confirmed": True
                        })
                        continue
                    elif earnings_date and not isinstance(earnings_date, list):
                        calendar.append({
                            "symbol": symbol,
                            "earningsDate": str(earnings_date)[:10],
                            "confirmed": True
                        })
                        continue
                elif hasattr(cal, 'empty') and not cal.empty:
                    earnings_date = cal.iloc[0].get("Earnings Date", None)
                    if earnings_date:
                        calendar.append({
                            "symbol": symbol,
                            "earningsDate": str(earnings_date)[:10],
                            "confirmed": True
                        })
                        continue

            # Fallback: try earnings_dates
            edates = stock.earnings_dates
            if edates is not None and len(edates) > 0:
                next_date = edates.index[0]
                calendar.append({
                    "symbol": symbol,
                    "earningsDate": str(next_date)[:10],
                    "confirmed": False
                })
            else:
                calendar.append({
                    "symbol": symbol,
                    "earningsDate": None,
                    "confirmed": False
                })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            calendar.append({
                "symbol": symbol,
                "earningsDate": None,
                "confirmed": False,
                "error": str(e)
            })

    # Sort by date
    calendar.sort(key=lambda x: x.get("earningsDate") or "9999-99-99")

    result = {
        "generatedAt": datetime.now().astimezone().isoformat(),
        "earnings": calendar
    }

    with open(OUTPUT, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(calendar)} earnings entries to {OUTPUT}")

    # Print upcoming (next 30 days)
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    upcoming = [e for e in calendar if e.get("earningsDate") and today <= e["earningsDate"] <= cutoff]
    if upcoming:
        print(f"\nUpcoming earnings (next 30 days):")
        for e in upcoming:
            print(f"  {e['symbol']}: {e['earningsDate']} {'✅' if e['confirmed'] else '❓'}")

if __name__ == "__main__":
    main()
