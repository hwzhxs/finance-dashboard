#!/bin/bash
# Deploy finance dashboard data to GitHub Pages
# Called after data updates to push latest to the public site
set -e

cd "$(dirname "$0")/.."

# Stage data files
git add -f \
  data/latest.json \
  data/scores.json \
  data/rankings.json \
  data/company_research.json \
  data/agent-insights.json \
  data/preopen-brief.md \
  data/postclose-brief.md \
  2>/dev/null || true

# Stage any changed scripts/config
git add -A

# Check if there are changes to commit
if git diff --cached --quiet; then
  echo "No changes to deploy"
  exit 0
fi

git commit -m "📊 data update $(date '+%Y-%m-%d %H:%M')"
git push origin main
echo "Deployed to GitHub Pages"
