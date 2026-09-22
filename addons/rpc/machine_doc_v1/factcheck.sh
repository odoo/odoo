#!/bin/bash
# rpc machine-doc fact-check. Run from any cwd. Read-only.
#
# Every fact is DERIVED from the tree: the routes from the controllers, the
# document from the checked-in copy, and the two are compared with each other
# rather than with a number written here. What this cannot do without a
# database is render the document; TestOpenAPIContract does that, and the
# assertions below are what holds between runs of it.

set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_fc_root="$SCRIPT_DIR"
while [[ "$_fc_root" != "/" && ! -f "$_fc_root/odoo-bin" ]]; do
    _fc_root="$(dirname -- "$_fc_root")"
done
# shellcheck source=/dev/null
source "$_fc_root/doc/machine_doc/factcheck_env.sh"

MOD="$(dirname "$SCRIPT_DIR")"
DOCS=("$SCRIPT_DIR"/*.md)
DOCUMENT="$SCRIPT_DIR/openapi.json"

fail=0
pass=0
skip=0

ok()   { pass=$((pass + 1)); }
bad()  { fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; }
note() { skip=$((skip + 1)); printf '  SKIP  %s\n' "$1"; }

assert_doc_cites() {  # <needle> <human description>
    if grep -qP -- "\\b\\Q$1\\E\\b" "${DOCS[@]}"; then ok
    else bad "docs never cite $2 ($1)"; fi
}

printf '== rpc machine_doc_v1 factcheck ==\n'

# ---------------------------------------------------------------- structure --
[ -f "$SCRIPT_DIR/API.md" ] && ok || bad "missing API.md"
[ -f "$DOCUMENT" ] && ok || bad "missing openapi.json"

# ------------------------------------------------------------------- routes --
# Every rule the controllers declare is a path of the document, and every path
# of the document is a rule the controllers declare.
route_report=$("$PY" - "$MOD" "$DOCUMENT" <<'PY'
import ast
import json
import pathlib
import re
import sys

mod = pathlib.Path(sys.argv[1])
document = json.loads(pathlib.Path(sys.argv[2]).read_text())

ARG = re.compile(r"<(?:[a-zA-Z_]\w*(?:\([^>]*\))?:)?(\w+)>")


def template(rule):
    return ARG.sub(lambda match: "{" + match.group(1) + "}", rule)


declared = {}
for path in sorted(mod.glob("controllers/*.py")):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            name = getattr(decorator.func, "attr", getattr(decorator.func, "id", ""))
            if name != "route":
                continue
            keywords = {
                keyword.arg: keyword.value.value
                for keyword in decorator.keywords
                if keyword.arg and isinstance(keyword.value, ast.Constant)
            }
            rules = []
            for argument in decorator.args:
                if isinstance(argument, ast.Constant):
                    rules.append(argument.value)
                elif isinstance(argument, ast.List | ast.Tuple):
                    rules.extend(
                        item.value
                        for item in argument.elts
                        if isinstance(item, ast.Constant)
                    )
            for rule in rules:
                declared[template(rule)] = keywords.get("auth")

described = set(document["paths"])
for path in sorted(set(declared) - described):
    print(f"BAD|{path} is a route of rpc that openapi.json does not describe")
for path in sorted(described - set(declared)):
    print(f"BAD|openapi.json describes {path}, which rpc no longer serves")
for path in sorted(set(declared) & described):
    print(f"OK|{path}")

# The auth of each route is the security of its operations.
expected = {"bearer": "bearerAuth", "user": "sessionCookie"}
for path, item in sorted(document["paths"].items()):
    auth = declared.get(path)
    for verb, operation in sorted(item.items()):
        names = [name for requirement in operation.get("security", ()) for name in requirement]
        if auth in expected:
            if names == [expected[auth]]:
                print(f"OK|{verb} {path}")
            else:
                print(f"BAD|{verb.upper()} {path} is auth={auth!r} but the document "
                      f"requires {names or 'nothing'}")
        elif names:
            print(f"BAD|{verb.upper()} {path} is auth={auth!r} but the document "
                  f"requires {names}")
        else:
            print(f"OK|{verb} {path}")

if document.get("openapi", "").startswith("3.1"):
    print("OK|openapi 3.1")
else:
    print(f"BAD|openapi.json says {document.get('openapi')!r}, not a 3.1 document")
PY
)
while IFS='|' read -r verdict detail; do
    [ -z "$verdict" ] && continue
    [ "$verdict" = "OK" ] && ok || bad "$detail"
done <<< "$route_report"

# --------------------------------------------------------------------- docs --
# The document's own regeneration command and the test that holds it.
assert_doc_cites "ODOO_WRITE_OPENAPI" "the variable that rewrites openapi.json"
assert_doc_cites "TestOpenAPIContract" "the test that validates the document"
assert_doc_cites "E8533" "the lint that keeps every machine route declared"

# Every backticked path in the docs resolves.
path_report=$("$PY" - "$SCRIPT_DIR" "$MOD" "$_fc_root" <<'PY'
import pathlib
import re
import sys

doc_dir, mod, repo = (pathlib.Path(p) for p in sys.argv[1:4])
TOKEN = re.compile(r"`([^`\s]+\.(?:py|json|md|sh|xml|js))`")
for doc in sorted(doc_dir.glob("*.md")):
    for token in TOKEN.findall(doc.read_text()):
        if any((base / token).exists() for base in (doc_dir, mod, repo)):
            print(f"OK|{token}")
        elif list(mod.rglob(pathlib.PurePath(token).name)):
            print(f"OK|{token}")
        else:
            print(f"BAD|{doc.name} backticks {token}, which resolves to no file")
PY
)
while IFS='|' read -r verdict detail; do
    [ -z "$verdict" ] && continue
    [ "$verdict" = "OK" ] && ok || bad "$detail"
done <<< "$path_report"

printf '\n%d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ]
