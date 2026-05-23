#!/usr/bin/env python3
from __future__ import annotations

import http.cookiejar
import json
import math
import statistics
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "watchlist.json"
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
COOKIE_JAR: http.cookiejar.CookieJar | None = None
CRUMB: str | None = None
CHART_HOST = "https://query1.finance.yahoo.com"  # query1 works better with curl
QUOTE_HOST = "https://query2.finance.yahoo.com"  # quote needs cookies from query2

AI_EXPOSURE = {
    "NVDA": 98,
    "MSFT": 88,
    "GOOGL": 82,
    "AAPL": 55,
    "TSLA": 65,
    "PDD": 20,
    "QQQ": 72,
    "SPY": 45,
    "VOO": 45,
    "VTI": 42,
    "SGOV": 0,
    "AMD": 88,
    "AVGO": 86,
    "TSM": 84,
    "ASML": 78,
    "AMZN": 75,
    "ORCL": 64,
    "PLTR": 82,
    "NOW": 62,
    "CRM": 55,
    "SNOW": 58,
    "DDOG": 54,
    "VRT": 74,
    "ETN": 48,
    "CEG": 45,
    "CRWD": 50,
    "PANW": 48,
    "SMH": 88,
    "XLK": 66,
    "IGV": 52,
}

MOAT_BASE = {
    "AAPL": 92,
    "MSFT": 94,
    "GOOGL": 88,
    "NVDA": 82,
    "TSLA": 58,
    "PDD": 55,
    "SPY": 82,
    "VOO": 84,
    "VTI": 88,
    "QQQ": 72,
    "SGOV": 40,
}

QUALITY_BASE = {
    "AAPL": 90,
    "MSFT": 92,
    "GOOGL": 86,
    "NVDA": 84,
    "TSLA": 60,
    "PDD": 62,
    "SPY": 78,
    "VOO": 80,
    "VTI": 82,
    "QQQ": 74,
    "SGOV": 82,
}

DIVERSIFICATION_BASE = {
    "VTI": 96,
    "VOO": 90,
    "SPY": 90,
    "QQQ": 64,
    "SGOV": 86,
}


@dataclass
class TickerConfig:
    symbol: str
    type: str
    theme: str
    expense_ratio: float | None = None


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    if math.isnan(value):
        return 0
    return max(low, min(high, value))


def http_json(url: str, timeout: int = 20, use_auth: bool = False, retries: int = 2) -> dict:
    """Fetch JSON via curl subprocess to avoid Python urllib TLS fingerprint detection."""
    import subprocess as _sp
    cookie_args = []
    if use_auth and Path("/tmp/yf_cookies.txt").exists():
        cookie_args = ["-b", "/tmp/yf_cookies.txt"]
    ua = USER_AGENT if use_auth else "Mozilla/5.0"
    for attempt in range(retries + 1):
        try:
            result = _sp.run(
                ["curl", "-s", "-m", str(timeout), "-H", f"User-Agent: {ua}"] + cookie_args + [url],
                capture_output=True, timeout=timeout + 5,
            )
            if result.returncode != 0:
                raise RuntimeError(f"curl exit {result.returncode}")
            body = result.stdout.decode("utf-8", errors="replace").strip()
            if not body:
                raise RuntimeError("empty response")
            data = json.loads(body)
            if isinstance(data, dict) and data.get("chart", {}).get("error"):
                err = data["chart"]["error"]
                if "Too Many" in str(err) and attempt < retries:
                    wait = 5 * (attempt + 1)
                    print(f"429 rate limit, waiting {wait}s (attempt {attempt+1}/{retries+1})", file=sys.stderr)
                    time.sleep(wait)
                    continue
            return data
        except (json.JSONDecodeError, RuntimeError) as exc:
            if attempt < retries:
                time.sleep(3)
                continue
            raise


