#!/bin/bash
# Grade the commit the agent made in /app.
# 1. Snapshot the result (new commits, message, diff, status) under /logs/verifier/.
# 2. Run the rewardkit criteria in /tests: structure/ (deterministic),
#    message/ and process/ (LLM judges). Scores land in /logs/verifier/reward.json.
set -uo pipefail

OUT=/logs/verifier
mkdir -p "$OUT"
BASE=c6f3b034f29220afa236737ab79d1228bdc9f3c0

# /app belongs to the agent user; the verifier runs as root.
git config --global --add safe.directory /app
cd /app

git log --format='%H' "$BASE"..HEAD > "$OUT/new_commits.txt" 2>/dev/null || true
git status --porcelain > "$OUT/status.txt" 2>/dev/null || true
if [ -s "$OUT/new_commits.txt" ]; then
    git log -1 --format='%B' HEAD > "$OUT/commit_message.txt"
    git log -1 --format='%an <%ae>' HEAD > "$OUT/commit_author.txt"
    git diff "$BASE" HEAD > "$OUT/commit.diff"
    git log --format='%h %s' "$BASE"..HEAD > "$OUT/commit_headers.txt"
else
    : > "$OUT/commit_message.txt"
    : > "$OUT/commit.diff"
    : > "$OUT/commit_headers.txt"
fi

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
