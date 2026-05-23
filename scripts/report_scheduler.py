#!/usr/bin/env python3
"""Finance data updater — runs update_data.py on a schedule.

Discord briefings are now handled by OpenClaw agent cron jobs
(finance-preopen-brief and finance-postclose-brief) which read the
generated data and write insightful analysis.

This scheduler only keeps data fresh.
"""
from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "scheduler-state.json"
NY = ZoneInfo("Asia/Shanghai")


def already_done(key: str) -> bool:
    if not STATE.exists():
        return False
    return key in STATE.read_text(encoding="utf-8")


def mark_done(key: str) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    existing = STATE.read_text(encoding="utf-8") if STATE.exists() else ""
    STATE.write_text(existing + key + "\n", encoding="utf-8")


def run_update() -> None:
    subprocess.run(["python3", str(ROOT / "scripts" / "update_data.py")], check=True)
    subprocess.run(["python3", str(ROOT / "scripts" / "update_research.py")], check=True)
    subprocess.run(["python3", str(ROOT / "scripts" / "update_sec_filings.py")], check=True)
    # Validate + auto-repair after each update
    subprocess.run(["python3", str(ROOT / "scripts" / "validate_data.py"), "--repair"], check=False)


def run_earnings_calendar() -> None:
    subprocess.run(["python3", str(ROOT / "scripts" / "earnings_calendar.py")], check=True)


def main() -> int:
    while True:
        now = datetime.now(NY)
        if now.weekday() < 5:
            date = now.date().isoformat()
            # Data update: before agent research (20:30) and before agent postclose brief (04:30)
            checks = [
                ("preopen-data", 20, 15),
                ("postclose-data", 4, 15),
            ]
            for kind, hour, minute in checks:
                key = f"{date}:{kind}"
                if now.hour == hour and now.minute >= minute and now.minute < minute + 5 and not already_done(key):
                    try:
                        run_update()
                        mark_done(key)
                        print(f"Data updated for {key}", flush=True)
                    except Exception as exc:
                        print(f"Data update failed for {key}: {exc}", flush=True)

            # Earnings calendar: update once daily at 08:00 BJT
            ecal_key = f"{date}:earnings-calendar"
            if now.hour == 8 and now.minute < 5 and not already_done(ecal_key):
                try:
                    run_earnings_calendar()
                    mark_done(ecal_key)
                    print(f"Earnings calendar updated for {ecal_key}", flush=True)
                except Exception as exc:
                    print(f"Earnings calendar failed: {exc}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