def init_yahoo_auth() -> bool:
    """Obtain Yahoo Finance cookie + crumb via curl."""
    global CRUMB
    import subprocess as _sp
    cookie_file = "/tmp/yf_cookies.txt"
    # Get cookies
    _sp.run(["curl", "-s", "-c", cookie_file, "https://fc.yahoo.com",
             "-H", f"User-Agent: {USER_AGENT}", "-o", "/dev/null", "-m", "10"],
            capture_output=True, timeout=15)
    # Get crumb
    r = _sp.run(["curl", "-s", "-b", cookie_file,
                 "https://query2.finance.yahoo.com/v1/test/getcrumb",
                 "-H", f"User-Agent: {USER_AGENT}", "-m", "10"],
               capture_output=True, timeout=15)
    crumb = r.stdout.decode().strip()
    if not crumb or "Unauthorized" in crumb or "Too Many" in crumb:
        print(f"Yahoo crumb failed: {crumb[:50]}", file=sys.stderr)
        CRUMB = None
        return False
    CRUMB = crumb
    print(f"Yahoo auth OK (crumb={CRUMB[:8]}...)")
    return True


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def fetch_quotes(symbols: list[str]) -> dict[str, dict]:
    if not symbols:
        return {}
    if CRUMB is None:
        print("No crumb; skipping quote endpoint", file=sys.stderr)
        return {}
    query = urllib.parse.urlencode({"symbols": ",".join(symbols), "crumb": CRUMB})
    url = f"https://query2.finance.yahoo.com/v7/finance/quote?{query}"
    try:
        data = http_json(url, use_auth=True)
    except Exception as exc:
        print(f"quote endpoint unavailable; using chart fallback ({exc})", file=sys.stderr)
        return {}
    results = data.get("quoteResponse", {}).get("result", [])
    return {item.get("symbol"): item for item in results if item.get("symbol")}


def fetch_chart(symbol: str) -> dict:
    url = (
        f"{CHART_HOST}/v8/finance/chart/"
        f"{urllib.parse.quote(symbol)}?range=1y&interval=1d&includePrePost=false"
    )
    try:
        data = http_json(url, retries=3)
    except Exception as exc:
        print(f"chart fetch failed for {symbol}: {exc}", file=sys.stderr)
        return {"rows": [], "meta": {}}
    result = (data.get("chart", {}).get("result") or [None])[0]
    if not result:
        return {"rows": [], "meta": {}}
    meta = result.get("meta") or {}
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    rows = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        rows.append({"date": datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat(), "close": float(close)})
    return {"rows": rows, "meta": meta}


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def historical_metrics(rows: list[dict]) -> dict:
    closes = [row["close"] for row in rows if row.get("close")]
    if len(closes) < 2:
        return {
            "return1mPct": None,
            "return3mPct": None,
            "return1yPct": None,
            "volatilityPct": None,
            "maxDrawdownPct": None,
            "history": rows,
        }
    returns = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1]]
    volatility = statistics.stdev(returns) * math.sqrt(252) * 100 if len(returns) > 2 else None
    peak = closes[0]
    max_dd = 0.0
    for close in closes:
        peak = max(peak, close)
        max_dd = min(max_dd, (close / peak - 1) * 100)
    return {
        "return1mPct": pct_change(closes[-1], closes[-22]) if len(closes) > 22 else None,
        "return3mPct": pct_change(closes[-1], closes[-63]) if len(closes) > 63 else None,
        "return1yPct": pct_change(closes[-1], closes[0]),
        "volatilityPct": volatility,
        "maxDrawdownPct": max_dd,
        "history": rows,
    }


def value_score(pe: float | None, forward_pe: float | None, kind: str) -> float:
    if kind == "ETF":
        return 70
    chosen = forward_pe or pe
    if not chosen or chosen <= 0:
        return 45
    if chosen <= 15:
        return 90
    if chosen <= 25:
        return 76
    if chosen <= 40:
        return 58
    if chosen <= 60:
        return 38
    return 22


def risk_score(volatility: float | None, max_drawdown: float | None, symbol: str) -> float:
    if symbol == "SGOV":
        return 96
    vol = volatility if volatility is not None else 35
    dd = abs(max_drawdown if max_drawdown is not None else -30)
    return clamp(100 - (vol * 1.05) - (dd * 0.55))


def momentum_score(ret1m: float | None, ret3m: float | None, ret1y: float | None) -> float:
    values = [v for v in [ret1m, ret3m, ret1y] if v is not None]
    if not values:
        return 50
    composite = 0
    if ret1m is not None:
        composite += ret1m * 1.2
    if ret3m is not None:
        composite += ret3m * 0.7
    if ret1y is not None:
        composite += ret1y * 0.25
    return clamp(50 + composite)


