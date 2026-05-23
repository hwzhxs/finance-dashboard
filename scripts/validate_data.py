#!/usr/bin/env python3
"""
Finance data integrity validator & repair tool.
Runs after each data pipeline update to ensure completeness, accuracy, and freshness.

Usage:
  python3 validate_data.py              # validate only
  python3 validate_data.py --repair     # validate + attempt repairs
  python3 validate_data.py --discord    # validate + send report to Discord
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_DIR = Path(__file__).parent.parent / "config"
REPORT_PATH = DATA_DIR / "validation-report.json"

# Staleness thresholds (hours)
STALENESS = {
    "latest.json": 6,           # should update twice daily (20:15 + 04:15)
    "company_research.json": 8,
    "scores.json": 6,
    "rankings.json": 6,
    "valuation-comps.json": 168, # weekly is ok
    "earnings-calendar.json": 168,
    "competitive-analysis.json": 168,
    "expert-holdings.json": 168,
    "thesis-tracker.json": 168,
    "sec-filings.json": 168,
    "agent-insights.json": 24,
}

# Required fields per security in latest.json (non-ETF)
STOCK_QUOTE_REQUIRED = [
    "regularMarketPrice", "regularMarketChangePercent",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
]

STOCK_QUOTE_IMPORTANT = [
    "trailingPE", "forwardPE", "marketCap", "epsTrailingTwelveMonths",
]

RESEARCH_FINANCIALS_REQUIRED = [
    "revenue", "netIncome", "grossMarginPct", "operatingMarginPct",
    "freeCashFlow", "roePct",
]

RESEARCH_FINANCIALS_IMPORTANT = [
    "trailingPE", "forwardPE", "fcfYieldPct", "priceToSales",
]

RESEARCH_SECTIONS = ["businessModel", "moatEvidence", "keyRisks", "judgment"]


def load_json(name):
    path = DATA_DIR / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def load_watchlist():
    path = CONFIG_DIR / "watchlist.json"
    if not path.exists():
        return []
    wl = json.loads(path.read_text())
    return wl.get("tickers", [])


def check_staleness(data, filename):
    """Check if data file is stale."""
    gen = data.get("generatedAt") if data else None
    if not gen:
        return {"status": "error", "message": f"{filename}: 无 generatedAt 时间戳"}
    try:
        gen_dt = datetime.fromisoformat(gen.replace("Z", "+00:00"))
        if gen_dt.tzinfo is None:
            gen_dt = gen_dt.replace(tzinfo=timezone.utc)
    except Exception:
        return {"status": "error", "message": f"{filename}: 时间戳格式错误 ({gen})"}
    age_hours = (datetime.now(timezone.utc) - gen_dt).total_seconds() / 3600
    threshold = STALENESS.get(filename, 24)
    if age_hours > threshold:
        return {
            "status": "stale",
            "message": f"{filename}: 数据已过期 ({age_hours:.1f}h, 阈值 {threshold}h)",
            "age_hours": round(age_hours, 1),
            "threshold": threshold,
        }
    return {
        "status": "ok",
        "message": f"{filename}: 新鲜 ({age_hours:.1f}h)",
        "age_hours": round(age_hours, 1),
    }


def check_completeness(latest, research, valuation, watchlist):
    """Check if all watchlist tickers have data."""
    issues = []
    wl_syms = set(t["symbol"] for t in watchlist)
    
    # Check latest.json coverage
    latest_syms = set(latest["securities"].keys()) if latest else set()
    missing_latest = wl_syms - latest_syms
    if missing_latest:
        issues.append({"severity": "critical", "message": f"latest.json 缺失: {sorted(missing_latest)}"})
    
    # Check research coverage
    research_syms = set(research["items"].keys()) if research else set()
    missing_research = wl_syms - research_syms
    if missing_research:
        issues.append({"severity": "high", "message": f"company_research.json 缺失: {sorted(missing_research)}"})
    
    # Check valuation coverage (ETFs excluded)
    if valuation:
        val_syms = set(s["symbol"] for s in valuation.get("stocks", []))
        stock_syms = set(t["symbol"] for t in watchlist if t.get("type") != "ETF")
        missing_val = stock_syms - val_syms
        if missing_val:
            issues.append({"severity": "medium", "message": f"valuation-comps.json 缺失: {sorted(missing_val)}"})
    
    return issues


def check_field_quality(latest, research, watchlist):
    """Check critical fields for null/missing values."""
    issues = []
    null_report = {}
    
    if not latest:
        return [{"severity": "critical", "message": "latest.json 不存在或无法加载"}]
    
    stock_tickers = [t for t in watchlist if t.get("type") != "ETF"]
    
    for ticker in stock_tickers:
        sym = ticker["symbol"]
        sec = latest["securities"].get(sym)
        if not sec:
            continue
        q = sec.get("quote", {})
        
        # Required fields (critical)
        for field in STOCK_QUOTE_REQUIRED:
            if q.get(field) is None:
                null_report.setdefault(f"quote.{field}", []).append(sym)
        
        # Important fields (high)
        for field in STOCK_QUOTE_IMPORTANT:
            if q.get(field) is None:
                null_report.setdefault(f"quote.{field}", []).append(sym)
    
    # Research financials
    if research:
        for ticker in stock_tickers:
            sym = ticker["symbol"]
            ri = research["items"].get(sym, {})
            fin = ri.get("financials", {})
            
            for field in RESEARCH_FINANCIALS_REQUIRED:
                if fin.get(field) is None:
                    null_report.setdefault(f"research.{field}", []).append(sym)
            
            for field in RESEARCH_FINANCIALS_IMPORTANT:
                if fin.get(field) is None:
                    null_report.setdefault(f"research.{field}", []).append(sym)
            
            for section in RESEARCH_SECTIONS:
                if not ri.get(section):
                    null_report.setdefault(f"research.{section}", []).append(sym)
    
    # Classify severity
    for field, syms in null_report.items():
        total = len(stock_tickers)
        pct = len(syms) / total * 100 if total else 0
        if pct >= 80:
            severity = "critical"  # systemic issue
        elif pct >= 50:
            severity = "high"
        elif pct >= 20:
            severity = "medium"
        else:
            severity = "low"
        issues.append({
            "severity": severity,
            "field": field,
            "null_count": len(syms),
            "total": total,
            "null_pct": round(pct, 1),
            "symbols": sorted(syms),
            "message": f"{field}: {len(syms)}/{total} null ({pct:.0f}%)"
        })
    
    return sorted(issues, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}[x["severity"]])


def check_accuracy(latest, valuation):
    """Cross-validate data between sources for consistency."""
    issues = []
    if not latest or not valuation:
        return issues
    
    val_map = {s["symbol"]: s for s in valuation.get("stocks", [])}
    
    for sym, sec in latest["securities"].items():
        vs = val_map.get(sym)
        if not vs:
            continue
        
        price = sec.get("quote", {}).get("regularMarketPrice")
        if price is None:
            continue
        
        # Check if price is reasonable (not zero, not negative, not absurdly different from market cap)
        if price <= 0:
            issues.append({"severity": "critical", "symbol": sym, "message": f"{sym}: 价格异常 ({price})"})
        
        # Check PE consistency between sources
        q_pe = sec.get("quote", {}).get("trailingPE")
        v_pe = vs.get("pe")
        if q_pe and v_pe and abs(q_pe - v_pe) / v_pe > 0.3:
            issues.append({
                "severity": "medium",
                "symbol": sym,
                "message": f"{sym}: PE 差异过大 (latest={q_pe:.1f} vs comps={v_pe:.1f})"
            })
    
    return issues


def check_score_sanity(latest):
    """Verify scores are within expected ranges."""
    issues = []
    if not latest:
        return issues
    
    for sym, sec in latest["securities"].items():
        scores = sec.get("scores", {})
        perspectives = scores.get("perspectives", {})
        
        for name, val in perspectives.items():
            if val is not None and (val < 0 or val > 100):
                issues.append({
                    "severity": "high",
                    "message": f"{sym}: {name} 分数越界 ({val})"
                })
        
        components = scores.get("components", {})
        for name, val in components.items():
            if val is not None and (val < 0 or val > 100):
                issues.append({
                    "severity": "medium",
                    "message": f"{sym}: component.{name} 越界 ({val})"
                })
    
    return issues


def repair_from_yahoo_chart(latest, watchlist):
    """Attempt to fill missing fields from Yahoo chart meta."""
    import time
    repaired = []
    
    stock_tickers = [t for t in watchlist if t.get("type") != "ETF"]
    for ticker in stock_tickers:
        sym = ticker["symbol"]
        sec = latest["securities"].get(sym)
        if not sec:
            continue
        q = sec.get("quote", {})
        
        needs_repair = any(q.get(f) is None for f in ["fiftyTwoWeekHigh", "fiftyTwoWeekLow", "regularMarketVolume"])
        if not needs_repair:
            continue
        
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?range=5d&interval=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            meta = data["chart"]["result"][0]["meta"]
            
            filled = []
            for field in ["fiftyTwoWeekHigh", "fiftyTwoWeekLow", "regularMarketVolume", "longName", "shortName"]:
                if q.get(field) is None and meta.get(field) is not None:
                    q[field] = meta[field]
                    filled.append(field)
            
            if meta.get("regularMarketPrice"):
                q["regularMarketPrice"] = meta["regularMarketPrice"]
            
            if filled:
                repaired.append({"symbol": sym, "fields": filled})
            
            time.sleep(1)
        except Exception as e:
            print(f"  repair failed for {sym}: {e}", file=sys.stderr)
    
    return repaired


def repair_pe_from_comps(latest, valuation):
    """Fill missing PE/forwardPE from valuation-comps."""
    repaired = []
    if not valuation:
        return repaired
    
    val_map = {s["symbol"]: s for s in valuation.get("stocks", [])}
    
    for sym, sec in latest["securities"].items():
        q = sec.get("quote", {})
        vs = val_map.get(sym)
        if not vs:
            continue
        
        filled = []
        if q.get("trailingPE") is None and vs.get("pe"):
            q["trailingPE"] = vs["pe"]
            filled.append("trailingPE")
        if q.get("forwardPE") is None and vs.get("forwardPE"):
            q["forwardPE"] = vs["forwardPE"]
            filled.append("forwardPE")
        if q.get("marketCap") is None and vs.get("marketCap"):
            q["marketCap"] = vs["marketCap"] * 1e9  # comps stores in billions
            filled.append("marketCap")
        
        if filled:
            repaired.append({"symbol": sym, "fields": filled})
    
    return repaired


def generate_report(watchlist, latest, research, valuation):
    """Run all checks and return structured report."""
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "summary": {"total_issues": 0, "critical": 0, "high": 0, "medium": 0, "low": 0},
        "freshness": [],
        "completeness": [],
        "field_quality": [],
        "accuracy": [],
        "score_sanity": [],
        "repairs": [],
    }
    
    # Freshness
    for filename in STALENESS:
        data = load_json(filename)
        if data is None:
            report["freshness"].append({"status": "missing", "message": f"{filename}: 文件不存在"})
        else:
            report["freshness"].append(check_staleness(data, filename))
    
    # Completeness
    report["completeness"] = check_completeness(latest, research, valuation, watchlist)
    
    # Field quality
    report["field_quality"] = check_field_quality(latest, research, watchlist)
    
    # Accuracy
    report["accuracy"] = check_accuracy(latest, valuation)
    
    # Score sanity
    report["score_sanity"] = check_score_sanity(latest)
    
    # Count issues
    all_issues = (
        [f for f in report["freshness"] if f["status"] in ("stale", "missing", "error")]
        + report["completeness"]
        + report["field_quality"]
        + report["accuracy"]
        + report["score_sanity"]
    )
    for issue in all_issues:
        sev = issue.get("severity", "medium")
        report["summary"][sev] = report["summary"].get(sev, 0) + 1
    report["summary"]["total_issues"] = len(all_issues)
    
    # Overall health
    if report["summary"]["critical"] > 0:
        report["summary"]["health"] = "🔴 CRITICAL"
    elif report["summary"]["high"] > 0:
        report["summary"]["health"] = "🟠 DEGRADED"
    elif report["summary"]["medium"] > 0:
        report["summary"]["health"] = "🟡 FAIR"
    else:
        report["summary"]["health"] = "🟢 HEALTHY"
    
    return report


def format_discord_report(report):
    """Format report as Discord-friendly text."""
    s = report["summary"]
    lines = [
        f"## 📋 数据校验报告",
        f"**{s['health']}** — {s['total_issues']} 个问题 (🔴{s['critical']} 🟠{s['high']} 🟡{s['medium']} 🟢{s['low']})",
        "",
    ]
    
    # Freshness
    stale = [f for f in report["freshness"] if f["status"] != "ok"]
    if stale:
        lines.append("### ⏰ 数据时效")
        for f in stale:
            lines.append(f"- {f['message']}")
        lines.append("")
    
    # Completeness
    if report["completeness"]:
        lines.append("### 📦 覆盖完整性")
        for c in report["completeness"]:
            lines.append(f"- [{c['severity']}] {c['message']}")
        lines.append("")
    
    # Field quality (only critical/high)
    critical_fields = [f for f in report["field_quality"] if f["severity"] in ("critical", "high")]
    if critical_fields:
        lines.append("### 🔍 关键字段缺失")
        for f in critical_fields:
            lines.append(f"- **{f['field']}**: {f['null_count']}/{f['total']} 为空 ({f['null_pct']}%)")
        lines.append("")
    
    # Repairs
    if report.get("repairs"):
        lines.append("### 🔧 自动修复")
        for r in report["repairs"]:
            lines.append(f"- {r['symbol']}: 补全 {', '.join(r['fields'])}")
        lines.append("")
    
    # Accuracy
    if report["accuracy"]:
        lines.append("### ⚖️ 数据一致性")
        for a in report["accuracy"]:
            lines.append(f"- {a['message']}")
        lines.append("")
    
    lines.append(f"_校验时间: {report['generatedAt']}_")
    return "\n".join(lines)


def main():
    do_repair = "--repair" in sys.argv
    do_discord = "--discord" in sys.argv
    
    print("📋 Finance Data Validator", file=sys.stderr)
    print("=" * 40, file=sys.stderr)
    
    watchlist = load_watchlist()
    latest = load_json("latest.json")
    research = load_json("company_research.json")
    valuation = load_json("valuation-comps.json")
    
    if not watchlist:
        print("❌ watchlist.json 为空或不存在", file=sys.stderr)
        sys.exit(1)
    
    report = generate_report(watchlist, latest, research, valuation)
    
    # Repair
    if do_repair and latest:
        print("\n🔧 Attempting repairs...", file=sys.stderr)
        
        # Repair PE from comps
        pe_repairs = repair_pe_from_comps(latest, valuation)
        report["repairs"].extend(pe_repairs)
        
        # Repair from chart meta
        chart_repairs = repair_from_yahoo_chart(latest, watchlist)
        report["repairs"].extend(chart_repairs)
        
        if report["repairs"]:
            # Save repaired latest.json
            latest_path = DATA_DIR / "latest.json"
            latest_path.write_text(json.dumps(latest, indent=2, ensure_ascii=False))
            print(f"  ✅ Saved repaired latest.json ({len(report['repairs'])} fixes)", file=sys.stderr)
        else:
            print("  ℹ️ Nothing to repair", file=sys.stderr)
    
    # Save report
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    
    # Print summary
    s = report["summary"]
    print(f"\n{s['health']}", file=sys.stderr)
    print(f"  Issues: {s['total_issues']} (🔴{s['critical']} 🟠{s['high']} 🟡{s['medium']} 🟢{s['low']})", file=sys.stderr)
    
    if do_discord:
        discord_text = format_discord_report(report)
        print(discord_text)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # Exit code: 2 for critical, 1 for high, 0 otherwise
    if s["critical"] > 0:
        sys.exit(2)
    elif s["high"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
