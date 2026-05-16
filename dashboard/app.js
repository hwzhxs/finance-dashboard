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
  const [latestRes, scoresRes, rankingsRes, researchRes, configRes, expertRes] = await Promise.all([
    fetch(`${assetBase}data/latest.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/scores.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/rankings.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/company_research.json?ts=${Date.now()}`),
    fetch(`${assetBase}config/watchlist.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/expert-holdings.json?ts=${Date.now()}`).catch(() => null)
  ]);
  latest = await latestRes.json();
  scores = await scoresRes.json();
  rankings = await rankingsRes.json();
  research = await researchRes.json();
  config = await configRes.json();
  if (expertRes && expertRes.ok) expertHoldings = await expertRes.json();
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
  const lineColor = isUp ? "#34c759" : "#ff3b30";
  const topColor = isUp ? "rgba(52,199,89,0.3)" : "rgba(255,59,48,0.2)";
  const bottomColor = isUp ? "rgba(52,199,89,0.02)" : "rgba(255,59,48,0.02)";

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
            <span class="stat">仓位 <strong>${m.pctOfPortfolio.toFixed(1)}%</strong></span>
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

const changeColors = { new: '#007aff', increased: '#34c759', reduced: '#ff3b30', exited: '#ff3b30', unchanged: '#8e8e93' };
const changeLabels = { new: '新建', increased: '加仓', reduced: '减持', exited: '清仓', unchanged: '不变' };

function getWatchlistTickers() {
  return (config.tickers || []).map(t => t.symbol);
}

function renderExperts() {
  const experts = (expertHoldings && expertHoldings.experts) || [];
  const fallback = config.expertFootprints || [];
  const list = document.getElementById("expertList");
  const source = experts.length ? experts : fallback;
  if (!source.length) return;
  const wlTickers = getWatchlistTickers();
  list.innerHTML = source.map((expert, index) => {
    const name = expert.name || expert.expert;
    const quarter = expert.quarter || '';
    const totalValue = expert.totalValue || '';
    const overlap = (expert.topHoldings || []).filter(h => wlTickers.includes(h.symbol)).length;
    return `
      <button class="expert-row ${index === activeExpert ? "selected" : ""}" data-index="${index}" type="button">
        <span class="ticker">${name}</span>
        <span class="subline">${expert.style}</span>
        <span class="expert-meta">
          ${quarter ? `<span class="expert-badge">${quarter}</span>` : ''}
          ${totalValue ? `<span class="expert-badge">${totalValue}</span>` : ''}
          ${overlap > 0 ? `<span class="expert-badge overlap">${overlap} 只重叠</span>` : ''}
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
  if (experts.length) {
    renderExpertDetailV2(experts[activeExpert]);
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
  const holdings = expert.topHoldings || [];
  const rows = holdings.filter(h => h.pctOfPortfolio > 0).map((h, i) => {
    const color = changeColors[h.change] || '#8e8e93';
    const label = changeLabels[h.change] || h.change;
    const isOverlap = wlTickers.includes(h.symbol);
    return `
      <tr class="${isOverlap ? 'overlap-row' : ''}">
        <td>${i + 1}</td>
        <td><strong>${h.symbol}</strong>${isOverlap ? ' <span class="overlap-dot">●</span>' : ''}</td>
        <td>${h.name}</td>
        <td>${h.pctOfPortfolio.toFixed(1)}%</td>
        <td><span class="change-badge" style="color:${color}">${label}</span></td>
        <td>${h.changeDetail} <span class="change-date">(${expert.quarter}, ${expert.filingDate})</span></td>
      </tr>
    `;
  }).join('');
  document.getElementById("expertActions").innerHTML = `
    <div class="expert-insight">
      <strong>💡 Insight:</strong> ${expert.keyInsight}
    </div>
    <table class="holdings-table">
      <thead>
        <tr><th>#</th><th>Ticker</th><th>公司</th><th>仓位</th><th>变化</th><th>详情</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
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
loadData().catch((error) => {
  document.body.innerHTML = `<main><h1>Dashboard failed to load</h1><p>${error.message}</p></main>`;
});