def expense_score(expense_ratio: float | None, kind: str) -> float:
    if kind != "ETF":
        return 0
    if expense_ratio is None:
        return 65
    if expense_ratio <= 0.04:
        return 96
    if expense_ratio <= 0.10:
        return 88
    if expense_ratio <= 0.20:
        return 74
    return 55


def fit_score(symbol: str, kind: str, risk: float, ai: float) -> float:
    if symbol == "SGOV":
        return 88
    if kind == "ETF":
        if symbol in {"VTI", "VOO", "SPY"}:
            return 90
        if symbol == "QQQ":
            return 76
        return 70
    base = 56
    if symbol == "PDD":
        base -= 12
    if ai >= 80:
        base += 8
    if risk < 45:
        base -= 12
    return clamp(base)


def weighted(parts: list[tuple[float, float]]) -> float:
    total_weight = sum(weight for _, weight in parts)
    if total_weight == 0:
        return 0
    return clamp(sum(score * weight for score, weight in parts) / total_weight)


def score_security(item: dict, config_item: TickerConfig, manager_refs: list[dict]) -> dict:
    symbol = config_item.symbol
    kind = config_item.type
    quote = item.get("quote", {})
    metrics = item.get("metrics", {})
    pe = quote.get("trailingPE")
    fpe = quote.get("forwardPE")
    value = value_score(pe, fpe, kind)
    risk = risk_score(metrics.get("volatilityPct"), metrics.get("maxDrawdownPct"), symbol)
    momentum = momentum_score(metrics.get("return1mPct"), metrics.get("return3mPct"), metrics.get("return1yPct"))
    ai = AI_EXPOSURE.get(symbol, 35 if kind == "Stock" else 40)
    quality = QUALITY_BASE.get(symbol, 62 if kind == "Stock" else 74)
    moat = MOAT_BASE.get(symbol, 58 if kind == "Stock" else 70)
    diversification = DIVERSIFICATION_BASE.get(symbol, 15 if kind == "Stock" else 68)
    expense = expense_score(config_item.expense_ratio, kind)
    fit = fit_score(symbol, kind, risk, ai)
    manager_signal = clamp(50 + min(len(manager_refs), 3) * 8)

    scores = {
        "components": {
            "value": round(value, 1),
            "quality": round(quality, 1),
            "moat": round(moat, 1),
            "risk": round(risk, 1),
            "momentum": round(momentum, 1),
            "aiExposure": round(ai, 1),
            "diversification": round(diversification, 1),
            "expense": round(expense, 1),
            "personalFit": round(fit, 1),
            "managerReference": round(manager_signal, 1),
        }
    }

    scores["perspectives"] = {
        "composite": weighted([
            (value, 0.16),
            (quality, 0.18),
            (risk, 0.18),
            (momentum, 0.12),
            (ai, 0.12),
            (fit, 0.16),
            (manager_signal, 0.08),
        ]),
        "buffett_munger": weighted([
            (moat, 0.28),
            (quality, 0.28),
            (value, 0.18),
            (risk, 0.16),
            (fit, 0.10),
        ]),
        "bogle": weighted([
            (diversification, 0.42),
            (expense, 0.28),
            (risk, 0.20),
            (fit, 0.10),
        ]) if kind == "ETF" else weighted([(diversification, 0.50), (risk, 0.30), (fit, 0.20)]),
        "peter_lynch": weighted([
            (momentum, 0.20),
            (ai, 0.20),
            (quality, 0.20),
            (value, 0.20),
            (fit, 0.20),
        ]),
        "howard_marks": weighted([
            (risk, 0.42),
            (value, 0.24),
            (fit, 0.18),
            (100 - max(0, momentum - 70), 0.16),
        ]),
        "tech_growth_risk": weighted([
            (ai, 0.30),
            (quality, 0.20),
            (momentum, 0.16),
            (risk, 0.18),
            (value, 0.10),
            (fit, 0.06),
        ]),
    }
    scores["perspectives"] = {key: round(value, 1) for key, value in scores["perspectives"].items()}
    scores["action"] = action_label(symbol, kind, scores["perspectives"]["composite"], risk, fit, item, config_item)
    scores["explanation"] = build_explanation(symbol, kind, scores, item)
    return scores


