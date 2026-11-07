#!/bin/bash
# Grade the fix the agent committed in /app.
# 1. Snapshot the result (new commits, message, diff, status) under /logs/verifier/.
# 2. Replay a stable deployment: install test_mail with the base code, then
#    switch to the agent's code and check a tracking email
#    - after a plain restart, without updating any module (the stable case);
#    - after `-u mail`;
#    then run the tracking tests. Logs land in /logs/verifier/odoo_*.log.
# 3. Run the rewardkit criteria in /tests: structure/, stable/ and behavior/
#    (deterministic), fix/, message/ and process/ (LLM judges). Scores land in
#    /logs/verifier/reward.json.
set -uo pipefail

OUT=/logs/verifier
mkdir -p "$OUT"

# /app belongs to the agent user; the verifier runs as root.
git config --global --add safe.directory /app
cd /app
# The checkout is a single commit: the base is the root.
BASE=$(git rev-list --max-parents=0 HEAD | tail -1)
echo "$BASE" > "$OUT/base_commit.txt"

git log --format='%H' "$BASE"..HEAD > "$OUT/new_commits.txt" 2>/dev/null || true
git status --porcelain > "$OUT/status.txt" 2>/dev/null || true
git log -1 --format='%B' HEAD > "$OUT/commit_message.txt" 2>/dev/null || true
git log --format='%h %s' "$BASE"..HEAD > "$OUT/commit_headers.txt" 2>/dev/null || true
# The committed change, and the whole change including anything left uncommitted,
# so a fix the agent forgot to commit is still graded as a fix.
git diff "$BASE" HEAD > "$OUT/commit.diff" 2>/dev/null || true
git add -A -N . 2>/dev/null
git diff "$BASE" > "$OUT/change.diff" 2>/dev/null || true
git reset -q 2>/dev/null
if [ ! -s "$OUT/new_commits.txt" ]; then
    : > "$OUT/commit_message.txt"
    : > "$OUT/commit_headers.txt"
fi

# An agent that changed nothing (it crashed, ran out of quota, or gave up) gets
# 0 on every dimension: the "did not break the policy" checks would otherwise
# pass on an empty change. The judges are not called.
if [ ! -s "$OUT/change.diff" ] && [ ! -s "$OUT/new_commits.txt" ]; then
    echo "no change in /app: every dimension scores 0" >&2
    echo '{"deploy": 0.0, "behavior": 0.0, "stable": 0.0, "fix": 0.0, "structure": 0.0, "message": 0.0, "process": 0.0, "reward": 0.0}' > "$OUT/reward.json"
    exit 0
fi

# The stable deployment: a database installed with the base code, then the
# agent's code started on it as is, as after a pull and a restart.
as_odoo() { runuser -u odoo -- "$@"; }
odoo_bin() {  # odoo_bin <timeout> <tree> <server|shell> <args...>
    local limit=$1 tree=$2 command=$3; shift 3
    timeout "$limit" runuser -u odoo -- /venv/main/bin/python3 "$tree/odoo-bin" "$command" \
        --addons-path="$tree/addons" -d eval_verifier --http-port 18069 "$@"
}
pg_isready -q || as_odoo pg_ctl -D "$PGDATA" -l "$PGDATA/server.log" -w start > /dev/null
as_odoo dropdb --if-exists eval_verifier
rm -rf /tmp/eval-base
as_odoo git -C /app worktree add -q --detach /tmp/eval-base "$BASE" > "$OUT/odoo_install.log" 2>&1
cp /tests/odoo_checks/check_email.py /tmp/eval_check_email.py && chmod 644 /tmp/eval_check_email.py

odoo_bin 1200 /tmp/eval-base server -i test_mail --stop-after-init >> "$OUT/odoo_install.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_install.log"

odoo_bin 300 /app shell --shell-interface python --no-http < /tmp/eval_check_email.py \
    > "$OUT/odoo_no_update.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_no_update.log"

odoo_bin 900 /app server -u mail --stop-after-init > "$OUT/odoo_update.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_update.log"
odoo_bin 300 /app shell --shell-interface python --no-http < /tmp/eval_check_email.py \
    >> "$OUT/odoo_update.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_update.log"

odoo_bin 1200 /app server -u test_mail --stop-after-init \
    --test-tags '/test_mail:TestTrackingAPI,/test_mail:TestTrackingTemplate,/test_mail:TestTrackingInternals,/test_mail:TestWebPushNotification' \
    > "$OUT/odoo_tests.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_tests.log"
as_odoo git -C /app worktree remove --force /tmp/eval-base

# odoo_checks/ holds Odoo code, not criteria. The process judge reads the agent's
# ATIF trajectory. Without one (the oracle, or an agent whose session could not
# be converted) rewardkit would abort the whole grading, so that dimension is
# dropped from a staged copy of the criteria.
STAGE=$(mktemp -d)
cp -R /tests/. "$STAGE"
rm -rf "$STAGE/odoo_checks"
if [ ! -s /logs/agent/trajectory.json ]; then
    echo "no /logs/agent/trajectory.json: skipping the process dimension" >&2
    rm -rf "$STAGE/process"
    sed -i 's/, process = [0-9.]*//' "$STAGE/reward.toml"
fi

export PATH="/usr/local/bin:$PATH"
uvx --from 'harbor-rewardkit==0.2.*' rewardkit "$STAGE"
