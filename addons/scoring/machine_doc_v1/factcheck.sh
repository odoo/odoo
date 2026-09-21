#!/bin/bash
# scoring machine-doc fact-check. Run from any cwd. Read-only.
#
# Every assertion derives its expected value from the module and then checks
# that the docs agree; no literal here is a second copy of the tree (rule:
# doc/coding_guidelines.rst §1.4). The engine's contract is a set of method
# names hosts implement by convention, which nothing in Python checks -- a
# renamed hook here is a host silently answering nothing there, so the hook
# names, the models, every field and the hosts in this checkout are gated.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_fc_root="$SCRIPT_DIR"
while [[ "$_fc_root" != "/" && ! -f "$_fc_root/odoo-bin" ]]; do
    _fc_root="$(dirname -- "$_fc_root")"
done
# shellcheck source=/dev/null
source "$_fc_root/doc/machine_doc/factcheck_env.sh"

MOD="$(dirname "$SCRIPT_DIR")"                  # <repo>/addons/scoring
ADDONS="$(dirname "$MOD")"
DOCS=("$SCRIPT_DIR"/*.md "$MOD/README.md")

fail=0
pass=0

ok()  { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; }

assert_doc_cites() {  # <needle> <human description>
    if grep -qF -- "$1" "${DOCS[@]}"; then ok; else bad "docs never cite $2 ($1)"; fi
}
assert_cited_in() {  # <file> <needle> <human description>
    if grep -qF -- "$2" "$SCRIPT_DIR/$1"; then ok
    else bad "$1 never cites $3 ($2)"; fi
}
manifest_key() {
    "$PY" - "$MOD/__manifest__.py" "$1" <<'PY'
import ast, sys
manifest = ast.literal_eval(open(sys.argv[1]).read())
value = manifest.get(sys.argv[2])
print(" ".join(value) if isinstance(value, list) else value)
PY
}

printf '== scoring machine_doc_v1 factcheck ==\n'

for f in index.md MODEL_MAP.md; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "missing $f"
done

# ----------------------------------------------------------------- manifest --
version="$(manifest_key version)"
assert_cited_in index.md "| Version | $version" "the manifest version"
for dep in $(manifest_key depends); do
    assert_cited_in index.md "\`$dep\`" "dependency $dep"
done

# ------------------------------------------------------------------- models --
mapfile -t declared < <(grep -rhoP '^\s+_name = "\K[^"]+' "$MOD"/models | sort -u)
for model in "${declared[@]}"; do
    assert_cited_in MODEL_MAP.md "## $model" "model $model"
done
mapfile -t documented < <(grep -oP '^## \K[a-z][a-z._]*' "$SCRIPT_DIR/MODEL_MAP.md" | sort -u)
for model in "${documented[@]}"; do
    if printf '%s\n' "${declared[@]}" | grep -qxF "$model"; then ok
    else bad "MODEL_MAP.md documents $model, which the module does not declare"; fi
done
abstract="$(grep -rlP 'models\.AbstractModel' "$MOD"/models/*.py | wc -l)"
concrete=$(( ${#declared[@]} - abstract ))
assert_cited_in index.md "| Models | ${#declared[@]} ($concrete concrete, $abstract abstract)" \
    "the model count"

# ------------------------------------------------------------------- fields --
while read -r field; do
    [ -z "$field" ] && continue
    assert_cited_in MODEL_MAP.md "\`$field\`" "field $field"
done < <(grep -hoP '^    \K[a-z_][a-z0-9_]*(?= = fields\.[A-Z])' "$MOD"/models/*.py | sort -u)

# ------------------------------------------------------------- hook contract --
# The hooks are the names the engine resolves with getattr; the README is where
# a host author reads them, so each one must be cited there as `<name>`.
for hook in $(grep -hoP 'f"_score_[a-z_]+_\{(code|dimension\.code)\}"' "$MOD"/models/*.py \
        | sed -E 's/f"(_score_[a-z_]+_)\{.*/\1<code>/' | sort -u); do
    assert_doc_cites "\`${hook}" "hook $hook"
done
for name in $(grep -hoP '^    def \K_score_[a-z_]+(?=\()' "$MOD"/models/mixin_scored.py | sort -u); do
    assert_cited_in MODEL_MAP.md "\`$name\`" "mixin.scored method $name"
done

# -------------------------------------------------------------------- hosts --
# Every concrete model in this checkout whose _inherit names mixin.scored is a
# host and index.md names it; a host added anywhere under addons/ moves this.
# Read through ast, not grep: scorecard.py names the mixin in a string.
hosts_list="$(py_capture - "$ADDONS" <<'PY'
import ast, pathlib, sys
addons = pathlib.Path(sys.argv[1])
hosts = set()
for path in addons.glob("*/models/*.py"):
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        continue
    for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
        name = inherit = None
        for node in cls.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                target = node.targets[0].id
                try:
                    value = ast.literal_eval(node.value)
                except ValueError:
                    continue
                if target == "_name":
                    name = value
                elif target == "_inherit":
                    inherit = value if isinstance(value, list) else [value]
        if inherit and "mixin.scored" in inherit and name and name != "mixin.scored":
            hosts.add(name)
print("\n".join(sorted(hosts)))
PY
)"
while read -r host; do
    [ -z "$host" ] && continue
    assert_cited_in index.md "\`$host\`" "host $host"
done <<< "$hosts_list"
hosts="$(printf '%s\n' "$hosts_list" | grep -c .)"
assert_cited_in index.md "| Hosts in this checkout | $hosts " "the host count"

# -------------------------------------------------------------------- tests --
for f in "$MOD"/tests/test_*.py; do
    assert_cited_in index.md "$(basename "$f")" "test file $(basename "$f")"
done

printf '%s\n' "================================================================"
printf 'TOTAL: %d passed, %d failed\n' "$pass" "$fail"
printf '%s\n' "================================================================"
[ "$fail" -eq 0 ]