def action_label(symbol: str, kind: str, composite: float, risk: float, fit: float, item: dict, config_item: TickerConfig) -> dict:
    if symbol == "PDD":
        return {
            "label": "Continue observing",
            "stance": "Do not add by default",
            "positionNote": "Current learning-pool position is already 20%, which is the soft single-stock limit.",
        }
    if symbol == "SGOV":
        return {
            "label": "Cash management candidate",
            "stance": "Consider for idle cash",
            "positionNote": "Useful for short-term USD cash management, not a long-term compounding engine.",
        }
    if kind == "ETF" and composite >= 78:
        return {
            "label": "Core candidate",
            "stance": "Consider gradual core allocation",
            "positionNote": "Use staged buying rather than one-shot deployment.",
        }
    if composite >= 76 and risk >= 55:
        return {
            "label": "Consider small position",
            "stance": "Needs trade checklist",
            "positionNote": "For a new individual stock, initial position usually stays around 3%-5% of the learning pool.",
        }
    if composite >= 62:
        return {"label": "Continue observing", "stance": "Watch", "positionNote": "Not enough edge to act without a specific thesis."}
    return {"label": "Not attractive for now", "stance": "Avoid impulsive buying", "positionNote": "Wait for better price or clearer evidence."}


def build_explanation(symbol: str, kind: str, scores: dict, item: dict) -> list[str]:
    c = scores["components"]
    notes = []
    if kind == "ETF":
        notes.append(f"ETF lens: diversification {c['diversification']}/100, cost {c['expense']}/100.")
    else:
        notes.append(f"Stock lens: moat {c['moat']}/100, quality {c['quality']}/100, value {c['value']}/100.")
    notes.append(f"Risk score is {c['risk']}/100 based on recent volatility and drawdown.")
    if c["aiExposure"] >= 75:
        notes.append("High AI/technology exposure; useful for learning but valuation discipline matters.")
    if symbol == "PDD":
        notes.append("Existing learning position; new capital should usually compare against core ETFs first.")
    return notes


def build_rankings(scored: dict[str, dict]) -> dict:
    perspective_names = ["composite", "buffett_munger", "bogle", "peter_lynch", "howard_marks", "tech_growth_risk"]
    rankings = {}
    for perspective in perspective_names:
        rows = []
        for symbol, data in scored.items():
            rows.append({
                "symbol": symbol,
                "score": data["scores"]["perspectives"][perspective],
                "action": data["scores"]["action"]["label"],
            })
        rows.sort(key=lambda row: row["score"], reverse=True)
        rankings[perspective] = rows
    return rankings


def brief_line(symbol: str, data: dict) -> str:
    q = data.get("quote", {})
    m = data.get("metrics", {})
    action = data["scores"]["action"]
    price = q.get("regularMarketPrice")
    day = q.get("regularMarketChangePercent")
    score = data["scores"]["perspectives"]["composite"]
    price_text = f"${price:.2f}" if isinstance(price, (int, float)) else "n/a"
    day_text = f"{day:+.2f}%" if isinstance(day, (int, float)) else "n/a"
    r3m = m.get("return3mPct")
    r3m_text = f"{r3m:+.1f}%" if isinstance(r3m, (int, float)) else "n/a"
    return f"- {symbol}: {action['label']} | score {score:.1f} | {price_text}, today {day_text}, 3m {r3m_text}"


