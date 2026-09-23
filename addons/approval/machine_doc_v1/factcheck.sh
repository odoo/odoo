#!/bin/bash
# approval machine-doc fact-check. Run from any cwd. Read-only.
#
# Every assertion DERIVES its expected value from the module and then checks
# that the docs agree. No expected value is written down here: a literal in
# this script would be a second copy of the tree, drifting independently of
# the first, which is why `addons/mail`'s harness is quarantined (CLAUDE.md §4)
# rather than trusted. Rule: `doc/coding_guidelines.rst` §1.4, a figure is
# gated or frozen, never bare.
#
# WHY THIS MODULE NEEDS ONE. `machine_doc_v1/` is the first thing CLAUDE.md
# tells a session to read, so its numbers become premises. Held by nothing,
# they drifted: the ACL summary stated `approval.test.document` carries "no ACL
# row at all" for a week during which it carried `1,1,1,1` for every internal
# user, and a session reading the security surface read a false one.
#
# Roots come from this script's own location, so a run always validates the
# tree it ships in.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Interpreter resolution + a scan that cannot fail silently. See the header of
# doc/machine_doc/factcheck_env.sh for what bare `"$PY"` did here.
_fc_root="$SCRIPT_DIR"
while [[ "$_fc_root" != "/" && ! -f "$_fc_root/odoo-bin" ]]; do
    _fc_root="$(dirname -- "$_fc_root")"
done
# shellcheck source=/dev/null
source "$_fc_root/doc/machine_doc/factcheck_env.sh"

