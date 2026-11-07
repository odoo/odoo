#!/bin/bash
# Grade the feature the agent built in /app from the spec.
# 1. Snapshot the result (new commits, diff, status) under /logs/verifier/, and
#    find the modules it touches: the new ones (every __manifest__.py added
#    since the base commit, committed or not) and the existing ones it changed
#    (translations aside). Dump the new modules' sources (module_source.txt)
#    and the changes to existing modules (existing_changes.diff) for the
#    judges.
# 2. Run them, without relying on any name from the spec: install without and
#    with demo data, load every view, action and menu they declare, build the
#    backend assets, run their scheduled actions, upgrade them, run their
#    tests, check the syntax of their JS. Logs land in /logs/verifier/*.log.
# 3. Run the rewardkit criteria in /tests: runtime/ (deterministic, from those
#    logs), coverage/ (LLM judge: the spec's behaviours, against the original
#    module) and guidelines/ (LLM judge: the code against the house rules).
#    Scores land in /logs/verifier/reward.json.
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
git log --format='%h %s' "$BASE"..HEAD > "$OUT/commit_headers.txt" 2>/dev/null || true
# The whole change, including anything left uncommitted, so a module the agent
# forgot to commit is still graded.
git add -A -N . 2>/dev/null
git diff "$BASE" > "$OUT/change.diff" 2>/dev/null || true
git diff --name-only --diff-filter=A "$BASE" | grep -E '(^|/)__manifest__\.py$' \
    | xargs -r -n1 dirname | sort -u > "$OUT/module_dirs.txt"
# Existing modules the agent changed: a changed file under a directory that
# had a __manifest__.py at the base commit, translations aside.
git diff --name-only "$BASE" | grep -v '/i18n/' | while read -r path; do
    dir=$(dirname "$path")
    while [ "$dir" != "." ] && [ "$dir" != "/" ]; do
        if git cat-file -e "$BASE:$dir/__manifest__.py" 2>/dev/null; then echo "$dir"; break; fi
        dir=$(dirname "$dir")
    done
done | sort -u > "$OUT/existing_dirs.txt"
: > "$OUT/existing_changes.diff"
: > "$OUT/own_test_files.txt"
if [ -s "$OUT/existing_dirs.txt" ]; then
    git diff "$BASE" -- $(cat "$OUT/existing_dirs.txt") ':(exclude)*/i18n/*' > "$OUT/existing_changes.diff" 2>/dev/null || true
    # Test files the agent added to existing modules: their tests are its
    # own, like every test of a new module. A test in an existing file it
    # changed stays an existing test, checked against the base commit, so
    # editing a test cannot hide a regression.
    git diff --name-only --diff-filter=A "$BASE" -- $(cat "$OUT/existing_dirs.txt") | grep -E '/tests/.*\.py$' > "$OUT/own_test_files.txt" || true
fi
git reset -q 2>/dev/null

# The guidelines judge reads the spec: a deviation it forces is fine when the
# code comments it.
cp /home/odoo/spec.md "$OUT/spec.md" 2>/dev/null || : > "$OUT/spec.md"

MODULES=$(cat "$OUT/module_dirs.txt" "$OUT/existing_dirs.txt" | xargs -r -n1 basename | paste -sd, -)
echo "$MODULES" > "$OUT/modules.txt"
# The judges read every text file of the new modules, and the changes to the
# existing ones.
python3 /tests/odoo_checks/dump_sources.py /app $(sed 's#^#/app/#' "$OUT/module_dirs.txt") \
    > "$OUT/module_source.txt"

# No change to any module (the agent crashed or gave up): every dimension
# scores 0, and the judges are not called.
if [ -z "$MODULES" ]; then
    echo "no module changed in /app: every dimension scores 0" >&2
    echo '{"runtime": 0.0, "coverage": 0.0, "guidelines": 0.0, "design": 0.0, "reward": 0.0}' > "$OUT/reward.json"
    exit 0
fi

# The addons path: the checkout's, plus wherever the agent put its modules.
ADDONS=/app/addons,/app/odoo/addons
for parent in $(cat "$OUT/module_dirs.txt" "$OUT/existing_dirs.txt" | xargs -r -n1 dirname | sort -u); do
    case ",$ADDONS," in *",/app/$parent,"*) ;; *) ADDONS="$ADDONS,/app/$parent" ;; esac
done

as_odoo() { runuser -u odoo -- "$@"; }
odoo_bin() {  # odoo_bin <timeout> <db> <server|shell> <args...>
    local limit=$1 db=$2 command=$3; shift 3
    timeout "$limit" runuser -u odoo -- /venv/main/bin/python3 /app/odoo-bin "$command" \
        --addons-path="$ADDONS" -d "$db" --http-port 18069 "$@"
}
pg_isready -q || as_odoo pg_ctl -D "$PGDATA" -l "$PGDATA/server.log" -w start > /dev/null
as_odoo dropdb --if-exists eval_nodemo
as_odoo dropdb --if-exists eval_demo

