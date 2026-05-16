#!/usr/bin/env python3
"""Fetch SEC EDGAR financial data for watchlist tickers.

This script ONLY handles structured financial data from SEC.
All qualitative analysis (businessModel, moatEvidence, keyRisks, judgment, etc.)
is produced by the Agent daily research cron and stored in agent-insights.json.

The dashboard merges both files at render time.
"""
from __future__ import annotations

import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "watchlist.json"
DATA_DIR = ROOT / "data"
SEC_UA = "OpenClawFinanceDashboard/0.1 contact=zhangxiaosong"

STATIC_CIKS = {
    "AAPL": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "MSFT": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
    "NVDA": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA Corp"},
    "TSLA": {"cik_str": 1318605, "ticker": "TSLA", "title": "Tesla, Inc."},
    "GOOGL": {"cik_str": 1652044, "ticker": "GOOGL", "title": "Alphabet Inc."},
    "PDD": {"cik_str": 1737806, "ticker": "PDD", "title": "PDD Holdings Inc."},
    "AMD": {"cik_str": 2488, "ticker": "AMD", "title": "Advanced Micro Devices, Inc."},
    "AVGO": {"cik_str": 1730168, "ticker": "AVGO", "title": "Broadcom Inc."},
    "TSM": {"cik_str": 1046179, "ticker": "TSM", "title": "Taiwan Semiconductor Manufacturing Co Ltd"},
    "ASML": {"cik_str": 937966, "ticker": "ASML", "title": "ASML Holding NV"},
    "AMZN": {"cik_str": 1018724, "ticker": "AMZN", "title": "Amazon.com, Inc."},
    "ORCL": {"cik_str": 1341439, "ticker": "ORCL", "title": "Oracle Corp"},
    "PLTR": {"cik_str": 1321655, "ticker": "PLTR", "title": "Palantir Technologies Inc."},
    "NOW": {"cik_str": 1373715, "ticker": "NOW", "title": "ServiceNow, Inc."},
    "CRM": {"cik_str": 1108524, "ticker": "CRM", "title": "Salesforce, Inc."},
}

