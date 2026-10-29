#!/bin/bash
# Grade the review the agent wrote in /app.
# 1. Snapshot the review and the PR under review under /logs/verifier/.
# 2. Without a review there is nothing to grade: score 0 everywhere.
# 3. Run the rewardkit judges in /tests: one per area of seeded issues (the
#    area's recall), and precision. Scores land in /logs/verifier/reward.json.
set -uo pipefail

OUT=/logs/verifier
mkdir -p "$OUT"

# /app belongs to the agent user; the verifier runs as root.
git config --global --add safe.directory /app
cd /app

cp /app/review.md "$OUT/review.md" 2>/dev/null || : > "$OUT/review.md"
BASE=c8d7430e3e15acc9224c53fe6c512414107897c3
SUBJECT="[ADD] equipment_booking: book shared equipment"
# The PR under review, for the precision judge.
git show --format='%s%n%n%b' "$(git rev-list -1 --fixed-strings --grep="$SUBJECT" HEAD)" > "$OUT/pr.diff" 2>/dev/null
{
    git status --porcelain --untracked-files=no
    [ "$(git log -1 --format=%s HEAD)" = "$SUBJECT" ] \
        || echo "HEAD is no longer the PR commit: $(git log -1 --format='%h %s' HEAD)"
    [ "$(git rev-parse -q --verify HEAD~1)" = "$BASE" ] || echo "the PR commit no longer sits on the base commit"
} > "$OUT/code_changes.txt" 2>&1

if ! grep -q '[^[:space:]]' "$OUT/review.md"; then
    echo "no /app/review.md: scoring 0" >&2
    python3 - "$OUT/reward.json" /tests/reward.toml <<'PY'
import json, re, sys
areas = re.findall(r'(\w+) = [0-9.]+', open(sys.argv[2]).read().split('weights', 1)[1])
json.dump({**{area: 0.0 for area in areas}, 'reward': 0.0}, open(sys.argv[1], 'w'))
PY
    exit 0
fi

export PATH="/usr/local/bin:$PATH"
uvx --from 'harbor-rewardkit==0.2.*' rewardkit /tests