odoo_bin 1200 eval_nodemo server -i "$MODULES" --stop-after-init > "$OUT/odoo_install.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_install.log"

odoo_bin 1200 eval_demo server --with-demo -i "$MODULES" --stop-after-init > "$OUT/odoo_install_demo.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_install_demo.log"

cp /tests/odoo_checks/check_module.py /tmp/eval_check_module.py && chmod 644 /tmp/eval_check_module.py
EVAL_MODULES="$MODULES" odoo_bin 900 eval_demo shell --shell-interface python --no-http \
    < /tmp/eval_check_module.py > "$OUT/odoo_checks.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_checks.log"

odoo_bin 900 eval_demo server -u "$MODULES" --stop-after-init > "$OUT/odoo_upgrade.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_upgrade.log"

TAGS=$(echo "$MODULES" | tr ',' '\n' | sed 's#^#/#' | paste -sd, -)
odoo_bin 1800 eval_demo server -u "$MODULES" --test-tags "$TAGS" --stop-after-init > "$OUT/odoo_tests.log" 2>&1
echo "exit code: $?" >> "$OUT/odoo_tests.log"

# Regressions: the agent's own tests (new modules, test files it added) are
# graded as they are. An existing test that fails is re-run on the base
# commit, the same way (the existing modules installed first, then updated
# with the tests), so that at-install tests see the same modules: one that
# fails there too is not the agent's doing.
NEW_MODULES=$(xargs -r -n1 basename < "$OUT/module_dirs.txt" | paste -sd, -)
EXISTING_MODULES=$(xargs -r -n1 basename < "$OUT/existing_dirs.txt" | paste -sd, -)
python3 /tests/odoo_checks/test_failures.py classify "$OUT/odoo_tests.log" "$OUT/own_test_files.txt" "$NEW_MODULES" \
    > "$OUT/test_results.json"
BASE_TAGS=$(python3 -c "import json, sys; print(json.load(open(sys.argv[1]))['base_tags'])" "$OUT/test_results.json")
: > "$OUT/base_failed.jsonl"
if [ -n "$BASE_TAGS" ] && [ -n "$EXISTING_MODULES" ]; then
    rm -rf /tmp/eval-base
    as_odoo git -C /app worktree add -q --detach /tmp/eval-base "$BASE" > "$OUT/odoo_tests_base.log" 2>&1
    BASE_ADDONS=$(echo "$ADDONS" | sed 's#/app/#/tmp/eval-base/#g')
    as_odoo dropdb --if-exists eval_base
    timeout 1800 runuser -u odoo -- /venv/main/bin/python3 /tmp/eval-base/odoo-bin server \
        --addons-path="$BASE_ADDONS" -d eval_base --http-port 18069 --with-demo \
        -i "$EXISTING_MODULES" --stop-after-init >> "$OUT/odoo_tests_base.log" 2>&1
    timeout 1800 runuser -u odoo -- /venv/main/bin/python3 /tmp/eval-base/odoo-bin server \
        --addons-path="$BASE_ADDONS" -d eval_base --http-port 18069 \
        -u "$EXISTING_MODULES" --test-tags "$BASE_TAGS" --stop-after-init >> "$OUT/odoo_tests_base.log" 2>&1
    echo "exit code: $?" >> "$OUT/odoo_tests_base.log"
    python3 /tests/odoo_checks/test_failures.py failed "$OUT/odoo_tests_base.log" > "$OUT/base_failed.jsonl"
    as_odoo dropdb --if-exists eval_base
    as_odoo git -C /app worktree remove --force /tmp/eval-base
fi

# JS syntax: the sources are ES modules; node checks each JS file of the new
# modules and each JS file the agent changed in existing ones.
: > "$OUT/js_check.log"
{
    while read -r dir; do
        find "/app/$dir/static" -name '*.js' -not -path '*/static/lib/*' 2>/dev/null
    done < "$OUT/module_dirs.txt"
    grep -E '^\+\+\+ b/.*/static/.*\.js$' "$OUT/existing_changes.diff" | sed 's#^+++ b/#/app/#'
} | sort -u | while read -r js; do
    [ -f "$js" ] || continue
    cp "$js" /tmp/eval_check.mjs
    if node --check /tmp/eval_check.mjs > /tmp/eval_check.out 2>&1; then
        echo "OK ${js#/app/}" >> "$OUT/js_check.log"
    else
        echo "FAIL ${js#/app/}: $(head -c 400 /tmp/eval_check.out | tr '\n' ' ')" >> "$OUT/js_check.log"
    fi
done

as_odoo dropdb --if-exists eval_nodemo
as_odoo dropdb --if-exists eval_demo

# odoo_checks/ holds Odoo code and helpers, not criteria.
STAGE=$(mktemp -d)
cp -R /tests/. "$STAGE"
rm -rf "$STAGE/odoo_checks"

export PATH="/usr/local/bin:$PATH"
uvx --from 'harbor-rewardkit==0.2.*' rewardkit "$STAGE"
