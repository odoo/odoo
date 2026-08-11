#!/usr/bin/env python3
"""Measure how synchronous Claude-style extraction calls block Odoo HTTP workers.

Backs ADR-003 with real numbers. Against a dedicated ``workers=2`` Odoo
server it fires six concurrent extractions and, mid-flight, times an
unrelated page (``/web/login``).

Methodology (deterministic, zero API cost):

1. The ``invoice_agent.measure_delay`` config parameter (seconds) makes
   ``invoice.llm.service._client()`` sleep inside the HTTP worker — exactly
   where a real Claude round-trip would hold the process (see
   custom_addons/invoice_agent/models/llm_service.py).
2. ``POST /invoice_agent/measure/trigger`` (dev-only controller route, see
   custom_addons/invoice_agent/controllers/main.py) runs ``extract_invoice``
   synchronously in the worker and returns the elapsed seconds.
3. Six concurrent triggers against a workers=2 server can only occupy 2
   processes at a time; the mid-flight login probe then shows the queueing
   stall.

Stdlib only (``urllib``) so it runs unchanged on the host or inside the
container — port 8073 is not published to the host, so run it with:

    docker compose cp scripts/measure_blocking.py odoo:/tmp/measure_blocking.py
    docker compose exec -T odoo python /tmp/measure_blocking.py --config claude
    docker compose cp odoo:/tmp/worker-blocking-claude-*.csv runs/

Or on the host against a published port:

    python scripts/measure_blocking.py --config claude
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

MEASURE_HOST = os.environ.get("MEASURE_HOST", "http://127.0.0.1:8073")
MEASURE_TRIGGER = f"{MEASURE_HOST}/invoice_agent/measure/trigger"
MEASURE_LOGIN = f"{MEASURE_HOST}/web/login"

# A real Claude extraction round-trip is tens of seconds; 5s is a
# conservative lower bound that still proves the worker hold and keeps the
# whole measurement under a minute.
CLAUDE_DELAY_S = 5.0
BASELINE_DELAY_S = 0.05


def _http_post(url, timeout=90):
    """POST an empty body; returns (elapsed_s, http_status, json_or_None)."""
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = time.monotonic() - started
            status = resp.status
            body = resp.read().decode("utf-8", "replace")
        try:
            payload = json.loads(body)
        except ValueError:
            payload = None
        return round(elapsed, 3), status, payload
    except urllib.error.HTTPError as exc:
        return round(time.monotonic() - started, 3), exc.code, None
    except Exception as exc:  # pragma: no cover
        return round(time.monotonic() - started, 3), f"ERR:{type(exc).__name__}", None


def _http_get(url, timeout=60):
    """GET a URL; returns (elapsed_s, http_status)."""
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return round(time.monotonic() - started, 4), resp.status
    except urllib.error.HTTPError as exc:
        return round(time.monotonic() - started, 4), exc.code
    except Exception as exc:  # pragma: no cover
        return round(time.monotonic() - started, 4), f"ERR:{type(exc).__name__}"


def _trigger_extraction():
    """POST one synchronous extraction; returns a result dict."""
    elapsed, status, payload = _http_post(MEASURE_TRIGGER)
    reported = payload.get("result", {}).get("elapsed_seconds") if payload else None
    return {
        "total_s": elapsed,
        "reported_s": reported,
        "status": status,
    }


def _login_latency():
    """Time one GET on /web/login — an unrelated, non-AI page."""
    elapsed, status = _http_get(MEASURE_LOGIN)
    return elapsed, status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="claude",
        choices=["claude", "baseline"],
        help="claude=5s held worker, baseline=50ms (near-zero)",
    )
    args = parser.parse_args()
    delay = CLAUDE_DELAY_S if args.config == "claude" else BASELINE_DELAY_S

    # --- Sanity: one trigger must take ~delay seconds -----------------------
    sanity = _trigger_extraction()
    print(f"[sanity] single trigger: {sanity['total_s']}s status={sanity['status']} "
          f"reported={sanity['reported_s']}")

    # --- Phase 1: idle login latency (no extraction in flight) --------------
    idle_logins = []
    for i in range(5):
        lat, status = _login_latency()
        idle_logins.append(lat)
        print(f"[idle] login probe {i}: {lat}s status={status}")
    idle_avg = sum(idle_logins) / len(idle_logins)

    # --- Phase 2: 6 concurrent extractions + a login probe mid-flight -------
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_trigger_extraction) for _ in range(6)]
        # Give the extractions a beat to occupy the workers, then probe.
        time.sleep(0.5)
        blocked_login, blocked_status = _login_latency()
        results = [f.result() for f in futures]

    os.makedirs("runs", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_csv = f"runs/worker-blocking-{args.config}-{ts}.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["phase", "kind", "index", "latency_s", "status", "reported_s"],
        )
        writer.writeheader()
        for i, lat in enumerate(idle_logins):
            writer.writerow(
                {"phase": "idle", "kind": "login", "index": i, "latency_s": lat,
                 "status": ""}
            )
        writer.writerow(
            {
                "phase": "blocked", "kind": "login", "index": -1,
                "latency_s": blocked_login, "status": blocked_status,
            }
        )
        for i, res in enumerate(results):
            writer.writerow(
                {
                    "phase": "blocked", "kind": "extract", "index": i,
                    "latency_s": res["total_s"], "status": res["status"],
                    "reported_s": res["reported_s"],
                }
            )

    ok = [r for r in results if isinstance(r["status"], int) and r["status"] == 200]
    print("=== worker blocking measurement ===")
    print(f"config         : {args.config} (worker-hold delay {delay}s)")
    print(f"idle login avg : {idle_avg:.4f} s")
    print(f"blocked login  : {blocked_login:.4f} s (status {blocked_status})")
    if ok:
        lats = [r["total_s"] for r in ok]
        print(f"extracts (ok)  : n={len(ok)} min={min(lats):.3f} max={max(lats):.3f} "
              f"avg={sum(lats) / len(lats):.3f}")
    print(f"csv            : {out_csv}")

    ratio = blocked_login / idle_avg if idle_avg else float("inf")
    print(f"degradation    : {ratio:.1f}x vs idle")
    if args.config == "claude":
        print("RESULT: BLOCKING PROVEN" if ratio > 5
              else "RESULT: no degradation observed")
    else:
        print("RESULT: measurement recorded (baseline control)")


if __name__ == "__main__":
    sys.exit(main())