MOD="$(dirname "$SCRIPT_DIR")"                  # <repo>/approval
DOCS=("$SCRIPT_DIR"/*.md)

fail=0
pass=0
skip=0

ok()   { pass=$((pass + 1)); }
bad()  { fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; }
note() { skip=$((skip + 1)); printf '  SKIP  %s\n' "$1"; }

# The docs must cite a string that was measured from the tree.
assert_doc_cites() {  # <needle> <human description>
    if grep -qF -- "$1" "${DOCS[@]}"; then ok; else bad "docs never cite $2 ($1)"; fi
}

# Same, but against one named document.
assert_cited_in() {  # <file> <needle> <human description>
    if grep -qF -- "$2" "$SCRIPT_DIR/$1"; then ok
    else bad "$1 never cites $3 ($2)"; fi
}

manifest_key() {  # <key>
    "$PY" - "$MOD/__manifest__.py" "$1" <<'PY'
import ast, sys
manifest = ast.literal_eval(open(sys.argv[1]).read())
value = manifest.get(sys.argv[2])
print(" ".join(value) if isinstance(value, list) else value)
PY
}

printf '== approval machine_doc_v1 factcheck ==\n'

# ---------------------------------------------------------------- structure --
for f in index.md architecture.md models.md conventions.md; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "missing $f"
done

# ----------------------------------------------------------------- manifest --
version="$(manifest_key version)"
assert_cited_in index.md "| Version | $version" "the manifest version"
for dep in $(manifest_key depends); do
    assert_doc_cites "$dep" "dependency $dep"
done

# ------------------------------------------------------------- file listing --
# Forward: every shipped Python file is named somewhere in the docs. A file
# that exists and is undocumented is the half of drift a reader cannot detect,
# because nothing in the document looks wrong.
for f in "$MOD"/models/*.py "$MOD"/wizards/*.py; do
    base="$(basename "$f")"
    [ "$base" = "__init__.py" ] && continue
    assert_doc_cites "$base" "source file $base"
done
for f in "$MOD"/tests/test_*.py; do
    assert_cited_in index.md "$(basename "$f")" "test file $(basename "$f")"
done

# Reverse, for source files only: a document naming a file that is gone reads
# as current and sends the reader looking for it. NOT applied to tests: the
# inventory deliberately records the incident-named files it dissolved
# (test_audit_regressions.py and friends) by name, and that history is the
# point of the paragraph.
while read -r cited; do
    [ -z "$cited" ] && continue
    if [ -f "$MOD/models/$cited" ] || [ -f "$MOD/wizards/$cited" ] \
       || [ -f "$MOD/reports/$cited" ]; then ok
    else bad "docs cite source file $cited, which no longer exists"; fi
done < <(grep -hoP '`\K(approval_\w+|approver_\w+|ir_attachment|mail_activity\w*|res_\w+)\.py(?=`)' \
    "${DOCS[@]}" | sort -u)

# ------------------------------------------------------------------- fields --
# Every field a model declares is named somewhere in the docs. This is the
# assertion whose absence let approval.rule drift: models.md carried a SECOND,
# older field table for it -- threshold_field/threshold_min, fields that exist
# nowhere -- while the live table was missing threshold_max and
# approval_minimum, which do. 151 assertions passed over both. A field table
# that is merely incomplete is the drift a reader cannot detect, the same
# argument the file listing above makes, one level down.
#
# `fields\.[A-Z]` and not `fields\.`: every Odoo field type is capitalised, and a
# local `rows = fields.get(...)` in a helper whose PARAMETER is called `fields` is not
# a field declaration. The scan reported one, and the answer was to stop shadowing the
# name AND to stop the pattern matching a lowercase attribute.
#
# Forward only. The reverse -- a documented field that no model declares --
# needs the field bound to its model to be decidable, and the docs name fields
# in prose as often as in tables, so it would report the prose as a defect.
while read -r field; do
    [ -z "$field" ] && continue
    assert_doc_cites "\`$field\`" "field $field"
done < <(grep -hoP '^    \K[a-z_][a-z0-9_]*(?= = fields\.[A-Z])' \
    "$MOD"/models/*.py "$MOD"/wizards/*.py | sort -u)

# ------------------------------------------------------------------- models --
# Every model the module declares must appear in models.md, and every
# approval.* model the docs name must exist.
mapfile -t declared < <(
    grep -rhoP '^\s+_name = "\K[^"]+' "$MOD"/models "$MOD"/wizards "$MOD"/reports | sort -u)
for model in "${declared[@]}"; do
    assert_cited_in models.md "$model" "model $model"
done
# Reverse, read off models.md's own section headings rather than every
# backticked token: the prose legitimately names field paths
# (`approval.request.amount`), XML ids (`approval.refusal_reason_auto_rule`)
# and config parameters (`approval.sequence.tier`), none of which are models.
# The headings are where a model is documented, so they are what must match.
mapfile -t documented < <(
    grep -oP '^## \K[a-z][a-z._]*' "$SCRIPT_DIR/models.md" | sort -u)
for model in "${documented[@]}"; do
    if printf '%s\n' "${declared[@]}" | grep -qx "$model"; then ok
    else bad "models.md documents $model, which the module does not declare"; fi
done

# No document may name a model this module used to declare and no longer does.
# The heading check above only sees `models.md`'s sections: when
# `approval.tier` was retired its heading went, and eleven stale mentions
# survived in field tables, the ACL summary and the architecture prose — the
# half of drift a reader cannot detect, because the sentence around it still
# reads as current.
for retired in approval.tier; do
    if grep -rqE "^\s+_name = \"$retired\"" "$MOD"/models "$MOD"/wizards "$MOD"/reports
    then
        bad "$retired is listed as retired but the module still declares it"
    else
        # PER LINE. The first version of this asked whether the docs contained
        # a history note anywhere, which one note at the top exempted the
        # whole tree from -- it passed against a deliberately planted stale
        # sentence. Every line naming a retired model must say `former`.
        stray=$(grep -rc "\`$retired\`" "${DOCS[@]}" 2>/dev/null | \
                awk -F: '{n+=$2} END {print n+0}')
        noted=$(grep -rc "former \`$retired\`" "${DOCS[@]}" 2>/dev/null | \
                awk -F: '{n+=$2} END {print n+0}')
        if [ "$stray" -ne "$noted" ]; then
            bad "$((stray - noted)) line(s) name the retired model $retired without marking it as former"
        else
            ok
        fi
    fi
done

# ------------------------------------------------------------------- counts --
# Stated in prose AND in the Key Statistics table, so both spellings are
# checked: a number corrected in one place and not the other is the drift
# this harness exists to catch.
# Directories holding a script, not directories: renaming the migration
# directories left 18 of the old names alive in a working checkout, each
# empty but for a __pycache__ of the script that moved away. git cannot see
# them (a directory of ignored files is not a path), so this read 19 in a
# fresh clone and 37 next to a tree someone had actually run -- a gate whose
# answer depends on that is not measuring the repository.
migrations=$(find "$MOD/migrations" -mindepth 2 -maxdepth 2 -name "*.py" \
    -not -path "*/__pycache__/*" -printf "%h\n" | sort -u | wc -l)
assert_doc_cites "$migrations script directories" "the migration directory count"
assert_cited_in index.md "| Migration script directories | $migrations |" \
    "the migration count in Key Statistics"

test_files=$(find "$MOD/tests" -maxdepth 1 -name 'test_*.py' | wc -l)
assert_doc_cites "$test_files test modules" "the test module count"
assert_cited_in index.md "| Python test files | $test_files (+ \`common.py\`) |" \
    "the test file count in Key Statistics"

own_models=$(grep -rhcP '^\s+_name = "' "$MOD"/models/*.py | paste -sd+ | bc)
assert_cited_in index.md "| ORM models (new) | $own_models in \`models/\`" \
    "the own-model count"

crons=$(grep -c 'model="ir.cron"' "$MOD/data/ir_cron_data.xml")
assert_cited_in index.md "| Cron jobs | $crons |" "the cron count"

groups=$(grep -c 'model="res.groups"' "$MOD/security/res_groups.xml")
assert_doc_cites "$groups groups" "the security group count"

# ------------------------------------------------- claims that must stay true --
# index.md promises the mixin's concrete test consumer is not shipped from
# here. It was, until 2026-09-02, and for a week before 2026-08-18 it also
# carried 1,1,1,1 for every internal user while conventions.md said it carried
# no ACL row at all. Both halves are asserted here, because the thing that
# failed was the DOCUMENT, and only a doc harness can catch that.
if grep -rq '_name = "approval.test.document"' "$MOD/models/"
then bad "index.md says approval.test.document lives in test_approval; this module declares it"
else ok; fi
[ -f "$MOD/security/ir.access.csv" ] && ok || bad "security/ir.access.csv is gone; the check below reads nothing"
if grep -q ',model_approval_test_document,' "$MOD/security/ir.access.csv"
then bad "index.md says approval.test.document has NO access row here; it has one"
else ok; fi

# The state machine the docs describe, read off the source rather than retyped.
terminal=$(grep -oP '_TERMINAL_STATES = frozenset\(\{\K[^}]+' \
    "$MOD/models/approval_request.py" | tr -d ' "' )
for state in ${terminal//,/ }; do
    [ -z "$state" ] && continue
    assert_doc_cites "$state" "terminal state $state"
done
grep -q '_DECISION_STATES = frozenset' "$MOD/models/approval_request.py" \
    && ok || bad "docs describe _DECISION_STATES as the approval-rate denominator; it is gone"

# The approver-ordering defaults index.md tabulates, derived from the data file.
while read -r param; do
    [ -z "$param" ] && continue
    value=$("$PY" - "$MOD/data/ir_config_parameter_data.xml" "$param" <<'PY'
import re, sys
xml = open(sys.argv[1]).read()
block = re.search(
    r'<record[^>]*>(?:(?!</record>).)*?%s(?:(?!</record>).)*?</record>' % re.escape(sys.argv[2]),
    xml, re.S)
value = re.search(r'name="value"[^>]*>([^<]+)<', block.group(0)) if block else None
print(value.group(1).strip() if value else "")
PY
)
    if [ -z "$value" ]; then
        bad "cannot read a value for $param out of ir_config_parameter_data.xml"
    else
        assert_cited_in index.md "\`${param#approval.sequence.}\` $value" \
            "the $param default"
    fi
done < <(grep -oP 'approval\.sequence\.\w+' "$MOD/data/ir_config_parameter_data.xml" | sort -u)

# Extension points index.md advertises must still exist to be extended.
while read -r hook; do
    [ -z "$hook" ] && continue
    if grep -rqF "def $hook" "$MOD"/models "$MOD"/wizards "$MOD"/reports; then ok
    else bad "index.md advertises extension point $hook(), which no longer exists"; fi
done < <(sed -n '/^## Extension Points/,$p' "$SCRIPT_DIR/index.md" \
    | grep -oP '^- `\K_\w+(?=\(\))' | sort -u)

printf '\n%d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ]
