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
  const [latestRes, scoresRes, rankingsRes, researchRes, configRes] = await Promise.all([
    fetch(`${assetBase}data/latest.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/scores.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/rankings.json?ts=${Date.now()}`),
    fetch(`${assetBase}data/company_research.json?ts=${Date.now()}`),
    fetch(`${assetBase}config/watchlist.json?ts=${Date.now()}`)
  ]);
  latest = await latestRes.json();
  scores = await scoresRes.json();
  rankings = await rankingsRes.json();
  research = await researchRes.json();
  config = await configRes.json();
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

function renderChart(item) {
  const svg = document.getElementById("priceChart");
  const history = item.metrics.history || [];
  const rangeCount = { "1M": 22, "3M": 63, "6M": 126, "1Y": 252 }[activeRange] || 63;
  const rows = history.slice(-rangeCount);
  if (rows.length < 2) {
    svg.innerHTML = `<text x="20" y="40" fill="#65706b">暂无足够价格数据</text>`;
    return;
  }
  const width = 720;
  const height = 220;
  const pad = 20;
  const closes = rows.map((row) => row.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = max - min || 1;
  const points = rows.map((row, index) => {
    const x = pad + (index / (rows.length - 1)) * (width - pad * 2);
    const y = height - pad - ((row.close - min) / span) * (height - pad * 2);
    return [x, y];
  });
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"} ${point[0].toFixed(1)} ${point[1].toFixed(1)}`).join(" ");
  const fill = `${path} L ${points[points.length - 1][0].toFixed(1)} ${height - pad} L ${points[0][0].toFixed(1)} ${height - pad} Z`;
  svg.innerHTML = `
    <line class="chart-axis" x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}"></line>
    <line class="chart-axis" x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}"></line>
    <path class="chart-fill" d="${fill}"></path>
    <path class="chart-line" d="${path}"></path>
    <text x="${pad}" y="18" fill="#65706b">${fmtPrice(max)}</text>
    <text x="${pad}" y="${height - 4}" fill="#65706b">${fmtPrice(min)}</text>
    <line class="chart-crosshair-v" x1="0" y1="${pad}" x2="0" y2="${height - pad}" stroke="#888" stroke-width="0.5" stroke-dasharray="3,3" opacity="0"></line>
    <line class="chart-crosshair-h" x1="${pad}" y1="0" x2="${width - pad}" y2="0" stroke="#888" stroke-width="0.5" stroke-dasharray="3,3" opacity="0"></line>
    <circle class="chart-dot" cx="0" cy="0" r="3.5" fill="var(--accent, #4f8cff)" opacity="0"></circle>
    <rect class="chart-tooltip-bg" x="0" y="0" width="130" height="38" rx="6" fill="rgba(30,34,40,0.92)" opacity="0"></rect>
    <text class="chart-tooltip-date" x="0" y="0" fill="#ccc" font-size="11"></text>
    <text class="chart-tooltip-price" x="0" y="0" fill="#fff" font-size="13" font-weight="600"></text>
    <rect class="chart-hover-area" x="${pad}" y="0" width="${width - pad * 2}" height="${height}" fill="transparent"></rect>
  `;
  // Interactive tooltip
  const hoverArea = svg.querySelector(".chart-hover-area");
  const crossV = svg.querySelector(".chart-crosshair-v");
  const crossH = svg.querySelector(".chart-crosshair-h");
  const dot = svg.querySelector(".chart-dot");
  const tooltipBg = svg.querySelector(".chart-tooltip-bg");
  const tooltipDate = svg.querySelector(".chart-tooltip-date");
  const tooltipPrice = svg.querySelector(".chart-tooltip-price");

  function nearest(clientX) {
    const rect = svg.getBoundingClientRect();
    const scaleX = width / rect.width;
    const mx = (clientX - rect.left) * scaleX;
    let best = 0, bestDist = Infinity;
    points.forEach(([px], i) => {
      const d = Math.abs(px - mx);
      if (d < bestDist) { bestDist = d; best = i; }
    });
    return best;
  }

  function showTooltip(idx) {
    const [px, py] = points[idx];
    const row = rows[idx];
    crossV.setAttribute("x1", px); crossV.setAttribute("x2", px); crossV.setAttribute("opacity", "1");
    crossH.setAttribute("y1", py); crossH.setAttribute("y2", py); crossH.setAttribute("opacity", "1");
    dot.setAttribute("cx", px); dot.setAttribute("cy", py); dot.setAttribute("opacity", "1");
    const dateStr = row.date;
    const priceStr = `$${row.close.toFixed(2)}`;
    const pctFromStart = ((row.close / rows[0].close - 1) * 100).toFixed(1);
    const pctSign = pctFromStart >= 0 ? "+" : "";
    // Position tooltip
    let tx = px + 10, ty = py - 24;
    if (tx + 140 > width - pad) tx = px - 140;
    if (ty < pad + 5) ty = py + 10;
    tooltipBg.setAttribute("x", tx); tooltipBg.setAttribute("y", ty); tooltipBg.setAttribute("opacity", "1");
    tooltipDate.setAttribute("x", tx + 8); tooltipDate.setAttribute("y", ty + 14); tooltipDate.textContent = dateStr;
    tooltipPrice.setAttribute("x", tx + 8); tooltipPrice.setAttribute("y", ty + 30); tooltipPrice.textContent = `${priceStr}  ${pctSign}${pctFromStart}%`;
  }

  function hideTooltip() {
    crossV.setAttribute("opacity", "0");
    crossH.setAttribute("opacity", "0");
    dot.setAttribute("opacity", "0");
    tooltipBg.setAttribute("opacity", "0");
    tooltipDate.textContent = "";
    tooltipPrice.textContent = "";
  }

  hoverArea.addEventListener("mousemove", (e) => showTooltip(nearest(e.clientX)));
  hoverArea.addEventListener("touchmove", (e) => { e.preventDefault(); showTooltip(nearest(e.touches[0].clientX)); }, { passive: false });
  hoverArea.addEventListener("mouseleave", hideTooltip);
  hoverArea.addEventListener("touchend", hideTooltip);
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
  const matches = expertFootprintsForSymbol(symbol);
  if (!matches.length) {
    container.innerHTML = `
      <div class="symbol-expert-card">
        <strong>暂无相关专家足迹</strong>
        <span>参考价值：低</span>
        <span>无动作</span>
        <p>当前专家足迹库里还没有和 ${symbol} 直接相关的买入、卖出、加仓或减仓记录。后续接入自动 13F 后会补全。</p>
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

function renderExperts() {
  const experts = config.expertFootprints || [];
  const list = document.getElementById("expertList");
  if (!experts.length) return;
  list.innerHTML = experts.map((expert, index) => `
    <button class="expert-row ${index === activeExpert ? "selected" : ""}" data-index="${index}" type="button">
      <span class="ticker">${expert.expert}</span>
      <span class="subline">${expert.style}</span>
    </button>
  `).join("");
  list.querySelectorAll(".expert-row").forEach((row) => {
    row.addEventListener("click", () => {
      activeExpert = Number(row.dataset.index);
      renderExperts();
    });
  });
  renderExpertDetail(experts[activeExpert]);
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

document.getElementById("refreshBtn").addEventListener("click", loadData);
loadData().catch((error) => {
  document.body.innerHTML = `<main><h1>Dashboard failed to load</h1><p>${error.message}</p></main>`;
});
