#!/usr/bin/env bash
# Publish a Luffy run into the central hub memory.
#
# Modes (auto):
#   1) direct  — clone hub, run hub-ingest-run.py, commit+push (needs write token)
#   2) dispatch — repository_dispatch luffy-run (needs classic PAT; GITHUB_TOKEN cannot)
#
# Env:
#   LUFFY_HUB_REPO     default Mr-Ashish/luffy-pr-review-agent
#   LUFFY_HUB_TOKEN    write token (or GH_TOKEN/GITHUB_TOKEN)
#   LUFFY_HUB_MODE     auto|direct|dispatch  (default auto)
#   LUFFY_HUB_PUBLISH  0 to skip
#   OUT_DIR, REPO, PR_NUMBER, ...
set -euo pipefail

log() { echo "$*" >&2; }
notice() { echo "::notice::$*" >&2; log "$*"; }

if [[ "${LUFFY_HUB_PUBLISH:-1}" == "0" ]]; then
  log "LUFFY_HUB_PUBLISH=0; skip hub publish"
  exit 0
fi

LUFFY_ROOT="${LUFFY_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${OUT_DIR:-$LUFFY_ROOT/.luffy-out}"
HUB_REPO="${LUFFY_HUB_REPO:-Mr-Ashish/luffy-pr-review-agent}"
TOKEN="${LUFFY_HUB_TOKEN:-${GH_TOKEN:-${GITHUB_TOKEN:-}}}"
MODE="${LUFFY_HUB_MODE:-auto}"
SOURCE_REPO="${REPO:-${GITHUB_REPOSITORY:-}}"

if [[ -z "$TOKEN" ]]; then
  log "No LUFFY_HUB_TOKEN/GITHUB_TOKEN; skip hub publish"
  exit 0
fi

command -v gh >/dev/null 2>&1 || { log "gh not found; skip"; exit 0; }
command -v python3 >/dev/null 2>&1 || { log "python3 not found; skip"; exit 0; }
command -v git >/dev/null 2>&1 || { log "git not found; skip"; exit 0; }

export OUT_DIR
python3 "$LUFFY_ROOT/scripts/build-hub-payload.py"
PAYLOAD="$OUT_DIR/hub-payload.json"
[[ -f "$PAYLOAD" ]] || { log "missing hub-payload.json"; exit 1; }

python3 - <<'PY' "$PAYLOAD" "$OUT_DIR/client_payload.json"
import json, sys
payload = json.loads(open(sys.argv[1]).read())
open(sys.argv[2], "w").write(json.dumps({"run": payload}, indent=2) + "\n")
print(sys.argv[2])
PY

export GH_TOKEN="$TOKEN"

# Decide mode
if [[ "$MODE" == "auto" ]]; then
  # Prefer direct write — works with GITHUB_TOKEN (contents:write) and PATs.
  # repository_dispatch is NOT allowed for GITHUB_TOKEN (403 integration).
  MODE="direct"
fi

publish_direct() {
  notice "Hub publish mode=direct → $HUB_REPO"
  WORK="$(mktemp -d)"
  cleanup() { rm -rf "$WORK"; }
  trap cleanup EXIT

  git clone --depth 1 \
    "https://x-access-token:${TOKEN}@github.com/${HUB_REPO}.git" \
    "$WORK/hub"

  # Prefer hub's own ingest script (from cloned main); fall back to local copy
  INGEST="$WORK/hub/scripts/hub-ingest-run.py"
  if [[ ! -f "$INGEST" ]]; then
    mkdir -p "$WORK/hub/scripts"
    cp -f "$LUFFY_ROOT/scripts/hub-ingest-run.py" "$INGEST"
  fi

  (
    cd "$WORK/hub"
    git config user.name "luffy-hub-bot"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    export CLIENT_PAYLOAD_FILE="$OUT_DIR/client_payload.json"
    export HUB_ROOT="$WORK/hub"
    python3 "$INGEST"
    git add memory/
    if git diff --cached --quiet; then
      log "No memory changes to commit"
      return 0
    fi
    MSG="chore(memory): ingest ${SOURCE_REPO} PR #${PR_NUMBER:-?} $(date -u +%Y-%m-%dT%H%MZ)"
    git commit -m "$MSG"
    for i in 1 2 3 4 5; do
      if git pull --rebase origin main && git push origin HEAD:main; then
        notice "Pushed hub memory update to $HUB_REPO"
        echo "HUB_PUBLISH=direct_ok"
        return 0
      fi
      log "push retry $i"
      sleep $((i * 2))
    done
    log "direct push failed after retries"
    return 1
  )
}

publish_dispatch() {
  notice "Hub publish mode=dispatch → $HUB_REPO (repository_dispatch luffy-run)"
  python3 - <<'PY' "$OUT_DIR/client_payload.json" "$OUT_DIR/dispatch-body.json"
import json, sys
client = json.loads(open(sys.argv[1]).read())
body = {"event_type": "luffy-run", "client_payload": client}
open(sys.argv[2], "w").write(json.dumps(body))
print(sys.argv[2])
PY
  set +e
  gh api --method POST \
    -H "Accept: application/vnd.github+json" \
    "/repos/${HUB_REPO}/dispatches" \
    --input "$OUT_DIR/dispatch-body.json"
  RC=$?
  set -e
  if [[ $RC -ne 0 ]]; then
    log "repository_dispatch failed (rc=$RC)"
    return "$RC"
  fi
  notice "Hub dispatch accepted (Ingest Luffy Run should start)"
  echo "HUB_PUBLISH=dispatch_ok"
}

case "$MODE" in
  direct)
    publish_direct
    ;;
  dispatch)
    publish_dispatch
    ;;
  both)
    publish_direct || true
    publish_dispatch || true
    ;;
  *)
    log "Unknown LUFFY_HUB_MODE=$MODE"
    exit 1
    ;;
esac
