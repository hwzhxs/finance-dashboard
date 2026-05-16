#!/usr/bin/env python3
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


PROFILE_NOTES = {
    "AAPL": {
        "businessModel": "高端消费电子、服务订阅、应用生态、支付和设备生态协同。",
        "moatEvidence": "品牌、庞大装机量、生态转换成本、渠道和服务 attach 能力。",
        "keyRisks": "硬件换机周期、中国市场暴露、反垄断/App Store 监管、增长放缓。",
        "aiAngle": "端侧 AI 和生态分发能力很强，但 AI 变现仍需要更多证据。",
        "growthCatalysts": "端侧 AI 功能、服务收入增长、生态订阅、回购、iPhone 换机周期改善。",
        "growthSignals": "服务收入增速、毛利率、活跃设备数、AI 功能采用率、中国市场恢复情况。",
    },
    "MSFT": {
        "businessModel": "企业软件、Azure 云、生产力订阅、安全、游戏和 AI 平台。",
        "moatEvidence": "企业转换成本、开发者生态、云规模、Office/Teams 等套件绑定。",
        "keyRisks": "估值、云竞争、AI 资本开支回报、监管。",
        "aiAngle": "通过 Azure、Copilot 和企业分发，同时覆盖 AI 基础设施和应用层。",
        "growthCatalysts": "Azure AI 需求、Copilot 商业化、企业软件提价、安全和数据产品扩张。",
        "growthSignals": "Azure 增速、AI 贡献比例、商业云毛利率、Copilot 付费渗透率、资本开支回报。",
    },
    "NVDA": {
        "businessModel": "GPU 加速器、网络、系统和面向 AI/加速计算的软件生态。",
        "moatEvidence": "CUDA 生态、性能领先、供应链规模、开发者和客户黏性。",
        "keyRisks": "市场预期高、半导体周期、自研芯片竞争、出口限制。",
        "aiAngle": "最直接的 AI 算力龙头，上行空间大，但估值和周期纪律很重要。",
        "growthCatalysts": "新一代 GPU 平台、数据中心资本开支、网络产品、软件生态、推理需求增长。",
        "growthSignals": "数据中心收入、订单能见度、毛利率、客户集中度、云厂商资本开支、库存变化。",
    },
    "TSLA": {
        "businessModel": "电动车、储能、软件/自动驾驶可选项和充电生态。",
        "moatEvidence": "品牌、制造规模、充电网络、数据和自动驾驶可选项。",
        "keyRisks": "电动车竞争、利润率压力、估值、执行风险、关键人物风险。",
        "aiAngle": "自动驾驶/机器人叙事强，但需要把已验证业务和远期可选项分开看。",
        "growthCatalysts": "自动驾驶进展、Robotaxi、储能业务增长、低价车型、软件订阅。",
        "growthSignals": "汽车毛利率、交付量、储能收入、FSD 采用率、价格战变化、监管批准。",
    },
    "GOOGL": {
        "businessModel": "搜索广告、YouTube 广告/订阅、Google Cloud、Android 和 AI 产品。",
        "moatEvidence": "搜索分发、数据、规模、YouTube 网络、云和 AI 人才。",
        "keyRisks": "AI 改变搜索行为、反垄断、广告周期、资本开支强度。",
        "aiAngle": "Gemini、搜索 AI、云端 AI 基础设施；AI 既是机会也是颠覆风险。",
        "growthCatalysts": "AI 搜索体验、Google Cloud 增长、YouTube 变现、Gemini 生态、广告恢复。",
        "growthSignals": "搜索份额、广告增长、云利润率、AI 产品采用率、反垄断进展。",
    },
    "PDD": {
        "businessModel": "中国折扣电商和通过 Temu 扩张的全球跨境平台。",
        "moatEvidence": "执行速度、性价比定位、商家网络、流量效率。",
        "keyRisks": "中概/ADR 风险、监管、地缘压力、Temu 可持续性、披露可信度。",
        "aiAngle": "不是核心 AI 股票，更适合作为电商/平台型公司的学习案例。",
        "growthCatalysts": "Temu 海外扩张、国内消费恢复、商家生态效率、广告变现、供应链优化。",
        "growthSignals": "Temu 增速和亏损、国内 GMV、利润率、获客成本、监管/关税变化。",
    },
    "AMD": {
        "businessModel": "CPU、GPU、数据中心芯片和 AI 加速器。",
        "moatEvidence": "x86 生态、数据中心客户关系、产品迭代能力和与台积电供应链协同。",
        "keyRisks": "AI GPU 竞争、毛利率压力、半导体周期、与 NVDA 的生态差距。",
        "aiAngle": "AI 加速器追赶者，适合和 NVDA/AVGO/TSM 对比。",
        "growthCatalysts": "MI 系列 AI 加速器放量、数据中心 CPU/GPU 份额提升、客户多元化。",
        "growthSignals": "AI GPU 收入、数据中心毛利率、客户订单、与 NVDA 的软件生态差距。",
    },
    "AVGO": {
        "businessModel": "网络芯片、定制 ASIC、基础设施软件和企业技术资产。",
        "moatEvidence": "高端网络/定制芯片客户关系、规模、并购整合和软件现金流。",
        "keyRisks": "客户集中、并购整合、半导体周期、估值预期。",
        "aiAngle": "AI 数据中心网络和定制芯片受益者。",
        "growthCatalysts": "AI 网络芯片、定制 ASIC、VMware 整合、基础设施软件现金流。",
        "growthSignals": "AI 相关收入、定制芯片客户数量、软件利润率、并购协同进展。",
    },
    "TSM": {
        "businessModel": "全球领先晶圆代工，为 AI、手机、HPC 等芯片提供制造能力。",
        "moatEvidence": "先进制程、规模、客户信任、资本开支壁垒和制造良率。",
        "keyRisks": "地缘政治、台海风险、资本开支周期、客户集中。",
        "aiAngle": "AI 芯片供应链核心制造环节。",
        "growthCatalysts": "先进制程需求、AI/HPC 芯片订单、先进封装、价格和产能利用率。",
        "growthSignals": "先进制程收入占比、资本开支、毛利率、客户集中、地缘风险变化。",
    },
    "ASML": {
        "businessModel": "半导体光刻设备，尤其是 EUV/High-NA 关键设备。",
        "moatEvidence": "技术垄断、客户锁定、极高研发和供应链壁垒。",
        "keyRisks": "出口限制、半导体资本开支周期、订单波动、估值。",
        "aiAngle": "先进 AI 芯片制造上游关键设备。",
        "growthCatalysts": "EUV/High-NA 需求、先进制程扩产、订单恢复、出口限制边际变化。",
        "growthSignals": "订单 backlog、新订单、毛利率、客户资本开支、出口政策。",
    },
    "AMZN": {
        "businessModel": "电商、AWS 云、广告、物流和订阅生态。",
        "moatEvidence": "规模、物流网络、AWS 客户黏性、Prime 生态和广告数据。",
        "keyRisks": "零售利润率、云竞争、监管、资本开支和执行复杂度。",
        "aiAngle": "AWS 是 AI 基础设施和企业 AI 服务重要平台。",
        "growthCatalysts": "AWS AI 需求、广告业务增长、零售利润率改善、物流效率、订阅生态。",
        "growthSignals": "AWS 增速和利润率、广告收入、零售经营利润率、资本开支回报。",
    },
    "ORCL": {
        "businessModel": "数据库、企业软件、云基础设施和 AI 云服务。",
        "moatEvidence": "数据库客户黏性、企业关键系统、高转换成本。",
        "keyRisks": "云竞争、负债/资本开支、AI 云增长可持续性。",
        "aiAngle": "AI 云基础设施受益者，但需要验证增长质量。",
        "growthCatalysts": "AI 云订单、数据库上云、企业客户迁移、GPU 云资源需求。",
        "growthSignals": "云收入增速、剩余履约义务、资本开支、债务压力、毛利率。",
    },
    "PLTR": {
        "businessModel": "政府和企业数据平台、AI 操作系统和分析软件。",
        "moatEvidence": "高切换成本、政府客户关系、复杂数据集成能力。",
        "keyRisks": "估值高、商业化节奏、客户集中、叙事高于财务兑现。",
        "aiAngle": "AI 应用软件代表之一，重点看收入和利润是否兑现。",
        "growthCatalysts": "AIP 商业化、政府与企业客户扩张、AI 应用落地、利润率提升。",
        "growthSignals": "商业客户数、RPO、营收增长、经营利润率、估值与增长匹配。",
    },
    "NOW": {
        "businessModel": "企业工作流平台、IT 服务管理和 AI 工作流自动化。",
        "moatEvidence": "企业流程嵌入、高续约率、平台扩展能力。",
        "keyRisks": "估值、企业 IT 开支周期、AI 功能变现。",
        "aiAngle": "AI 嵌入企业工作流，偏应用层效率提升。",
        "growthCatalysts": "AI 工作流产品、企业续约扩张、平台模块渗透、IT 自动化需求。",
        "growthSignals": "订阅收入增长、净留存率、RPO、经营利润率、AI 产品采用。",
    },
    "CRM": {
        "businessModel": "CRM、销售/服务/营销云、数据云和企业 AI。",
        "moatEvidence": "客户关系管理生态、企业数据、应用套件和切换成本。",
        "keyRisks": "增长放缓、竞争、并购整合、AI 产品变现。",
        "aiAngle": "企业 AI CRM 和数据云方向，重点看增长重新加速证据。",
        "growthCatalysts": "AI CRM、数据云、利润率改善、客户扩展和回购。",
        "growthSignals": "CRPO、订阅收入增长、数据云采用率、经营利润率、客户预算变化。",
    },
}

