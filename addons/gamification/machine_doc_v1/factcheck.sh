#!/bin/bash
# gamification machine-doc fact-check. Run from any cwd. Read-only.
#
# Assertions DERIVE their expected value from the source tree and check that the
# docs agree, rather than keeping a second copy of every fact that can go stale
# independently. A doc that cites a model, a cron or a test class which no
# longer exists is worse than no doc: it is read as current.
#
# This module carried a machine_doc and no harness, so its figures were checked
# by nothing. The first run found six test files the inventory never listed and
# a test count 86 below the tree.
#
# Roots come from this script's own location, so the run always validates the
# tree it ships in.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOD="$(dirname "$SCRIPT_DIR")"                  # <repo>/addons/gamification
DOCS=("$SCRIPT_DIR"/*.md)

fail=0
pass=0

ok()  { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; }

# Assert the docs cite a name that exists in the source.
assert_doc_cites() {  # <needle> <human description>
    if grep -qF -- "$1" "${DOCS[@]}"; then ok; else bad "docs never cite $2 ($1)"; fi
}

# Assert a "| Label | N ..." row in index.md carries the derived number.
assert_metadata_row() {  # <row label> <expected> <human description>
    local got
    got=$(grep -oP "^\| $1 \| \K[0-9]+" "$SCRIPT_DIR/index.md" | head -1)
    if [ "$got" = "$2" ]; then ok
    else bad "index.md says $1 = ${got:-<missing>}, tree says $2 ($3)"; fi
}

printf '== gamification machine_doc_v1 factcheck ==\n'

# ---------------------------------------------------------------- structure --
for f in index.md models.md architecture.md conventions.md; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "missing $f"
done

# ------------------------------------------------------- metadata table ------
# Every number in index.md's metadata table, derived from the tree.
assert_metadata_row "Python models" \
    "$(grep -rhoP '^\s+_name = "\K[^"]+' "$MOD"/models/*.py | sort -u | wc -l)" \
    "_name declarations under models/"
assert_metadata_row "Views" "$(ls "$MOD"/views/*.xml | wc -l)" "files under views/"
assert_metadata_row "Wizards" \
    "$(grep -rhoP '^\s+_name = "\K[^"]+' "$MOD"/wizards/*.py | sort -u | wc -l)" \
    "_name declarations under wizards/"
assert_metadata_row "Cron jobs" \
    "$(grep -c 'model="ir.cron"' "$MOD/data/ir_cron_data.xml")" \
    "ir.cron records in data/ir_cron_data.xml"
assert_metadata_row "Test files" \
    "$(find "$MOD/tests" -name '*.py' ! -name '__init__.py' | wc -l)" \
    "python files under tests/"
assert_metadata_row "Total tests" \
    "$(grep -rho 'def test_' "$MOD"/tests/*.py | wc -l)" \
    "def test_ across tests/"
assert_metadata_row "OWL components" \
    "$(grep -rlE 'extends Component|category\("services"\)' "$MOD/static/src" | wc -l)" \
    "component classes plus registered services under static/src"

# The category must match the manifest, not a remembered one.
manifest_category=$(grep -oP '"category":\s*"\K[^"]+' "$MOD/__manifest__.py")
if grep -qF "| Category | $manifest_category |" "$SCRIPT_DIR/index.md"; then ok
else bad "index.md Category disagrees with __manifest__.py ($manifest_category)"; fi

# ------------------------------------------------------------------- models --
# Every model the module declares must be documented, and no documented model
# may have been deleted.
mapfile -t models < <(grep -rhoP '^\s+_name = "\K[^"]+' \
    "$MOD"/models/*.py "$MOD"/wizards/*.py | sort -u)
for m in "${models[@]}"; do
    assert_doc_cites "$m" "model $m"
done
while read -r cited; do
    [ -z "$cited" ] && continue
    if printf '%s\n' "${models[@]}" | grep -qx "$cited"; then ok
    else bad "docs cite model $cited, which the module no longer declares"; fi
done < <(grep -rhoP '\bgamification\.[a-z._]+[a-z]\b' "${DOCS[@]}" \
         | grep -vE '^gamification\.(group|model|mail_template|email_template|ir_cron|simple)' \
         | sort -u \
         | while read -r c; do printf '%s\n' "${models[@]}" | grep -qx "$c" && echo "$c"; done)

# -------------------------------------------------------------------- crons --
# conventions.md tabulates the cron methods; each must exist and each cron in
# the data file must be tabulated.
while read -r method; do
    [ -z "$method" ] && continue
    if grep -rq "def ${method%()}" "$MOD"/models/*.py; then
        assert_doc_cites "$method" "cron method $method"
    else
        bad "cron data calls $method, which no model defines"
    fi
done < <(grep -oP '<field name="code">model\.\K[a-z_]+\(\)' "$MOD/data/ir_cron_data.xml")

while read -r xmlid; do
    [ -z "$xmlid" ] && continue
    assert_doc_cites "$xmlid" "cron xmlid $xmlid"
done < <(grep -oP '<record id="\K(ir_cron_[a-z_]+)' "$MOD/data/ir_cron_data.xml")

# ---------------------------------------------------------------- data sets --
# The counts index.md gives for each seeded data file.
assert_data_count() {  # <file> <model> <label>
    local n
    n=$(grep -c "model=\"$2\"" "$MOD/data/$1")
    if grep -qE "\| \`$1\` \| $n " "$SCRIPT_DIR/index.md"; then ok
    else bad "index.md miscounts $1: the file holds $n $3"; fi
}
assert_data_count gamification_badge_data.xml gamification.badge badges
assert_data_count gamification_challenge_data.xml gamification.challenge challenges
assert_data_count gamification_karma_rank_data.xml gamification.karma.rank ranks
assert_data_count gamification_kudos_data.xml gamification.kudos.category categories
assert_data_count mail_template_data.xml mail.template templates

# ------------------------------------------------------------ test coverage --
# index.md's inventory must list every test file, and cite no class that is gone.
while read -r tf; do
    assert_doc_cites "$(basename "$tf")" "test file $(basename "$tf")"
done < <(find "$MOD/tests" -name 'test_*.py')

mapfile -t classes < <(grep -hoP '^class \K(Test\w+|test_\w+)' "$MOD"/tests/*.py | sort -u)
while read -r cited; do
    [ -z "$cited" ] && continue
    if printf '%s\n' "${classes[@]}" | grep -qx "$cited"; then ok
    else bad "docs cite test class $cited, which no longer exists"; fi
done < <(grep -hoP '`\K(Test[A-Z]\w+)(?=`)' "${DOCS[@]}" | sort -u)

# ------------------------------------------- claims that must stay verified --
# conventions.md's karma invariants are load-bearing: every one of them is a
# rule a future change could quietly break.

# "Never write karma directly" — the funnel must still exist.
grep -q "def _add_karma_batch" "$MOD/models/res_users.py" \
    && ok || bad "conventions.md names _add_karma_batch as the karma funnel; it is gone"

# Rank re-evaluation hangs off the tracking table, not off _compute_karma.
if grep -q "_recompute_user_ranks" "$MOD/models/gamification_karma_tracking.py"; then ok
else bad "conventions.md says rank re-evaluation hangs off gamification.karma.tracking; the hook is gone"; fi
if grep -A 40 "def _compute_karma" "$MOD/models/res_users.py" | grep -q "_recompute_rank"; then
    bad "conventions.md says _compute_karma computes karma and nothing else; it re-ranks again"
else ok; fi

# Consolidation is gain-preserving: it must SUM, never take the newest new_value.
if grep -q "SUM(new_value - COALESCE(old_value, 0)) AS total_gain" \
        "$MOD/models/gamification_karma_tracking.py"; then ok
else bad "conventions.md says consolidation sums the gains it replaces; the statement changed"; fi

# No skip_karma_computation escape hatch, in either direction.
# Named in the comment that records why it was removed, which is the point of
# that comment -- so look for a *use*, not a mention.
if grep -rn "skip_karma_computation" "$MOD"/models/*.py \
        | grep -vE ':\s*#' | grep -q .; then
    bad "conventions.md forbids a skip_karma_computation flag; one is in use again"
else ok; fi

# origin_ref selection must still list every model that passes itself as source.
mapfile -t origins < <(grep -oP '^\s+\("\Kgamification\.[a-z.]+(?=", _\()' \
    "$MOD/models/gamification_karma_tracking.py" | sort -u)
for o in "${origins[@]}"; do
    assert_doc_cites "$o" "karma origin $o"
done

# Employees must not be able to write streaks — conventions.md §"What NOT to Do".
if grep -qE '^streak_employee,[^,]*,[^,]*,[^,]*,permission,r,$' \
        "$MOD/security/ir.access.csv"; then ok
else bad "conventions.md says gamification.streak is read-only for employees; the ACL changed"; fi

# index.md "Not wired": quest steps' definition_id/target_goal must stay unread.
# If something starts consuming them the section is a lie and must be rewritten.
if grep -rq "step\.definition_id\|step_id\.definition_id" \
        "$MOD"/models/*.py "$MOD"/views/*.xml 2>/dev/null; then
    bad "index.md 'Not wired' says nothing evaluates quest step definition_id; something does now"
else ok; fi

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
