#!/usr/bin/env bash
# Package a durable per-run trace (no secrets).
#
# Env:
#   LUFFY_ROOT, OUT_DIR, HERMES_HOME
#   REPO, PR_NUMBER
#   GITHUB_RUN_ID, GITHUB_RUN_ATTEMPT, GITHUB_SHA, GITHUB_REF (optional)
#   TRACE_ROOT (default: $LUFFY_ROOT/.luffy-out/traces)
#   LUFFY_MODEL, WORKSPACE_ROOT
#
# Writes:
#   $TRACE_DIR/
#     meta.json          # run identity + status
#     prompt.md          # full agent prompt
#     context.md         # assembled PR context
#     pr.json            # gh pr view JSON
#     pr.diff            # (truncated) diff
#     files.txt          # file list summary
#     review.raw.md      # hermes stdout before normalize
#     review.md          # posted review body
#     hermes.stderr      # hermes stderr if any
#     memory-before.md   # optional snapshot if present
#     memory-after.md    # MEMORY.md after distill
#     timings.json       # stage durations if available
#     trace.json         # index + file inventory (SHA256)
set -euo pipefail

log() { echo "$*" >&2; }

LUFFY_ROOT="${LUFFY_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${OUT_DIR:-$LUFFY_ROOT/.luffy-out}"
HERMES_HOME="${HERMES_HOME:-$LUFFY_ROOT/.luffy-hermes-home}"
TRACE_ROOT="${TRACE_ROOT:-$OUT_DIR/traces}"

if [[ -f "$OUT_DIR/meta.env" ]]; then
  # shellcheck disable=SC1091
  source "$OUT_DIR/meta.env"
fi

PR_NUMBER="${PR_NUMBER:-unknown}"
REPO="${REPO:-${GITHUB_REPOSITORY:-unknown}}"
RUN_ID="${GITHUB_RUN_ID:-local}"
RUN_ATTEMPT="${GITHUB_RUN_ATTEMPT:-1}"
MODEL="${LUFFY_MODEL:-${OPENROUTER_MODEL:-unknown}}"
STATUS="${LUFFY_STATUS:-unknown}"
STARTED_AT="${LUFFY_STARTED_AT:-}"
ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

TRACE_ID="pr${PR_NUMBER}-run${RUN_ID}-a${RUN_ATTEMPT}"
TRACE_DIR="${TRACE_ROOT}/${TRACE_ID}"
mkdir -p "$TRACE_DIR"

copy_if() {
  local src="$1" dest="$2"
  if [[ -f "$src" ]]; then
    cp -f "$src" "$dest"
  fi
}

copy_if "$OUT_DIR/prompt.md" "$TRACE_DIR/prompt.md"
copy_if "$OUT_DIR/context.md" "$TRACE_DIR/context.md"
copy_if "$OUT_DIR/pr.json" "$TRACE_DIR/pr.json"
copy_if "$OUT_DIR/pr.diff" "$TRACE_DIR/pr.diff"
copy_if "$OUT_DIR/files.txt" "$TRACE_DIR/files.txt"
copy_if "$OUT_DIR/meta.env" "$TRACE_DIR/meta.env"
copy_if "$OUT_DIR/timings.json" "$TRACE_DIR/timings.json"
copy_if "$OUT_DIR/review-${PR_NUMBER}.raw.md" "$TRACE_DIR/review.raw.md"
copy_if "$OUT_DIR/review-${PR_NUMBER}.md" "$TRACE_DIR/review.md"
copy_if "$OUT_DIR/hermes-${PR_NUMBER}.stderr" "$TRACE_DIR/hermes.stderr"

# Memory snapshots (never include HERMES_HOME/.env)
if [[ -f "$HERMES_HOME/memories/MEMORY.md" ]]; then
  cp -f "$HERMES_HOME/memories/MEMORY.md" "$TRACE_DIR/memory-after.md"
