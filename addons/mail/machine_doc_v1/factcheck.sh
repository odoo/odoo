#!/bin/bash
# Mail module machine-doc fact-check (round 4 — 2026-08-20)
# Run from any cwd. Read-only. CI-safe.
# Mirrors the web module's machine_doc_v1/factcheck.sh: every numeric/structural
# claim in these docs gets a code-reality assertion, and each is paired with a
# doc-consistency assertion so code<->doc drift fails loud at CI time.
#
# INVARIANT (round 4, coding_guidelines.rst §1.4): a figure the DOCS
# state is DERIVED here and the doc is asserted to cite it -- `assert_doc_cites`,
# the same reasoning as `doc_restated_counts.py --update` for
# `doc/architecture/`. Reach for it in the commit that MOVES the tree; a figure
# goes stale there, not in the run that notices.
#
# Round 3 required the opposite -- every `expected` a LITERAL -- because round 2
# had shipped 14 assertions of the form `assert_eq "$(grep X f)" "$(grep X f)"`,
# a value compared to itself that can never fail. The literal rule fixed that and
# created its own defect: the expected values became a second copy of the tree,
# and `e4df7f5569b` ("[REM] mail: delete the twenty-one round-numbered hardening
# suites") moved 21 files without re-deriving one of them, taking 22 assertions
# red and the docs with them. Deriving is not self-comparison: the value is
# measured ONCE from the tree and compared against the DOCUMENT, which is a
# different thing and can fail.
#
# A literal `0` or `1` asserting an INVARIANT -- "no common/ file imports from a
# higher layer", "this file exists" -- stays a literal. It is not a measurement
# of tree size, so it has no second copy to drift.

set -u
# Resolve every root from this script's own location, the way the rest of the
# repo's tooling does (tooling/_repo_root.py locates the checkout by its
# odoo-bin marker). These used to be absolute paths baked in from one
# developer's layout: on a checkout arranged differently every grep hit a
# missing file and returned empty, which the assertions reported as 156
# "failures" that were really one path error.
DOC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# Interpreter resolution + a scan that cannot fail silently. See the header of
# doc/machine_doc/factcheck_env.sh for what bare `"$PY"` did here.
_fc_root="$DOC"
while [[ "$_fc_root" != "/" && ! -f "$_fc_root/odoo-bin" ]]; do
    _fc_root="$(dirname -- "$_fc_root")"
done
# shellcheck source=/dev/null
source "$_fc_root/doc/machine_doc/factcheck_env.sh"

MAIL="$(dirname -- "$DOC")"
# A couple of claims depend on the FRAMEWORK, not on mail. Resolve it once, here,
# rather than spelling "$MAIL/../.." at each use — otherwise relocating the
# module makes those greps hit a missing file and return empty, which reads as a
# confusing failure. The marker check below turns that into one loud error.
ODOO="$(cd -- "$MAIL/../.." && pwd)"
if [ ! -f "$ODOO/odoo-bin" ]; then
    echo "FATAL: resolved framework root '$ODOO' has no odoo-bin." >&2
    echo "       This script expects <checkout>/addons/mail/machine_doc_v1/." >&2
    exit 2
fi
PASS=0
FAIL=0
UPDATED=0

# The rewriter below needs a python; the venv's is preferred so a workspace run
# matches CI, but any "$PY" will do -- it only edits text.
VENV_PY="${VENV_PY:-}"
if [ -z "$VENV_PY" ] || [ ! -x "$VENV_PY" ]; then
    for _cand in "$(dirname "$ODOO")"/*/bin/python3 "$(dirname "$ODOO")"/*/bin/python; do
        [ -x "$_cand" ] && VENV_PY="$_cand" && break
    done
fi
[ -n "$VENV_PY" ] && [ -x "$VENV_PY" ] || VENV_PY="$(command -v "$PY")"

# `--update` is opt-in and touches nothing on the default path, so a CI run and a
# developer run execute the same assertions.
FACTCHECK_UPDATE=0
for _arg in "$@"; do
    case "$_arg" in
        --update) FACTCHECK_UPDATE=1 ;;
        *) echo "usage: factcheck.sh [--update]" >&2; exit 2 ;;
    esac
done

assert_eq() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "PASS: $name [$actual]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — expected [$expected] got [$actual]"; FAIL=$((FAIL+1))
    fi
}
assert_doc_cites() {
    # $1 = human name, $2 = actual value(s), $3 = printf-style grep pattern, one
    # %s per value, $4 = doc file.
    #
    # $2 takes SEVERAL space-separated values because a restated figure often
    # comes as a ratio -- "766 of 768 files" -- and pinning only the numerator
    # leaves the denominator ungated, which is the exact hole §1.4 exists to
    # close. It also let the rewriter below fix half a sentence and give up.
    local name="$1" actual="$2" pat="$3"
    # Deliberately unquoted: word-splitting is how N values reach N %s slots.
    # shellcheck disable=SC2086
    local rendered; rendered=$(printf "$pat" $actual)
    # grep -c already prints "0" (and exits 1) on no match, so a `|| echo 0`
    # here appended a SECOND "0" -> "0\n0" -> `[: integer expected`. Let the
    # count stand and only default the missing-file case (empty output).
    local hits; hits=$(grep -cE "$rendered" "$DOC/$4" 2>/dev/null); hits=${hits:-0}
    if [ "$hits" -ge 1 ]; then
        echo "PASS: $name [doc cites $actual]"; PASS=$((PASS+1))
    elif [ "$FACTCHECK_UPDATE" = 1 ] && _rewrite_figure "$DOC/$4" "$pat" "$actual"; then
        echo "UPDATED: $name — $4 now cites $actual"; UPDATED=$((UPDATED+1))
    else
        echo "FAIL: $name — filesystem says $actual, $4 does not cite it"; FAIL=$((FAIL+1))
    fi
}
# Rewrite the one figure a failing assert_doc_cites was looking for.
#
# The pattern already locates the sentence; the only unknown is the digits in
# its `%s` slot. Rendering the slot as a capture turns the SAME pattern into
# both the locator and the edit, so an updater cannot drift from the assertion
# the way a second hand-written regex would.
#
# Refuses on 0 or 2+ matching lines rather than guessing: an ambiguous pattern
# is a pattern that needs tightening at its call site, and silently rewriting
# the first of several would produce a doc that passes while saying something
# false. $1 = file, $2 = printf pattern, $3 = actual value.
_rewrite_figure() {
    FIG_FILE="$1" FIG_PAT="$2" FIG_VAL="$3" "$VENV_PY" - <<'PY'
import os, re, sys

path, pat = os.environ["FIG_FILE"], os.environ["FIG_PAT"]
vals = os.environ["FIG_VAL"].split()
if "%s" not in pat or not vals or not all(v.isdigit() for v in vals):
    sys.exit(1)
# grep -E and python re agree on everything these patterns use (\|, \*, ., .*,
# character classes); the slot becomes a capture spanning digits and the group
# separators a figure may carry.
locator = re.compile(pat.replace("%s", "([0-9][0-9,]*)"))
if locator.groups != len(vals):
    sys.exit(1)
try:
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
except OSError:
    sys.exit(1)
hits = [(i, m) for i, line in enumerate(lines) for m in [locator.search(line)] if m]
if len(hits) != 1:
    sys.exit(1)
i, m = hits[0]
line = lines[i]
# Right to left: rewriting a slot shifts every span after it.
for g in range(len(vals), 0, -1):
    start, end = m.span(g)
    line = line[:start] + vals[g - 1] + line[end:]
lines[i] = line
open(path, "w", encoding="utf-8").writelines(lines)
PY
}

assert_range() {
    local name="$1" actual="$2" lo="$3" hi="$4"
    if [ "$actual" -ge "$lo" ] && [ "$actual" -le "$hi" ]; then
        echo "PASS: $name [$actual in $lo..$hi]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — expected $lo..$hi got [$actual]"; FAIL=$((FAIL+1))
    fi
}

