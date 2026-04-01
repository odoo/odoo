#!/usr/bin/env bash
set -euo pipefail

FORGE_ENGINE_PID_FILE="${FORGE_ENGINE_PID_FILE:-logs/forge-engine.pid}"

if [ ! -f "$FORGE_ENGINE_PID_FILE" ]; then
    echo "[forge-engine-stop] No PID file found. Nothing to stop."
    exit 0
fi

engine_pid="$(cat "$FORGE_ENGINE_PID_FILE" 2>/dev/null || true)"
if [ -z "$engine_pid" ]; then
    rm -f "$FORGE_ENGINE_PID_FILE"
    echo "[forge-engine-stop] Empty PID file removed."
    exit 0
fi

if kill -0 "$engine_pid" 2>/dev/null; then
    echo "[forge-engine-stop] stopping forge_engine PID $engine_pid..."
    kill "$engine_pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
        if ! kill -0 "$engine_pid" 2>/dev/null; then
            break
        fi
        sleep 0.2
    done
    if kill -0 "$engine_pid" 2>/dev/null; then
        kill -9 "$engine_pid" 2>/dev/null || true
    fi
else
    echo "[forge-engine-stop] PID $engine_pid is not running."
fi

rm -f "$FORGE_ENGINE_PID_FILE"
echo "[forge-engine-stop] done."