def build_daily_brief(kind: str, scored: dict[str, dict], rankings: dict) -> str:
    now_cn = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")
    title = "Pre-market brief" if kind == "preopen" else "Post-close brief"
    top = rankings["composite"][:4]
    caution = [row for row in rankings["howard_marks"] if row["score"] < 55][:3]
    pdd = scored.get("PDD")
    lines = [
        f"# {title} - {now_cn} CST",
        "",
        "Conclusion: observe first; act only if a trade checklist is triggered.",
        "",
        "## Top candidates",
    ]
    for row in top:
        lines.append(brief_line(row["symbol"], scored[row["symbol"]]))
    lines.append("")
    lines.append("## Risk notes")
    if pdd:
        lines.append("- PDD is the existing learning position at the soft single-stock limit; avoid adding by default.")
    for row in caution:
        lines.append(f"- {row['symbol']}: Howard Marks risk lens is cautious ({row['score']:.1f}/100).")
    lines.append("")
    lines.append("Dashboard: http://127.0.0.1:18888")
    return "\n".join(lines) + "\n"


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    config = load_config()
    ticker_configs = [
        TickerConfig(
            symbol=item["symbol"].upper(),
            type=item.get("type", "Stock"),
            theme=item.get("theme", ""),
            expense_ratio=item.get("expenseRatio"),
        )
        for item in config["tickers"]
    ]
    symbols = [item.symbol for item in ticker_configs]
    init_yahoo_auth()
    quotes = fetch_quotes(symbols)
    latest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "prices": "Yahoo Finance unofficial public endpoints",
            "managerFootprints": "Curated reference notes; verify 13F before treating as current holdings",
        },
        "profile": config.get("learningPool", {}),
        "securities": {},
    }
    scored = {}
    manager_map = config.get("managerFootprints", {})
    for config_item in ticker_configs:
        symbol = config_item.symbol
        chart = fetch_chart(symbol)
        metrics = historical_metrics(chart["rows"])
        quote = quotes.get(symbol, {})
        if not quote:
            last_close = (chart["rows"][-1]["close"] if chart["rows"] else None)
            prev_close = (chart["rows"][-2]["close"] if len(chart["rows"]) > 1 else chart["meta"].get("chartPreviousClose"))
            day_change_pct = pct_change(last_close, prev_close)
            quote = {
                "shortName": symbol,
                "regularMarketPrice": chart["meta"].get("regularMarketPrice") or last_close,
                "regularMarketChange": (last_close - prev_close) if last_close is not None and prev_close else None,
                "regularMarketChangePercent": day_change_pct,
                "regularMarketPreviousClose": prev_close,
            }
        item = {
            "symbol": symbol,
            "type": config_item.type,
            "theme": config_item.theme,
            "quote": {
                key: quote.get(key)
                for key in [
                    "shortName",
                    "longName",
                    "regularMarketPrice",
                    "regularMarketChange",
                    "regularMarketChangePercent",
                    "regularMarketPreviousClose",
                    "marketCap",
                    "trailingPE",
                    "forwardPE",
                    "epsTrailingTwelveMonths",
                    "fiftyTwoWeekHigh",
                    "fiftyTwoWeekLow",
                    "regularMarketVolume",
                    "priceToBook",
                    "returnOnEquity",
                    "dividendYield",
                    "trailingAnnualDividendYield",
                ]
            },
            "metrics": metrics,
            "expenseRatio": config_item.expense_ratio,
            "managerFootprints": manager_map.get(symbol, []),
        }
        item["scores"] = score_security(item, config_item, item["managerFootprints"])
        latest["securities"][symbol] = item
        scored[symbol] = item
        time.sleep(1.5)

    rankings = build_rankings(scored)
    scores = {
        "generatedAt": latest["generatedAt"],
        "perspectives": {
            "composite": "Balanced score for Xiaosong's learning pool",
            "buffett_munger": "Moat, quality, cash generation, long-term certainty, margin of safety",
            "bogle": "Low cost, broad diversification, low decision burden",
            "peter_lynch": "Understandable growth, evidence, valuation discipline",
            "howard_marks": "Risk, cycle awareness, downside protection, avoiding over-optimism",
            "tech_growth_risk": "AI/technology upside with valuation and risk constraints",
        },
        "scores": {
            symbol: item["scores"] for symbol, item in scored.items()
        },
    }
    write_json(DATA_DIR / "latest.json", latest)
    write_json(DATA_DIR / "scores.json", scores)
    write_json(DATA_DIR / "rankings.json", {"generatedAt": latest["generatedAt"], "rankings": rankings})
    for kind in ["preopen", "postclose"]:
        brief = build_daily_brief(kind, scored, rankings)
        (DATA_DIR / f"{kind}-brief.md").write_text(brief, encoding="utf-8")
        (REPORTS_DIR / f"{datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()}-{kind}.md").write_text(brief, encoding="utf-8")
    (DATA_DIR / "daily-brief.md").write_text(build_daily_brief("preopen", scored, rankings), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "update_research.py")], check=False)
    print(f"Updated {len(symbols)} tickers in {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
