#!/bin/bash
# automation machine-doc fact-check. Run from any cwd. Read-only.
#
# Every assertion DERIVES its expected value from the module and then checks
# that the docs agree. No expected value is written down here: a literal in this
# script would be a second copy of the tree, drifting independently of the
# first. Rule: `doc/coding_guidelines.rst` §1.4, a figure is gated or frozen,
# never bare.
#
# WHY THIS MODULE NEEDS ONE. It is the module CLAUDE.md calls strategic, and it
# was the least protected. Every one of these was live on 2026-08-26, found by
# reading the doc against the tree rather than by any gate:
#
#   - Decision 1 in vision.md locked the visual layer onto `web_flow`, a module
#     `agromarin` deleted as unused on 2026-04-21. The doc outlived its subject
#     by four months, and models.md still tabulated the field list of a model
#     that no longer existed.
#   - models.md called `trigger` a 17-value Selection. It has 19, and the
#     Trigger Categories block below it enumerated 18 -- `on_unlink` appeared in
#     neither count nor category.
#   - index.md's file table listed 4 test files. There are 8.
#   - The "Current State vs Target" table and Phase 1 described work as pending
#     that had already shipped: `action_state`, `is_ready` and
#     `use_workflow_dag` were gone, and `automation_id` carried no domain.
#
# A reader starting here -- which CLAUDE.md tells them to do -- took all of that
# as premise. The gate below turns each class of claim into something the tree
# has to keep answering for.
#
# Roots come from this script's own location, so a run always validates the tree
# it ships in.

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

MOD="$(dirname "$SCRIPT_DIR")"                  # <repo>/addons/automation
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

printf '== automation machine_doc_v1 factcheck ==\n'

# ---------------------------------------------------------------- structure --
for f in index.md architecture.md models.md conventions.md vision.md; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "missing $f"
done

# ------------------------------------------------------------------ models ---
# Every model this module defines must be documented, and every model the docs
# present as one of ours must exist. models.md deliberately keeps a `flow.diagram
# -- does not exist` section as a tombstone, so the reverse check reads `_name`
# declarations rather than headings.
while read -r model; do
    assert_doc_cites "$model" "model $model"
