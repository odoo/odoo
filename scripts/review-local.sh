#!/usr/bin/env bash
# Local / manual Luffy review helper.
#
# Usage:
#   ./scripts/review-local.sh owner/repo 123
#   POST_COMMENT=1 ./scripts/review-local.sh owner/repo 123
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export LUFFY_ROOT="$ROOT"
export WORKSPACE_ROOT="${WORKSPACE_ROOT:-$ROOT}"
export OUT_DIR="${OUT_DIR:-$ROOT/.luffy-out}"
export HERMES_HOME="${HERMES_HOME:-$ROOT/.luffy-hermes-home}"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

if [[ $# -ge 2 ]]; then
  export REPO="${1}"
  export PR_NUMBER="${2}"
elif [[ $# -eq 1 ]]; then
  export PR_NUMBER="${1}"
  export REPO="${REPO:-${GITHUB_REPOSITORY:-}}"
fi

: "${REPO:?Usage: $0 owner/repo PR_NUMBER}"
: "${PR_NUMBER:?Usage: $0 owner/repo PR_NUMBER}"
: "${OPENROUTER_API_KEY:?Set OPENROUTER_API_KEY or put it in .env}"

export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "${GH_TOKEN}" ]] && command -v gh >/dev/null 2>&1; then
  if gh auth token >/dev/null 2>&1; then
    export GH_TOKEN="$(gh auth token)"
  fi
fi

"$ROOT/scripts/run-luffy-review.sh"

echo "Done. Review: $OUT_DIR/review-${PR_NUMBER}.md"
if [[ "${POST_COMMENT:-0}" != "1" ]]; then
  echo "Set POST_COMMENT=1 to post, or run:"
  echo "  ./scripts/post-review-comment.sh $OUT_DIR/review-${PR_NUMBER}.md $PR_NUMBER"
fi
