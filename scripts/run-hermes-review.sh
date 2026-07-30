#!/usr/bin/env bash
# Run Hermes one-shot review (requires assembled prompt).
#
# Env:
#   OPENROUTER_API_KEY
#   LUFFY_ROOT, HERMES_HOME, WORKSPACE_ROOT
#   OUT_DIR, PROMPT_PATH (or meta.env)
#   LUFFY_MODEL / OPENROUTER_MODEL
#   PR_NUMBER
set -euo pipefail

log() { echo "$*" >&2; }
notice() { echo "::notice::$*" >&2; log "$*"; }
die() { echo "::error::$*" >&2; exit 1; }

: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is required}"

LUFFY_ROOT="${LUFFY_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="${OUT_DIR:-$LUFFY_ROOT/.luffy-out}"
HERMES_HOME="${HERMES_HOME:-$LUFFY_ROOT/.luffy-hermes-home}"
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$LUFFY_ROOT}"
MODEL="${LUFFY_MODEL:-${OPENROUTER_MODEL:-openai/gpt-5-mini}}"

mkdir -p "$OUT_DIR" "$HERMES_HOME/memories"

if [[ -f "$OUT_DIR/meta.env" ]]; then
  # shellcheck disable=SC1091
  source "$OUT_DIR/meta.env"
fi

PROMPT_PATH="${PROMPT_PATH:-$OUT_DIR/prompt.md}"
PR_NUMBER="${PR_NUMBER:-unknown}"
[[ -f "$PROMPT_PATH" ]] || die "Missing prompt: $PROMPT_PATH"

export HERMES_HOME
export OPENROUTER_API_KEY
export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:${PATH}"

# ---------------------------------------------------------------------------
# Ensure Hermes
# ---------------------------------------------------------------------------
ensure_hermes() {
  if command -v hermes >/dev/null 2>&1; then
    notice "hermes: $(command -v hermes)"
    return
  fi
  notice "Installing Hermes Agent..."
  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
  export PATH="${HOME}/.local/bin:${HOME}/.hermes/bin:${PATH}"
  # shellcheck disable=SC1091
  [[ -f "${HOME}/.bashrc" ]] && source "${HOME}/.bashrc" || true
  hash -r 2>/dev/null || true
  for candidate in \
    "${HOME}/.local/bin/hermes" \
    "${HOME}/.hermes/bin/hermes" \
    "${HOME}/.hermes/hermes"; do
    if [[ -x "$candidate" ]]; then
      export PATH="$(dirname "$candidate"):${PATH}"
      break
    fi
  done
  command -v hermes >/dev/null 2>&1 || die "hermes not found after install"
  notice "hermes installed: $(command -v hermes)"
}

ensure_hermes

# ---------------------------------------------------------------------------
# Seed HERMES_HOME (preserve growing MEMORY.md)
# ---------------------------------------------------------------------------
cp -f "$LUFFY_ROOT/agent/config.yaml" "$HERMES_HOME/config.yaml"
cp -f "$LUFFY_ROOT/agent/SOUL.md" "$HERMES_HOME/SOUL.md"
umask 077
cat >"$HERMES_HOME/.env" <<EOF
OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
EOF

if [[ ! -f "$HERMES_HOME/memories/MEMORY.md" ]]; then
  if [[ -f "$LUFFY_ROOT/agent/MEMORY.seed.md" ]]; then
    cp -f "$LUFFY_ROOT/agent/MEMORY.seed.md" "$HERMES_HOME/memories/MEMORY.md"
  else
    printf '# Luffy review memory\n\n' >"$HERMES_HOME/memories/MEMORY.md"
  fi
fi

PROMPT="$(cat "$PROMPT_PATH")"
RAW_OUT="$OUT_DIR/review-${PR_NUMBER}.raw.md"
STDERR_FILE="$OUT_DIR/hermes-${PR_NUMBER}.stderr"
FINAL_OUT="$OUT_DIR/review-${PR_NUMBER}.md"

notice "Hermes review · model=$MODEL workspace=$WORKSPACE_ROOT hermes_home=$HERMES_HOME"

set +e
(
  cd "$WORKSPACE_ROOT"
  hermes -z "$PROMPT" \
    --provider openrouter \
    --model "$MODEL" \
    >"$RAW_OUT" 2>"$STDERR_FILE"
)
RC=$?
if [[ $RC -ne 0 || ! -s "$RAW_OUT" ]]; then
  notice "hermes -z failed or empty (rc=$RC); trying hermes chat -q"
  (
    cd "$WORKSPACE_ROOT"
    hermes chat -q "$PROMPT" \
      --provider openrouter \
      --model "$MODEL" \
      >"$RAW_OUT" 2>"$STDERR_FILE"
  )
  RC=$?
fi
set -e

if [[ $RC -ne 0 ]]; then
  notice "hermes exit=$RC"
  [[ -s "$STDERR_FILE" ]] && cat "$STDERR_FILE" >&2 || true
fi

if [[ ! -s "$RAW_OUT" ]]; then
  cat >"$RAW_OUT" <<EOF
## 🏴‍☠️ Luffy Review — PR #${PR_NUMBER}

**Verdict:** COMMENT
**Confidence:** low

### Summary
Luffy failed to produce a review (hermes exit ${RC}). Check workflow logs, Hermes install, and OpenRouter credits/key.

### Blocking
- Review agent run failed — re-trigger with \`@luffy review this pr\` after fixing CI/OpenRouter.

### Suggestions
- None

### Nits
- None

### Tests & risk
- Coverage: unknown
- Risk: unknown
- Rollback: n/a

### What I checked
- Agent runner only (no successful model response)

---
*Luffy · Hermes Agent · OpenRouter · memory-backed review*
EOF
fi

# Normalize into final review.md
python3 "$LUFFY_ROOT/scripts/normalize-review.py" \
  --input "$RAW_OUT" \
  --output "$FINAL_OUT" \
  --pr "$PR_NUMBER" \
  --run-id "${GITHUB_RUN_ID:-local}"

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "review_file=$FINAL_OUT"
    echo "raw_file=$RAW_OUT"
    echo "hermes_rc=$RC"
  } >>"$GITHUB_OUTPUT"
fi

echo "REVIEW_FILE=$FINAL_OUT"
notice "Review written: $FINAL_OUT ($(wc -c <"$FINAL_OUT" | tr -d ' ') bytes)"
