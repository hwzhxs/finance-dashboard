const perspectiveLabels = {
  composite: "综合",
  buffett_munger: "巴菲特",
  bogle: "博格",
  peter_lynch: "林奇",
  howard_marks: "马克斯",
  tech_growth_risk: "科技成长"
};

const perspectiveHelp = {
  composite: "综合视角：平衡估值、质量、风险、动量、AI 暴露和你的学习池适配度。",
  buffett_munger: "巴菲特/芒格：重视看得懂的生意、护城河、现金流、长期确定性和安全边际。",
  bogle: "博格：重视低成本、宽基分散、少决策、少交易，通常更偏向 ETF。",
  peter_lynch: "彼得·林奇：看得懂的成长、真实业务变化、增长与估值是否匹配。",
  howard_marks: "霍华德·马克斯：重视周期、下行风险、市场情绪和避免乐观预期过度透支。",
  tech_growth_risk: "科技成长：关注 AI/云/芯片/软件平台机会，同时用估值和风险约束仓位。"
};

const actionLabels = {
  "Continue observing": "继续观察",
  "Not attractive for now": "暂不具吸引力",
  "Cash management candidate": "现金管理候选",
  "Core candidate": "核心仓候选",
  "Consider small position": "可考虑小仓位"
};

let latest = null;
let scores = null;
let rankings = null;
let research = null;
let config = null;
let expertHoldings = null;
let valuationData = null;
let thesisData = null;
let earningsCalendar = null;
let competitiveData = null;
let secFilingsJSON = null;
let activeView = "stocks";
let activePerspective = "composite";
let activeSymbol = "VTI";
let activeRange = "3M";
let activeExpert = 0;

const assetBase = location.pathname.includes("/dashboard/") ? "../" : "./";

const translateAction = (value) => actionLabels[value] || value || "继续观察";
const fmtNum = (value, digits = 1) => typeof value === "number" ? value.toFixed(digits) : "n/a";
const fmtPrice = (value) => typeof value === "number" ? `$${value.toFixed(2)}` : "n/a";
const fmtPctText = (value, digits = 1) => typeof value === "number" ? `${value > 0 ? "+" : ""}${value.toFixed(digits)}%` : "n/a";
const pctClass = (value) => typeof value === "number" && value > 0 ? "up" : typeof value === "number" && value < 0 ? "down" : "neutral";

async function loadData() {
  const [latestRes, scoresRes, rankingsRes, researchRes, configRes, expertRes, valuationRes, thesisRes, earningsRes, competitiveRes, secFilingsRes] = await Promise.all([
    fetch(`${assetBase}data/latest.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/scores.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/rankings.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/company_research.json?ts=${Date.now()}`),
    fetch(`${assetBase}config/watchlist.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/expert-holdings.json?ts=${Date.now()}`).catch(() => null),
    fetch(`${assetBase}data/valuation-comps.json?ts=${Date.now()}`).catch(() => null),
    fetch(`${assetBase}data/thesis-tracker.json?ts=${Date.now()}`).catch(() => null),
    fetch(`${assetBase}data/earnings-calendar.json?ts=${Date.now()}`).catch(() => null),
    fetch(`${assetBase}data/competitive-analysis.json?ts=${Date.now()}`).catch(() => null),
    fetch(`${assetBase}data/sec-filings.json?ts=${Date.now()}`).catch(() => null)
  ]);
  latest = await latestRes.json();
  scores = await scoresRes.json();
  rankings = await rankingsRes.json();
  research = await researchRes.json();
  config = await configRes.json();
  if (expertRes && expertRes.ok) expertHoldings = await expertRes.json();
  if (valuationRes && valuationRes.ok) valuationData = await valuationRes.json();
  if (thesisRes && thesisRes.ok) thesisData = await thesisRes.json();
  if (earningsRes && earningsRes.ok) earningsCalendar = await earningsRes.json();
  if (competitiveRes && competitiveRes.ok) competitiveData = await competitiveRes.json();
  if (secFilingsRes && secFilingsRes.ok) secFilingsJSON = await secFilingsRes.json();
  if (!latest.securities[activeSymbol]) activeSymbol = Object.keys(latest.securities)[0];
  render();
}

function render() {
  document.getElementById("updatedAt").textContent = new Date(latest.generatedAt).toLocaleString();
  renderPrimaryTabs();
  renderPerspectiveTabs();
  renderStockList();
  renderStockDetail(activeSymbol);
  renderExperts();
  renderValuation();
  renderThesis();
}

function renderPrimaryTabs() {
  document.querySelectorAll(".primary-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === activeView);
    button.onclick = () => {
      activeView = button.dataset.view;
      document.querySelectorAll(".primary-tab").forEach((item) => item.classList.toggle("active", item.dataset.view === activeView));
      document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `${activeView}View`));
    };
  });
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `${activeView}View`));
}

function renderPerspectiveTabs() {
  const container = document.getElementById("perspectiveTabs");
  container.innerHTML = "";
  Object.entries(perspectiveLabels).forEach(([key, label]) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = label;
    btn.className = key === activePerspective ? "active" : "";
    btn.addEventListener("mouseenter", () => setPerspectiveHelp(key));
    btn.addEventListener("focus", () => setPerspectiveHelp(key));
    btn.addEventListener("mouseleave", () => setPerspectiveHelp(activePerspective));
    btn.addEventListener("click", () => {
      activePerspective = key;
      renderPerspectiveTabs();
      renderStockList();
      renderStockDetail(activeSymbol);
    });
    container.appendChild(btn);
  });
  setPerspectiveHelp(activePerspective);
}

function setPerspectiveHelp(key) {
  document.getElementById("perspectiveHelp").textContent = perspectiveHelp[key] || "";
}

function sortedSecurities() {
  return Object.values(latest.securities).sort((a, b) => {
    const aScore = a.scores.perspectives[activePerspective] ?? 0;
    const bScore = b.scores.perspectives[activePerspective] ?? 0;
    return bScore - aScore;
  }).slice(0, 20);
}

function renderStockList() {
  const container = document.getElementById("stockList");
  container.innerHTML = sortedSecurities().map((item, index) => {
    const score = item.scores.perspectives[activePerspective];
    const day = item.quote.regularMarketChangePercent;
    return `
      <button class="stock-row ${item.symbol === activeSymbol ? "selected" : ""}" data-symbol="${item.symbol}" type="button">
        <span class="rank">${index + 1}</span>
        <span>
          <span class="ticker">${item.symbol}</span>
          <span class="subline">${item.type === "ETF" ? "ETF" : "股票"} · ${fmtPrice(item.quote.regularMarketPrice)} · <span class="${pctClass(day)}">${fmtPctText(day, 2)}</span></span>
          <span class="subline">${translateAction(item.scores.action.label)}</span>
        </span>
        <span class="score-pill">${fmtNum(score, 1)}</span>
      </button>
    `;
  }).join("");
  container.querySelectorAll(".stock-row").forEach((row) => {
    row.addEventListener("click", () => {
      activeSymbol = row.dataset.symbol;
      renderStockList();
      renderStockDetail(activeSymbol);
    });
  });
}

