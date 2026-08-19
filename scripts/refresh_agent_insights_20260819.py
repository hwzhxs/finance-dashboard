#!/usr/bin/env python3
import json
from pathlib import Path

base = Path(__file__).resolve().parents[1]
path = base / "data" / "agent-insights.json"
data = json.loads(path.read_text())
data["generatedAt"] = "2026-08-19T20:30:00+08:00"
items = data["items"]

notes = {
    "SPY": "10Y Treasury yield 约 4.69%、30Y 一度触及 5.33%，高利率与油价共同压制 growth multiple；半导体同步去风险说明指数集中度风险正在兑现。SPY 长持成本仍输 VOO，Continue observing。",
    "QQQ": "半导体板块继续去风险：NVDA -2.34%、AMD -4.27%、AVGO -3.17%、TSM -4.07%、ASML -4.26%。这更像高 yield 下的 factor de-rating，而非 AI demand 已断，但 QQQ 的底层相关性再次暴露，只适合作 satellite。",
    "VOO": "10Y yield 约 4.69% 与科技/半导体回撤提醒高位估值没有免费午餐；VOO 仍是低费率 core，但今天没有值得追价的安全边际，按 IPS 分批而非一次性建仓。",
    "VTI": "高长债收益率压制大盘 growth，中小盘又更敏感于融资成本；VTI 仍是 watchlist 最干净的默认 core，但 80% 现金应绑定分批规则，不因单日 -0.81% 就重仓。",
    "SGOV": "10Y/30Y yields 处于多年高位，SGOV 的短久期现金管理价值上升；但它只保存 dry powder，不解决 80% 现金的长期机会成本，必须预设转入 VTI/VOO 的触发条件。",
    "PDD": "公司确认 8/24 盘前发布 Q2 2026：市场约看 EPS $2.73、revenue $16.99B。现价 $87.27、今日 +0.38%，但 Q1 EPS $1.38 明显低于 $2.40 预期，且 20% 持仓已达 IPS 单股软上限；财报前 Continue observing / 不加仓。",
    "AAPL": "Redburn 8/17 据报将 AAPL 从 Hold 升至 Buy、PT $400，逻辑包含折叠 iPhone 与 AI 改善；这仍是 sell-side/产品预期，不是新增 FCF。今日 +1.45%，Q4 +9-11% 弱指引、GM 47-48% 与中国压力未被解决，Not attractive for now。",
    "MSFT": "AI 部门 CMO Andrea Mallard 离职与 Copilot 账户体验调整属组织/产品层消息，未改变 Azure 变现 thesis。现价 $481.63；真正 gate 仍是 Azure ~45% cc、Copilot paid seats，以及单季 capex >$50B 后的 FCF，Continue observing。",
    "NVDA": "今日 -2.34% 至 $219.74，主要随高 yield 与半导体去风险；另有报道开始向 ByteDance/Tencent 交付 H200，若后续由公司/客户确认将改善中国收入能见度。8/26 财报前仍以 Data Center growth、GM、中国口径与 Rubin ramp 为准，不追 headline。",
    "TSLA": "今日 -0.72%，未见足以修复 Q2 EPS miss、1.4% operating margin、负 FCF 与 2026 capex >$25B 的硬数据。Robotaxi 进展仍远未转成可验证利润，维持 Not attractive for now。",
    "GOOGL": "今日基本持平；Spirit 数据采购、Chrome 团队吸纳创业公司员工属于能力补强，未形成可量化 revenue。$195-205B capex、季度负 FCF 与 AI lab 客户集中度仍是核心反方，Continue observing。",
    "AMD": "今日 -4.27% 至 $484.39，市场继续用更高门槛审视 MI450/Helios：Q2 Data Center +107% 已很强，但价格要求 rack-scale 交付、ROCm adoption 与 GM 连续兑现。高 yield 下 1 年大涨后的 multiple 更脆，维持 Not attractive for now。",
    "AVGO": "今日 -3.17% 至 $380，连同半导体板块回撤，更像高 yield 下的拥挤交易降杠杆；未见足以改变 custom silicon 长期 thesis 的新增运营数据。9/4 财报前仍看 AI semiconductor revenue、客户集中度与 VMware FCF，Not attractive for now。",
    "TSM": "今日 -4.07% 至 $413.41；高 yield 与半导体 de-risking 主导价格，CoWoS 需求溢出至其他供应商的报道反而说明封装瓶颈仍紧。好生意没有变便宜到足够覆盖台海、海外 fab 折旧与 Q3 GM 65-67% 风险，Continue observing。",
    "ASML": "今日 -4.26%；市场报道 TSMC 可能把 High-NA EUV 大规模采用推迟至 2029，这是需要认真跟踪的近端订单/收入时点风险，而非 EUV moat 消失。若确认，当前高估值应下调短期增长预期，维持 Not attractive for now。",
    "AMZN": "扩张 Prime Air、目标年底覆盖近 500 个美国城市，是物流 moat 的长期增量，但对当前利润贡献尚不可量化。现价 $259.45，AWS 强增长已被充分定价，$220B capex 与 2026 FCF 转负仍压安全边际，Not attractive for now。",
    "ORCL": "有报道指约 $165B 新墨西哥 AI data-center 扩建因能源/管线受阻而延迟；这直接强化 RPO 转收入时点、融资成本与 power availability 风险。即使 OCI 增速强，$638B RPO 只有约 12% 一年内确认，维持 Not attractive for now。",
    "PLTR": "第二场 Sovereignty Bootcamp 据报吸引近 100 家新组织，需求信号偏正；但它只是 pipeline，不是 booked ARR/FCF。1 个月 +27.2%、当前估值仍要求 U.S. Commercial 149% 增速长期维持，Not attractive for now。",
    "NOW": "今日 +1.52%、1 个月 +14.1%，但未见新的公司级硬数据；反弹不能替代 subscription growth、RPO、AI upsell 与 margin 的季度验证。企业软件预算向 AI infrastructure 倾斜仍是反方，Not attractive for now。",
    "CRM": "今日 +2.71%，市场提前交易 8/26 财报；共识约 EPS $3.27、revenue $11.33B。Agentforce ARR ~$1B、AI + Data ARR ~$3.4B 是正面，但必须证明能拉动 organic growth 而非只做叙事，财报前 Not attractive for now。"
}

for symbol, note in notes.items():
    items[symbol]["judgment"]["todayNote"] = note

required = ["businessModel", "moatEvidence", "keyRisks", "aiAngle", "growthCatalysts", "growthSignals", "judgment"]
judgment_required = ["positives", "concerns", "actionContext", "todayNote", "etfQuestion"]
expected = {"SPY", "QQQ", "VOO", "VTI", "SGOV", "PDD", "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMD", "AVGO", "TSM", "ASML", "AMZN", "ORCL", "PLTR", "NOW", "CRM"}
assert set(items) == expected, (set(items) - expected, expected - set(items))
for symbol, item in items.items():
    missing = [k for k in required if k not in item]
    assert not missing, (symbol, missing)
    j = item["judgment"]
    missing_j = [k for k in judgment_required if k not in j]
    assert not missing_j, (symbol, missing_j)
    assert len(j["positives"]) >= 2 and len(j["concerns"]) >= 2
    assert j["actionContext"] in {"Consider adding to watchlist", "Consider small position", "Continue observing", "Not attractive for now", "Consider trimming or avoiding"}

path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"updated {path} with {len(items)} items")