done < <(grep -hoP '_name = "\K[a-z_.]+' "$MOD"/models/*.py | sort -u)

# ---------------------------------------------------------------- triggers ---
# The Selection is the source of truth for both the count and the categories.
# Both drifted, independently, which is why both are asserted.
trigger_count=$("$PY" - "$MOD/models/automation_rule.py" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "trigger":
        for kw in node.value.keywords:
            if kw.arg == "selection":
                print(len(kw.value.elts)); raise SystemExit
        if node.value.args:
            print(len(node.value.args[0].elts)); raise SystemExit
print("PARSE_FAILED")
PY
)
if [ "$trigger_count" = "PARSE_FAILED" ]; then
    bad "could not parse the trigger Selection -- the gate below is blind"
else
    assert_cited_in models.md "Selection ($trigger_count values)" "the trigger count"
fi

# Forward: every value in the Selection is named somewhere in the docs. This is
# the check `on_unlink` failed -- it was a real trigger no document mentioned.
while read -r value; do
    assert_doc_cites "$value" "trigger value $value"
done < <("$PY" - "$MOD/models/automation_rule.py" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "trigger":
        elts = None
        for kw in node.value.keywords:
            if kw.arg == "selection":
                elts = kw.value.elts
        if elts is None and node.value.args:
            elts = node.value.args[0].elts
        for e in elts or []:
            print(ast.literal_eval(e)[0])
        break
PY
)

# Reverse: the Trigger Categories block must not invent a value. A category line
# naming a trigger the Selection dropped sends the reader configuring something
# that cannot be selected.
valid_triggers=$("$PY" - "$MOD/models/automation_rule.py" <<'PY'
import ast, sys
tree = ast.parse(open(sys.argv[1]).read())
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "trigger":
        elts = None
        for kw in node.value.keywords:
            if kw.arg == "selection":
                elts = kw.value.elts
        if elts is None and node.value.args:
            elts = node.value.args[0].elts
        print(" ".join(ast.literal_eval(e)[0] for e in elts or []))
        break
PY
)
while read -r cited; do
    [ -z "$cited" ] && continue
    case " $valid_triggers " in
        *" $cited "*) ok ;;
        *) bad "docs cite trigger '$cited', absent from the Selection" ;;
    esac
done < <(sed -n '/^### Trigger Categories/,/^```$/p' "$SCRIPT_DIR/models.md" \
         | grep -oE '\bon_[a-z_]+\b' | sort -u)

# --------------------------------------------------------------- constants ---
# Compared NUMERICALLY, never as text. The source writes `4 * 60` where the doc
# writes 240, and `0.10` where Python renders 0.1 -- a gate matching strings
# forces one side to spell the number the other's language prefers, which is how
# a correct document fails a gate and gets "fixed" into a worse one.
constants_report=$("$PY" - "$MOD/models/automation_rule.py" "$SCRIPT_DIR/models.md" <<'PY'
import ast, re, sys

source, doc = sys.argv[1], sys.argv[2]
text = open(doc).read()
tree = ast.parse(open(source).read())
for node in tree.body:
    if not (isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)):
        continue
    name = node.targets[0].id
    if not name.isupper():
        continue
    try:
        value = ast.literal_eval(node.value)
    except ValueError:
        continue
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        continue
    row = re.search(rf"^\|\s*`{re.escape(name)}`\s*\|\s*([0-9.]+)\s*\|", text, re.M)
    if row is None:
        print(f"BAD|models.md tabulates no value for constant {name}")
    elif float(row.group(1)) != float(value):
        print(f"BAD|models.md says {name} is {row.group(1)}, source says {value}")
    else:
        print(f"OK|{name}")
PY
)
while IFS='|' read -r verdict detail; do
    [ -z "$verdict" ] && continue
    [ "$verdict" = "OK" ] && ok || bad "$detail"
done <<< "$constants_report"

# ------------------------------------------------------------- file listing --
# Forward: every shipped source and test file is named in index.md's table. The
# test half of this is what caught index.md listing 4 of 8.
for f in "$MOD"/models/*.py "$MOD"/controllers/*.py "$MOD"/tests/test_*.py; do
    [ -f "$f" ] || continue
    base="$(basename "$f")"
    [ "$base" = "__init__.py" ] && continue
    rel="${f#"$MOD"/}"
    assert_cited_in index.md "\`$rel\`" "shipped file $rel"
done

# Reverse: a table row naming a file that is gone reads as current and sends the
# reader looking for it.
while read -r cited; do
    [ -z "$cited" ] && continue
    [ -f "$MOD/$cited" ] && ok || bad "index.md cites $cited, which no longer exists"
done < <(grep -oP '^\| `\K(models|controllers|tests)/[a-z_]+\.py(?=`)' "$SCRIPT_DIR/index.md")

# ------------------------------------------------------------ removed things --
# Phase 1 removed these, and the docs now state they are gone. That statement is
# only worth anything if something checks it: a reintroduced `action_state` is
# exactly the concurrent-run corruption the phase existed to delete, and the
# doc would go on claiming it was fixed.
for field in action_state is_ready use_workflow_dag auto_execute_workflow; do
    if grep -qE "^\s+$field = fields\." "$MOD"/models/*.py; then
        bad "$field is declared again; vision.md Phase 1 claims it was removed"
    else ok; fi
done
# error_message moved rather than vanished -- assert both halves.
if grep -qE '^\s+error_message = fields\.' "$MOD/models/ir_actions_server.py"; then
    bad "error_message is back on ir.actions.server; it belongs on automation.runtime.line"
else ok; fi
if grep -qE '^\s+error_message = fields\.' "$MOD/models/automation_runtime_line.py"; then ok
else bad "error_message is gone from automation.runtime.line, where the docs place it"; fi

# --------------------------------------------------------------- web_flow ----
# vision.md Decision 1 rests on the module being absent. If a sibling agromarin
# checkout is reachable, hold the doc to that; CI checks out `odoo` alone, so
# the honest answer there is a skip rather than a silent pass.
sibling="$MOD/../../../agromarin"
if [ -d "$sibling" ]; then
    if [ -d "$sibling/web_flow" ]; then
        bad "agromarin/web_flow exists again; vision.md Decision 1 says it was deleted"
    else ok; fi
else
    note "no sibling agromarin checkout -- cannot confirm web_flow is still absent"
fi

# --------------------------------------------------- backticked path sweep ---
# `odoo/CLAUDE.md` holds these directories to an invariant: a backticked path
# asserts that one particular file exists, so a deliberately-absent file — or
# one in a sibling repo CI never checks out — is named in PLAIN PROSE instead.
# That is not a style preference. A backticked path that resolves nowhere sends
# the reader hunting for a file, and reads exactly like one that does.
#
# Resolution is deliberately confined to THIS repository, because that is the
# only tree CI has. Anything naming a sibling checkout is therefore a violation
# by construction, which is precisely why the rule says prose.
path_report=$("$PY" - "$SCRIPT_DIR" "$MOD" <<'PY'
import pathlib, re, sys

doc_dir, mod = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
repo = mod.parent.parent                       # <repo>/addons/<module> -> <repo>
TOKEN = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|xml|js|md|csv|sh|scss|json))`")
SIBLINGS = ("agromarin/", "agromarin-knowledge/", "enterprise/", "design-themes/")

# THE TREE UNDER TEST MUST BE FINDABLE, or every path reads as dead and the
# sweep reports a wall of false failures — the failure mode web's equivalent
# records having shipped once. A gate that fails on everything is read as
# broken and ignored, which costs as much as one that passes on everything.
if not (repo / "odoo-bin").exists():
    print("BAD|repo root misresolved (no odoo-bin at %s) — sweep would be blind" % repo)
    raise SystemExit(0)

for doc in sorted(doc_dir.glob("*.md")):
    for token in sorted({m.group(1) for m in TOKEN.finditer(doc.read_text())}):
        if token.startswith(SIBLINGS):
            print(f"BAD|{doc.name} backticks {token}, which lives in a sibling "
                  f"checkout CI does not have — name it in plain prose")
            continue
        if any((base / token).exists() for base in (doc_dir, mod, repo)):
            print(f"OK|{token}")
        elif list(mod.rglob(pathlib.PurePath(token).name)):
            print(f"OK|{token}")
        else:
            print(f"BAD|{doc.name} backticks {token}, which resolves to no file "
                  f"in this repository")
PY
)
while IFS='|' read -r verdict detail; do
    [ -z "$verdict" ] && continue
    [ "$verdict" = "OK" ] && ok || bad "$detail"
done <<< "$path_report"

# ------------------------------------------------------------------ summary --
printf '\n%d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ] || exit 1