# ============================ Module size ============================
js_src_total=$(find "$MAIL/static/src" -name '*.js' -type f | wc -l)
assert_doc_cites "ARCHITECTURE.md cites the static/src JS count" "$js_src_total" \
    '\| JavaScript \(`static/src/`\) \| %s \|' ARCHITECTURE.md
assert_doc_cites "DIRECTORY_MAP.md subtree rows sum to the static/src JS count" \
    "$js_src_total" 'rows above sum to \*\*%s\*\*' DIRECTORY_MAP.md
js_test_total=$(find "$MAIL/static/tests" -name '*.test.js' | wc -l)
assert_doc_cites "TEST_TAGS.md cites the *.test.js count" "$js_test_total" \
    '`static/tests/`, %s `\*\.test\.js`' TEST_TAGS.md
assert_doc_cites "TEST_TAGS.md per-subtree rows sum to it" "$js_test_total" \
    'Rows below sum to %s' TEST_TAGS.md
py_model_total=$(find "$MAIL/models" -name '*.py' ! -name '__init__.py' | wc -l)
assert_doc_cites "ARCHITECTURE.md cites the models/ file count" "$py_model_total" \
    '\| Python models \(`models/`, incl\. `discuss/`\) \| %s \(' ARCHITECTURE.md
assert_doc_cites "DIRECTORY_MAP.md cites the models/ file count" "$py_model_total" \
    '\| %s Python model files' DIRECTORY_MAP.md
assert_eq "discuss/ model files (excl __init__)" \
    "$(find "$MAIL/models/discuss" -name '*.py' ! -name '__init__.py' | wc -l)" "14"
py_test_total=$(find "$MAIL/tests" -name 'test_*.py' | wc -l)
assert_doc_cites "TEST_TAGS.md cites the test_*.py count" "$py_test_total" \
    '`tests/`, %s `test_\*\.py` files' TEST_TAGS.md
assert_eq "Python wizard files (excl __init__/xml)" \
    "$(find "$MAIL/wizards" -name '*.py' ! -name '__init__.py' | wc -l)" "9"

