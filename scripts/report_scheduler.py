#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "scheduler-state.json"
NY = ZoneInfo("America/New_York")


def already_sent(key: str) -> bool:
    if not STATE.exists():
        return False
    return key in STATE.read_text(encoding="utf-8")


def mark_sent(key: str) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    existing = STATE.read_text(encoding="utf-8") if STATE.exists() else ""
    STATE.write_text(existing + key + "\n", encoding="utf-8")


def run_report(kind: str) -> None:
    subprocess.run(["python3", str(ROOT / "scripts" / "update_data.py")], check=True)
    subprocess.run(["python3", str(ROOT / "scripts" / "send_discord_report.py"), "--kind", kind], check=True)


def main() -> int:
    while True:
        now = datetime.now(NY)
        if now.weekday() < 5:
            date = now.date().isoformat()
            checks = [
                ("preopen", 9, 0),
                ("postclose", 16, 15),
            ]
            for kind, hour, minute in checks:
                key = f"{date}:{kind}"
                if now.hour == hour and now.minute == minute and not already_sent(key):
                    try:
                        run_report(kind)
                        mark_sent(key)
                    except Exception as exc:
                        print(f"finance report failed for {key}: {exc}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
