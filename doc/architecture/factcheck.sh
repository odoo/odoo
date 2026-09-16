#!/bin/bash
# doc/architecture fact-check. Run from any cwd. Read-only.
#
# The architecture pages state figures the tree can answer -- how many mixins
# compose BaseModel, how many `env["<base model>"]` reaches sit outside the
# ports, how many statements the model layers still execute, how many
# `env.backend` dispatch sites there are. Since `tooling/` went (2026-09-11)
# nothing failed when one drifted, and one did: module.md and gates.md said
# "seven statements" for two days after 99b81f3472ed ported two of them.
#
# Every expected value is DERIVED here -- from the class, or from the pin
# tests that freeze the maps -- and the pages must cite it. No literal in this
# file (doc/coding_guidelines.rst §1.4). A dated figure ("31 on 2026-09-11") is
# frozen, not gated, and is not checked here.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../machine_doc/factcheck_env.sh"
ROOT="$FACTCHECK_ROOT"

fail=0
pass=0
ok()  { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; }

printf '== doc/architecture factcheck ==\n'

for f in ARCHITECTURE.md module.md gates.md runtime.md data.md risks.md qualities.md; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "missing $f"
done

# Each line: LABEL|value|page|regex the page must match, with @ standing for
# the value spelled as the page spells it (digits, or the number word).
report=$(cd "$ROOT" && "$PY" - "$SCRIPT_DIR" <<'PY'
import pathlib, re, sys

sys.path.insert(0, ".")
import odoo.init  # noqa: F401  # the interpreter floor and the native build
from odoo.orm.models.base import BaseModel
from odoo.orm.tests import test_architecture_pins as pins
from odoo.orm.tests import test_backend_dispatch_surface as dispatch

pages = pathlib.Path(sys.argv[1])
WORDS = {v: k for k, v in dispatch._NUMBER_WORDS.items()}

def spelled(value):
    return {str(value), WORDS.get(value, "")} - {""}

def cite(label, value, page, pattern):
    text = (pages / page).read_text()
    for form in spelled(value):
        if re.search(pattern.replace("@", re.escape(form)), text):
            print(f"OK|{label}")
            return
    print(f"BAD|{page} does not cite {label} = {value} ({pattern})")

bases = BaseModel.__bases__
public = sum(1 for b in bases if not b.__name__.startswith("_"))
private = len(bases) - public
cite("BaseModel mixins", len(bases), "module.md", r"BaseModel \+ @ mixins")
cite("BaseModel mixins (prose)", len(bases), "module.md", r"composed from @ `__slots__ = \(\)` mixins")
cite("public mixins", public, "module.md", r"@ public \(`CreateMixin`")
cite("private mixins", private, "module.md", r"plus @ private")

reaches = sum(pins.BASE_MODEL_REACHES.values())
statements = sum(pins.EXECUTED_STATEMENTS.values())
cite("base-model reaches", reaches, "module.md", r"sites left outside them are @ \(")
cite("base-model reaches", reaches, "gates.md", r"the @\s+`env\[\"<base model>\"\]` sites")
cite("executed statements", statements, "module.md", r"freezes the @\s+statements")
cite("executed statements", statements, "gates.md", r"the @\s+statements the models")

sites = len(dispatch.DISPATCH_SITES)
files = len({path for path, _ in dispatch.DISPATCH_SITES})
layer1 = sum(1 for path, _ in dispatch.DISPATCH_SITES if path.startswith(("fields/", "domain/")))
cite("dispatch sites", sites, "module.md", r"\| dispatch sites \| @ across")
cite("dispatch files", files, "module.md", r"\| dispatch sites \| \d+ across @ files")
cite("Layer-1 dispatch sites", layer1, "module.md", r"across \d+ files, @ in Layer 1")
PY
) || { bad "the derivation itself failed (see stderr above)"; report=""; }

while IFS='|' read -r verdict detail; do
    [ -z "$verdict" ] && continue
    [ "$verdict" = "OK" ] && ok || bad "$detail"
done <<< "$report"

printf 'doc/architecture: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
