#!/usr/bin/env python3
from __future__ import annotations

import argparse
import http.server
import socketserver
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FinanceHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path in {"/", ""}:
            self.send_response(302)
            self.send_header("Location", "/dashboard/")
            self.end_headers()
            return
        super().do_GET()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18888)
    args = parser.parse_args()
    with socketserver.ThreadingTCPServer((args.host, args.port), FinanceHandler) as httpd:
        print(f"Finance dashboard listening on http://{args.host}:{args.port}")
        httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
