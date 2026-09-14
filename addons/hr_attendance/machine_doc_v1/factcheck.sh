#!/bin/bash
# hr_attendance machine-doc fact-check. Run from any cwd. Read-only.
#
# Every assertion DERIVES its expected value from the module and then checks
# that the docs agree. No expected value is written down here: a literal in
# this script would be a second copy of the tree, drifting independently of
# the first. Rule: `doc/coding_guidelines.rst` §1.4, a figure is gated or
# frozen, never bare.
#
# WHY THIS MODULE NEEDS ONE. CLAUDE.md sends a session to `machine_doc_v*/`
# before it reads any code, so these numbers become premises for work that
# never revisits them. This module in particular states its contracts as
# figures -- three fixed-point passes, thirteen routes, two crons, four
# loggers -- and every one of them is a claim about code that moves.
#
# Roots come from this script's own location, so a run always validates the
# tree it ships in.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_fc_root="$SCRIPT_DIR"
while [[ "$_fc_root" != "/" && ! -f "$_fc_root/odoo-bin" ]]; do
    _fc_root="$(dirname -- "$_fc_root")"
done
# shellcheck source=/dev/null
source "$_fc_root/doc/machine_doc/factcheck_env.sh"

MOD="$(dirname "$SCRIPT_DIR")"                  # <repo>/addons/hr_attendance
DOCS=("$SCRIPT_DIR"/*.md)

fail=0
pass=0
skip=0

ok()   { pass=$((pass + 1)); }
bad()  { fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; }
note() { skip=$((skip + 1)); printf '  SKIP  %s\n' "$1"; }

assert_doc_cites() {  # <needle> <human description>
    if grep -qF -- "$1" "${DOCS[@]}"; then ok; else bad "docs never cite $2 ($1)"; fi
}

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

printf '== hr_attendance machine_doc_v1 factcheck ==\n'

# ---------------------------------------------------------------- structure --
for f in index.md architecture.md models.md conventions.md; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "missing $f"
done

# ----------------------------------------------------------------- manifest --
version="$(manifest_key version)"
assert_cited_in index.md "| Version | $version |" "the manifest version"
assert_cited_in index.md "| License | $(manifest_key license) |" "the licence"
for dep in $(manifest_key depends); do
    assert_cited_in index.md "\`$dep\`" "dependency $dep"
done
# Reverse: a dependency the docs advertise and the manifest dropped sends a
# reader looking for an integration that is not there.
while read -r cited; do
    [ -z "$cited" ] && continue
    if manifest_key depends | tr ' ' '\n' | grep -qx "$cited"; then ok
    else bad "index.md lists $cited as a dependency; the manifest does not"; fi
done < <(sed -n 's/^| Dependencies |//p' "$SCRIPT_DIR/index.md" \
    | grep -oP '`\K[a-z_]+(?=`)' | sort -u)

# ------------------------------------------------------------- file listing --
# Forward: every shipped Python source file is named somewhere in the docs. A
# file that exists and is undocumented is the half of drift a reader cannot
# detect, because nothing in the document looks wrong.
for f in "$MOD"/models/*.py "$MOD"/controllers/*.py "$MOD"/tools/*.py; do
    base="$(basename "$f")"
    [ "$base" = "__init__.py" ] && continue
    assert_doc_cites "$base" "source file $base"
done
for f in "$MOD"/tests/test_*.py; do
    assert_cited_in index.md "$(basename "$f")" "test file $(basename "$f")"
done

# Reverse, source files only.
while read -r cited; do
    [ -z "$cited" ] && continue
    if [ -f "$MOD/models/$cited" ] || [ -f "$MOD/controllers/$cited" ] \
       || [ -f "$MOD/tools/$cited" ] || [ -f "$MOD/tests/$cited" ]; then ok
    else bad "docs cite source file $cited, which no longer exists"; fi
done < <(grep -hoP '`\K(?:[a-z_]+/)?[a-z_][a-z0-9_]*\.py(?=`)' "${DOCS[@]}" \
    | xargs -rn1 basename | sort -u)

# Every backticked MODULE-RELATIVE path resolves. `odoo/CLAUDE.md` makes this
# the repo's convention: a backticked path in a machine doc asserts that the
# file exists, so a deliberately-absent one is named in plain prose. A sibling
# repo's path (`enterprise/...`) is outside this tree and is skipped, not
# silently passed -- it is counted as a skip so the summary says so.
while read -r cited; do
    [ -z "$cited" ] && continue
    case "$cited" in
        enterprise/*|addons/*|odoo/*|@*) note "path outside this module: $cited"; continue ;;
    esac
    if [ -e "$MOD/${cited%/}" ]; then ok
    else bad "docs cite \`$cited\`, which does not exist under the module"; fi
done < <(grep -hoP '`\K[a-z_@][A-Za-z0-9_./-]*/[A-Za-z0-9_./-]*(?=`)' "${DOCS[@]}" | sort -u)

# ------------------------------------------------------------------- models --
# `_name` alone does not mean "new": hr_version.py redeclares hr.version with
# hr.version in its own _inherit, the extension idiom. A count that misses that
# reads 5 where the module owns 4, and the reader concludes an extension is a
# model of ours.
mapfile -t declared < <("$PY" - "$MOD" <<'PY'
import ast, pathlib, sys
for path in sorted(pathlib.Path(sys.argv[1], "models").glob("*.py")):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        assigned = {}
        for statement in node.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
                if isinstance(target, ast.Name):
                    try:
                        assigned[target.id] = ast.literal_eval(statement.value)
                    except ValueError:
                        pass
        name = assigned.get("_name")
        inherit = assigned.get("_inherit") or []
        if isinstance(inherit, str):
            inherit = [inherit]
        if name and name not in inherit:
            print(name)
PY
)
for model in "${declared[@]}"; do
    assert_cited_in models.md "$model" "model $model"
    assert_cited_in index.md "\`$model\`" "model $model in the ownership table"
done
own_models=${#declared[@]}
assert_cited_in index.md "| ORM models (new) | $own_models in \`models/\` |" \
    "the own-model count"

# Reverse, off models.md's own headings: the prose names field paths and xml
# ids too, so only a heading is a claim that this module documents a model.
mapfile -t documented < <(
    grep -oP '^## \K(hr|res|ir)\.[a-z._]*' "$SCRIPT_DIR/models.md" | sort -u)
for model in "${documented[@]}"; do
    if grep -rqE "^\s+_(name|inherit) = [\"'\[]" "$MOD/models" \
       && grep -rqF "\"$model\"" "$MOD/models"; then ok
    else bad "models.md documents $model, which the module never names"; fi
done

# Every model this module EXTENDS, and separately every mixin it MIXES IN.
# Not the same list and not the same claim: `mixin.mail.thread` on
# `hr.attendance` is a capability this module takes on, while `res.company` is
# a model it changes for everybody. Lumping them reads as seven extensions and
# sends a reader looking for what this module did to the mail mixin.
mapfile -t extended < <("$PY" - "$MOD" extend <<'CLASSIFY'
import ast, pathlib, sys
extends, mixes = set(), set()
for path in sorted(pathlib.Path(sys.argv[1], "models").glob("*.py")):
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.ClassDef):
            continue
        assigned = {}
        for statement in node.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
                if isinstance(target, ast.Name):
                    try:
                        assigned[target.id] = ast.literal_eval(statement.value)
                    except ValueError:
                        pass
        inherit = assigned.get("_inherit") or []
        if isinstance(inherit, str):
            inherit = [inherit]
        name = assigned.get("_name")
        (mixes if name and name not in inherit else extends).update(inherit)
print("\n".join(sorted(extends if sys.argv[2] == "extend" else mixes)))
CLASSIFY
)
for model in "${extended[@]}"; do
    assert_cited_in index.md "\`$model\`" "extended model $model"
done
mapfile -t mixins < <("$PY" - "$MOD" mix <<'CLASSIFY'
import ast, pathlib, sys
extends, mixes = set(), set()
for path in sorted(pathlib.Path(sys.argv[1], "models").glob("*.py")):
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, ast.ClassDef):
            continue
        assigned = {}
        for statement in node.body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
                if isinstance(target, ast.Name):
                    try:
                        assigned[target.id] = ast.literal_eval(statement.value)
                    except ValueError:
                        pass
        inherit = assigned.get("_inherit") or []
        if isinstance(inherit, str):
            inherit = [inherit]
        name = assigned.get("_name")
        (mixes if name and name not in inherit else extends).update(inherit)
print("\n".join(sorted(extends if sys.argv[2] == "extend" else mixes)))
CLASSIFY
)
for model in "${mixins[@]}"; do
    assert_doc_cites "\`$model\`" "mixin $model"
done

# ------------------------------------------------------------------- fields --
# Every field every model declares is named somewhere in the docs. A field
# table that is merely incomplete is drift a reader cannot detect: the table
# around the hole still reads as current.
#
# `fields\.[A-Z]`, not `fields\.`: every Odoo field type is capitalised, and a
# local `vals = fields.get(...)` is not a field declaration.
while read -r field; do
    [ -z "$field" ] && continue
    assert_doc_cites "\`$field\`" "field $field"
done < <(grep -hoP '^    \K[a-z_][a-z0-9_]*(?= = fields\.[A-Z])' \
    "$MOD"/models/*.py | sort -u)

# ------------------------------------------------------------------- counts --
model_files=$(find "$MOD/models" -maxdepth 1 -name '*.py' \
    -not -name '__init__.py' | wc -l)
assert_cited_in index.md "| Python model files | $model_files |" \
    "the model file count"

test_files=$(find "$MOD/tests" -maxdepth 1 -name 'test_*.py' | wc -l)
assert_cited_in index.md "| Python test files | $test_files |" \
    "the test file count"

routes=$(grep -c '@http\.route' "$MOD/controllers/main.py")
assert_cited_in index.md "| HTTP routes | $routes |" "the route count"

# The two entry points index.md names by URL. A route renamed without the doc
# following it sends an integrator to a 404, and the count above would not move.
while read -r path; do
    [ -z "$path" ] && continue
    if grep -qF "\"$path\"" "$MOD/controllers/main.py"; then ok
    else bad "index.md names the route $path, which controllers/main.py does not serve"; fi
done < <(grep -hoP '`\K/hr_attendance/[a-z_]+(?=`)' "${DOCS[@]}" | sort -u)

crons=$(grep -rhc 'model="ir.cron"' "$MOD"/data/*.xml | paste -sd+ | bc)
assert_cited_in index.md "| Cron jobs | $crons |" "the cron count"

groups=$(grep -rhc 'model="res.groups"' "$MOD"/security/*.xml | paste -sd+ | bc)
assert_cited_in index.md "| Security groups | $groups |" "the group count"

js_files=$(find "$MOD/static/src" -name '*.js' | wc -l)
assert_cited_in index.md "| JavaScript source files | $js_files |" \
    "the JS source count"

# Migration directories holding a script, not directories: an emptied one
# survives in a working checkout as a `__pycache__` git cannot see, so a count
# of directories reads differently in a fresh clone and next to a tree someone
# has run.
migrations=$(find "$MOD/migrations" -mindepth 2 -maxdepth 2 -name '*.py' \
    -not -path '*/__pycache__/*' -printf '%h\n' | sort -u | wc -l)
assert_cited_in index.md "| Migration script directories | $migrations |" \
    "the migration count"
while read -r dir; do
    [ -z "$dir" ] && continue
    assert_cited_in index.md "| \`$dir\` |" "migration $dir"
done < <(find "$MOD/migrations" -mindepth 2 -maxdepth 2 -name '*.py' \
    -not -path '*/__pycache__/*' -printf '%h\n' | xargs -rn1 basename | sort -u)

# --------------------------------------------------------------------- crons --
# Named by xml id, so a rename cannot leave the table describing a job that no
# scheduler will ever run.
while read -r cron_id; do
    [ -z "$cron_id" ] && continue
    assert_cited_in index.md "\`$cron_id\`" "cron $cron_id"
done < <(grep -B1 'model="ir.cron"' "$MOD"/data/*.xml \
    | grep -oP 'id="\K[^"]+' | sort -u)

# The methods those crons call must exist. A cron whose `code` names a gone
# method fails at 2am in a log nobody reads.
while read -r method; do
    [ -z "$method" ] && continue
    if grep -rqE "def $method\\(" "$MOD/models"; then ok
    else bad "a cron calls $method(), which no model defines"; fi
done < <(grep -oP '_cron_\w+' "$MOD"/data/*.xml | cut -d: -f2 | sort -u)

# ------------------------------------------------- claims that must stay true --

# "One attendance, one zone": the pair conventions.md names, and the cap it
# states, read off the source rather than retyped.
passes=$(grep -oP '_SCHEDULE_VERSION_PASSES = \K\d+' "$MOD/models/hr_attendance.py")
if [ -z "$passes" ]; then
    bad "conventions.md describes _SCHEDULE_VERSION_PASSES; it is gone"
else
    case "$passes" in
        3) assert_cited_in conventions.md "at most \`_SCHEDULE_VERSION_PASSES\` times" \
               "the fixed-point cap" ;;
        *) bad "_SCHEDULE_VERSION_PASSES is $passes; conventions.md says three" ;;
    esac
fi

# The `[False]` rule. Both halves: the flexible guard and the key.
#
# Read off the function's own AST, not a fixed window of lines after its
# `def`, and with the DOCSTRINGS STRIPPED. Both halves were learned from a
# mutation test of this harness:
#
#   grep -A12       -- the docstring explaining WHY the guard is there had
#                      already pushed the guard past line 12, so the gate
#                      failed on documented code and passed on bare code.
#   docstring kept  -- replacing the guard's condition with `False` still
#                      PASSED, because the docstring names `_is_flexible()`.
#                      A check that a prose mention satisfies is not a check
#                      on the code; it is a second doc assertion wearing the
#                      code assertion's name.
body_of() {  # <file> <function>  -> its source, docstrings removed
    "$PY" - "$1" "$2" <<'SEGMENT'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if not (isinstance(node, ast.FunctionDef) and node.name == sys.argv[2]):
        continue
    for inner in ast.walk(node):
        if not isinstance(inner, ast.ClassDef | ast.FunctionDef
                          | ast.AsyncFunctionDef | ast.Module):
            continue
        if (inner.body and isinstance(inner.body[0], ast.Expr)
                and isinstance(inner.body[0].value, ast.Constant)
                and isinstance(inner.body[0].value.value, str)):
            inner.body.pop(0)
            if not inner.body:
                inner.body.append(ast.Pass())
    print(ast.unparse(node))
    break
SEGMENT
}
lunch=$(body_of "$MOD/models/hr_attendance.py" _lunch_intervals)
if [ -z "$lunch" ]; then
    bad "conventions.md describes _lunch_intervals(); hr.attendance has no such method"
else
    printf '%s' "$lunch" | grep -q '_is_flexible()' \
        && ok || bad "conventions.md says _lunch_intervals guards on _is_flexible(); it does not"
    printf '%s' "$lunch" | grep -qF ')[False]' \
        && ok || bad "conventions.md says _lunch_intervals reads the [False] key; it does not"
fi

# The deferral, and the cron that deliberately does not use it.
grep -qE 'def _deferring_overtime\(' "$MOD/models/hr_attendance.py" \
    && ok || bad "conventions.md describes _deferring_overtime(); it is gone"
if "$PY" - "$MOD/models/hr_attendance.py" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "_cron_absence_detection":
        for inner in ast.walk(node):
            if isinstance(inner, ast.Attribute) and inner.attr == "_deferring_overtime":
                sys.exit(1)
        sys.exit(0)
sys.exit(2)
PY
then ok
else bad "conventions.md says _cron_absence_detection is NOT deferred; it is, or it is gone"; fi

# The presence asymmetry: `present` ungated, `absent` gated. Asserted on the
# source because the symmetric shape reads as the tidier one and was proposed.
if "$PY" - "$MOD/models/hr_employee.py" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if not (isinstance(node, ast.FunctionDef)
            and node.name == "_compute_hr_presence_state"):
        continue
    gated = {}
    for branch in ast.walk(node):
        if not isinstance(branch, ast.If):
            continue
        source = ast.dump(branch.test)
        for statement in branch.body:
            if not (isinstance(statement, ast.Assign)
                    and isinstance(statement.value, ast.Constant)):
                continue
            gated[statement.value.value] = "hr_presence_control_attendance" in source
    sys.exit(0 if gated.get("present") is False and gated.get("absent") is True else 1)
sys.exit(2)
PY
then ok
else bad "the presence branches are not the asymmetry conventions.md states"; fi

# duration vs manual_duration, both directions.
if grep -B3 'def _compute_expected_hours' "$MOD/models/hr_attendance.py" \
   | grep -qF 'linked_overtime_ids.duration'; then ok
else bad "conventions.md says expected_hours derives from duration; it does not"; fi
if grep -B3 'def _compute_overtime_hours' "$MOD/models/hr_attendance.py" \
   | grep -qF 'linked_overtime_ids.manual_duration'; then ok
else bad "conventions.md says overtime_hours sums manual_duration; it does not"; fi
# `body_of`, not `grep -A12`: that window ran off the end of
# `_regeneration_key` into `_regeneration_key_from_vals`, whose `vals.get(
# "duration")` satisfied it. The check passed for the wrong function.
key=$(body_of "$MOD/models/hr_attendance_overtime.py" _regeneration_key)
if printf '%s' "$key" | grep -qF 'self.duration'; then ok
else bad "conventions.md says _regeneration_key() keys on duration; it does not"; fi

# The non-stored computes that must keep their depends.
for field in hours_today hours_this_month; do
    if "$PY" - "$MOD/models/hr_employee.py" "$field" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if not (isinstance(node, ast.FunctionDef)
            and node.name == "_compute_%s" % sys.argv[2]):
        continue
    for decorator in node.decorator_list:
        if (isinstance(decorator, ast.Call)
                and getattr(decorator.func, "attr", "") == "depends"):
            sys.exit(0)
    sys.exit(1)
sys.exit(2)
PY
    then ok
    else bad "conventions.md says _compute_$field declares @api.depends; it does not"; fi
done

# The kiosk's single refusal shape.
for helper in _refuse _employee_of; do
    grep -qE "def $helper\\(" "$MOD/controllers/main.py" \
        && ok || bad "conventions.md names $helper(); controllers/main.py has no such method"
done

# An attendance is not copyable. The method must exist AND raise: `grep -q
# 'def copy'` passed against a `def copy_disabled`, which is the rename that
# would actually restore copying.
copy=$(body_of "$MOD/models/hr_attendance.py" copy)
if [ -z "$copy" ]; then
    bad "conventions.md says copy() raises; hr.attendance does not override it"
elif printf '%s' "$copy" | grep -q 'raise'; then ok
else bad "conventions.md says copy() raises; the override no longer raises"; fi

# ------------------------------------------------------------ instrumentation --
# Every logger the docs advertise exists, and the root is the one they tell a
# reader to arm. A doc that names a logger nobody can arm is worse than none:
# the reader concludes the module is uninstrumented.
root=$(grep -oP '^_ROOT = "\K[^"]+' "$MOD/tools/debug_log.py")
assert_doc_cites "$root" "the debug-logger root"
while read -r logger; do
    [ -z "$logger" ] && continue
    assert_doc_cites "\`$logger\`" "logger $logger"
done < <(grep -oP '^(logic|performance|pipeline|lifecycle)(?= = )' \
    "$MOD/tools/debug_log.py" | sort -u)
# Reverse, and it is the half that matters: renaming a logger in
# debug_log.py silently REMOVED its forward assertion, because the forward
# list is derived from that same file. A gate whose scope shrinks with the
# thing it guards reports fewer passes and no failure.
while read -r logger; do
    [ -z "$logger" ] && continue
    if grep -qP "^$logger = " "$MOD/tools/debug_log.py"; then ok
    else bad "index.md advertises the logger \`$logger\`, which debug_log.py does not define"; fi
done < <(sed -n '/^## Instrumentation/,/^## /p' "$SCRIPT_DIR/index.md" \
    | grep -oP '^\| `\K[a-z_]+(?=` \|)' | sort -u)
sites=$(grep -rc 'dbg\.' "$MOD"/models/*.py "$MOD"/controllers/*.py \
    | awk -F: '{n+=$2} END {print n+0}')
[ "$sites" -gt 0 ] && ok || bad "index.md says every call site imports debug_log as dbg; none does"

# The HttpCase classes a `--no-http` lane cannot run, by name. A count alone
# would let a class be added and the sentence stay plausible, which is the
# shape of the trap the sentence is warning about.
http_cases=$(grep -rhoP '^class \K\w+(?=\(HttpCase\))' "$MOD"/tests/test_*.py | sort -u)
assert_cited_in index.md "skips $(printf '%s\n' "$http_cases" | wc -l) \`HttpCase\` classes" \
    "the HttpCase count"
for case in $http_cases; do
    assert_cited_in index.md "\`$case\`" "HttpCase class $case"
done

# ------------------------------------------------------------------ frozen --
# A frozen figure is pinned to a named base commit (`doc/coding_guidelines.rst`
# §1.4) precisely because it cannot be re-derived, so the one thing a harness
# CAN check is that the pin resolves. An orphaned base makes the figure
# unattributable, which is a different fault from the figure being wrong and is
# invisible without this.
while read -r sha; do
    [ -z "$sha" ] && continue
    # `merge-base --is-ancestor`, not `cat-file -e`. A rebase rewrites a commit
    # and the old object survives in the local database until it is collected,
    # so `cat-file` says yes to a sha this branch no longer contains -- and
    # says yes for as long as the one person running the harness has the old
    # object, which is nobody after a fresh clone. That is `ratchet.py`'s
    # ORPHANED-BASE in a different tool: a pin measured on a tree this history
    # never had.
    if git -C "$MOD" merge-base --is-ancestor "$sha" HEAD 2>/dev/null; then ok
    else bad "docs pin a figure to $sha, which is not an ancestor of HEAD (rewritten by a rebase, or never in this history)"; fi
done < <(grep -hoP '`\K[0-9a-f]{12}(?=`)' "${DOCS[@]}" | sort -u)

# Every test class the docs name by hand must exist. A frozen figure that
# points at a live assertion is only useful while that assertion is findable.
while read -r case; do
    [ -z "$case" ] && continue
    if grep -rqP "^class $case\\(" "$MOD"/tests/*.py; then ok
    else bad "docs name the test class $case, which tests/ does not declare"; fi
done < <(grep -hoP '`\K(Test|Schedule)\w+(?=`)' "${DOCS[@]}" | sort -u)

# EVERY `def <name>` CHECK BELOW AND ABOVE REQUIRES THE OPEN PAREN. Without
# it, `grep "def _deferring_overtime"` matches `def _deferring_overtime_ctx`,
# so renaming an advertised method by SUFFIX passes every one of these -- which
# is the rename most likely to happen, because that is what an author does when
# they split a method in two. Mutation-tested: the suffix rename escaped this
# harness until the parens went in, in the same week the identical trap was
# found and fixed for `def copy` / `def copy_disabled`.

# ---------------------------------------------------------- extension points --
# Advertising a renamed method is how a downstream override gets written
# against a name that has not existed for a month.
while read -r hook; do
    [ -z "$hook" ] && continue
    if grep -rqE "def $hook\\(" "$MOD"/models "$MOD"/controllers; then ok
    else bad "index.md advertises extension point $hook(), which no longer exists"; fi
done < <(sed -n '/^## Extension Points/,$p' "$SCRIPT_DIR/index.md" \
    | grep -oP '^- `\K_\w+(?=\(\))' | sort -u)

# ------------------------------------------------- cross-repo override arity --
# An override sits ahead of the base in the MRO for EVERY caller, so a sibling
# repo carrying the old arity of an advertised extension point does not fail
# in that sibling -- it fails in whatever generic path next calls the hook,
# with a TypeError out of a stored field's compute. `enterprise`'s
# `hr_work_entry_attendance` kept `_get_employee_calendar(self)` after the base
# grew a `version` parameter, and six tests died in `unlink()` and
# `flush_all()`. hr_attendance's own lane was green throughout: it installs no
# enterprise module, so the base signature was the only one in the MRO.
#
# CLAUDE.md §9: a cross-repo gate judges only the scopes it can see. Absent
# siblings are SKIPPED and counted, never silently passed.
_fc_ws="$(cd -- "$_fc_root/.." && pwd)"
for sibling in enterprise agromarin design-themes; do
    if [ ! -d "$_fc_ws/$sibling" ]; then
        note "sibling repo $sibling is not in this workspace"
        continue
    fi
    while read -r line; do
        [ -z "$line" ] && continue
        case "$line" in
            OK\ *) ok ;;
            *) bad "$line" ;;
        esac
    done < <("$PY" - "$MOD/models/hr_attendance.py" "$_fc_ws/$sibling" \
                 "$SCRIPT_DIR/index.md" <<'ARITY'
import ast, pathlib, re, sys

base_path, sibling, index = sys.argv[1], pathlib.Path(sys.argv[2]), sys.argv[3]
hooks = set(re.findall(r"^- `(_\w+)\(\)`", pathlib.Path(index).read_text(), re.M))


def signatures(path):
    found = {}
    try:
        tree = ast.parse(path.read_text())
    except (SyntaxError, UnicodeDecodeError):
        return found
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        # `_name` as well as `_inherit`: the BASE class declares
        # `_name = "hr.attendance"` and inherits only `mixin.mail.thread`, so a
        # scan keyed on `_inherit` alone read an empty base and then skipped
        # every sibling override as "a hook the base does not have". It passed,
        # scanning nothing, which is the shape this whole harness exists to
        # refuse.
        binds = any(
            isinstance(statement, ast.Assign)
            and any(
                getattr(t, "id", "") in ("_inherit", "_name")
                for t in statement.targets
            )
            and "hr.attendance" in ast.dump(statement.value)
            for statement in node.body
        )
        if not binds:
            continue
        for statement in node.body:
            if isinstance(statement, ast.FunctionDef) and statement.name in hooks:
                args = statement.args
                found[statement.name] = (
                    [a.arg for a in args.posonlyargs + args.args],
                    len(args.defaults),
                    bool(args.vararg or args.kwarg),
                )
    return found


base = signatures(pathlib.Path(base_path))
for path in sorted(sibling.rglob("*.py")):
    if "__pycache__" in path.parts:
        continue
    for hook, (names, defaults, catchall) in signatures(path).items():
        if hook not in base:
            continue
        want, want_defaults, _ = base[hook]
        rel = path.relative_to(sibling.parent)
        if catchall or names == want:
            print(f"OK {rel}:{hook}")
        elif names == want[: len(names)] and len(want) - len(names) <= want_defaults:
            print(
                f"{rel} overrides {hook}{tuple(names)} while the base takes "
                f"{tuple(want)}; the override shadows the base for every caller "
                f"and raises TypeError on the new call sites"
            )
        else:
            print(
                f"{rel} overrides {hook}{tuple(names)}, which does not match the "
                f"base {tuple(want)}"
            )
ARITY
)
done

printf '\n%d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ]