function renderStockDetail(symbol) {
  const item = latest.securities[symbol];
  const researchItem = research.items[symbol] || {};
  if (!item) return;
  document.getElementById("selectedType").textContent = item.type === "ETF" ? "ETF" : "Stock";
  document.getElementById("selectedSymbol").textContent = `${symbol} ${item.quote.longName || item.quote.shortName || ""}`;
  document.getElementById("selectedTheme").textContent = item.theme || researchItem.businessModel || "";
  document.getElementById("selectedPrice").textContent = fmtPrice(item.quote.regularMarketPrice);
  const day = item.quote.regularMarketChangePercent;
  const dayEl = document.getElementById("selectedDay");
  dayEl.textContent = fmtPctText(day, 2);
  dayEl.className = pctClass(day);
  document.getElementById("selectedScore").textContent = `${perspectiveLabels[activePerspective]} ${fmtNum(item.scores.perspectives[activePerspective], 1)}`;
  renderChart(item);
  renderFundamentals(item, researchItem);
  renderJudgments(item, researchItem);
  renderPerspectiveDetail(item, researchItem);
  renderSymbolExpertFootprints(symbol);
  renderStockEarnings(symbol);
  renderStockCompetitive(symbol);
  renderStockCrossAnalysis(symbol);
  renderRangeTabs();
}

function renderRangeTabs() {
  document.querySelectorAll("#rangeTabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.range === activeRange);
    button.onclick = () => {
      activeRange = button.dataset.range;
      renderRangeTabs();
      renderChart(latest.securities[activeSymbol]);
    };
  });
}

let tvChartInstance = null;
let tvSeries = null;

function renderChart(item) {
  const container = document.getElementById("tvChart");
  const history = item.metrics.history || [];
  const rangeCount = { "1M": 22, "3M": 63, "6M": 126, "1Y": 252 }[activeRange] || 63;
  const rows = history.slice(-rangeCount);

  if (rows.length < 2) {
    container.innerHTML = '<div style="padding:40px;color:#999">暂无足够价格数据</div>';
    return;
  }

  const closes = rows.map(r => r.close);
  const startPrice = closes[0];
  const endPrice = closes[closes.length - 1];
  const isUp = endPrice >= startPrice;
  const lineColor = isUp ? "#008a05" : "#222222";
  const topColor = isUp ? "rgba(0,138,5,0.15)" : "rgba(34,34,34,0.1)";
  const bottomColor = isUp ? "rgba(0,138,5,0.02)" : "rgba(34,34,34,0.02)";

  if (tvChartInstance) {
    tvChartInstance.remove();
    tvChartInstance = null;
    tvSeries = null;
  }

  tvChartInstance = LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: 400,
    layout: {
      background: { type: "solid", color: "#fbfcfb" },
      textColor: "#65706b",
      fontFamily: "Inter, system-ui, sans-serif",
      fontSize: 12,
    },
    grid: {
      vertLines: { color: "#f0f2f0" },
      horzLines: { color: "#f0f2f0" },
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Magnet,
      vertLine: {
        color: lineColor,
        width: 1,
        style: LightweightCharts.LineStyle.Dashed,
        labelBackgroundColor: lineColor,
      },
      horzLine: {
        color: "#999",
        width: 1,
        style: LightweightCharts.LineStyle.Dashed,
        labelBackgroundColor: "#555",
      },
    },
    rightPriceScale: { borderColor: "#e8ebe9" },
    timeScale: { borderColor: "#e8ebe9", timeVisible: false },
    handleScroll: true,
    handleScale: true,
  });

  tvSeries = tvChartInstance.addSeries(LightweightCharts.AreaSeries, {
    lineColor: lineColor,
    lineWidth: 2,
    topColor: topColor,
    bottomColor: bottomColor,
    crosshairMarkerVisible: true,
    crosshairMarkerRadius: 5,
    crosshairMarkerBorderColor: "#fff",
    crosshairMarkerBorderWidth: 2,
    crosshairMarkerBackgroundColor: lineColor,
    priceFormat: { type: "price", precision: 2, minMove: 0.01 },
  });

  const data = rows.map(r => ({ time: r.date, value: r.close }));
  tvSeries.setData(data);
  tvChartInstance.timeScale().fitContent();

  const ro = new ResizeObserver(() => {
    if (tvChartInstance) tvChartInstance.applyOptions({ width: container.clientWidth });
  });
  ro.observe(container);
}

function renderFundamentals(item, researchItem) {
  const f = researchItem.financials || {};
  const latestFund = f.latest || {};
  const q = item.quote || {};
  const rows = item.type === "ETF" ? [
    ["统计口径", f.period?.basis || "最近交易数据"],
    ["角色", researchItem.businessModel || item.theme],
    ["费率", typeof item.expenseRatio === "number" ? `${item.expenseRatio}%` : "n/a"],
    ["1月表现", fmtPctText(item.metrics.return1mPct)],
    ["3月表现", fmtPctText(item.metrics.return3mPct)],
    ["1年表现", fmtPctText(item.metrics.return1yPct)],
    ["波动率", fmtPctText(item.metrics.volatilityPct)],
    ["最大回撤", fmtPctText(item.metrics.maxDrawdownPct)],
    ["行动建议", translateAction(item.scores.action.label)]
  ] : [
    ["统计口径", formatPeriod(latestFund.period || f.period)],
    ["最新收入", latestFund.revenueText || f.revenueText || "n/a"],
    ["最新收入同比", fmtPctText(latestFund.revenueGrowthPct)],
    ["最新经营利润率", fmtPctText(latestFund.operatingMarginPct)],
    ["最新自由现金流", latestFund.freeCashFlowText || "n/a"],
    ["年度收入", f.revenueText || "n/a"],
    ["年度收入增长", fmtPctText(f.revenueGrowthPct)],
    ["年度经营利润率", fmtPctText(f.operatingMarginPct)],
    ["PE", fmtNum(q.trailingPE, 1)],
    ["Forward PE", fmtNum(q.forwardPE, 1)],
    ["FCF收益率", fmtPctText(f.fcfYieldPct)],
    ["负债/资产", fmtPctText(f.debtToAssetsPct)]
  ];
  document.getElementById("fundamentalGrid").innerHTML = rows.map(([label, value]) => `
    <div class="metric"><span>${label}</span><strong>${value}</strong></div>
  `).join("");
}

