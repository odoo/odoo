#!/usr/bin/env bash
# Post Luffy's Markdown review as a GitHub PR comment.
#
# Usage:
#   ./scripts/post-review-comment.sh [review.md] [pr_number]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${OUT_DIR:-$ROOT/.luffy-out}"

log() { echo "$*" >&2; }
die() { echo "::error::$*" >&2; exit 1; }

REVIEW_FILE="${1:-${REVIEW_FILE:-}}"
PR_NUMBER="${2:-${PR_NUMBER:-}}"
REPO="${REPO:-${GITHUB_REPOSITORY:-}}"

if [[ -z "$REVIEW_FILE" ]]; then
  if compgen -G "$OUT_DIR/review-*.md" >/dev/null; then
    REVIEW_FILE="$(ls -t "$OUT_DIR"/review-*.md | grep -v '\.raw\.md$' | head -1)"
  else
    die "REVIEW_FILE not set and no review-*.md found"
  fi
fi

[[ -f "$REVIEW_FILE" ]] || die "Review file not found: $REVIEW_FILE"
[[ -n "$REPO" ]] || die "REPO or GITHUB_REPOSITORY must be set"

if [[ -z "$PR_NUMBER" ]]; then
  base="$(basename "$REVIEW_FILE")"
  if [[ "$base" =~ review-([0-9]+)\.md ]]; then
    PR_NUMBER="${BASH_REMATCH[1]}"
  elif [[ -n "${GITHUB_EVENT_PATH:-}" && -f "${GITHUB_EVENT_PATH}" ]]; then
    PR_NUMBER="$(python3 -c 'import json,os; e=json.load(open(os.environ["GITHUB_EVENT_PATH"])); print(e["issue"]["number"])')"
  else
    die "PR_NUMBER must be set"
  fi
fi

export GH_REPO="$REPO"
export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
command -v gh >/dev/null 2>&1 || die "gh CLI is required"

log "Posting review to $REPO#$PR_NUMBER from $REVIEW_FILE"
gh pr comment "$PR_NUMBER" --repo "$REPO" --body-file "$REVIEW_FILE"
log "Posted PR comment on #$PR_NUMBER"
