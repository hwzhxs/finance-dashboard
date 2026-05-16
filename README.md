# Finance Dashboard

This is the first version of the Admin-backed investment learning workspace.

Admin is the analyst and reporter. The dashboard is only a local view over the
same data files that Admin reads.

## What It Does

- Tracks a small US market watchlist.
- Scores stocks and ETFs through several investing lenses.
- Builds rankings for the local dashboard.
- Creates short pre-market and post-close Discord-ready briefs.

## Local URLs

- Dashboard: http://127.0.0.1:18888

## GitHub Pages

This repo can be deployed as a public static dashboard with GitHub Pages.

- The public site is static.
- GitHub Actions regenerates a public data snapshot on deploy.
- Local Discord delivery and local launch agents are not part of GitHub Pages.
- Generated logs, Discord channel cache, and scheduler state are excluded from the public site.

## Files

- `config/watchlist.json` controls tracked tickers and perspective settings.
- `data/latest.json` contains the latest fetched market data.
- `data/scores.json` contains per-perspective scores.
- `data/rankings.json` contains rankings by perspective.
- `data/daily-brief.md` is the short summary Admin can send to Discord.
- `reports/` stores generated pre-market and post-close reports.

## Commands

```bash
cd /Users/zhangxiaosong/.openclaw/workspace/finance
python3 scripts/update_data.py
python3 scripts/server.py
python3 scripts/send_discord_report.py --kind preopen --dry-run
```

## Background Services

Two LaunchAgents are installed:

- `com.openclaw.finance-dashboard`: serves the local dashboard on port 18888.
- `com.openclaw.finance-report-scheduler`: updates data and sends Discord reports at 9:00 and 16:15 America/New_York on weekdays.

This workspace is educational and decision-support only. It does not place
orders and does not provide guaranteed outcomes.