function formatPeriod(period) {
  if (!period) return "最近完整财年";
  const parts = [];
  if (period.fiscalYear) parts.push(`FY${period.fiscalYear}${period.period && period.period !== "FY" ? ` ${period.period}` : ""}`);
  if (period.start && period.end) parts.push(`${period.start} 至 ${period.end}`);
  return parts.join(" · ") || period.basis || "最近完整财年";
}

function renderJudgments(item, researchItem) {
  const rows = [
    ["生意模式", researchItem.businessModel || item.theme || "n/a"],
    ["护城河", researchItem.moatEvidence || "n/a"],
    ["主要风险", researchItem.keyRisks || "n/a"],
    ["AI 关系", researchItem.aiAngle || "n/a"],
    ["增长潜力/催化剂", researchItem.growthCatalysts || "n/a"],
    ["需要跟踪的增长信号", researchItem.growthSignals || "n/a"],
    ["ETF 对比问题", researchItem.judgment?.etfQuestion || "它是否比 VTI/VOO/QQQ 更值得承担风险？"],
    ["行动建议", item.scores.action.positionNote || translateAction(item.scores.action.label)]
  ];
  document.getElementById("judgmentGrid").innerHTML = rows.map(([label, value]) => `
    <div class="judgment-card"><span>${label}</span><strong>${value}</strong></div>
  `).join("");
}

function renderPerspectiveDetail(item, researchItem) {
  const components = item.scores.components;
  const notes = item.scores.explanation || [];
  const positives = researchItem.judgment?.positives || [];
  const concerns = researchItem.judgment?.concerns || [];
  document.getElementById("perspectiveDetail").innerHTML = `
    <p><strong>${perspectiveLabels[activePerspective]}</strong> 当前评分：${fmtNum(item.scores.perspectives[activePerspective], 1)}。</p>
    <p>关键分项：估值 ${fmtNum(components.value)}，质量 ${fmtNum(components.quality)}，风险 ${fmtNum(components.risk)}，AI 暴露 ${fmtNum(components.aiExposure)}，个人适配 ${fmtNum(components.personalFit)}。</p>
    <p>支持理由：${[...positives, ...notes].slice(0, 3).join(" ") || "暂无明确支持理由。"}</p>
    <p>主要反方：${concerns.slice(0, 3).join(" ") || researchItem.keyRisks || "暂无明确反方。"}</p>
  `;
}

function expertFootprintsForSymbol(symbol) {
  const experts = config.expertFootprints || [];
  const matches = [];
  experts.forEach((expert) => {
    (expert.actions || []).forEach((action) => {
      if (action.symbol === symbol) {
        matches.push({
          expert: expert.expert,
          style: expert.style,
          lastUpdated: expert.lastUpdated,
          ...action
        });
      }
    });
  });
  return matches;
}

function renderSymbolExpertFootprints(symbol) {
  const container = document.getElementById("symbolExpertFootprints");
  // Try expert-holdings.json first for rich data
  const experts = (expertHoldings && expertHoldings.experts) || [];
  const richMatches = [];
  experts.forEach(expert => {
    (expert.topHoldings || []).forEach(h => {
      if (h.symbol === symbol) {
        richMatches.push({ expert: expert.name, quarter: expert.quarter, totalValue: expert.totalValue, ...h });
      }
    });
  });
  if (richMatches.length) {
    container.innerHTML = richMatches.map(m => {
      const color = changeColors[m.change] || '#8e8e93';
      const label = changeLabels[m.change] || m.change;
      return `
        <div class="symbol-expert-card rich">
          <div class="symbol-expert-header">
            <strong>${m.expert}</strong>
            <span class="expert-badge">${m.quarter}</span>
          </div>
          <div class="symbol-expert-stats">
            <span class="stat">仓位 <strong>${m.pctOfPortfolio ? m.pctOfPortfolio.toFixed(1) + '%' : '—'}</strong></span>
            <span class="stat">变化 <strong style="color:${color}">${label}</strong></span>
            <span class="stat change-date">${e.quarter} · ${e.filingDate}</span>
          </div>
          <p>${m.changeDetail}</p>
          ${m.trendSignal ? `<p class="trend-signal-inline">${m.trendSignal}</p>` : ''}
          ${m.quarterHistory ? `<div class="quarter-trend">${m.quarterHistory.map(q => 
            `<span class="qt-item" title="${q.action}">${q.q}: ${(q.shares/1e6).toFixed(1)}M (${q.pct}%)</span>`
          ).join(' → ')}</div>` : ''}
        </div>
      `;
    }).join('');
    return;
  }
  // Fallback to config expertFootprints
  const matches = expertFootprintsForSymbol(symbol);
  if (!matches.length) {
    container.innerHTML = `
      <div class="symbol-expert-card">
        <strong>暂无相关专家足迹</strong>
        <p>当前专家足迹库里没有和 ${symbol} 直接相关的持仓记录。</p>
      </div>
    `;
    return;
  }
  container.innerHTML = matches.map((match) => `
    <div class="symbol-expert-card">
      <strong>${match.expert}</strong>
      <span>${match.action}</span>
      <span>参考价值：${match.relevance}</span>
      <p>${match.note} ${match.lastUpdated ? `数据说明：${match.lastUpdated}。` : ""}</p>
    </div>
  `).join("");
}

const changeColors = { new: '#222222', increased: '#008a05', reduced: '#c13515', exited: '#c13515', unchanged: '#929292', held: '#929292', new_top10: '#222222' };
const changeLabels = { new: '新建', increased: '加仓', reduced: '减持', exited: '清仓', unchanged: '不变', held: '维持', new_top10: '新进前十' };

function getWatchlistTickers() {
  return (config.tickers || []).map(t => t.symbol);
}

let activeExpertSort = 'default';

const expertSortOptions = {
  default: { label: '默认', fn: null },
  aum_desc: { label: 'AUM ↓', fn: (a, b) => parseAUM(b.totalValue) - parseAUM(a.totalValue) },
  aum_asc: { label: 'AUM ↑', fn: (a, b) => parseAUM(a.totalValue) - parseAUM(b.totalValue) },
  overlap: { label: '重叠多', fn: (a, b, wl) => countOverlap(b, wl) - countOverlap(a, wl) },
  activity: { label: '动作多', fn: (a, b) => countActivity(b) - countActivity(a) },
  name: { label: '名称 A-Z', fn: (a, b) => (a.name || '').localeCompare(b.name || '') }
};

function parseAUM(val) {
  if (!val) return 0;
  const match = val.match(/([\d.]+)\s*([TBM])/i);
  if (!match) return 0;
  let num = parseFloat(match[1]) || 0;
  const unit = match[2].toUpperCase();
  if (unit === 'T') num *= 1000;
  if (unit === 'M') num /= 1000;
  return num; // returns in billions
}

function countOverlap(expert, wl) {
  return (expert.topHoldings || []).filter(h => wl.includes(h.symbol)).length;
}

