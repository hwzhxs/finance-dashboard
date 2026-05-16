#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 scripts/update_data.py
exec python3 scripts/server.py --host 127.0.0.1 --port 18888