ETF_NOTES = {
    "SPY": "规模大、流动性强的 S&P 500 ETF，适合作为美股大盘基准，但费率高于 VOO。",
    "VOO": "低费率 S&P 500 ETF，适合作为美股大盘核心仓候选。",
    "VTI": "低费率全美股票市场 ETF，比 S&P 500 覆盖更广，适合作为核心仓候选。",
    "QQQ": "纳斯达克 100 ETF，科技/成长暴露更高，同时集中度和波动也更高。",
    "SGOV": "短期美国国债 ETF，适合美元现金管理，不是长期权益复利资产。",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def http_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": SEC_UA, "Accept-Encoding": "identity"})
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def sec_ticker_map() -> dict[str, dict]:
    try:
        data = http_json("https://www.sec.gov/files/company_tickers.json")
    except Exception:
        return dict(STATIC_CIKS)
    mapping = {}
    for row in data.values():
        mapping[row["ticker"].upper()] = row
    mapping.update({ticker: value for ticker, value in STATIC_CIKS.items() if ticker not in mapping})
    return mapping


def company_facts(cik: int) -> dict:
    return http_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")


def fact_series(facts: dict, concept_names: list[str]) -> list[dict]:
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    candidates = []
    for concept in concept_names:
        node = us_gaap.get(concept)
        if not node:
            continue
        units = node.get("units", {})
        values = units.get("USD") or units.get("shares") or []
        rows = []
        for item in values:
            form = item.get("form")
            fp = item.get("fp")
            if form not in {"10-K", "10-Q", "20-F", "40-F"}:
                continue
            if item.get("val") is None or not item.get("end"):
                continue
            rows.append({
                "start": item.get("start"),
                "end": item.get("end"),
                "fy": item.get("fy"),
                "fp": fp,
                "form": form,
                "val": float(item.get("val")),
                "filed": item.get("filed"),
            })
        rows.sort(key=lambda row: (row["end"], row.get("filed") or ""))
        if rows:
            candidates.append(rows)
    if not candidates:
        return []
    candidates.sort(key=lambda rows: (rows[-1]["end"], len(rows)), reverse=True)
    return candidates[0]


def latest_annual(series: list[dict]) -> tuple[float | None, float | None]:
    annual = []
    for row in series:
        if row.get("fp") != "FY" and row.get("form") not in {"10-K", "20-F", "40-F"}:
            continue
        if row.get("start"):
            try:
                start = datetime.fromisoformat(row["start"])
                end = datetime.fromisoformat(row["end"])
                if (end - start).days < 300:
                    continue
            except Exception:
                pass
        annual.append(row)
    annual.sort(key=lambda row: (row["end"], row.get("filed") or ""))
    if not annual:
        return None, None
    latest = annual[-1]["val"]
    previous = annual[-2]["val"] if len(annual) >= 2 else None
    return latest, previous


def latest_annual_row(series: list[dict]) -> tuple[dict | None, dict | None]:
    annual = []
    for row in series:
        if row.get("fp") != "FY" and row.get("form") not in {"10-K", "20-F", "40-F"}:
            continue
        if row.get("start"):
            try:
                start = datetime.fromisoformat(row["start"])
                end = datetime.fromisoformat(row["end"])
                if (end - start).days < 300:
                    continue
            except Exception:
                pass
        annual.append(row)
    annual.sort(key=lambda row: (row["end"], row.get("filed") or ""))
    if not annual:
        return None, None
    return annual[-1], annual[-2] if len(annual) >= 2 else None


def latest_period_row(series: list[dict]) -> tuple[dict | None, dict | None]:
    rows = []
    for row in series:
        if row.get("form") not in {"10-Q", "10-K", "20-F", "40-F"}:
            continue
        if row.get("start"):
            try:
                start = datetime.fromisoformat(row["start"])
                end = datetime.fromisoformat(row["end"])
                days = (end - start).days
                if days < 55 or days > 120:
                    continue
            except Exception:
                pass
        rows.append(row)
    rows.sort(key=lambda row: (row["end"], row.get("filed") or ""))
    if not rows:
        return None, None
    latest = rows[-1]
    previous = None
    for candidate in reversed(rows[:-1]):
        if candidate.get("fp") == latest.get("fp") and candidate.get("fy") == (latest.get("fy") or 0) - 1:
            previous = candidate
            break
    return latest, previous


def safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def growth(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def fmt(value: float | None, suffix: str = "") -> str:
    if value is None or math.isnan(value):
        return "n/a"
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B{suffix}"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M{suffix}"
    return f"{value:.1f}{suffix}"


def stock_research(symbol: str, ticker_info: dict | None, latest_data: dict) -> dict:
    notes = PROFILE_NOTES.get(symbol, {})
    quote = latest_data.get("securities", {}).get(symbol, {}).get("quote", {})
    base = {
        "symbol": symbol,
        "type": "Stock",
        "companyName": quote.get("longName") or quote.get("shortName") or symbol,
        "businessModel": notes.get("businessModel", "需要补充生意模式研究。"),
        "moatEvidence": notes.get("moatEvidence", "需要补充护城河研究。"),
        "keyRisks": notes.get("keyRisks", "需要补充风险研究。"),
        "aiAngle": notes.get("aiAngle", "暂无 AI 相关投资假设。"),
        "growthCatalysts": notes.get("growthCatalysts", "需要补充未来增长催化剂。"),
        "growthSignals": notes.get("growthSignals", "需要补充可跟踪增长信号。"),
        "sec": {"available": False},
        "financials": {},
        "judgment": {},
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

    revenue_series = fact_series(facts, [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    ])
    revenue_row, revenue_prev_row = latest_annual_row(revenue_series)
    latest_revenue_row, latest_revenue_prev_row = latest_period_row(revenue_series)
    net_income_row, net_income_prev_row = latest_annual_row(fact_series(facts, ["NetIncomeLoss", "ProfitLoss"]))
    latest_net_income_row, latest_net_income_prev_row = latest_period_row(fact_series(facts, ["NetIncomeLoss", "ProfitLoss"]))
    operating_income_row, _ = latest_annual_row(fact_series(facts, ["OperatingIncomeLoss"]))
    latest_operating_income_row, _ = latest_period_row(fact_series(facts, ["OperatingIncomeLoss"]))
    gross_profit_row, _ = latest_annual_row(fact_series(facts, ["GrossProfit"]))
    latest_gross_profit_row, _ = latest_period_row(fact_series(facts, ["GrossProfit"]))
    op_cf_row, op_cf_prev_row = latest_annual_row(fact_series(facts, ["NetCashProvidedByUsedInOperatingActivities"]))
    latest_op_cf_row, latest_op_cf_prev_row = latest_period_row(fact_series(facts, ["NetCashProvidedByUsedInOperatingActivities"]))
    capex_row, _ = latest_annual_row(fact_series(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"]))
    latest_capex_row, _ = latest_period_row(fact_series(facts, ["PaymentsToAcquirePropertyPlantAndEquipment"]))
    assets_row, _ = latest_annual_row(fact_series(facts, ["Assets"]))
    liabilities_row, _ = latest_annual_row(fact_series(facts, ["Liabilities"]))
    equity_row, _ = latest_annual_row(fact_series(facts, ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]))
    revenue = revenue_row["val"] if revenue_row else None
    revenue_prev = revenue_prev_row["val"] if revenue_prev_row else None
    net_income = net_income_row["val"] if net_income_row else None
    net_income_prev = net_income_prev_row["val"] if net_income_prev_row else None
    operating_income = operating_income_row["val"] if operating_income_row else None
    gross_profit = gross_profit_row["val"] if gross_profit_row else None
    op_cf = op_cf_row["val"] if op_cf_row else None
    op_cf_prev = op_cf_prev_row["val"] if op_cf_prev_row else None
    capex = capex_row["val"] if capex_row else None
    assets = assets_row["val"] if assets_row else None
    liabilities = liabilities_row["val"] if liabilities_row else None
    equity = equity_row["val"] if equity_row else None
    fcf = op_cf - capex if op_cf is not None and capex is not None else None
    latest_revenue = latest_revenue_row["val"] if latest_revenue_row else None
    latest_revenue_prev = latest_revenue_prev_row["val"] if latest_revenue_prev_row else None
    latest_net_income = latest_net_income_row["val"] if latest_net_income_row else None
    latest_net_income_prev = latest_net_income_prev_row["val"] if latest_net_income_prev_row else None
    latest_operating_income = latest_operating_income_row["val"] if latest_operating_income_row else None
    latest_gross_profit = latest_gross_profit_row["val"] if latest_gross_profit_row else None
    latest_op_cf = latest_op_cf_row["val"] if latest_op_cf_row else None
    latest_op_cf_prev = latest_op_cf_prev_row["val"] if latest_op_cf_prev_row else None
    latest_capex = latest_capex_row["val"] if latest_capex_row else None
    latest_fcf = latest_op_cf - latest_capex if latest_op_cf is not None and latest_capex is not None else None
    market_cap = quote.get("marketCap")
    price_to_sales = safe_ratio(market_cap, revenue)
    fcf_yield = safe_ratio(fcf, market_cap)
    base["financials"] = {
        "revenue": revenue,
        "revenueText": fmt(revenue),
        "revenueGrowthPct": growth(revenue, revenue_prev),
        "netIncome": net_income,
        "netIncomeText": fmt(net_income),
        "netIncomeGrowthPct": growth(net_income, net_income_prev),
        "grossMarginPct": safe_ratio(gross_profit, revenue) * 100 if safe_ratio(gross_profit, revenue) is not None else None,
        "operatingMarginPct": safe_ratio(operating_income, revenue) * 100 if safe_ratio(operating_income, revenue) is not None else None,
        "freeCashFlow": fcf,
        "freeCashFlowText": fmt(fcf),
        "freeCashFlowGrowthPct": growth(op_cf, op_cf_prev),
        "debtToAssetsPct": safe_ratio(liabilities, assets) * 100 if safe_ratio(liabilities, assets) is not None else None,
        "roePct": safe_ratio(net_income, equity) * 100 if safe_ratio(net_income, equity) is not None else None,
        "priceToSales": price_to_sales,
        "fcfYieldPct": fcf_yield * 100 if fcf_yield is not None else None,
        "trailingPE": quote.get("trailingPE"),
        "forwardPE": quote.get("forwardPE"),
        "latest": {
            "revenue": latest_revenue,
            "revenueText": fmt(latest_revenue),
            "revenueGrowthPct": growth(latest_revenue, latest_revenue_prev),
            "netIncome": latest_net_income,
            "netIncomeText": fmt(latest_net_income),
            "netIncomeGrowthPct": growth(latest_net_income, latest_net_income_prev),
            "grossMarginPct": safe_ratio(latest_gross_profit, latest_revenue) * 100 if safe_ratio(latest_gross_profit, latest_revenue) is not None else None,
            "operatingMarginPct": safe_ratio(latest_operating_income, latest_revenue) * 100 if safe_ratio(latest_operating_income, latest_revenue) is not None else None,
            "freeCashFlow": latest_fcf,
            "freeCashFlowText": fmt(latest_fcf),
            "freeCashFlowGrowthPct": growth(latest_op_cf, latest_op_cf_prev),
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
    base["judgment"] = build_stock_judgment(symbol, base["financials"], latest_data)
    return base


def build_stock_judgment(symbol: str, financials: dict, latest_data: dict) -> dict:
    positives = []
    concerns = []
    if (financials.get("revenueGrowthPct") or 0) > 10:
        positives.append("收入仍有明显增长。")
    elif financials.get("revenueGrowthPct") is not None:
        concerns.append("收入增长偏弱或为负。")
    if (financials.get("operatingMarginPct") or 0) > 20:
        positives.append("经营利润率显示出定价权或规模效应。")
    elif financials.get("operatingMarginPct") is not None:
        concerns.append("经营利润率需要继续观察。")
    if (financials.get("freeCashFlow") or 0) > 0:
        positives.append("业务能产生正自由现金流。")
    else:
        concerns.append("自由现金流偏弱或数据不可用。")
    if (financials.get("fcfYieldPct") or 0) > 3:
        positives.append("自由现金流收益率不算明显过度紧绷。")
    elif financials.get("fcfYieldPct") is not None:
        concerns.append("自由现金流收益率偏低，估值需要更谨慎。")
    score_data = latest_data.get("securities", {}).get(symbol, {}).get("scores", {})
    action = score_data.get("action", {}).get("label", "Continue observing")
    return {
        "positives": positives[:4],
        "concerns": concerns[:4],
        "actionContext": action,
        "etfQuestion": "同样承担风险，为什么它比 VTI/VOO/QQQ 更值得？",
    }


def etf_research(item: dict, latest_data: dict) -> dict:
    symbol = item["symbol"]
    security = latest_data.get("securities", {}).get(symbol, {})
    return {
        "symbol": symbol,
        "type": "ETF",
        "companyName": symbol,
        "businessModel": ETF_NOTES.get(symbol, item.get("theme", "")),
        "moatEvidence": "ETF 的价值取决于低成本、流动性、分散度，以及它在组合里的角色是否清晰。",
        "keyRisks": "根据 ETF 类型不同，主要风险可能是市场回撤、集中度、久期/再投资风险或机会成本。",
        "aiAngle": "主题暴露取决于持仓；QQQ 的科技暴露高于宽基 ETF。",
        "growthCatalysts": "ETF 的增长潜力来自其持仓资产整体盈利增长、估值扩张和资金流入。",
        "growthSignals": "跟踪指数盈利增速、行业权重、资金流入、利率变化和估值分位。",
        "financials": {
            "period": {
                "basis": "价格与表现为最近交易数据；费率为配置文件记录",
                "source": "行情 chart 数据 + 本地 ETF 配置",
            },
            "expenseRatioPct": item.get("expenseRatio"),
            "return1mPct": security.get("metrics", {}).get("return1mPct"),
            "return3mPct": security.get("metrics", {}).get("return3mPct"),
            "return1yPct": security.get("metrics", {}).get("return1yPct"),
            "volatilityPct": security.get("metrics", {}).get("volatilityPct"),
            "maxDrawdownPct": security.get("metrics", {}).get("maxDrawdownPct"),
        },
        "judgment": {
            "positives": ["可以作为基准或资产配置积木。"],
            "concerns": ["需要先明确角色：核心权益、科技倾斜，还是现金管理。"],
            "actionContext": security.get("scores", {}).get("action", {}).get("label", "Continue observing"),
            "etfQuestion": "这个 ETF 在组合里的角色是什么：核心仓、科技倾斜，还是现金管理？",
        },
    }


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG_PATH)
    latest_path = DATA_DIR / "latest.json"
    latest_data = load_json(latest_path) if latest_path.exists() else {"securities": {}}
    try:
        ticker_map = sec_ticker_map()
    except Exception:
        ticker_map = {}
    research = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "generatedAtLocal": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S CST"),
        "sources": {
            "secCompanyFacts": "https://www.sec.gov/edgar/sec-api-documentation",
            "secCompanyTickers": "https://www.sec.gov/files/company_tickers.json",
            "notes": "Business model and risk notes are curated starting assumptions; financial values are refreshed from available public data when possible.",
        },
        "items": {},
    }
    for item in config.get("tickers", []):
        symbol = item["symbol"].upper()
        if item.get("type") == "ETF":
            research["items"][symbol] = etf_research(item, latest_data)
        else:
            research["items"][symbol] = stock_research(symbol, ticker_map.get(symbol), latest_data)
    write_json(DATA_DIR / "company_research.json", research)
    print(f"Updated research matrix for {len(research['items'])} tickers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
