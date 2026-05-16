#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
ADMIN_CONFIG = HOME / ".openclaw" / "openclaw.json"
LOCAL_CONFIG = ROOT / "config" / "watchlist.json"
DATA_DIR = ROOT / "data"
CHANNEL_CACHE = DATA_DIR / "discord-channel.json"
DISCORD_API = "https://discord.com/api/v10"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discord_request(token: str, method: str, path: str, payload: dict | None = None) -> dict | list:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        DISCORD_API + path,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "OpenClawFinanceDashboard/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def resolve_channel_id(admin: dict, local: dict) -> str:
    cached = load_json(CHANNEL_CACHE) if CHANNEL_CACHE.exists() else {}
    channel_name = local.get("discord", {}).get("channelName", "")
    if cached.get("name") == channel_name and cached.get("id"):
        return cached["id"]
    discord = admin.get("channels", {}).get("discord", {})
    token = discord.get("token") or os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("Discord token not found in Admin config or DISCORD_BOT_TOKEN.")
    if channel_name.isdigit():
        return channel_name
    guilds = discord.get("guilds", {})
    for guild_id in guilds:
        channels = discord_request(token, "GET", f"/guilds/{guild_id}/channels")
        for channel in channels:
            if channel.get("name") == channel_name:
                CHANNEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
                CHANNEL_CACHE.write_text(json.dumps({"name": channel_name, "id": channel["id"]}, indent=2), encoding="utf-8")
                return channel["id"]
    fallback = discord.get("defaultTo")
    if fallback:
        return fallback
    raise RuntimeError(f"Discord channel not found: {channel_name}")


def load_report(kind: str) -> str:
    report = DATA_DIR / f"{kind}-brief.md"
    if not report.exists():
        raise RuntimeError(f"Missing report. Run update_data.py first: {report}")
    return report.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["preopen", "postclose"], default="preopen")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    admin = load_json(ADMIN_CONFIG)
    local = load_json(LOCAL_CONFIG)
    content = load_report(args.kind)
    if len(content) > 1900:
        content = content[:1850].rstrip() + "\n\n... Dashboard has the full report: http://127.0.0.1:18888"

    channel_id = resolve_channel_id(admin, local)
    if args.dry_run:
        print(f"Would send {args.kind} report to Discord channel {channel_id}:\n")
        print(content)
        return 0

    token = admin.get("channels", {}).get("discord", {}).get("token") or os.environ.get("DISCORD_BOT_TOKEN")
    try:
        discord_request(token, "POST", f"/channels/{channel_id}/messages", {"content": content})
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Discord send failed: HTTP {exc.code} {detail}") from exc
    print(f"Sent {args.kind} report to Discord channel {channel_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