function countActivity(expert) {
  const all = [...(expert.topHoldings || []), ...(expert.notableMoves || [])];
  return all.filter(h => h.change && h.change !== 'unchanged' && h.change !== 'held').length;
}

function renderExperts() {
  const experts = (expertHoldings && expertHoldings.experts) || [];
  const fallback = config.expertFootprints || [];
  const list = document.getElementById("expertList");
  const source = experts.length ? experts : fallback;
  if (!source.length) return;
  const wlTickers = getWatchlistTickers();

  // Render sort tabs
  const sortTabsEl = document.getElementById('expertSortTabs');
  if (sortTabsEl) {
    sortTabsEl.innerHTML = Object.entries(expertSortOptions).map(([key, opt]) =>
      `<button class="sector-tab ${key === activeExpertSort ? 'active' : ''}" data-sort="${key}" type="button">${opt.label}</button>`
    ).join('');
    sortTabsEl.querySelectorAll('.sector-tab').forEach(btn => {
      btn.onclick = () => { activeExpertSort = btn.dataset.sort; activeExpert = 0; renderExperts(); };
    });
  }

  // Sort
  const indexed = source.map((e, i) => ({ ...e, _origIndex: i }));
  const sortOpt = expertSortOptions[activeExpertSort];
  const sorted = sortOpt && sortOpt.fn ? [...indexed].sort((a, b) => sortOpt.fn(a, b, wlTickers)) : indexed;

  list.innerHTML = sorted.map((expert, index) => {
    const name = expert.name || expert.expert;
    const quarter = expert.quarter || '';
    const totalValue = expert.totalValue || '';
    const overlap = (expert.topHoldings || []).filter(h => wlTickers.includes(h.symbol)).length;
    const activity = countActivity(expert);
    return `
      <button class="expert-row ${index === activeExpert ? "selected" : ""}" data-index="${index}" data-orig="${expert._origIndex}" type="button">
        <span class="ticker">${name}</span>
        <span class="subline">${expert.style}</span>
        <span class="expert-meta">
          ${quarter ? `<span class="expert-badge">${quarter}</span>` : ''}
          ${totalValue ? `<span class="expert-badge">${totalValue}</span>` : ''}
          ${overlap > 0 ? `<span class="expert-badge overlap">${overlap} 只重叠</span>` : ''}
          ${activity > 0 ? `<span class="expert-badge">${activity} 个动作</span>` : ''}
        </span>
      </button>
    `;
  }).join("");
  list.querySelectorAll(".expert-row").forEach((row) => {
    row.addEventListener("click", () => {
      activeExpert = Number(row.dataset.index);
      renderExperts();
    });
  });
  if (sorted.length) {
    renderExpertDetailV2(sorted[activeExpert]);
  } else {
    renderExpertDetail(fallback[activeExpert]);
  }
}

function renderExpertDetail(expert) {
  if (!expert) return;
  document.getElementById("expertName").textContent = expert.expert;
  document.getElementById("expertStyle").textContent = `${expert.style} · ${expert.lastUpdated}`;
  const actions = expert.actions || [];
  document.getElementById("expertActions").innerHTML = actions.map((action) => `
    <div class="expert-action">
      <strong>${action.symbol}</strong>
      <span>${action.action}</span>
      <span>相关性：${action.relevance}</span>
      <p>${action.note}</p>
    </div>
  `).join("") + `
    <div class="expert-action">
      <strong>说明</strong>
      <span>不是抄作业</span>
      <span>13F 延迟</span>
      <p>专家足迹只作为参考信号。真实仓位、成本、对冲和卖出动作可能已经变化。</p>
    </div>
  `;
}

function renderExpertDetailV2(expert) {
  if (!expert) return;
  const wlTickers = getWatchlistTickers();
  document.getElementById("expertName").textContent = expert.name;
  document.getElementById("expertStyle").textContent = `${expert.style} · ${expert.quarter} · Filed ${expert.filingDate} · AUM ${expert.totalValue}`;
  const allHoldings = expert.topHoldings || [];
  const coreHoldings = allHoldings.slice(0, 10);
  const notableMoves = (expert.notableMoves || []).concat(allHoldings.slice(10));
  const makeRow = (h, i) => {
    const color = changeColors[h.change] || '#8e8e93';
    const label = changeLabels[h.change] || h.change;
    const isOverlap = wlTickers.includes(h.symbol);
    const pctDisplay = h.pctOfPortfolio ? h.pctOfPortfolio.toFixed(1) + '%' : '—';
    return `
      <tr class="${isOverlap ? 'overlap-row' : ''}">
        <td>${i + 1}</td>
        <td><strong>${h.symbol}</strong>${isOverlap ? ' <span class="overlap-dot">●</span>' : ''}</td>
        <td>${h.name}</td>
        <td>${pctDisplay}</td>
        <td><span class="change-badge" style="color:${color}">${label}</span></td>
        <td>${h.changeDetail} <span class="change-date">(${expert.quarter}, ${expert.filingDate})</span></td>
      </tr>
    `;
  };
  const coreRows = coreHoldings.map((h, i) => makeRow(h, i)).join('');
  const activeNotable = notableMoves.filter(h => h.change && h.change !== 'unchanged' && h.change !== 'held');
  const notableRows = activeNotable.map((h, i) => makeRow(h, i)).join('');
  document.getElementById("expertActions").innerHTML = `
    <div class="expert-insight">
      <strong>💡 Insight:</strong> ${expert.keyInsight || expert.analystNote || ''}
    </div>
    <table class="holdings-table">
      <thead>
        <tr><th>#</th><th>Ticker</th><th>公司</th><th>仓位</th><th>变化</th><th>详情</th></tr>
      </thead>
      <tbody>${coreRows}</tbody>
    </table>
    ${activeNotable.length ? `
    <div class="notable-moves">
      <h4>📌 其他重要动向</h4>
      <table class="holdings-table notable">
        <thead>
          <tr><th>#</th><th>Ticker</th><th>公司</th><th>仓位</th><th>变化</th><th>详情</th></tr>
        </thead>
        <tbody>${notableRows}</tbody>
      </table>
    </div>` : ''}
    ${(expert.trendSummary && expert.trendSummary.length) ? `
    <div class="trend-summary">
      <h4>📈 趋势信号</h4>
      ${expert.trendSummary.map(s => `<div class="trend-signal">${s}</div>`).join('')}
    </div>` : ''}
    <div class="expert-action disclaimer">
      <strong>⚠️ 说明</strong>
      <p>13F 数据有 45 天延迟，不是抄作业信号。真实仓位、成本、对冲和卖出动作可能已变化。<span class="overlap-dot">●</span> = 你的 watchlist 重叠股。</p>
    </div>
  `;
}

document.getElementById("refreshBtn").addEventListener("click", loadData);

// ===== Valuation Tab =====
let activeSector = 'all';