fi
if [[ -f "$OUT_DIR/memory-before.md" ]]; then
  cp -f "$OUT_DIR/memory-before.md" "$TRACE_DIR/memory-before.md"
fi

# Redact any accidental API keys in copied text files
python3 - <<'PY' "$TRACE_DIR"
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
patterns = [
    (re.compile(r"sk-or-v1-[A-Za-z0-9_-]{10,}"), "[OPENROUTER_KEY_REDACTED]"),
    (re.compile(r"(OPENROUTER_API_KEY=)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(api[_-]?key[\"']?\s*[:=]\s*[\"']?)([^\"'\s]+)", re.I), r"\1[REDACTED]"),
]
for path in root.rglob("*"):
    if not path.is_file():
        continue
    if path.suffix.lower() in {".png", ".jpg", ".zip", ".gz", ".tar"}:
        continue
    try:
        text = path.read_text(errors="replace")
    except OSError:
        continue
    new = text
    for rx, repl in patterns:
        new = rx.sub(repl, new)
    if new != text:
        path.write_text(new)
PY

# Build inventory + meta
export TRACE_DIR TRACE_ID REPO PR_NUMBER RUN_ID RUN_ATTEMPT MODEL STATUS STARTED_AT ENDED_AT
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-}"
export GITHUB_SHA="${GITHUB_SHA:-}"
export GITHUB_REF="${GITHUB_REF:-}"
export GITHUB_EVENT_NAME="${GITHUB_EVENT_NAME:-}"
export HERMES_RC="${HERMES_RC:-}"
export TRIGGER_COMMENT="${TRIGGER_COMMENT:-}"

python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

trace_dir = Path(os.environ["TRACE_DIR"])
files = {}
for p in sorted(trace_dir.iterdir()):
    if p.is_file() and p.name not in {"trace.json", "meta.json"}:
        data = p.read_bytes()
        files[p.name] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

meta = {
    "trace_id": os.environ["TRACE_ID"],
    "schema_version": 1,
    "repo": os.environ.get("REPO"),
    "pr_number": os.environ.get("PR_NUMBER"),
    "run_id": os.environ.get("RUN_ID"),
    "run_attempt": os.environ.get("RUN_ATTEMPT"),
    "model": os.environ.get("MODEL"),
    "status": os.environ.get("STATUS"),
    "started_at": os.environ.get("STARTED_AT") or None,
    "ended_at": os.environ.get("ENDED_AT"),
    "workspace_root": os.environ.get("WORKSPACE_ROOT") or None,
    "github_sha": os.environ.get("GITHUB_SHA") or None,
    "github_ref": os.environ.get("GITHUB_REF") or None,
    "github_event_name": os.environ.get("GITHUB_EVENT_NAME") or None,
    "hermes_rc": os.environ.get("HERMES_RC") or None,
    "trigger_comment": (os.environ.get("TRIGGER_COMMENT") or "")[:500],
    "files": files,
}

(trace_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
(trace_dir / "trace.json").write_text(
    json.dumps(
        {
            "trace_id": meta["trace_id"],
            "schema_version": 1,
            "meta": "meta.json",
            "artifacts": list(files.keys()),
            "review": "review.md" if "review.md" in files else None,
            "prompt": "prompt.md" if "prompt.md" in files else None,
            "raw_review": "review.raw.md" if "review.raw.md" in files else None,
        },
        indent=2,
    )
    + "\n"
)
print(trace_dir)
PY

# Pointer for orchestrator / GITHUB_OUTPUT
echo "$TRACE_DIR" >"$OUT_DIR/latest-trace-dir.txt"
echo "TRACE_DIR=$TRACE_DIR"
echo "TRACE_ID=$TRACE_ID"
log "Trace stored at $TRACE_DIR ($(du -sh "$TRACE_DIR" | awk '{print $1}'))"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "trace_dir=$TRACE_DIR"
    echo "trace_id=$TRACE_ID"
  } >>"$GITHUB_OUTPUT"
fi
