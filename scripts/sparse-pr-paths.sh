#!/usr/bin/env bash
# List PR changed paths for sparse-checkout (one path per line).
# Env: REPO, PR_NUMBER, GH_TOKEN|GITHUB_TOKEN
set -euo pipefail

REPO="${REPO:-${GITHUB_REPOSITORY:-}}"
PR_NUMBER="${PR_NUMBER:-}"
export GH_TOKEN="${GH_TOKEN:-${GITHUB_TOKEN:-}}"
export GH_REPO="$REPO"

[[ -n "$REPO" && -n "$PR_NUMBER" ]] || {
  echo "::error::REPO and PR_NUMBER required" >&2
  exit 1
}

# Leading slash = single-file path in git sparse-checkout --no-cone mode
gh pr view "$PR_NUMBER" --repo "$REPO" --json files \
  --jq '.files[].path' 2>/dev/null | head -400 | sed 's|^|/|'