# ============================ ROUTE_MAP ============================
route_handlers=$(cat "$MAIL"/controllers/*.py "$MAIL"/controllers/discuss/*.py | grep -cE '@(http\.)?route\(')
assert_doc_cites "ROUTE_MAP.md cites the handler count and its split" \
    "$route_handlers $(cat "$MAIL"/controllers/*.py | grep -cE '@(http\.)?route\(') $(cat "$MAIL"/controllers/discuss/*.py | grep -cE '@(http\.)?route\(')" \
    '\*\*Total: %s `@http\.route` handlers\*\* — %s in `controllers/`, %s in `controllers/discuss/`' \
    ROUTE_MAP.md
# The count above tallies DECORATORS, not URLs — decorators are multi-line, so a URL can be
# renamed or dropped without moving it (verified by mutation: deleting the
# /discuss/voice/worklet_processor URL line left the count at 65). Pin the URL set itself.
route_urls=$("$PY" - "$MAIL" <<'PYEOF'
import ast,pathlib,hashlib,sys
urls=[]
for p in sorted(pathlib.Path(sys.argv[1],"controllers").rglob("*.py")):
    if p.name=="__init__.py": continue
    for cls in [n for n in ast.parse(p.read_text()).body if isinstance(n,ast.ClassDef)]:
        for fn in [n for n in cls.body if isinstance(n,ast.FunctionDef)]:
            for d in fn.decorator_list:
                if isinstance(d,ast.Call) and ast.unparse(d.func).endswith("route") and d.args:
                    v=ast.literal_eval(d.args[0])
                    urls += [v] if isinstance(v,str) else list(v)
u=sorted(set(urls))
print(f"{len(urls)} {len(u)} {hashlib.sha256(chr(10).join(u).encode()).hexdigest()}")
PYEOF
)
# The URL SET, not its size: a fingerprint is not a measurement of tree size, so
# it stays a literal. Re-pin it in the commit that adds, drops or renames a route,
# and say which in the message -- a bumped digest with no such sentence is the one
# way this assertion can be defeated. This pin moved once, from
# e556cf5066...f66363: `3d39ae624a0` dropped `/mail/thread/recipients/fields`,
# taking the URL set from 85 to 84 without re-deriving the digest.
assert_eq "route URL set is exactly the documented one (sha256)" \
    "$(echo "$route_urls" | cut -d' ' -f3)" \
    "6e12c092cec25fc865dfa2a892d7f4789901f41eb648a29626b43c8555c86a8f"
assert_doc_cites "ARCHITECTURE.md cites the route count" "$route_handlers" \
    'files · \*\*%s\*\* routes' ARCHITECTURE.md
# The two central data endpoints exist.
# Count the ROUTE, not every mention: the previous form counted grep hits for the
# URL anywhere in the file (3 and 2), so a docstring losing the word took it red
# while the route it names was untouched.
assert_eq "webclient.py defines /mail/data" \
    "$(grep -cE '^\s+(@http\.route\()?"/mail/data"' "$MAIL/controllers/webclient.py")" "1"
assert_eq "webclient.py defines /mail/action" \
    "$(grep -cE '@http\.route\("/mail/action"' "$MAIL/controllers/webclient.py")" "1"
assert_eq "ROUTE_MAP.md marks /mail/data as the readonly endpoint" \
    "$(grep -c '| `/mail/data` | jsonrpc | \*\*yes\*\*' "$DOC/ROUTE_MAP.md")" "1"
assert_eq "webclient.py: /mail/data route is readonly=True" \
    "$(grep -c '"/mail/data", methods=\["POST"\], type="jsonrpc", auth="public", readonly=True' "$MAIL/controllers/webclient.py")" "1"
assert_eq "webclient.py: /mail/action route is NOT readonly" \
    "$(grep -c '@http.route("/mail/action", methods=\["POST"\], type="jsonrpc", auth="public")' "$MAIL/controllers/webclient.py")" "1"

# Framework contract the ROUTE_MAP legend depends on: `readonly` defaults to auth=="none",
# NOT to False. Confirmed against the live routing map (all 20 font_to_img URLs report
# readonly=True while declaring nothing). If upstream changes this, the legend goes stale.
assert_eq "framework routing.py is where we think it is" \
    "$([ -f "$ODOO/odoo/http/routing.py" ] && echo 1 || echo 0)" "1"
assert_eq "odoo/http: readonly defaults to (auth == 'none')" \
    "$(grep -c 'default_mode = fragment.get("readonly", default_auth == "none")' "$ODOO/odoo/http/routing.py")" "1"
assert_eq "ROUTE_MAP.md documents the auth=='none' readonly default" \
    "$(grep -c 'readonly` \*\*defaults to `auth == "none"`\*\*' "$DOC/ROUTE_MAP.md")" "1"
assert_eq "ROUTE_MAP.md no stale 'readonly=False' default claim" \
    "$(grep -c 'csrf=True` (http), `readonly=False`' "$DOC/ROUTE_MAP.md")" "0"
assert_eq "export_icon_to_png is mail's only auth='none' handler" \
    "$(grep -rc "auth=\"none\"" "$MAIL/controllers"/*.py "$MAIL/controllers/discuss"/*.py | grep -vc ':0')" "1"

# ============================ Guest auth ============================
assert_eq "tools/discuss.py defines add_guest_to_context" \
    "$(grep -c 'def add_guest_to_context' "$MAIL/tools/discuss.py")" "1"
assert_eq "mail_guest.py cookie name is dgid" \
    "$(grep -c '_cookie_name = .dgid.' "$MAIL/models/discuss/mail_guest.py")" "1"
assert_eq "mail_guest.py defines _get_guest_from_token" \
    "$(grep -c 'def _get_guest_from_token' "$MAIL/models/discuss/mail_guest.py")" "1"
assert_eq "no custom _auth_method_ in mail" \
    "$(grep -rl '_auth_method_' "$MAIL/controllers" "$MAIL/models" 2>/dev/null | wc -l)" "0"
assert_eq "ROUTE_MAP.md documents the dgid guest cookie" \
    "$(grep -c 'dgid' "$DOC/ROUTE_MAP.md")" "2"
assert_eq "mail_guest.py cookie separator is |" \
    "$(grep -c '_cookie_separator = "|"' "$MAIL/models/discuss/mail_guest.py")" "1"
assert_eq "_get_guest_from_token rejects a non-digit id (no 500 on hostile cookie)" \
    "$(grep -c 'if not guest_id.isdigit():' "$MAIL/models/discuss/mail_guest.py")" "1"
assert_eq "_get_guest_from_context asserts a single-record guest" \
    "$(grep -c 'assert len(guest) <= 1' "$MAIL/models/discuss/mail_guest.py")" "1"
assert_eq "CONVENTIONS.md documents add_guest_to_context" \
    "$(grep -c 'add_guest_to_context' "$DOC/CONVENTIONS.md")" "2"

# ============================ Python mixin API ============================
# The mixins are models/mixin_<what they add>.py since coding_guidelines 2.2.1; `mail.thread`
# is `mixin.mail.thread` and models/mail_thread.py does not exist. Round 3 greps still named the
# old paths, so four assertions failed on a missing file rather than on anything being wrong.
assert_eq "mixin_mail_thread.py defines _name mixin.mail.thread" \
    "$(grep -c '_name = .mixin.mail.thread.' "$MAIL/models/mixin_mail_thread.py")" "1"
assert_eq "no models/mail_thread.py (pre-rename path)" \
    "$([ -e "$MAIL/models/mail_thread.py" ] && echo 1 || echo 0)" "0"
# A COUNT CANNOT SAY WHICH MIXIN IS UNDOCUMENTED. This was `models/ holds 14
# mixin_*.py files`, a literal that went red the moment a fifteenth landed and
# said nothing about the four that MODEL_MAP.md had no row for -- the "expected
# values are a second copy of the tree" shape §1.4 exists to remove. Both
# directions are checked, so a mixin added without a row fails here, and so does
# a row naming a file that has been deleted.
undocumented=""
for f in "$MAIL"/models/mixin_*.py "$MAIL"/models/*/mixin_*.py; do
    [ -e "$f" ] || continue
    base="$(basename "$f")"
    grep -qF "\`$base\`" "$DOC/MODEL_MAP.md" || undocumented="$undocumented $base"
done
assert_eq "MODEL_MAP.md has a row for every models/ mixin_*.py${undocumented:+ —$undocumented}" \
    "$(printf '%s' "$undocumented" | wc -w)" "0"
phantom=""
while read -r cited; do
    [ -z "$cited" ] && continue
    [ -n "$(find "$MAIL/models" -name "$cited" -print -quit)" ] \
        || phantom="$phantom $cited"
done < <(grep -ohP '`\Kmixin_\w+\.py' "$DOC"/*.md | sort -u)
assert_eq "MODEL_MAP.md cites no mixin_*.py that is gone${phantom:+ —$phantom}" \
    "$(printf '%s' "$phantom" | wc -w)" "0"
assert_eq "discuss/ holds mixin_bus_listener.py" \
    "$([ -f "$MAIL/models/discuss/mixin_bus_listener.py" ] && echo 1 || echo 0)" "1"
assert_eq "no doc names a pre-rename mixin file path" \
    "$(grep -cE '`(mail_thread|mail_thread_cc|mail_thread_blacklist|mail_render_mixin|mail_activity_mixin|mail_alias_mixin|template_reset_mixin|bus_listener_mixin)\.py`' "$DOC"/*.md | grep -vc ':0')" "0"
assert_eq "mixin_mail_thread.py defines message_post" \
    "$(grep -cE 'def message_post\(' "$MAIL/models/mixin_mail_thread.py")" "1"
assert_eq "mixin_mail_thread.py defines _notify_thread" \
    "$(grep -cE 'def _notify_thread\(' "$MAIL/models/mixin_mail_thread.py")" "1"
# The gateway left the thread mixin in 20d1a0995c6; assert it by its new home,
# and that it did not stay behind in the old one.
assert_eq "mixin_mail_gateway.py defines message_process (gateway)" \
    "$(grep -cE 'def message_process\(' "$MAIL/models/mixin_mail_gateway.py")" "1"
assert_eq "message_process is NOT still on mixin_mail_thread.py" \
    "$(grep -cE 'def message_process\(' "$MAIL/models/mixin_mail_thread.py")" "0"
assert_eq "base.py defines _mail_get_partners (helper on base)" \
    "$(grep -cE 'def _mail_get_partners\(' "$MAIL/models/base.py")" "1"
assert_eq "MODEL_MAP.md names message_post the central entry point" \
    "$(grep -c 'post a message on the record (central entry point)' "$DOC/MODEL_MAP.md")" "1"
assert_eq "CONVENTIONS.md gotcha: message_post canonical" \
    "$(grep -c 'message_post. is the canonical posting API' "$DOC/CONVENTIONS.md")" "1"

# ============================ JS Store/Record framework ============================
# Count models by .register() call sites — NOT by grepping 'extends Record'. That grep is
# wrong twice over (it misses `Attachment extends FileModelMixin(Record)` and falsely matches
# `StoreInternal extends RecordInternal`); the two errors cancel, so it returns the right
# number for the wrong reason and would drift silently.
registered_models=$(grep -rh '\.register();' "$MAIL/static/src" | wc -l)
assert_doc_cites "ARCHITECTURE.md cites the registered-model count" \
    "$(( registered_models - 1 )) $registered_models" \
    '\| JS model classes \(registered with `\.register\(\)`\) \| %s \(\+ the base `Record` itself → %s calls\) \|' \
    ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE.md's .register() note cites the same count" "$registered_models" \
    'Count `\.register\(\)` call sites instead: %s,' ARCHITECTURE.md
assert_eq "base Record registers itself in model/record.js" \
    "$(grep -c '^Record.register();' "$MAIL/static/src/model/record.js")" "1"
assert_eq "Attachment is a model despite not matching 'extends Record'" \
    "$(grep -c 'export class Attachment extends FileModelMixin(Record)' "$MAIL/static/src/core/common/attachment_model.js")" "1"
assert_eq "StoreInternal is NOT a model (false 'extends Record' substring match)" \
    "$(grep -c 'export class StoreInternal extends RecordInternal' "$MAIL/static/src/model/store_internal.js")" "1"
assert_eq "every core/common .register() is a model or the Store singleton" \
    "$(( $(grep -rh '\.register();' "$MAIL/static/src/core/common" | wc -l) > 0 ))" "1"
# static _name split: 25 declare one, 14 are keyed by class name. Verified against the live
# modelRegistry in a browser (40 entries there: these 39 + ai.prompt.button from the `ai`
# module — the registry is global, so only the source-side count is assertable here).
named=0; unnamed=0
for f in $(grep -rl '\.register();' "$MAIL/static/src"); do
    if grep -q 'static _name = "' "$f"; then named=$((named+1)); else unnamed=$((unnamed+1)); fi
done
assert_eq "registered models declaring static _name" "$named" "25"
assert_doc_cites "CONVENTIONS.md gotcha 4 cites both halves of the _name split" \
    "$unnamed $registered_models" \
    '%s of the %s registered models have no `static _name`' CONVENTIONS.md
assert_eq "Thread really has no static _name (reached via pyToJsModels)" \
    "$(grep -c 'static _name' "$MAIL/static/src/core/common/thread_model.js")" "0"
assert_eq "Settings is fed by the res.users.settings bus type" \
    "$(grep -c '_bus_send("res.users.settings"' "$MAIL/models/res_users_settings.py")" "1"
assert_eq "model/record.js exports class Record" \
    "$(grep -c '^export class Record' "$MAIL/static/src/model/record.js")" "1"
assert_eq "model/store.js exports class Store extends Record" \
    "$(grep -c '^export class Store extends Record' "$MAIL/static/src/model/store.js")" "1"
assert_eq "model/make_store.js exports function makeStore" \
    "$(grep -c '^export function makeStore' "$MAIL/static/src/model/make_store.js")" "1"
assert_eq "misc.js registers modelRegistry under discuss.model" \
    "$(grep -c 'discuss.model' "$MAIL/static/src/model/misc.js")" "1"
assert_eq "store_service.js registers mail.store service" \
    "$(grep -c 'registry.category("services").add("mail.store"' "$MAIL/static/src/core/common/store_service.js")" "1"
assert_eq "STATE_MANAGEMENT.md documents the 8-queue flush order" \
    "$(grep -c 'FC  computes' "$DOC/STATE_MANAGEMENT.md")" "1"
assert_eq "store.js flush loop guards at 1000 iterations" \
    "$(grep -c 'if (++flushIterations > 1000)' "$MAIL/static/src/model/store.js")" "1"
assert_eq "STATE_MANAGEMENT.md cites the same 1000 cap" \
    "$(grep -c 'iteration cap 1000' "$DOC/STATE_MANAGEMENT.md")" "1"

# ============================ JS services ============================
services_actual=$(grep -rhzoE 'registry\.category\("services"\)\.add\(\s*"[^"]+"' "$MAIL/static/src" \
    | tr '\0' '\n' | grep -oE '"[^"]+"$' | sort -u | wc -l)
assert_doc_cites "ARCHITECTURE.md cites the OWL service count" "$services_actual" \
    '\*\*%s OWL services\*\*' ARCHITECTURE.md
# The RTC engine service exists where the docs say.
assert_eq "discuss.rtc service in rtc_service.js" \
    "$(grep -c 'registry.category("services").add("discuss.rtc"' "$MAIL/static/src/discuss/call/common/rtc_service.js")" "1"

# ============================ ASSET_LAYERS ============================
assert_eq "manifest esm.bundles lists exactly the 3 documented ESM bundles" \
    "$("$PY" -c "import ast,sys;m=ast.literal_eval(open('$MAIL/__manifest__.py').read());print(','.join(sorted(m['esm']['bundles'])))")" \
    "mail.assets_discuss_public_test_tours,mail.assets_lamejs,mail.assets_public"
assert_eq "manifest declares the SFU client as a library" \
    "$("$PY" -c "import ast;m=ast.literal_eval(open('$MAIL/__manifest__.py').read());print(m['esm']['external_libs']['@odoo/sfu'])")" \
    "/mail/static/lib/odoo_sfu/odoo_sfu.js"
# 15: web.assets_web_dark went away with the dark-mode rework (mail ships no
# *.dark.scss and web now answers both colour schemes from one stylesheet), and
# mail.assets_odoo_sfu became the `@odoo/sfu` library.
assert_eq "manifest declares 15 asset bundles" \
    "$("$PY" -c "import ast;m=ast.literal_eval(open('$MAIL/__manifest__.py').read());print(len(m['assets']))")" "15"
assert_eq "manifest declares no dark bundle" \
    "$(grep -c 'assets_web_dark' "$MAIL/__manifest__.py")" "0"
assert_eq "mail ships no *.dark.scss" \
    "$(find "$MAIL/static/src" -name '*.dark.scss' | wc -l)" "0"
assert_eq "manifest declares mail.assets_core_common sub-bundle" \
    "$(grep -c '"mail.assets_core_common"' "$MAIL/__manifest__.py")" "1"
# lamejs appears 3x: the assets-dict bundle key + esm.bundles + dynamic_children.
# The SFU client is a library, not a bundle, since 2026-09-06.
assert_eq "manifest no longer declares mail.assets_odoo_sfu" \
    "$(grep -c '"mail.assets_odoo_sfu"' "$MAIL/__manifest__.py")" "0"
assert_eq "manifest declares mail.assets_lamejs (bundle + esm + dynamic_child)" \
    "$(grep -c '"mail.assets_lamejs"' "$MAIL/__manifest__.py")" "3"
# discuss remove tuples (formatted one element per line): 1 in web.assets_backend + 1 in
# mail.assets_public. Was 4 while
# each also stripped *.dark.scss; those two went with the dark-mode rework.
assert_eq "manifest has discuss remove-then-re-add block (2 remove lines)" \
    "$(grep -A1 -E '"remove",' "$MAIL/__manifest__.py" | grep -c 'mail/static/src/discuss')" "2"
# Vendored libs exist.
for lib in idb-keyval/idb-keyval.js lame/lame.js odoo_sfu/odoo_sfu.js selfie_segmentation/selfie_segmentation.js; do
    assert_eq "static/lib/$lib exists" \
        "$([ -f "$MAIL/static/lib/$lib" ] && echo 1 || echo 0)" "1"
done
# ASSET_LAYERS.md must name each of the five deployment layers.
for layer in common web public_web web_portal public; do
    assert_eq "ASSET_LAYERS.md names layer '$layer'" \
        "$([ "$(grep -c "\`$layer/\`" "$DOC/ASSET_LAYERS.md")" -ge 1 ] && echo 1 || echo 0)" "1"
done

# Layer distribution (files by layer segment) — lock the shape.
assert_range "common-layer JS files" \
    "$(find "$MAIL/static/src" -type f -name '*.js' -path '*/common/*' | wc -l)" 180 220
# The web-layer file count was an `assert_range 100..130` that no doc states. A
# range that wide guards nothing -- the tree moved 32 files inside it and the
# assertion never noticed, then failed on the 33rd -- and there is no document to
# cite, so it is dropped rather than re-ranged. ASSET_LAYERS.md is where the
# `web` suffix earns an assertion, and it already has one.

# ============================ Layer import rule (spot check) ============================
# common/ must not import from a higher layer. Assert no core/common file imports
# from @mail/*/web/ or @mail/*/public_web/ (would break the public page).
assert_eq "no core/common import from a web layer" \
    "$(grep -rlE 'from \"@mail/[a-z_/]*/(web|web_portal|public_web|public)/' "$MAIL/static/src/core/common" 2>/dev/null | wc -l)" "0"

# Vendored-lib versions (fact-check round found idb-keyval was mis-cited as 2.0).
assert_eq "idb-keyval source header version is 3.2.0" \
    "$(grep -oiE 'idb-keyval.js [0-9]+\.[0-9]+\.[0-9]+' "$MAIL/static/lib/idb-keyval/idb-keyval.js" | head -1)" "idb-keyval.js 3.2.0"
assert_eq "ASSET_LAYERS.md cites idb-keyval 3.2.0 (not 2.0)" \
    "$(grep -c 'idb-keyval.js. | 3.2.0' "$DOC/ASSET_LAYERS.md")" "1"
# Pin the __info__ block, not a bare "1.3.3" — the bundle contains many dependency versions.
assert_eq "odoo_sfu __info__ declares version 1.3.3" \
    "$(grep -c "    version: '1.3.3'," "$MAIL/static/lib/odoo_sfu/odoo_sfu.js")" "1"
assert_eq "ASSET_LAYERS.md cites odoo_sfu 1.3.3" \
    "$(grep -c '| 1.3.3 |' "$DOC/ASSET_LAYERS.md")" "1"
assert_eq "selfie_segmentation build id is 0.1.1632777926" \
    "$(grep -oE '0\.1\.1632777926' "$MAIL/static/lib/selfie_segmentation/selfie_segmentation.js" | head -1)" "0.1.1632777926"

# mail.mail uses _inherits (delegation), NOT _inherit — the fact-check caught this.
assert_eq "mail_mail.py uses _inherits (delegation)" \
    "$(grep -c '_inherits = {\"mail.message\": \"mail_message_id\"}' "$MAIL/models/mail_mail.py")" "1"
assert_eq "mail_mail.py does NOT use plain _inherit for mail.message" \
    "$(grep -cE '^\s*_inherit = ' "$MAIL/models/mail_mail.py")" "0"
assert_eq "MODEL_MAP.md documents mail.mail delegation, not _inherit" \
    "$(grep -c 'Delegation inheritance, \*\*not\*\* `_inherit`' "$DOC/MODEL_MAP.md")" "1"
assert_eq "mixin.mail.alias is the other _inherits user (via alias_id)" \
    "$(grep -c '_inherits = {"mail.alias": "alias_id"}' "$MAIL/models/mixin_mail_alias.py")" "1"

# The bracketless except form (Py 3.14 / PEP 758) really is present in controllers.
except_count=$(grep -rhE 'except [A-Za-z_.]+, [A-Za-z_.]+:' "$MAIL/controllers" | wc -l)
assert_eq "bracketless 'except A, B:' occurrences in controllers (valid Py3.14)" "$except_count" "6"
assert_eq "CONVENTIONS.md gotcha documents the except A, B form" \
    "$(grep -c 'except A, B' "$DOC/CONVENTIONS.md")" "1"

# MAKE_UPDATE 8-queue flush order (verified against store.js): every queue is swapped
# out once per iteration through _takeQueue.
queue_takes=$(grep -oE '_takeQueue\("[A-Z]+_QUEUE"\)' "$MAIL/static/src/model/store.js" | sort -u | wc -l)
assert_eq "store.js drains all 8 flush queues (_takeQueue calls)" "$queue_takes" "8"

# ============================ TEST_TAGS ============================
# `e4df7f5569b` deleted the twenty-one round-numbered hardening suites. What is
# gated now is that they STAY gone from the docs: a tag table naming a file that
# does not exist sends every reader to a test run that selects nothing, which is
# how this harness spent ten days telling sessions to run `mail_hardening_v6`.
assert_eq "no round-numbered hardening suite is back in tests/" \
    "$(find "$MAIL/tests" -name 'test_mail_hardening_v*.py' -o -name 'test_mail_audit_v*.py' | wc -l)" "0"
# Naming them is fine -- the blockquote in TEST_TAGS.md that records the deletion
# has to. What must never come back is a doc that OFFERS one: a tag-table row, or
# a `--test-tags` line, either of which sends a reader to a run that selects
# nothing and reports success.
assert_eq "no doc offers a round-numbered hardening suite as a runnable tag" \
    "$(grep -rhE '^\| `mail_(hardening|audit)_v[0-9]|--test-tags mail_(hardening|audit)_v[0-9]' "$DOC" | wc -l)" "0"
assert_eq "mail_js tags both HOOT suite classes in test_js.py" \
    "$(grep -c '@odoo.tests.tagged("post_install", "-at_install", "mail_js")' "$MAIL/tests/test_js.py")" "2"
assert_eq "tests/common.py defines MailCommon" \
    "$(grep -c 'class MailCommon' "$MAIL/tests/common.py")" "1"
assert_eq "tests/common.py defines mock_mail_gateway" \
    "$(grep -c 'def mock_mail_gateway' "$MAIL/tests/common.py")" "1"
assert_eq "TEST_TAGS.md documents the MailCommon tower" \
    "$(grep -c 'MailCommon' "$DOC/TEST_TAGS.md")" "3"
assert_eq "tests/common.py defines the MailCase middle tier" \
    "$(grep -c '^class MailCase' "$MAIL/tests/common.py")" "1"
assert_eq "tests/common.py defines the MockEmail foundation" \
    "$(grep -c '^class MockEmail' "$MAIL/tests/common.py")" "1"

# ============================ Round-2 fact-check corrections ============================
# Each pairs a code-reality check with the doc assertion, so the corrected fact can't drift back.

# lame.js is 1.2.1 (the earlier "2.1" was LGPL boilerplate "version 2.1 of the License").
assert_eq "lame.js header version is 1.2.1" \
    "$(grep -c 'V.1.2.1' "$MAIL/static/lib/lame/lame.js")" "1"
assert_eq "ASSET_LAYERS.md cites lame 1.2.1 (not 2.1)" \
    "$(grep -c '1.2.1 (lamejs)' "$DOC/ASSET_LAYERS.md")" "1"
assert_eq "ASSET_LAYERS.md no stale bare lame 2.1 cite" \
    "$(grep -cE '[^.0-9]2\.1 \(lamejs\)' "$DOC/ASSET_LAYERS.md")" "0"

# discussComponentRegistry uses category "discuss.component", NOT "discuss.model".
assert_eq "discuss_component_registry.js uses category discuss.component" \
    "$(grep -c 'registry.category("discuss.component")' "$MAIL/static/src/core/common/discuss_component_registry.js")" "1"
assert_eq "STATE_MANAGEMENT.md cites discuss.component category" \
    "$(grep -c 'discuss.component' "$DOC/STATE_MANAGEMENT.md")" "3"
assert_eq "modelRegistry really uses category discuss.model" \
    "$(grep -c 'registry.category("discuss.model")' "$MAIL/static/src/model/misc.js")" "1"
stale_sibling=$(grep -rhE 'discuss\.model. component|component sibling' "$DOC"/*.md | wc -l)
assert_eq "no doc claims discuss.model component sibling" "$stale_sibling" "0"

# MessagingMenu registers itself into systray (not a web-layer patch).
assert_eq "messaging_menu.js registers into systray in-file" \
    "$(grep -c 'category("systray")' "$MAIL/static/src/core/public_web/messaging_menu.js")" "1"

# ir_binary.py is an empty placeholder (0 bytes, not imported) — no ir.binary model.
# Measure BYTES, not lines: `wc -l` counts newlines, so a file holding `class Foo: pass`
# with no trailing newline reports 0 and would pass an "is empty" check while non-empty.
# Both 0-byte ir_binary.py placeholders are now deleted outright. Round 3 measured their
# byte count, which is a file-exists assertion in disguise -- it fails loudly once they go.
assert_eq "models/ir_binary.py is deleted" \
    "$([ -e "$MAIL/models/ir_binary.py" ] && echo 1 || echo 0)" "0"
assert_eq "models/discuss/ir_binary.py is deleted" \
    "$([ -e "$MAIL/models/discuss/ir_binary.py" ] && echo 1 || echo 0)" "0"
assert_eq "ir_binary not imported in models/__init__.py" \
    "$(grep -c 'ir_binary' "$MAIL/models/__init__.py")" "0"
assert_eq "ir_binary not imported in models/discuss/__init__.py" \
    "$(grep -c 'ir_binary' "$MAIL/models/discuss/__init__.py")" "0"

# Gateway partner/user finders are on mail_thread.py, not base.py.
assert_eq "_mail_get_user_for_gateway is on mixin_mail_gateway.py" \
    "$(grep -c 'def _mail_get_user_for_gateway' "$MAIL/models/mixin_mail_gateway.py")" "1"
assert_eq "_mail_get_user_for_gateway is NOT on base.py" \
    "$(grep -c 'def _mail_get_user_for_gateway' "$MAIL/models/base.py")" "0"

# mail.thread class-level knob defaults.
assert_eq "_mail_flat_thread default is True" \
    "$(grep -c '_mail_flat_thread = True' "$MAIL/models/mixin_mail_thread.py")" "1"
assert_eq "_mail_thread_customer default is False" \
    "$(grep -c '_mail_thread_customer = False' "$MAIL/models/mixin_mail_thread.py")" "1"
assert_eq "_mail_post_access default is write" \
    "$(grep -c '_mail_post_access = "write"' "$MAIL/models/base.py")" "1"
assert_eq "_primary_email default is email" \
    "$(grep -c '_primary_email = "email"' "$MAIL/models/mixin_mail_thread.py")" "1"

# Directory-map corrected counts.
# Every subtree row of DIRECTORY_MAP's top-level split, derived. The total above
# is asserted to be their sum, so a row and the sum cannot drift apart.
for _sub in model core discuss chatter views utils webclient worklets; do
    assert_doc_cites "DIRECTORY_MAP.md cites the $_sub/ JS count" \
        "$(find "$MAIL/static/src/$_sub" -name '*.js' -not -path '*/@types/*' 2>/dev/null | wc -l)" \
        "\\| \`$_sub/\` \\| %s \\|" DIRECTORY_MAP.md
done
assert_eq "DIRECTORY_MAP.md no stale views ~35 cite" \
    "$(grep -c '~35' "$DOC/DIRECTORY_MAP.md")" "0"
# static/src/js/ is gone. Gated as absence for the same reason as the hardening
# suites above: a DIRECTORY_MAP row for a subtree that is not there is a reader
# sent to a path that does not exist.
assert_eq "static/src/js/ stays gone" \
    "$([ -d "$MAIL/static/src/js" ] && echo 1 || echo 0)" "0"
assert_eq 'no doc still carries a `js/` subtree row' \
    "$(grep -c '^| `js/` |' "$DOC/DIRECTORY_MAP.md")" "0"
assert_eq "mock_models file count is 35" \
    "$(find "$MAIL/static/tests/mock_server/mock_models" -name '*.js' | wc -l)" "35"
assert_eq "TEST_TAGS.md cites 35 mock model files" \
    "$(grep -c '35 mock model files' "$DOC/TEST_TAGS.md")" "1"
assert_eq "wizard .py files (excl __init__) is 9" \
    "$(find "$MAIL/wizards" -name '*.py' ! -name '__init__.py' | wc -l)" "9"

# ROUTE_MAP: two channel.py routes require login (update_avatar + sub_channel/delete).
# The literal said 1 while the line above it said two, so this could never pass.
assert_eq "channel.py's two auth=user routes (update_avatar + sub_channel/delete)" \
    "$(grep -c 'auth="user"' "$MAIL/controllers/discuss/channel.py")" "2"

# ================= Round-3 fact-check: previously uncovered claims =================
# Everything below was wrong or missing in the docs and had NO assertion guarding it.

# XML totals. ARCHITECTURE.md claimed "~380"; the real module-wide total is 232 and its own
# breakdown only ever summed to 224 (it omitted wizards/security/test XML).
assert_eq "module-wide XML file count" "$(find "$MAIL" -name '*.xml' | wc -l)" "233"
assert_eq "static OWL template XML" "$(find "$MAIL/static/src" -name '*.xml' | wc -l)" "165"
assert_eq "views/ XML"   "$(find "$MAIL/views"  -name '*.xml' | wc -l)" "41"
assert_eq "data/ XML"    "$(find "$MAIL/data"   -name '*.xml' | wc -l)" "15"
assert_eq "wizards/ XML"  "$(find "$MAIL/wizards" -name '*.xml' | wc -l)" "6"
assert_eq "demo/ XML"    "$(find "$MAIL/demo"   -name '*.xml' | wc -l)" "4"
assert_eq "ARCHITECTURE.md cites the 232 XML total with its breakdown" \
    "$(grep -c '232 = 164 static OWL + 41 views + 15 data + 6 wizard + 4 demo + 1 security + 1 test' "$DOC/ARCHITECTURE.md")" "1"
assert_eq "ARCHITECTURE.md no stale ~380 XML cite" \
    "$(grep -c '~380' "$DOC/ARCHITECTURE.md")" "0"

# static/src/worklets/ — omitted entirely from DIRECTORY_MAP's top-level split, which left
# its rows summing to 391 against a real 392.
assert_eq "static/src/worklets/ holds the RTC audio worklet" \
    "$(find "$MAIL/static/src/worklets" -name '*.js' | wc -l)" "1"
assert_eq "DIRECTORY_MAP.md lists the worklets/ row" \
    "$(grep -c '| `worklets/` | 1 |' "$DOC/DIRECTORY_MAP.md")" "1"
# The top-level split must account for every static/src JS file.
top_split=$(( $(find "$MAIL/static/src/model" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/core" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/discuss" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/chatter" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/views" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/utils" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/js" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/webclient" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src/worklets" -name '*.js' | wc -l) \
            + $(find "$MAIL/static/src" -maxdepth 1 -name '*.js' | wc -l) ))
assert_eq "DIRECTORY_MAP top-level split accounts for all static/src JS" \
    "$top_split" "$(find "$MAIL/static/src" -name '*.js' | wc -l)"

# Mock-server route count. TEST_TAGS.md claimed "~52"; the real figure is 39.
assert_doc_cites "TEST_TAGS.md cites the mocked RPC route count" \
    "$(grep -cE '^registerRoute\(' "$MAIL/static/tests/mock_server/mail_mock_server.js")" \
    '%s mocked RPC routes' TEST_TAGS.md
assert_eq "TEST_TAGS.md no stale ~52 cite" \
    "$(grep -c '~52' "$DOC/TEST_TAGS.md")" "0"

# JS test directory table. core/ was cited as 15 (really 16) and widgets/ as 2 (really 1);
# the two errors cancelled, so the table summed correctly while both rows were wrong.
assert_eq "static/tests/core/ test files"    "$(find "$MAIL/static/tests/core"    -name '*.test.js' | wc -l)" "30"
assert_eq "static/tests/widgets/ test files" "$(find "$MAIL/static/tests/widgets" -name '*.test.js' | wc -l)" "1"
assert_doc_cites "TEST_TAGS.md cites the discuss/ test-file count" \
    "$(find "$MAIL/static/tests/discuss" -name '*.test.js' | wc -l)" \
    '\| `discuss/` \| %s \|' TEST_TAGS.md
assert_doc_cites "TEST_TAGS.md cites the core/ test-file count" \
    "$(find "$MAIL/static/tests/core" -name '*.test.js' | wc -l)" \
    '\| `core/` \| %s \|' TEST_TAGS.md
assert_eq "TEST_TAGS.md moved widgets/ to the '1 each' row" \
    "$(grep -c 'translation/`, `widgets/`' "$DOC/TEST_TAGS.md")" "1"

# Test-class tagging. Both @tagged and @odoo.tests.tagged spellings are in use; counting only
# the bare form undercounts (that is how "97 post_install classes" was reached).
tagged_total=$(grep -rhcE '^@(odoo\.tests\.)?tagged\(' "$MAIL/tests" | awk '{s+=$1} END{print s}')
tagged_post=$(grep -rhE '^@(odoo\.tests\.)?tagged\(' "$MAIL/tests" | grep -c 'post_install')
assert_doc_cites "TEST_TAGS.md cites both halves of the tagged-class split" \
    "$tagged_total $tagged_post" \
    'Of \*\*%s\*\* tagged classes, \*\*%s\*\*' TEST_TAGS.md
assert_eq "TEST_TAGS.md warns about the two decorator spellings" \
    "$(grep -c 'decorator spellings are in use' "$DOC/TEST_TAGS.md")" "1"

# Per-tag class counts that the docs assert in prose.
# The topic-tag table against the tree's actual tags. This is the assertion whose
# absence let 21 deleted suites sit in TEST_TAGS.md for ten days: every count here
# was gated and the SET was not, so removing a file moved a number nobody had
# written down and left the table naming files that were gone.
tree_tags=$(grep -rhE '^@(odoo\.tests\.)?tagged\(' "$MAIL/tests" \
    | grep -oE '"[a-zA-Z_][a-zA-Z0-9_]*"' | tr -d '"' \
    | grep -vE '^(post_install|at_install)$' | sort -u)
undocumented=$(for t in $tree_tags; do
    grep -qE "\`$t\`" "$DOC/TEST_TAGS.md" || echo "$t"
done | wc -l)
assert_eq "every topic tag in tests/ is named in TEST_TAGS.md" "$undocumented" "0"
# ...and every row that states a class count states the right one. The set check
# above cannot see this: `mail_asset_index` was named correctly and claimed 3
# classes against a real 1. Derived per row rather than asserted row by row, so a
# row added later is gated by having been written, not by someone remembering.
tag_count_drift=$(
    grep -oE '^\| `[a-z_]+` \([0-9]+' "$DOC/TEST_TAGS.md" | while read -r row; do
        tag=$(echo "$row" | grep -oE '`[a-z_]+`' | tr -d '`')
        claimed=$(echo "$row" | grep -oE '[0-9]+$')
        real=$(grep -rhE '^@(odoo\.tests\.)?tagged\(' "$MAIL/tests" | grep -c "\"$tag\"")
        [ "$claimed" = "$real" ] || echo "$tag: doc $claimed, tree $real"
    done | wc -l
)
assert_eq "every TEST_TAGS.md row that states a class count states the tree's" \
    "$tag_count_drift" "0"
assert_eq "mail_controller classes (7 in discuss/ + 3 in controller_contract + mock_server_contract)" \
    "$(grep -rhE '^@(odoo\.tests\.)?tagged\(' "$MAIL/tests" | grep -c 'mail_controller')" "11"

# Controller file count: 19, not 21 — the docs were counting the two __init__.py, which is
# inconsistent with the models row (76, which excludes it).
assert_doc_cites "ROUTE_MAP.md cites the controller file count" \
    "$(find "$MAIL/controllers" -name '*.py' ! -name '__init__.py' | wc -l)" \
    '\*\*%s\*\* controller files' ROUTE_MAP.md
assert_eq "no doc still claims 21 controller files" \
    "$(grep -rc '21 controller files' "$DOC"/*.md | grep -vc ':0')" "0"
# The row carries two figures. It used to be pinned as one literal string holding
# both, so the route half was a second copy of the count asserted above and the
# file half could not move without it.
assert_doc_cites "ARCHITECTURE.md cites the controller file count" \
    "$(find "$MAIL/controllers" -name '*.py' ! -name '__init__.py' | wc -l)" \
    '\| Python controllers \| %s files ·' ARCHITECTURE.md
assert_eq "ARCHITECTURE.md wizard row agrees with DIRECTORY_MAP (9, excl __init__)" \
    "$(grep -c '| Python wizards | 9 |' "$DOC/ARCHITECTURE.md")" "1"

# The layer import rule holds module-wide, not just in core/common.
assert_eq "no common/ file anywhere imports from a higher layer" \
    "$(grep -rlE 'from "@mail/[a-z_/]*/(web|web_portal|public_web|public)/' --include='*.js' "$MAIL/static/src" 2>/dev/null | grep -c '/common/')" "0"

# service_worker.js is in no bundle at all (CONVENTIONS gotcha 2 named a non-existent
# "@odoo-module ignore" annotation; the real evidence is manifest absence).
assert_eq "service_worker.js appears in no asset bundle" \
    "$("$PY" -c "import ast;m=ast.literal_eval(open('$MAIL/__manifest__.py').read());print(sum(1 for b in m['assets'].values() for i in b if isinstance(i,str) and i.endswith('src/service_worker.js')))")" "0"
assert_eq "service_worker_utils.js IS exposed to HOOT" \
    "$("$PY" -c "import ast;m=ast.literal_eval(open('$MAIL/__manifest__.py').read());print(int('mail/static/src/service_worker_utils.js' in m['assets']['web.assets_unit_tests']))")" "1"

# ================= Round-4 fact-check: previously uncovered claims =================
# Everything below was wrong or unguarded in round 3.

# The renamed helper families. Each old name is a method an override can still be WRITTEN
# against -- it compiles, overrides nothing, and raises nothing -- so assert both that the new
# name exists AND that the old one does not, in the code and in the docs.
assert_eq "base.py: _message_get_suggested_recipients_sources (was _message_add_...)" \
    "$(grep -cE 'def _message_get_suggested_recipients_sources\(' "$MAIL/models/base.py")" "1"
assert_eq "base.py: _message_get_default_recipients_sources exists" \
    "$(grep -cE 'def _message_get_default_recipients_sources\(' "$MAIL/models/base.py")" "1"
assert_eq "_message_add_suggested_recipients is gone module-wide" \
    "$(grep -rE 'def _message_add_suggested_recipients\(' "$MAIL" --include='*.py' | wc -l)" "0"
assert_eq "the one _add_ helper that mutates in place kept its verb" \
    "$(grep -cE 'def _message_add_suggested_recipients_from_replies\(' "$MAIL/models/base.py")" "1"
assert_eq "mixin.mail.thread.cc overrides the _sources hook, not the _add_ one" \
    "$(grep -cE 'def _message_get_suggested_recipients_sources\(' "$MAIL/models/mixin_mail_thread_cc.py")" "1"
assert_eq "no doc names _message_add_suggested_recipients as the hook" \
    "$(grep -c 'overrides `_message_add_suggested_recipients`' "$DOC"/*.md | grep -vc ':0')" "0"

# _partner_get_or_create_from_emails is on base.py. MODEL_MAP.md asserted the opposite in prose --
# "on mail_thread.py, not base.py" -- while CONVENTIONS.md had it right, so the two docs
# contradicted each other and nothing caught it. Pin the location and both docs.
assert_eq "_partner_get_or_create_from_emails is on base.py" \
    "$(grep -cE 'def _partner_get_or_create_from_emails\(' "$MAIL/models/base.py")" "1"
assert_eq "_partner_get_or_create_from_emails is NOT on mixin_mail_thread.py" \
    "$(grep -cE 'def _partner_get_or_create_from_emails\(' "$MAIL/models/mixin_mail_thread.py")" "0"
assert_eq "no doc claims _partner_get_or_create_from_emails lives on the thread mixin" \
    "$(grep -c 'finders `_partner_get_or_create_from_emails`' "$DOC"/*.md | grep -vc ':0')" "0"

# mail.followers: _insert_followers -> _add_followers, and the OLD _add_followers (which
# returned payloads) -> _prepare_followers_vals. The name _add_followers therefore exists on
# both sides of the rename meaning different things -- a carried-over call site compiles.
assert_eq "mail.followers._add_followers creates the records" \
    "$(grep -cE 'def _add_followers\(' "$MAIL/models/mail_followers.py")" "1"
assert_eq "mail.followers._prepare_followers_vals builds the vals" \
    "$(grep -cE 'def _prepare_followers_vals\(' "$MAIL/models/mail_followers.py")" "1"
assert_eq "_insert_followers is gone (SQL DML verb, ORM create)" \
    "$(grep -rE 'def _insert_followers\(' "$MAIL" --include='*.py' | wc -l)" "0"
# name/email were deleted: related+related_sudo leaked past the res.partner ACL to every
# internal user, and rode the chatter payload. is_active and display_name stay.
assert_eq "mail.followers no longer exposes name/email related fields" \
    "$(grep -cE '^ *(name|email) = fields\.' "$MAIL/models/mail_followers.py")" "0"
assert_eq "mail.followers keeps is_active" \
    "$(grep -c 'is_active = fields.Boolean' "$MAIL/models/mail_followers.py")" "1"
assert_eq "MODEL_MAP.md no longer lists name/email on mail.followers" \
    "$(grep -c '`name`/`email`/`is_active` (related)' "$DOC/MODEL_MAP.md")" "0"

# mail.template: the four _generate_template* builders are _prepare_* under 2.4.
assert_eq "_generate_template* is gone from mail.template" \
    "$(grep -cE 'def _generate_template' "$MAIL/models/mail_template.py")" "0"
assert_eq "mail.template _prepare_mail_vals exists" \
    "$(grep -cE 'def _prepare_mail_vals\(' "$MAIL/models/mail_template.py")" "1"
assert_eq "mail.template _prepare_recipient_vals exists" \
    "$(grep -cE 'def _prepare_recipient_vals\(' "$MAIL/models/mail_template.py")" "1"
assert_eq "MODEL_MAP.md no stale _generate_template cite" \
    "$(grep -c '_generate_template(res_ids, fields)' "$DOC/MODEL_MAP.md")" "0"

# mail.message is split across three files; MODEL_MAP attributed all of it to mail_message.py.
assert_eq "mail_message_access.py holds the access rule" \
    "$(grep -cE 'def _get_forbidden_access\(' "$MAIL/models/mail_message_access.py")" "1"
assert_eq "mail_message_store.py holds _to_store" \
    "$(grep -cE 'def _to_store\(' "$MAIL/models/mail_message_store.py")" "1"
assert_eq "_check_access moved off mail_message.py" \
    "$(grep -cE 'def _check_access\(' "$MAIL/models/mail_message.py")" "0"
# 3x each: the section-1 data-model row, the three-files note, and the model index.
assert_eq "MODEL_MAP.md lists mail_message_access.py" \
    "$(grep -c 'mail_message_access.py' "$DOC/MODEL_MAP.md")" "3"
assert_eq "MODEL_MAP.md lists mail_message_store.py" \
    "$(grep -c 'mail_message_store.py' "$DOC/MODEL_MAP.md")" "3"
assert_eq "the parity pin holding the rule's two spellings exists" \
    "$(grep -c '^class TestMailMessageAccessParity' "$MAIL/tests/test_mail_message_access_parity.py")" "1"

# Restricted rendering is a parsed-tree walk now, not a regex. _render_regex_resolve is gone;
# the root allow-list (object, user) it enforced is what actually matters, so pin that.
assert_eq "_render_regex_resolve is gone" \
    "$(grep -rE 'def _render_regex_resolve\(' "$MAIL" --include='*.py' | wc -l)" "0"
assert_eq "_get_static_expression_value replaces it" \
    "$(grep -cE 'def _get_static_expression_value\(' "$MAIL/models/mixin_mail_render.py")" "1"
# The two roots became one table, `_static_expression_roots`, rather than a
# branch each -- so assert the table names both and that a root outside it is
# refused rather than guessed.
assert_eq "it accepts root 'object'" \
    "$(grep -c '"object": record, "user"' "$MAIL/models/mixin_mail_render.py")" "1"
assert_eq "it accepts root 'user'" \
    "$(grep -c '"user": self.env.user}' "$MAIL/models/mixin_mail_render.py")" "1"
assert_eq "an unknown root is refused, not guessed" \
    "$(grep -c 'unsupported root' "$MAIL/models/mixin_mail_render.py")" "1"
assert_eq "the allow-list itself is still on base.py" \
    "$(grep -cE 'def mail_allowed_qweb_expressions\(' "$MAIL/models/base.py")" "1"
assert_eq "CONVENTIONS.md gotcha 8 names the current helper" \
    "$(grep -c '_get_static_expression_value' "$DOC/CONVENTIONS.md")" "1"

# ASSET_LAYERS cited a formatters.js path that does not exist. Pin the manifest string.
assert_eq "mail.assets_public re-includes web/static/src/core/formatters.js" \
    "$(grep -c '"web/static/src/core/formatters.js"' "$MAIL/__manifest__.py")" "1"
assert_eq "no such file as web/static/src/fields/formatters.js" \
    "$([ -e "$ODOO/addons/web/static/src/fields/formatters.js" ] && echo 1 || echo 0)" "0"
assert_eq "ASSET_LAYERS.md cites the core/ formatters path" \
    "$(grep -c 'web/static/src/core/formatters.js' "$DOC/ASSET_LAYERS.md")" "1"


# Per-subtree JS counts DIRECTORY_MAP states. Round 3 pinned only views/ and js/, so core/,
# discuss/ and utils/ drifted unnoticed.
assert_doc_cites "DIRECTORY_MAP.md cites the core/ JS count" \
    "$(find "$MAIL/static/src/core" -name '*.js' | wc -l)" '\| `core/` \| %s \|' DIRECTORY_MAP.md
assert_eq "discuss/ recursive JS count" "$(find "$MAIL/static/src/discuss" -name '*.js' | wc -l)" "146"
assert_eq "utils/ recursive JS count"   "$(find "$MAIL/static/src/utils"   -name '*.js' | wc -l)" "12"
assert_eq "chatter/ recursive JS count" "$(find "$MAIL/static/src/chatter" -name '*.js' | wc -l)" "13"
assert_eq "DIRECTORY_MAP.md cites discuss 146" "$(grep -c '| `discuss/` | 146 |' "$DOC/DIRECTORY_MAP.md")" "1"

# SCSS count: stated in ARCHITECTURE's table, never asserted.
assert_eq "static/src SCSS count" "$(find "$MAIL/static/src" -name '*.scss' | wc -l)" "101"
assert_eq "ARCHITECTURE.md cites 101 SCSS" \
    "$(grep -c '| SCSS (`static/src/`) | 101 |' "$DOC/ARCHITECTURE.md")" "1"

# tools/ file list, stated in DIRECTORY_MAP and two files short.
assert_eq "tools/ .py count (excl __init__)" \
    "$(find "$MAIL/tools" -maxdepth 1 -name '*.py' ! -name '__init__.py' | wc -l)" "18"
for t in access_scan channel_avatar; do
    assert_eq "DIRECTORY_MAP.md lists tools/$t.py" \
        "$(grep -c "\`$t.py\`" "$DOC/DIRECTORY_MAP.md")" "1"
done

# Doc-set hygiene: no doc may spell the module path as if the checkout were nested.
assert_eq "no doc spells the module addons/odoo/addons/mail" \
    "$(grep -c 'addons/odoo/addons/mail' "$DOC"/*.md | grep -vc ':0')" "0"

# TEST_TAGS' run commands must name paths that exist in this workspace.
assert_eq "TEST_TAGS.md no stale config/p314o19marin.conf path" \
    "$(grep -c 'config/p314o19marin.conf' "$DOC/TEST_TAGS.md")" "0"
assert_eq "TEST_TAGS.md no stale venv/ interpreter path" \
    "$(grep -c 'venv/p314o19marin/bin/python' "$DOC/TEST_TAGS.md")" "0"

# Untagged test files: TEST_TAGS states 28 of 52 are unreachable by --test-tags.
untagged=$("$PY" - "$MAIL" <<'PYEOF'
import ast, pathlib, sys
root = pathlib.Path(sys.argv[1], "tests")
SKIP = {"post_install", "-at_install", "at_install", "standard", "-standard"}
tagged, allf = set(), {p for p in root.rglob("test_*.py")}
for p in root.rglob("*.py"):
    for cls in (n for n in ast.walk(ast.parse(p.read_text())) if isinstance(n, ast.ClassDef)):
        for d in cls.decorator_list:
            if isinstance(d, ast.Call) and ast.unparse(d.func).endswith("tagged"):
                if any(ast.literal_eval(a) not in SKIP
                       for a in d.args if isinstance(a, ast.Constant)):
                    tagged.add(p)
print(len(allf - tagged))
PYEOF
)
assert_doc_cites "TEST_TAGS.md cites both halves of the untagged split" \
    "$untagged $py_test_total" \
    '\*\*%s of the %s test files carry no topic tag at all\*\*' TEST_TAGS.md

# The same walk scoped to discuss/. This figure sat in the prose ungated and had
# drifted to "14 of the 23" against a filesystem of 27 -- both halves wrong, and
# invisible because nothing checked it.
disc=$("$PY" - "$MAIL" <<'PYEOF'
import ast, pathlib, sys
root = pathlib.Path(sys.argv[1], "tests", "discuss")
SKIP = {"post_install", "-at_install", "at_install", "standard", "-standard"}
tagged, allf = set(), {p for p in root.rglob("test_*.py")}
for p in root.rglob("*.py"):
    for cls in (n for n in ast.walk(ast.parse(p.read_text())) if isinstance(n, ast.ClassDef)):
        for d in cls.decorator_list:
            if isinstance(d, ast.Call) and ast.unparse(d.func).endswith("tagged"):
                if any(ast.literal_eval(a) not in SKIP
                       for a in d.args if isinstance(a, ast.Constant)):
                    tagged.add(p)
print(len(allf - tagged), len(allf))
PYEOF
)
assert_doc_cites "TEST_TAGS.md cites both halves of the discuss/ untagged split" \
    "$disc" \
    'and \*\*%s of the %s files\*\* in `discuss/`' TEST_TAGS.md

# ============================ Doc set completeness ============================
for f in ARCHITECTURE CONVENTIONS DIRECTORY_MAP MODEL_MAP ROUTE_MAP STATE_MANAGEMENT TEST_TAGS ASSET_LAYERS; do
    assert_eq "$f.md exists" "$([ -f "$DOC/$f.md" ] && echo 1 || echo 0)" "1"
done

echo ""
echo "================================================================"
if [ "$UPDATED" -gt 0 ]; then
    echo "TOTAL: $PASS passed, $FAIL failed, $UPDATED updated (round 4)"
    echo "Re-run without --update to confirm the rewrites hold."
else
    echo "TOTAL: $PASS passed, $FAIL failed (round 4)"
fi
echo "================================================================"
exit $FAIL
