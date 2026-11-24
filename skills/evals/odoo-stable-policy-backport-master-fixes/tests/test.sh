#!/bin/bash
# Grade the commits the agent made in /app.
# 1. Snapshot the result (new commits, diff) under /logs/verifier/.
# 2. Replay a stable deployment: install l10n_it_stock_ddt and mrp_account with
#    the base code, then switch to the agent's code and check the installed
#    picking form and the DDT sequence renaming
#    - after a plain restart, without updating any module (the stable case);
#    - after `-u l10n_it_stock_ddt,mrp_account`, which also runs both modules'
#      tests, with the agent's own test changes.
#    Logs land in /logs/verifier/odoo_*.log.
# 3. Run the rewardkit criteria in /tests: build/ and stable/ (deterministic),
#    review/ (LLM judge). Scores land in /logs/verifier/reward.json.
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
git log --format='%h %an %s' "$BASE"..HEAD > "$OUT/commit_headers.txt" 2>/dev/null || true
# The committed change, and the whole change including anything left uncommitted,
# so a fix the agent forgot to commit is still graded as a fix.
git diff "$BASE" HEAD > "$OUT/commit.diff" 2>/dev/null || true
git add -A -N . 2>/dev/null
git diff "$BASE" > "$OUT/change.diff" 2>/dev/null || true
git reset -q 2>/dev/null

# An agent that changed nothing (it crashed, ran out of quota, or gave up) gets
# 0 on every dimension: the "did not break the policy" checks would otherwise
# pass on an empty change. The judges are not called.
if [ ! -s "$OUT/change.diff" ] && [ ! -s "$OUT/new_commits.txt" ]; then
    echo "no change in /app: every dimension scores 0" >&2
    echo '{"build": 0.0, "stable": 0.0, "review": 0.0, "reward": 0.0}' > "$OUT/reward.json"
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
cp /tests/odoo_checks/check_ddt.py /tmp/eval_check_ddt.py && chmod 644 /tmp/eval_check_ddt.py

odoo_bin 1500 /tmp/eval-base server -i l10n_it_stock_ddt,mrp_account --stop-after-init >> "$OUT/odoo_install.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_install.log"

odoo_bin 300 /app shell --shell-interface python --no-http < /tmp/eval_check_ddt.py \
    > "$OUT/odoo_no_update.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_no_update.log"

# The update logs the duplicate-label warning if it is still there, then the
# tests of both modules run (the DDT tests are post_install).
odoo_bin 1500 /app server -u l10n_it_stock_ddt,mrp_account --stop-after-init \
    --test-tags '/l10n_it_stock_ddt,/mrp_account:TestMrpAccount' \
    > "$OUT/odoo_update_tests.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_update_tests.log"
odoo_bin 300 /app shell --shell-interface python --no-http < /tmp/eval_check_ddt.py \
    > "$OUT/odoo_after_update.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_after_update.log"
as_odoo git -C /app worktree remove --force /tmp/eval-base

# odoo_checks/ holds Odoo code, not criteria: grade from a staged copy without it.
STAGE=$(mktemp -d)
cp -R /tests/. "$STAGE"
rm -rf "$STAGE/odoo_checks"

export PATH="/usr/local/bin:$PATH"
uvx --from 'harbor-rewardkit==0.2.*' rewardkit "$STAGE"
