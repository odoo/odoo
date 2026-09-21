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

# The pages this harness knows about, checked BOTH ways. `tooling/`'s
# test_architecture_doc.py read every .md in the directory as one document and
# failed if its list and the directory disagreed in either direction, so a new
# view could not land unpinned; it went on 2026-09-11 and this harness, written
# on 2026-09-15 to replace it, was born two pages short -- deployment.md and
# scenarios.md had been in the directory since 2026-08-07 and are in no list
# here. Only the forward direction was rebuilt, and the forward direction is
# the half that cannot notice.
#
# deployment.md's figures are gated by tests/service/test_deployment_figures.py,
# which derives them from the service constants the way cite() below does.
PAGES="ARCHITECTURE.md data.md deployment.md gates.md module.md qualities.md risks.md runtime.md scenarios.md"

for f in $PAGES; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "$f is in this harness's list and not in doc/architecture/"
done
for path in "$SCRIPT_DIR"/*.md; do
    name="$(basename "$path")"
    case " $PAGES " in
        *" $name "*) ok ;;
        *) bad "$name is in doc/architecture/ and in no list here; add it, and gate whatever figures it states" ;;
    esac
done

# Each line: LABEL|value|page|regex the page must match, with @ standing for
# the value spelled as the page spells it (digits, or the number word).
report=$(cd "$ROOT" && "$PY" - "$SCRIPT_DIR" <<'PY'
import ast, pathlib, re, sys

sys.path.insert(0, ".")
import odoo.init  # noqa: F401  # the interpreter floor and the native build
from odoo.orm.models.base import BaseModel
from odoo.orm.tests import test_architecture_pins as pins
from odoo.db import cursor
from odoo.orm.runtime import _registry_signaling as signaling
from odoo.orm.runtime import transaction
from odoo.service import transaction as transaction_svc
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

# data.md's diagram counts the signalling tables. They are generated from a
# cache list rather than written down, so the page cannot be read off the
# source by eye: it said 8 from the day it was written (2026-08-07) while the
# list moved two days later, and the comment beside the definition has said
# "eleven watermarks" ever since.
cite("signalling tables", len(signaling.SIGNALING_TABLES), "data.md", r"\(@ of them\)")
# runtime.md states the same count as the width of the sequence read. Found by
# asking, of every figure gated here, which other page states its value near
# its own subject -- the generalisation of runtime.md citing scenarios.md.
# (`_registry_signaling.py`'s own comment, "the eleven watermarks", is a third
# statement of it, in source prose this harness does not read.)
cite(
    "signalling tables (runtime.md)",
    len(signaling.SIGNALING_TABLES),
    "runtime.md",
    r"@ sequence reads",
)

# qualities.md's contention scenario names the retry budget and the back-off
# curve it describes. They are constants, not measurements -- the 2026-08-28
# stamp on that scenario belongs to its throughput table -- so they are gated
# and not frozen. `\s*` because the page wraps between the name and the value.
cite(
    "retry budget",
    transaction_svc.MAX_TRIES_ON_CONCURRENCY_FAILURE,
    "qualities.md",
    r"`MAX_TRIES_ON_CONCURRENCY_FAILURE`\s*\(@\)",
)
cite(
    "back-off base",
    transaction_svc.BASE_CONCURRENCY_BACKOFF_SECONDS,
    "qualities.md",
    r"`BASE_CONCURRENCY_BACKOFF_SECONDS`\s*\(@\)",
)
cite(
    "back-off ceiling",
    transaction_svc.MAX_CONCURRENCY_BACKOFF_SECONDS,
    "qualities.md",
    r"`MAX_CONCURRENCY_BACKOFF_SECONDS`\s*\(@\)",
)

# risks.md sizes the in-memory read_group the differential walk has to cover.
memory_backend = ast.parse(pathlib.Path("odoo/orm/runtime/_backend_memory.py").read_text())
in_memory = next(
    n for n in ast.walk(memory_backend)
    if isinstance(n, ast.ClassDef) and n.name == "_InMemoryReadGroup"
)
cite(
    "_InMemoryReadGroup size",
    in_memory.end_lineno - in_memory.lineno + 1,
    "risks.md",
    r"`_InMemoryReadGroup` — @ lines of",
)

# scenarios.md numbers the load it considers worth naming and says how many
# it left out. `restore_relations_dropped_by_migrations` landed on 2026-09-20
# and appeared in neither table for a day: the page said 23 calls where the
# loader made 24, which is the drift the deleted test_architecture_doc.py
# would have caught the moment a phase was added.
loading = ast.parse((pathlib.Path("odoo/modules/loading.py")).read_text())
load_modules = next(
    n for n in ast.walk(loading)
    if isinstance(n, ast.FunctionDef) and n.name == "load_modules"
)
phases = [
    n.func.attr for n in ast.walk(load_modules)
    if isinstance(n, ast.Call)
    and isinstance(n.func, ast.Attribute)
    and isinstance(n.func.value, ast.Name)
    and n.func.value.id == "loader"
]
scenarios = (pages / "scenarios.md").read_text()
tabled = re.findall(r"^\| \d+ \| `([a-z_]+)\(\)`", scenarios, re.M)
# The left-out table only, and only its first column: its second column
# cites names of its own (`at_install`), and a later table on the page lists
# the migration script kinds (`pre`, `post`, `end`) in the same shape.
lines = scenarios.splitlines()
first = next(i for i, l in enumerate(lines) if "left out split two ways" in l)
after = next(
    (i for i, l in enumerate(lines[first + 1 :], first + 1) if l.strip() and not l.startswith("|")),
    len(lines),
)
left_out = [
    name
    for line in lines[first:after]
    if line.startswith("| `")
    for name in re.findall(r"`([a-z_]+)`", line.split("|")[1])
]
cite("load_modules phases", len(phases), "scenarios.md", r"`load_modules`' @ calls")
cite("load_modules phases tabled", len(tabled), "scenarios.md", r"(?i)@ of `load_modules`")
cite("load_modules phases left out", len(phases) - len(tabled), "scenarios.md", r"The @ left out")
# runtime.md states the same loader total for its own sketch, and tells the
# reader how many scenarios.md selects. The second is a page citing a page:
# correcting scenarios.md's table from thirteen to fourteen left runtime.md
# saying thirteen, and a gate that reads one page cannot see that.
cite("load_modules phases (runtime.md)", len(phases), "runtime.md", r"of the @ `loader\.\*` calls")
cite("load_modules phases (runtime.md prose)", len(phases), "runtime.md", r"Every one of the @ is")
cite("scenarios' selection as runtime.md cites it", len(tabled), "runtime.md", r"selects @")

cite(
    "fixpoint ceiling",
    transaction.MAX_FIXPOINT_ITERATIONS,
    "runtime.md",
    r"MAX_FIXPOINT_ITERATIONS \(@\)",
)
cite(
    "flush passes",
    cursor.BaseCursor._MAX_FLUSH_PASSES,
    "runtime.md",
    r"_MAX_FLUSH_PASSES \(@\)",
)

unknown = sorted(set(tabled + left_out) - set(phases))
print(
    f"OK|every phase scenarios.md names is a loader call"
    if not unknown
    else f"BAD|scenarios.md names phases load_modules does not call: {unknown}"
)
unnamed = sorted(set(phases) - set(tabled) - set(left_out))
print(
    "OK|every loader call scenarios.md accounts for"
    if not unnamed
    else f"BAD|load_modules calls phases scenarios.md never names: {unnamed}"
)
PY
) || { bad "the derivation itself failed (see stderr above)"; report=""; }

while IFS='|' read -r verdict detail; do
    [ -z "$verdict" ] && continue
    [ "$verdict" = "OK" ] && ok || bad "$detail"
done <<< "$report"

printf 'doc/architecture: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
