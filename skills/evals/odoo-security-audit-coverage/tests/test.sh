#!/bin/bash
# Grade the security review the agent wrote in /app.
# 1. Snapshot the review and any change to the module under /logs/verifier/.
# 2. Run the rewardkit criteria in /tests: structure/ (deterministic),
#    findings/ and process/ (LLM judges). Scores land in /logs/verifier/reward.json.
set -uo pipefail

OUT=/logs/verifier
mkdir -p "$OUT"

# /app belongs to the agent user; the verifier runs as root.
git config --global --add safe.directory /app
cd /app

cp /app/security_review.md "$OUT/security_review.md" 2>/dev/null || : > "$OUT/security_review.md"
BASE=c6f3b034f29220afa236737ab79d1228bdc9f3c0
{
    git status --porcelain -- addons/property_rental
    [ "$(git log -1 --format=%s HEAD)" = "[ADD] property_rental: rent properties to portal tenants" ] \
        || echo "HEAD is no longer the module commit: $(git log -1 --format='%h %s' HEAD)"
    [ "$(git rev-parse -q --verify HEAD~1)" = "$BASE" ] || echo "the module commit no longer sits on the base commit"
} > "$OUT/module_changes.txt" 2>&1

# The process judge reads the agent's ATIF trajectory. Without one (the oracle,
# or an agent whose session could not be converted) rewardkit would abort the
# whole grading, so that dimension is dropped from a staged copy of the criteria.
STAGE=$(mktemp -d)
cp -R /tests/. "$STAGE"
if [ ! -s /logs/agent/trajectory.json ]; then
    echo "no /logs/agent/trajectory.json: skipping the process dimension" >&2
    rm -rf "$STAGE/process"
    sed -i 's/, process = [0-9.]*//' "$STAGE/reward.toml"
fi

export PATH="/usr/local/bin:$PATH"
uvx --from 'harbor-rewardkit==0.2.*' rewardkit "$STAGE"