ETF_NOTES = {
    "SPY": "S&P 500 ETF — 美股大盘基准",
    "QQQ": "Nasdaq 100 ETF — 科技成长倾斜",
    "VOO": "Vanguard S&P 500 — 低费率核心仓",
    "VTI": "Vanguard Total Market — 全市场覆盖",
    "SGOV": "短期国债 ETF — 现金管理工具",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def http_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": SEC_UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def sec_ticker_map() -> dict[str, dict]:
    try:
        data = http_json("https://www.sec.gov/files/company_tickers.json")
        return {entry["ticker"].upper(): entry for entry in data.values()}
    except Exception:
        return {}


def company_facts(cik: int) -> dict:
    return http_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")


def fact_series(facts: dict, concept_names: list[str]) -> list[dict]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    ifrs = facts.get("facts", {}).get("ifrs-full", {})
    for name in concept_names:
        concept = us_gaap.get(name) or ifrs.get(name)
        if not concept:
            continue
        units = concept.get("units", {})
        series = units.get("USD") or units.get("USD/shares") or list(units.values())[0] if units else []
        if series:
            return sorted(series, key=lambda r: r.get("end", ""))
    return []


def latest_annual_row(series: list[dict]) -> tuple[dict | None, dict | None]:
    annuals = [r for r in series if r.get("fp") == "FY" or r.get("form") in ("10-K", "20-F")]
    if not annuals:
        return None, None
    by_fy = {}
    for row in annuals:
        fy = row.get("fy")
        if fy and (fy not in by_fy or row.get("filed", "") > by_fy[fy].get("filed", "")):
            by_fy[fy] = row
    sorted_fy = sorted(by_fy.keys(), reverse=True)
    latest = by_fy[sorted_fy[0]] if sorted_fy else None
    prev = by_fy[sorted_fy[1]] if len(sorted_fy) > 1 else None
    return latest, prev


def latest_period_row(series: list[dict]) -> tuple[dict | None, dict | None]:
    quarterly = [r for r in series if r.get("fp") in ("Q1", "Q2", "Q3", "Q4") or r.get("form") in ("10-Q", "6-K")]
    if not quarterly:
        return None, None
    by_key = {}
    for row in quarterly:
        key = (row.get("fy"), row.get("fp"))
        if key not in by_key or row.get("filed", "") > by_key[key].get("filed", ""):
            by_key[key] = row
    sorted_keys = sorted(by_key.keys(), reverse=True)
    latest = by_key[sorted_keys[0]] if sorted_keys else None
    prev = by_key[sorted_keys[1]] if len(sorted_keys) > 1 else None
    return latest, prev


def safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den


def growth(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return (current / previous - 1) * 100


def fmt(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1e12:
        return f"{sign}${abs_val/1e12:.1f}T{suffix}"
    if abs_val >= 1e9:
        return f"{sign}${abs_val/1e9:.1f}B{suffix}"
    if abs_val >= 1e6:
        return f"{sign}${abs_val/1e6:.0f}M{suffix}"
    return f"{sign}${abs_val:,.0f}{suffix}"


def stock_financials(symbol: str, ticker_info: dict | None, latest_data: dict) -> dict:
    """Extract SEC financials for a stock. No qualitative analysis."""
    quote = latest_data.get("securities", {}).get(symbol, {}).get("quote", {})
    base = {
        "symbol": symbol,
        "type": "Stock",
        "companyName": quote.get("longName") or quote.get("shortName") or symbol,
        "sec": {"available": False},
        "financials": {},
    }
    if not ticker_info:
        base["sec"]["note"] = "没有找到 SEC ticker 匹配。"
        return base

    cik = int(ticker_info["cik_str"])
    base["sec"] = {
        "available": True,
        "cik": f"{cik:010d}",
        "title": ticker_info.get("title"),
        "source": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
    }
    try:
        facts = company_facts(cik)
    except Exception as exc:
        base["sec"]["available"] = False
        base["sec"]["note"] = f"SEC 数据获取失败：{exc}"
        return base

    revenue_series = fact_series(facts, ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"])
    revenue_row, revenue_prev_row = latest_annual_row(revenue_series)
    latest_revenue_row, latest_revenue_prev_row = latest_period_row(revenue_series)
    net_income_row, net_income_prev_row = latest_annual_row(fact_series(facts, ["NetIncomeLoss", "ProfitLoss"]))
    latest_net_income_row, latest_net_income_prev_row = latest_period_row(fact_series(facts, ["NetIncomeLoss", "ProfitLoss"]))
    operating_income_row, _ = latest_annual_row(fact_series(facts, ["OperatingIncomeLoss"]))
    latest_operating_income_row, _ = latest_period_row(fact_series(facts, ["OperatingIncomeLoss"]))
    gross_profit_row, _ = latest_annual_row(fact_series(facts, ["GrossProfit"]))
    latest_gross_profit_row, _ = latest_period_row(fact_series(facts, ["GrossProfit"]))
    op_cf_row, op_cf_prev_row = latest_annual_row(fact_series(facts, ["NetCashProvidedByUsedInOperatingActivities"]))
    latest_op_cf_row, _ = latest_period_row(fact_series(facts, ["NetCashProvidedByUsedInOperatingActivities"]))
    capex_row, _ = latest_annual_row(fact_series(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"]))
    latest_capex_row, _ = latest_period_row(fact_series(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"]))
    assets_row, _ = latest_annual_row(fact_series(facts, ["Assets"]))
    liabilities_row, _ = latest_annual_row(fact_series(facts, ["Liabilities"]))
    equity_row, _ = latest_annual_row(fact_series(facts, ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]))

    def val(row): return row["val"] if row else None

    revenue, revenue_prev = val(revenue_row), val(revenue_prev_row)
    net_income, net_income_prev = val(net_income_row), val(net_income_prev_row)
    operating_income = val(operating_income_row)
    gross_profit = val(gross_profit_row)
    op_cf = val(op_cf_row)
    capex = val(capex_row)
    assets, liabilities, equity = val(assets_row), val(liabilities_row), val(equity_row)
    fcf = op_cf - capex if op_cf is not None and capex is not None else None
    market_cap = quote.get("marketCap")

    latest_revenue = val(latest_revenue_row)
    latest_revenue_prev = val(latest_revenue_prev_row)
    latest_net_income = val(latest_net_income_row)
    latest_operating_income = val(latest_operating_income_row)
    latest_gross_profit = val(latest_gross_profit_row)
    latest_op_cf = val(latest_op_cf_row)
    latest_capex = val(latest_capex_row)
    latest_fcf = latest_op_cf - latest_capex if latest_op_cf is not None and latest_capex is not None else None

    def pct(n, d): r = safe_ratio(n, d); return r * 100 if r is not None else None

    base["financials"] = {
        "revenue": revenue, "revenueText": fmt(revenue),
        "revenueGrowthPct": growth(revenue, revenue_prev),
        "netIncome": net_income, "netIncomeText": fmt(net_income),
        "netIncomeGrowthPct": growth(net_income, net_income_prev),
        "grossMarginPct": pct(gross_profit, revenue),
        "operatingMarginPct": pct(operating_income, revenue),
        "freeCashFlow": fcf, "freeCashFlowText": fmt(fcf),
        "debtToAssetsPct": pct(liabilities, assets),
        "roePct": pct(net_income, equity),
        "priceToSales": safe_ratio(market_cap, revenue),
        "fcfYieldPct": pct(fcf, market_cap),
        "trailingPE": quote.get("trailingPE"),
        "forwardPE": quote.get("forwardPE"),
        "latest": {
            "revenue": latest_revenue, "revenueText": fmt(latest_revenue),
            "revenueGrowthPct": growth(latest_revenue, latest_revenue_prev),
            "netIncome": latest_net_income, "netIncomeText": fmt(latest_net_income),
            "grossMarginPct": pct(latest_gross_profit, latest_revenue),
            "operatingMarginPct": pct(latest_operating_income, latest_revenue),
            "freeCashFlow": latest_fcf, "freeCashFlowText": fmt(latest_fcf),
            "period": {
                "basis": "最新财报季度",
                "form": latest_revenue_row.get("form") if latest_revenue_row else None,
                "fiscalYear": latest_revenue_row.get("fy") if latest_revenue_row else None,
                "period": latest_revenue_row.get("fp") if latest_revenue_row else None,
                "start": latest_revenue_row.get("start") if latest_revenue_row else None,
                "end": latest_revenue_row.get("end") if latest_revenue_row else None,
                "filed": latest_revenue_row.get("filed") if latest_revenue_row else None,
                "source": "SEC companyfacts",
            },
        },
        "period": {
            "basis": "最近完整财年",
            "form": revenue_row.get("form") if revenue_row else None,
            "fiscalYear": revenue_row.get("fy") if revenue_row else None,
            "period": revenue_row.get("fp") if revenue_row else None,
            "start": revenue_row.get("start") if revenue_row else None,
            "end": revenue_row.get("end") if revenue_row else None,
            "filed": revenue_row.get("filed") if revenue_row else None,
            "source": "SEC companyfacts",
        },
    }
    return base


def etf_financials(item: dict, latest_data: dict) -> dict:
    """Extract basic ETF info. No qualitative analysis."""
    symbol = item["symbol"]
    security = latest_data.get("securities", {}).get(symbol, {})
    return {
        "symbol": symbol,
        "type": "ETF",
        "companyName": ETF_NOTES.get(symbol, item.get("theme", symbol)),
        "financials": {
            "period": {"basis": "价格与表现为最近交易数据", "source": "行情 chart 数据 + 本地配置"},
            "expenseRatioPct": item.get("expenseRatio"),
            "return1mPct": security.get("metrics", {}).get("return1mPct"),
            "return3mPct": security.get("metrics", {}).get("return3mPct"),
            "return1yPct": security.get("metrics", {}).get("return1yPct"),
            "volatilityPct": security.get("metrics", {}).get("volatilityPct"),
            "maxDrawdownPct": security.get("metrics", {}).get("maxDrawdownPct"),
        },
    }


def main() -> int:
    import time
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG_PATH)
    latest_path = DATA_DIR / "latest.json"
    latest_data = load_json(latest_path) if latest_path.exists() else {"securities": {}}

    ticker_map = STATIC_CIKS.copy()
    try:
        live = sec_ticker_map()
        ticker_map.update(live)
    except Exception:
        pass

    research = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "generatedAtLocal": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S CST"),
        "sources": {
            "secCompanyFacts": "https://www.sec.gov/edgar/sec-api-documentation",
            "notes": "Financials from SEC EDGAR. Qualitative analysis in agent-insights.json.",
        },
        "items": {},
    }
    for item in config.get("tickers", []):
        symbol = item["symbol"].upper()
        if item.get("type") == "ETF":
            research["items"][symbol] = etf_financials(item, latest_data)
        else:
            research["items"][symbol] = stock_financials(symbol, ticker_map.get(symbol), latest_data)
        time.sleep(0.3)  # SEC rate limit

    # Merge agent insights if available
    insights_path = DATA_DIR / "agent-insights.json"
    if insights_path.exists():
        try:
            insights = load_json(insights_path)
            for symbol, insight in insights.get("items", {}).items():
                if symbol in research["items"]:
                    # Agent fields override, but financials from SEC are preserved
                    for key in ("businessModel", "moatEvidence", "keyRisks", "aiAngle",
                                "growthCatalysts", "growthSignals", "judgment"):
                        if key in insight:
                            research["items"][symbol][key] = insight[key]
            research["agentInsightsDate"] = insights.get("generatedAt")
        except Exception as exc:
            print(f"Warning: could not merge agent insights: {exc}")

    write_json(DATA_DIR / "company_research.json", research)
    print(f"Updated research for {len(research['items'])} tickers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