function renderValuation() {
  if (!valuationData || !valuationData.stocks) return;
  const stocks = valuationData.stocks;
  const sectors = ['all', ...new Set(stocks.map(s => s.sector))];
  const sectorLabels = { all: '全部' };

  // Sector tabs
  const tabsEl = document.getElementById('sectorTabs');
  if (tabsEl) {
    tabsEl.innerHTML = sectors.map(s => 
      `<button class="sector-tab ${s === activeSector ? 'active' : ''}" data-sector="${s}" type="button">${sectorLabels[s] || s}</button>`
    ).join('');
    tabsEl.querySelectorAll('.sector-tab').forEach(btn => {
      btn.onclick = () => { activeSector = btn.dataset.sector; renderValuation(); };
    });
  }

  const filtered = activeSector === 'all' ? stocks : stocks.filter(s => s.sector === activeSector);
  const sorted = [...filtered].sort((a, b) => (a.peg || 999) - (b.peg || 999));

  // Calculate sector medians
  const medians = {};
  sectors.filter(s => s !== 'all').forEach(sector => {
    const group = stocks.filter(s => s.sector === sector);
    const vals = (key) => group.map(s => s[key]).filter(v => v != null).sort((a,b) => a-b);
    const median = (arr) => arr.length ? arr[Math.floor(arr.length/2)] : null;
    medians[sector] = { evRevenue: median(vals('evRevenue')), evEbitda: median(vals('evEbitda')), pe: median(vals('pe')), peg: median(vals('peg')) };
  });

  const valClass = (val, med) => {
    if (val == null || med == null) return 'val-fair';
    const ratio = val / med;
    if (ratio < 0.85) return 'val-cheap';
    if (ratio > 1.15) return 'val-expensive';
    return 'val-fair';
  };

  const tableEl = document.getElementById('valuationTable');
  if (tableEl) {
    tableEl.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>#</th><th>Ticker</th><th>公司</th><th>板块</th>
            <th>营收增速</th><th>毛利率</th><th>EBITDA%</th>
            <th>EV/Rev</th><th>EV/EBITDA</th><th>P/E</th><th>PEG</th>
            <th>Signal</th>
          </tr>
        </thead>
        <tbody>
          ${sorted.map((s, i) => {
            const med = medians[s.sector] || {};
            return `<tr>
              <td>${i+1}</td>
              <td><strong>${s.symbol}</strong></td>
              <td>${s.name}</td>
              <td><span class="moat-tag">${s.sector}</span></td>
              <td class="${s.revenueGrowth > 30 ? 'val-cheap' : s.revenueGrowth < 10 ? 'val-expensive' : ''}">${s.revenueGrowth != null ? s.revenueGrowth.toFixed(1)+'%' : '—'}</td>
              <td>${s.grossMargin != null ? s.grossMargin.toFixed(1)+'%' : '—'}</td>
              <td>${s.ebitdaMargin != null ? s.ebitdaMargin.toFixed(1)+'%' : '—'}</td>
              <td class="${valClass(s.evRevenue, med.evRevenue)}">${s.evRevenue != null ? s.evRevenue.toFixed(1)+'x' : '—'}</td>
              <td class="${valClass(s.evEbitda, med.evEbitda)}">${s.evEbitda != null ? s.evEbitda.toFixed(1)+'x' : '—'}</td>
              <td class="${valClass(s.pe, med.pe)}">${s.pe != null ? s.pe.toFixed(1)+'x' : '—'}</td>
              <td class="${valClass(s.peg, med.peg)}"><strong>${s.peg != null ? s.peg.toFixed(2) : '—'}</strong></td>
              <td>${s.signal || ''}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    `;
  }

  // Insight section
  const insightEl = document.getElementById('valuationInsight');
  if (insightEl && sorted.length) {
    const cheapest = sorted[0];
    const priciest = sorted[sorted.length - 1];
    insightEl.innerHTML = `
      <strong>💡 估值快照</strong><br>
      PEG 最低（最便宜）：<strong>${cheapest.symbol}</strong> (${cheapest.peg != null ? cheapest.peg.toFixed(2) : 'N/A'})
       |  PEG 最高：<strong>${priciest.symbol}</strong> (${priciest.peg != null ? priciest.peg.toFixed(2) : 'N/A'})<br>
      <em>→ PEG < 1 表示增长未被充分定价，> 2 表示可能过贵。绿色=低估，红色=高估（vs 同板块中位数）</em>
    `;
  }
}

// ===== Thesis Tracker Tab =====
const moatLabels = { brand: '品牌', network: '网络效应', switching: '转换成本', scale: '规模经济', cost: '成本优势', intangible: '无形资产' };

// ===== Stock Detail: Earnings Countdown =====
function renderStockEarnings(symbol) {
  const el = document.getElementById('stockEarnings');
  if (!el) return;
  if (!earningsCalendar || !earningsCalendar.earnings) { el.innerHTML = '<p style="color:var(--muted)">暂无财报日历数据</p>'; return; }
  const entry = earningsCalendar.earnings.find(e => e.symbol === symbol);
  if (!entry || !entry.earningsDate) { el.innerHTML = '<p style="color:var(--muted)">暂无财报日期</p>'; return; }
  const today = new Date();
  const eDate = new Date(entry.earningsDate + 'T16:00:00');
  const diffDays = Math.ceil((eDate - today) / (1000 * 60 * 60 * 24));
  let status = '';
  if (diffDays < 0) status = `<span style="color:var(--muted)">已发布 (${Math.abs(diffDays)} 天前)</span>`;
  else if (diffDays === 0) status = '<span style="color:var(--bad);font-weight:800">🔴 今天!</span>';
  else if (diffDays <= 7) status = `<span style="color:var(--bad);font-weight:800">⏰ ${diffDays} 天后</span>`;
  else if (diffDays <= 30) status = `<span style="color:var(--accent);font-weight:600">${diffDays} 天后</span>`;
  else status = `<span style="color:var(--muted)">${diffDays} 天后</span>`;
  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0">
      <div><strong>下次财报:</strong> ${entry.earningsDate} ${entry.confirmed ? '✅' : '❓'}</div>
      <div>${status}</div>
    </div>
  `;
}

// ===== Stock Detail: Competitive Landscape =====
function renderStockCompetitive(symbol) {
  const el = document.getElementById('stockCompetitive');
  if (!el) return;
  if (!competitiveData || !competitiveData.companies) { el.innerHTML = '<p style="color:var(--muted)">暂无竞争分析数据</p>'; return; }
  const comp = competitiveData.companies.find(c => c.symbol === symbol);
  if (!comp) { el.innerHTML = '<p style="color:var(--muted)">暂无该股票竞争分析</p>'; return; }
  const threatColors = { high: 'var(--bad)', medium: 'var(--accent)', low: 'var(--muted)' };
  const threatLabels = { high: '高威胁', medium: '中威胁', low: '低威胁' };
  el.innerHTML = `
    <div style="margin-bottom:8px">
      <strong>护城河:</strong> ${comp.moatType} (${comp.moatStrength}/5)
      <br><strong>市场地位:</strong> ${comp.marketPosition}
    </div>
    <div style="font-size:13px">
      ${(comp.competitors || []).map(c => `
        <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px dashed var(--line)">
          <span>${c.name}</span>
          <span style="color:${threatColors[c.threat] || 'var(--muted)'}">${threatLabels[c.threat] || c.threat} · ${c.detail}</span>
        </div>
      `).join('')}
    </div>
    <div style="margin-top:8px;font-size:12px;color:var(--muted)">${comp.competitiveAdvantage}</div>
  `;
}

// ===== Stock Detail: Cross Analysis (Expert × Valuation) =====
function renderStockCrossAnalysis(symbol) {
  const el = document.getElementById('stockCrossAnalysis');
  if (!el) return;
  const signals = [];

  // Expert holdings signal
  if (expertHoldings && expertHoldings.experts) {
    const holders = [];
    const movers = [];
    expertHoldings.experts.forEach(expert => {
      const allHoldings = [...(expert.topHoldings || []), ...(expert.notableMoves || [])];
      const match = allHoldings.find(h => h.symbol === symbol);
      if (match) {
        if (match.change === 'increased' || match.change === 'new' || match.change === 'new_top10') {
          movers.push({ name: expert.name.split('/')[0].trim(), action: '加仓', color: 'var(--good)', detail: match.changeDetail });
        } else if (match.change === 'reduced' || match.change === 'exited') {
          movers.push({ name: expert.name.split('/')[0].trim(), action: '减持', color: 'var(--bad)', detail: match.changeDetail });
        } else {
          holders.push(expert.name.split('/')[0].trim());
        }
      }
    });
    if (movers.length) {
      signals.push(`<div class="cross-signal"><strong>🏛️ 专家动向:</strong> ` +
        movers.map(m => `<span style="color:${m.color}">${m.name} ${m.action}</span>`).join(' · ') +
        `</div>`);
    }
    if (holders.length) {
      signals.push(`<div class="cross-signal" style="color:var(--muted)">持有: ${holders.join(', ')}</div>`);
    }
  }

  // Valuation signal
  if (valuationData && valuationData.stocks) {
    const vs = valuationData.stocks.find(s => s.symbol === symbol);
    if (vs) {
      let pegSignal = '';
      if (vs.peg != null) {
        if (vs.peg < 1) pegSignal = `<span style="color:var(--good);font-weight:600">PEG ${vs.peg.toFixed(2)} — 增长未被充分定价</span>`;
        else if (vs.peg > 2) pegSignal = `<span style="color:var(--bad);font-weight:600">PEG ${vs.peg.toFixed(2)} — 可能偏贵</span>`;
        else pegSignal = `<span>PEG ${vs.peg.toFixed(2)} — 估值合理</span>`;
      }
      if (pegSignal) signals.push(`<div class="cross-signal"><strong>📊 估值:</strong> ${pegSignal} ${vs.signal ? '· ' + vs.signal : ''}</div>`);
    }
  }

  // Thesis signal
  if (thesisData && thesisData.theses) {
    const th = thesisData.theses.find(t => t.symbol === symbol);
    if (th) {
      signals.push(`<div class="cross-signal"><strong>🎯 论点:</strong> 信心 ${'⭐'.repeat(th.conviction)} (${th.conviction}/5) — ${th.thesis || ''}</div>`);
    }
  }

  // Earnings countdown signal
  if (earningsCalendar && earningsCalendar.earnings) {
    const ec = earningsCalendar.earnings.find(e => e.symbol === symbol);
    if (ec && ec.earningsDate) {
      const diffDays = Math.ceil((new Date(ec.earningsDate) - new Date()) / (1000 * 60 * 60 * 24));
      if (diffDays >= 0 && diffDays <= 14) {
        signals.push(`<div class="cross-signal" style="color:var(--bad)"><strong>⏰ 财报预警:</strong> ${diffDays} 天后 (${ec.earningsDate})</div>`);
      }
    }
  }

  if (signals.length) {
    el.innerHTML = signals.join('');
  } else {
    el.innerHTML = '<p style="color:var(--muted)">暂无交叉分析信号</p>';
  }
}

function renderThesis() {
  if (!thesisData || !thesisData.theses) return;
  const container = document.getElementById('thesisCards');
  if (!container) return;

  const sorted = [...thesisData.theses].sort((a, b) => (b.conviction || 0) - (a.conviction || 0));

  container.innerHTML = sorted.map(t => `
    <div class="thesis-card">
      <div class="thesis-header">
        <h3>${t.symbol} — ${t.name}</h3>
        <span class="conviction conviction-${t.conviction}">⭐ ${t.conviction}/5</span>
      </div>
      <div class="thesis-summary">${t.thesis || ''}</div>
      <div class="thesis-moat">
        ${(t.moatType || []).map(m => `<span class="moat-tag">${moatLabels[m] || m}</span>`).join('')}
      </div>
      <div class="thesis-section">
        <h4>🚀 Bull Case</h4>
        <ul>${(t.bullCase || []).map(b => `<li>${b}</li>`).join('')}</ul>
      </div>
      <div class="thesis-section">
        <h4>⚠️ Bear Case</h4>
        <ul>${(t.bearCase || []).map(b => `<li>${b}</li>`).join('')}</ul>
      </div>
      ${(t.catalysts && t.catalysts.length) ? `
      <div class="thesis-section">
        <h4>🎯 催化剂</h4>
        <div class="thesis-catalysts">
          ${t.catalysts.map(c => `
            <div class="catalyst-item">
              <span>${c.event}</span>
              <span class="catalyst-impact-${c.impact}">${c.date || ''} · ${c.impact === 'high' ? '高影响' : c.impact === 'medium' ? '中影响' : '低影响'}</span>
            </div>
          `).join('')}
        </div>
      </div>` : ''}
      <div style="font-size:11px;color:var(--muted);margin-top:8px;">Updated: ${t.lastUpdated || 'N/A'}</div>
    </div>
  `).join('');
}
// ===== Expert Sub-Tab Navigation =====
document.querySelectorAll('.expert-sub-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.expert-sub-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.expert-subview').forEach(v => v.classList.remove('active'));
    tab.classList.add('active');
    const view = tab.dataset.subview;
    if (view === 'list') document.getElementById('expertListView').classList.add('active');
    else if (view === 'commonality') {
      document.getElementById('expertCommonalityView').classList.add('active');
      renderCommonality();
    }
  });
});

// ===== Commonality Analysis =====
let commonalityPrices = {};
let secFilingsData = [];

function buildConsensusData() {
  const experts = (expertHoldings && expertHoldings.experts) || [];
  if (!experts.length) return [];
  const tickerMap = {}; // symbol -> { name, experts: [{name, pct, change}], count }
  experts.forEach(expert => {
    const allH = [...(expert.topHoldings || []), ...(expert.notableMoves || [])];
    allH.forEach(h => {
      if (!h.symbol) return;
      if (!tickerMap[h.symbol]) tickerMap[h.symbol] = { name: h.name || h.symbol, experts: [], count: 0, changes: {} };
      tickerMap[h.symbol].experts.push({
        name: (expert.name || '').split('/')[0].trim(),
        pct: h.pctOfPortfolio || 0,
        change: h.change || 'unchanged'
      });
      tickerMap[h.symbol].count++;
      const c = h.change || 'unchanged';
      tickerMap[h.symbol].changes[c] = (tickerMap[h.symbol].changes[c] || 0) + 1;
    });
  });
  // Convert to array, filter multi-holder, sort by count desc
  return Object.entries(tickerMap)
    .filter(([, v]) => v.count >= 2)
    .map(([symbol, v]) => ({
      symbol,
      name: v.name,
      count: v.count,
      pctTotal: v.experts.length,
      avgWeight: v.experts.reduce((s, e) => s + e.pct, 0) / v.experts.length,
      maxWeight: Math.max(...v.experts.map(e => e.pct)),
      experts: v.experts,
      changes: v.changes,
      newBuys: (v.changes['new'] || 0) + (v.changes['new_top10'] || 0),
      increased: v.changes['increased'] || 0,
      reduced: v.changes['reduced'] || 0,
      exited: v.changes['exited'] || 0
    }))
    .sort((a, b) => b.count - a.count || b.avgWeight - a.avgWeight);
}

async function fetchConsensusPrices(symbols) {
  // Use Yahoo Finance v8 quote endpoint
  const symbolStr = symbols.join(',');
  try {
    const res = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${symbols[0]}?interval=1d&range=1d`);
    // Batch approach: fetch each individually (Yahoo v8 doesn't support batch well)
    const prices = {};
    await Promise.all(symbols.slice(0, 20).map(async sym => {
      try {
        const r = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${sym}?interval=1d&range=1d`);
        if (!r.ok) return;
        const d = await r.json();
        const meta = d.chart?.result?.[0]?.meta;
        if (meta) {
          prices[sym] = {
            price: meta.regularMarketPrice,
            prevClose: meta.previousClose || meta.chartPreviousClose,
            change: meta.regularMarketPrice - (meta.previousClose || meta.chartPreviousClose),
            changePct: ((meta.regularMarketPrice - (meta.previousClose || meta.chartPreviousClose)) / (meta.previousClose || meta.chartPreviousClose) * 100)
          };
        }
      } catch(e) { /* skip */ }
    }));
    return prices;
  } catch(e) {
    console.warn('Price fetch failed:', e);
    return {};
  }
}

async function fetchSECFilings() {
  // Fetch recent Form 4 and 13D/G filings from SEC EDGAR full-text search
  const experts = (expertHoldings && expertHoldings.experts) || [];
  const expertNames = experts.map(e => (e.name || '').split('/').pop().trim()).filter(Boolean);
  try {
    // Use SEC EDGAR EFTS (full-text search) for recent Form 4 filings
    const res = await fetch('https://efts.sec.gov/LATEST/search-index?q=%22form+4%22&dateRange=custom&startdt=' + getDateDaysAgo(7) + '&enddt=' + getToday() + '&forms=4,SC+13D,SC+13G&from=0&size=20', {
      headers: { 'User-Agent': 'Finance Dashboard research@example.com' }
    });
    if (!res.ok) return [];
    return await res.json();
  } catch(e) {
    console.warn('SEC filing fetch failed:', e);
    return [];
  }
}

function getToday() { return new Date().toISOString().slice(0, 10); }
function getDateDaysAgo(n) { const d = new Date(); d.setDate(d.getDate() - n); return d.toISOString().slice(0, 10); }

async function renderCommonality() {
  const consensus = buildConsensusData();
  if (!consensus.length) {
    document.getElementById('consensusHeatmap').innerHTML = '<p style="color:var(--muted)">暂无足够专家数据进行共性分析</p>';
    return;
  }

  const totalExperts = (expertHoldings && expertHoldings.experts || []).length;
  const wlTickers = getWatchlistTickers();

  // Render heatmap
  const maxCount = consensus[0].count;
  document.getElementById('consensusHeatmap').innerHTML = `
    <div class="heatmap-title">
      <h3>🔥 共识热力图</h3>
      <span class="heatmap-subtitle">气泡越大 = 持有专家越多 · 颜色越深 = 平均仓位越重</span>
    </div>
    <div class="heatmap-grid">
      ${consensus.slice(0, 30).map(c => {
        const size = Math.max(48, Math.min(120, 48 + (c.count / maxCount) * 72));
        const intensity = Math.min(1, c.avgWeight / 15);
        const isWl = wlTickers.includes(c.symbol);
        const priceInfo = commonalityPrices[c.symbol];
        const priceHtml = priceInfo ? `<span class="hm-price ${priceInfo.changePct >= 0 ? 'up' : 'down'}">${priceInfo.changePct >= 0 ? '+' : ''}${priceInfo.changePct.toFixed(1)}%</span>` : '';
        return `
          <div class="hm-bubble ${isWl ? 'wl' : ''}" style="width:${size}px;height:${size}px;background:rgba(59,130,246,${0.15 + intensity * 0.6})" title="${c.name}\n${c.count}/${totalExperts} 位专家持有\n平均仓位 ${c.avgWeight.toFixed(1)}%">
            <span class="hm-symbol">${c.symbol}</span>
            <span class="hm-count">${c.count}</span>
            ${priceHtml}
          </div>
        `;
      }).join('')}
    </div>
  `;

  // Render consensus table
  document.getElementById('consensusTable').innerHTML = `
    <h3>📊 共识排名</h3>
    <table class="holdings-table consensus">
      <thead>
        <tr>
          <th>#</th><th>Ticker</th><th>公司</th><th>持有人数</th><th>平均仓位</th>
          <th>最重仓位</th><th>加仓</th><th>新买</th><th>减持</th><th>实时价格</th><th>涨跌</th>
        </tr>
      </thead>
      <tbody>
        ${consensus.map((c, i) => {
          const isWl = wlTickers.includes(c.symbol);
          const p = commonalityPrices[c.symbol];
          return `
            <tr class="${isWl ? 'overlap-row' : ''}">
              <td>${i + 1}</td>
              <td><strong>${c.symbol}</strong>${isWl ? ' <span class="overlap-dot">●</span>' : ''}</td>
              <td>${c.name}</td>
              <td><strong>${c.count}</strong> / ${totalExperts}</td>
              <td>${c.avgWeight.toFixed(1)}%</td>
              <td>${c.maxWeight.toFixed(1)}%</td>
              <td>${c.increased ? `<span style="color:var(--good)">+${c.increased}</span>` : '—'}</td>
              <td>${c.newBuys ? `<span style="color:var(--good);font-weight:700">🆕 ${c.newBuys}</span>` : '—'}</td>
              <td>${c.reduced ? `<span style="color:var(--bad)">-${c.reduced}</span>` : '—'}${c.exited ? ` <span style="color:var(--bad)">🚪${c.exited}</span>` : ''}</td>
              <td>${p ? `$${p.price.toFixed(2)}` : '—'}</td>
              <td class="${p ? (p.changePct >= 0 ? 'val-cheap' : 'val-expensive') : ''}">${p ? `${p.changePct >= 0 ? '+' : ''}${p.changePct.toFixed(2)}%` : '—'}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
    <div class="consensus-insights">
      <div class="expert-action disclaimer">
        <strong>💡 解读</strong>
        <p>共识度高不等于该买。多位大师持有说明标的经过了多重筛选，但 13F 有 45 天延迟。结合实时价格和 SEC 异动信号综合判断。<span class="overlap-dot">●</span> = 你的 watchlist 重叠股。</p>
      </div>
    </div>
  `;

  // Render SEC filings placeholder
  document.getElementById('secFilings').innerHTML = `
    <h3>📡 SEC 近期异动 (Form 4 / 13D/G)</h3>
    <div id="secFilingsContent" class="sec-filings-list">
      <p style="color:var(--muted)">加载中...</p>
    </div>
  `;

  // Fetch real-time prices
  const symbols = consensus.slice(0, 20).map(c => c.symbol);
  commonalityPrices = await fetchConsensusPrices(symbols);
  document.getElementById('commonalityUpdatedAt').textContent = `行情更新: ${new Date().toLocaleTimeString('zh-CN')}`;
  // Re-render with prices
  renderCommonality_pricesOnly(consensus, totalExperts, wlTickers);

  // Fetch SEC filings
  await renderSECFilings(consensus);
}

function renderCommonality_pricesOnly(consensus, totalExperts, wlTickers) {
  // Update just the price columns and heatmap price badges
  const maxCount = consensus[0].count;
  document.getElementById('consensusHeatmap').innerHTML = `
    <div class="heatmap-title">
      <h3>🔥 共识热力图</h3>
      <span class="heatmap-subtitle">气泡越大 = 持有专家越多 · 颜色越深 = 平均仓位越重 · 实时涨跌</span>
    </div>
    <div class="heatmap-grid">
      ${consensus.slice(0, 30).map(c => {
        const size = Math.max(48, Math.min(120, 48 + (c.count / maxCount) * 72));
        const intensity = Math.min(1, c.avgWeight / 15);
        const isWl = wlTickers.includes(c.symbol);
        const priceInfo = commonalityPrices[c.symbol];
        const priceHtml = priceInfo ? `<span class="hm-price ${priceInfo.changePct >= 0 ? 'up' : 'down'}">${priceInfo.changePct >= 0 ? '+' : ''}${priceInfo.changePct.toFixed(1)}%</span>` : '';
        return `
          <div class="hm-bubble ${isWl ? 'wl' : ''}" style="width:${size}px;height:${size}px;background:rgba(59,130,246,${0.15 + intensity * 0.6})" title="${c.name}\n${c.count}/${totalExperts} 位专家持有\n平均仓位 ${c.avgWeight.toFixed(1)}%">
            <span class="hm-symbol">${c.symbol}</span>
            <span class="hm-count">${c.count}</span>
            ${priceHtml}
          </div>
        `;
      }).join('')}
    </div>
  `;

  // Update table prices
  const tbody = document.querySelector('.holdings-table.consensus tbody');
  if (tbody) {
    const rows = tbody.querySelectorAll('tr');
    consensus.forEach((c, i) => {
      if (!rows[i]) return;
      const cells = rows[i].querySelectorAll('td');
      const p = commonalityPrices[c.symbol];
      if (cells.length >= 11 && p) {
        cells[9].textContent = `$${p.price.toFixed(2)}`;
        cells[10].className = p.changePct >= 0 ? 'val-cheap' : 'val-expensive';
        cells[10].textContent = `${p.changePct >= 0 ? '+' : ''}${p.changePct.toFixed(2)}%`;
      }
    });
  }
}

async function renderSECFilings(consensus) {
  const el = document.getElementById('secFilingsContent');
  if (!el) return;
  const consensusSymbols = consensus.map(c => c.symbol);
  
  // Use pre-fetched sec-filings.json data
  if (secFilingsJSON && secFilingsJSON.symbolFilings) {
    const entries = [];
    consensusSymbols.forEach(sym => {
      const filings = secFilingsJSON.symbolFilings[sym];
      if (filings && filings.length) {
        filings.forEach(f => entries.push({ ...f, relatedSymbol: sym }));
      }
    });
    (secFilingsJSON.recentFilings || []).forEach(f => entries.push(f));
    
    if (!entries.length) {
      el.innerHTML = '<p style="color:var(--muted)">近 14 天无相关 SEC 异动记录</p>';
      return;
    }
    
    const seen = new Set();
    const unique = entries.filter(e => {
      const key = `${e.filer}-${e.date}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 25);
    
    el.innerHTML = unique.map(h => `
      <div class="sec-filing-row">
        <span class="sec-form">${h.form || 'Form 4'}</span>
        <span class="sec-filer">${h.filer || ''}${h.relatedSymbol ? ' <span class="overlap-dot" title="共识股">(${h.relatedSymbol})</span>' : ''}</span>
        <span class="sec-date">${h.date || ''}</span>
        ${h.url ? `<a href="${h.url}" target="_blank" rel="noopener">→</a>` : ''}
      </div>
    `).join('');
    
    if (secFilingsJSON.generatedAt) {
      const age = Math.round((Date.now() - new Date(secFilingsJSON.generatedAt).getTime()) / 3600000);
      el.innerHTML += `<p style="font-size:11px;color:var(--muted);margin-top:8px">数据更新: ${new Date(secFilingsJSON.generatedAt).toLocaleString('zh-CN')} (${age}h ago)</p>`;
    }
    return;
  }
  
  el.innerHTML = '<p style="color:var(--muted)">暂无 SEC 数据。运行 update_sec_filings.py 获取最新数据。</p>';
}

// Refresh button for commonality
document.getElementById('commonalityRefresh')?.addEventListener('click', () => {
  commonalityPrices = {};
  renderCommonality();
});

loadData().catch((error) => {
  document.body.innerHTML = `<main><h1>Dashboard failed to load</h1><p>${error.message}</p></main>`;
});
