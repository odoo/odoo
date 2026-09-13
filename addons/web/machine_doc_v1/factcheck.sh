#!/bin/bash
# Web module architecture fact-check. Run from any cwd.
#
# Read-only by default. `--update` rewrites the figures that
# `assert_doc_cites` derives, so nobody retypes a digit — the same
# reasoning as `doc_restated_counts.py --update` for
# `doc/architecture/`. Reach for it in the commit that MOVES the tree;
# a figure goes stale there, not in the run that notices.
#
# Assertions DERIVE their expected value from the filesystem and check that the
# docs cite it (assert_doc_cites), rather than keeping a second copy of every
# number that can go stale independently.
#
# Roots are derived from this script's own location, so the run always validates
# the tree it ships in. Checks needing a sibling repo (enterprise) or the
# framework tree SKIP with a count when it is absent, so a single-repo checkout
# reports honestly instead of failing or silently passing.
#
# Overrides: VENV_PY, ODOO_CONF, FACTCHECK_DB.

set -u
# All roots derive from this script's location so the run validates the tree it
# ships in. Hardcoded absolute paths made a copied/CI checkout silently verify
# the ORIGINAL tree and report a clean pass.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Interpreter resolution + a scan that cannot fail silently. See the header of
# doc/machine_doc/factcheck_env.sh for what bare `"$PY"` did here.
_fc_root="$SCRIPT_DIR"
while [[ "$_fc_root" != "/" && ! -f "$_fc_root/odoo-bin" ]]; do
    _fc_root="$(dirname -- "$_fc_root")"
done
# shellcheck source=/dev/null
source "$_fc_root/doc/machine_doc/factcheck_env.sh"

WEB="$(dirname "$SCRIPT_DIR")"                 # <repo>/addons/web
REPO="$(cd "$WEB/../.." && pwd)"               # <repo>  (the odoo fork)
ADDONS="$(dirname "$REPO")"                    # <workspace> — holds the sibling
                                               # checkouts (odoo/, enterprise/,
                                               # agromarin/, design-themes/)
WORKSPACE="$ADDONS"                            # same directory: this fork keeps
                                               # the venv and <env>.conf here too

# The interpreter and config are DISCOVERED, not assumed. `WORKSPACE` used to be
# `dirname "$ADDONS"` — one level above the checkouts — which named a layout this
# workspace does not use: the `<ws>/venv/<env>/bin/python` probe missed, `"$PY"`
# took over as the fallback, `parse_config` was handed a path that does not
# exist, and all eight prepare_suite counts reported LOADER_FAILED. A gate reduced
# to noise by a path guess is the same failure mode the roots above were written
# to avoid.
#
# Convention (workspace CLAUDE.md): one `<env>.conf` per environment at the
# workspace root, each paired with a venv directory of the same name —
# `<workspace>/p314o19m.conf` + `<workspace>/p314o19m/bin/python`.
# Pair them BY NAME so a workspace holding several environments cannot run one
# environment's config under another's interpreter.
_discover_env() {
    # $1 = directory holding <env>.conf; $2 = directory holding <env>/bin/python
    local conf_dir="$1" venv_dir="$2" conf env_name py
    for conf in "$conf_dir"/*.conf; do
        [ -f "$conf" ] || continue
        env_name="$(basename "$conf" .conf)"
        py="$venv_dir/$env_name/bin/python"
        [ -x "$py" ] || continue
        printf '%s\n%s\n' "$py" "$conf"
        return 0
    done
    return 1
}
# This workspace's layout first, then the nested one, so a checkout using
# either is validated rather than silently degraded.
_env_found="$(_discover_env "$WORKSPACE" "$WORKSPACE" \
    || _discover_env "$(dirname "$WORKSPACE")/config" "$(dirname "$WORKSPACE")/venv" \
    || true)"
VENV_PY="${VENV_PY:-$(printf '%s' "$_env_found" | sed -n 1p)}"
ODOO_CONF="${ODOO_CONF:-$(printf '%s' "$_env_found" | sed -n 2p)}"
if [ -z "$VENV_PY" ] || [ ! -x "$VENV_PY" ]; then
    VENV_PY="$(command -v "$PY")"
    # A discovery miss silently falls back to system "$PY", whose grammar
    # can differ from this repo's own floor (a comma-except line the repo's
    # actual interpreter accepts can be a SyntaxError under system "$PY",
    # reported as an ordinary PARSE_FAILED assertion -- indistinguishable
    # from real doc staleness). Loud on the miss so that distinction is not
    # lost silently.
    echo "factcheck.sh: no <env>.conf paired with a <env>/bin/python venv" \
        "found under $WORKSPACE or $(dirname "$WORKSPACE")/{config,venv};" \
        "falling back to system '$VENV_PY'. Export VENV_PY to override." >&2
fi
DOC="$WEB/machine_doc_v1"
PASS=0
FAIL=0
SKIP=0
UPDATED=0

# `--update` is opt-in and touches nothing on the default path, so a CI run and
# a developer run execute the same assertions.
FACTCHECK_UPDATE=0
for _arg in "$@"; do
    case "$_arg" in
        --update) FACTCHECK_UPDATE=1 ;;
        *) echo "usage: factcheck.sh [--update]" >&2; exit 2 ;;
    esac
done

# Which sibling checkouts are present. CI checks `odoo` out ALONE -- no workflow
# passes `repository:` to actions/checkout -- so every fork-wide measurement here
# has nothing to measure there. The header promises such checks SKIP with a
# count rather than fail; five did not, and reported a smaller tree as drift --
# registerField 109 against a documented 110, and the plain/spec split with it.
# A gate that fails on everything is read as broken and ignored, which is the
# lesson the doc sweep below already learned once, at 557.
SIBLINGS_ABSENT=""
for _sib in enterprise agromarin design-themes; do
    [ -d "$WORKSPACE/$_sib" ] || SIBLINGS_ABSENT="$SIBLINGS_ABSENT $_sib"
done
# $1 = what is skipped, $2 = how many assertions it covers.
skip_without_siblings() {
    [ -n "$SIBLINGS_ABSENT" ] || return 1
    echo "SKIP: $1 — $2 assertion(s) (fork-wide; absent:$SIBLINGS_ABSENT)"
    SKIP=$((SKIP+$2)); return 0
}

assert_eq() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "PASS: $name [$actual]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — expected [$expected] got [$actual]"; FAIL=$((FAIL+1))
    fi
}
# Assert the docs cite the number the filesystem actually reports, instead of
# a label could read "= 44" while the expected value said 48, and still PASS).
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
# Assertions that need a sibling repo or the framework tree SKIP (loudly) when
# it is absent, so a single-repo CI checkout is not permanently red.
skip_missing() {
    # $1 = path that must exist, $2 = what is skipped, $3 = how many assertions
    # it covers, so the SKIP total counts unrun CHECKS, not skipped blocks.
    if [ -e "$1" ]; then return 1; fi
    echo "SKIP: $2 — $3 assertion(s) (no $1)"; SKIP=$((SKIP+$3)); return 0
}
assert_range() {
    local name="$1" actual="$2" lo="$3" hi="$4"
    if [ "$actual" -ge "$lo" ] && [ "$actual" -le "$hi" ]; then
        echo "PASS: $name [$actual in $lo..$hi]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — expected $lo..$hi got [$actual]"; FAIL=$((FAIL+1))
    fi
}

# ------- Module size -------
# -not -name ".*" excludes gitignored editor droppings (.__e.js), which are not
# source and inflated every count derived from this one.
find_src_js() { find "$WEB/static/src" -name "*.js" -type f -not -name ".*"; }
SRC_JS=$(find_src_js | wc -l)
assert_doc_cites "ARCHITECTURE cites the src JS count" "$SRC_JS" '%s JavaScript' ARCHITECTURE.md

# ------- Type coverage -------
assert_eq "@ts-check coverage" \
    "$(find_src_js | xargs grep -l "@ts-check" | wc -l)" "$((SRC_JS - 2))"
assert_eq "Untyped JS files (intentional: module_loader + service_worker)" \
    "$(find_src_js | xargs grep -L "@ts-check" | wc -l)" "2"
# Two documents state this coverage; pin BOTH to the one measurement. They
# disagreed for a week -- ARCHITECTURE.md's 761 (gated by the assert above) against
# EXTENSION_ARCHITECTURE_REVIEW's "756 of 763 -- exact", which was never true at
# any commit. A gated figure does not protect its own restatement elsewhere,
# and the doc most likely to be believed is the one that calls itself exact.
# Both halves derive: the denominator interpolates SRC_JS rather than sitting
# here as a literal, so the pattern cannot itself become the stale copy.
#
# THREE sites, three pins, each anchored to its own sentence. One loose pin over
# a value the document repeats is a coin flip: `assert_doc_cites` asks only
# whether the value appears SOMEWHERE, so the site that is still correct
# satisfies it while another rots. Anchoring is what makes "pin every
# restatement" (§1.4) mean anything. The historical "756 of 763" on lines 33 and
# 159 is deliberate -- it names the defect -- and no pattern here matches it.
# Both halves of the ratio are values, not one value and one literal baked into
# the regex. With the denominator inside the pattern, a tree that moved made the
# pattern match NOTHING -- the assertion failed for the right reason but named
# only the numerator, and no rewriter could repair a sentence it could not find.
assert_doc_cites "EXT_ARCH_REVIEW: Survived-unchanged line cites @ts-check coverage" \
    "$((SRC_JS - 2)) $SRC_JS" '\*\*%s of %s\*\* files' EXTENSION_ARCHITECTURE_REVIEW.md
assert_doc_cites "EXT_ARCH_REVIEW: F6 prose cites @ts-check coverage" \
    "$((SRC_JS - 2)) $SRC_JS" 'internally: %s of %s files' EXTENSION_ARCHITECTURE_REVIEW.md
assert_doc_cites "EXT_ARCH_REVIEW: F6 table row cites @ts-check coverage" \
    "$((SRC_JS - 2))" '\| `addons/web` \| %s \|' EXTENSION_ARCHITECTURE_REVIEW.md

# ------- Test scope -------
HOOT_JS=$(find "$WEB/static/tests" -name "*.test.js" 2>/dev/null | wc -l)
TESTS_JS=$(find "$WEB/static/tests" -name "*.js" -type f | wc -l)
assert_eq "Legacy QUnit tree deleted (static/tests/legacy)" \
    "$([ -d "$WEB/static/tests/legacy" ] && echo 1 || echo 0)" "0"
assert_eq "Vendored QUnit deleted (static/lib/qunit)" \
    "$([ -d "$WEB/static/lib/qunit" ] && echo 1 || echo 0)" "0"
assert_eq "No qunit bundles left in manifest" \
    "$(grep -c "qunit" "$WEB/__manifest__.py")" "0"
assert_eq "No QUnit. references remain (legacy chain fully removed)" \
    "$(grep -rl "QUnit\." "$WEB/static/tests" --include="*.js" 2>/dev/null | wc -l)" "0"
assert_eq "No QUnit.test/QUnit.module calls anywhere in static/" \
    "$(grep -rE "QUnit\.(test|module)\(" "$WEB/static" --include="*.js" 2>/dev/null | wc -l)" "0"
assert_eq "legacy_js test tree deleted (suites retired with the namespace)" \
    "$([ -d "$WEB/static/tests/legacy_js" ] && echo 1 || echo 0)" "0"
assert_eq "lazyloader HOOT suite lives in tests/public" \
    "$(find "$WEB/static/tests/public" -name "lazyloader.test.js" 2>/dev/null | wc -l)" "1"

# ------- Reactivity migration progress -------
# File-count grep over-counts because reactive.js itself matches via docstring.
REACTIVE_PATTERN='^(\s*export\s+)?class\s+\w+\s+extends\s+Reactive\b'
SIGNALSTORE_PATTERN='^(\s*export\s+)?class\s+\w+\s+extends\s+SignalStore\b'

# Helper: count declarations in production code only (exclude tests + machine_doc + .md).
#
# `-R`, not `-r`. `-r` skips symlinked directories it meets during recursion, and
# a verification rig built the way §9.3 prescribes -- a `git worktree` beside
# SYMLINKS to the sibling checkouts -- puts every sibling behind exactly such a
# link. This counted `odoo` alone there and reported 15 against a real 25, which
# was filed as a standing defect before anyone noticed the rig, not the tree, was
# what had changed. `skip_missing` uses `[ -e ]`, which DOES follow the link, so
# the assertion ran and answered confidently with two thirds of its scope
# missing. Same answer in a workspace and in a worktree rig, or the gate is only
# trustworthy in one of them.
# `--include` and the `--exclude-dir` list are not an optimisation, they are what
# makes this runnable at all. The scope is the WORKSPACE, which holds the
# checkouts but also the `data_dir` and the venv: measured here, 888165 files
# under `.data/` against 157211 across all four checkouts, and 884241 of those
# -- 99.6% -- are attachment blobs under a `filestore/` directory that cannot
# contain a JS class. Walking them took this function past THIRTY MINUTES per
# call while CI, whose checkout has neither beside it, ran in seconds; the same
# "green in CI, unusable in the workspace" shape the roots above were written to
# avoid. Pruned, and restricted to the files the pattern is about, the same call
# answers in 0.4s with the same counts (SignalStore 25, Reactive 0).
count_prod_decls() {
    local pattern="$1"
    local files
    # -r, not -R: -R follows symlinks, and a deployment serves each addon's
    # static/ through a symlink farm beside the checkouts. Every matching file
    # was then found twice, once by its real path and once through the farm, so
    # this counted 50 declarations against the 25 that exist. The exclusions
    # below are the same defence by name; not following symlinks is that defence
    # made general, and no addon in the path is reached only through a link.
    files=$(grep -rEl --include='*.js' \
        --exclude-dir=filestore --exclude-dir=sessions \
        --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=__pycache__ \
        --exclude-dir=worktrees --exclude-dir=.worktrees \
        "$pattern" "$ADDONS/" 2>/dev/null \
        | grep -v "machine_doc\|\.test\.js\|\.md$")
    if [ -z "$files" ]; then
        echo 0
    else
        echo "$files" | xargs grep -Ec "$pattern" \
            | awk -F: '{ s += $NF } END { print s+0 }'
    fi
}
reactive_prod=$(count_prod_decls "$REACTIVE_PATTERN")
assert_eq "Reactive class declarations (production)" "$reactive_prod" "0"

reactive_web=$(grep -rEln "$REACTIVE_PATTERN" "$WEB/static/src" 2>/dev/null | wc -l)
assert_eq "Reactive class declarations in core/addons/web" "$reactive_web" "0"

if skip_missing "$ADDONS/enterprise" "SignalStore cross-repo declaration count" 1; then :; else
    signalstore=$(count_prod_decls "$SIGNALSTORE_PATTERN")
    assert_doc_cites "STATE_MANAGEMENT cites the SignalStore declaration count" \
        "$signalstore" '%s production class declarations fork-wide' STATE_MANAGEMENT.md
fi
assert_eq "load_coordinator.js stays deleted" \
    "$([ -f "$WEB/static/src/model/relational_model/load_coordinator.js" ] && echo 1 || echo 0)" "0"

# Verify web_studio's parallel Reactive class is gone — replaced by SignalStore + toRaw().
if skip_missing "$ADDONS/enterprise" "web_studio Reactive/raw assertions" 2; then :; else
web_studio_reactive_class=$(grep -c "^export class Reactive {" \
    "$ADDONS/enterprise/web_studio/static/src/client_action/utils.js" 2>/dev/null)
assert_eq "web_studio's parallel Reactive class (deleted)" "$web_studio_reactive_class" "0"

# Verify the .raw() callers were correctly migrated to toRaw(this).
web_studio_raw_calls=$(grep -rc "\.raw()" "$ADDONS/enterprise/web_studio/static/src" 2>/dev/null \
    | awk -F: '{ s += $NF } END { print s+0 }')
assert_eq "web_studio .raw() callers (replaced by toRaw(this))" "$web_studio_raw_calls" "0"
fi

# web_vitals_service.js captures LCP/FCP/CLS/TTFB/INP via PerformanceObserver
# (INP as a worst-observed P100 running max — a strict upper bound on the
# canonical Chromium P98) and beacons to /web/observability/cwv on pagehide.
# 2 matching files: the service itself + core/browser/browser.js, which now
# exposes window.PerformanceObserver through the browser abstraction.
rum_telemetry=$(grep -rln "PerformanceObserver\|web-vitals" "$WEB/static/src" 2>/dev/null | wc -l)
assert_eq "PerformanceObserver/web-vitals (service + browser abstraction)" "$rum_telemetry" "2"
assert_eq "web_vitals INP reducer keeps a worst-observed (P100) running max" \
    "$(grep -c 'metrics.inp = e.duration' "$WEB/static/src/core/network/web_vitals/web_vitals_service.js")" "1"
assert_eq "MODEL_MAP.md inp row no longer claims 'currently always null'" \
    "$(grep -c 'currently always null' "$WEB/machine_doc_v1/MODEL_MAP.md")" "0"
# Coverage in BOTH directions: every models/*.py has a section, every section
# has an index row, and every documented method actually exists. Cardinality
# checks miss a file that is simply never mentioned.
read -r mm_undoc mm_noidx mm_badmethod <<<"$("$VENV_PY" - "$WEB" <<'PYEOF' 2>/dev/null
import ast, re, pathlib, sys
web = pathlib.Path(sys.argv[1])
doc = (web / "machine_doc_v1/MODEL_MAP.md").read_text()
secs = re.findall(r"^### (models/[\w./]+\.py)([^\n]*)\n(.*?)(?=^### |\Z)", doc, re.S | re.M)
sec_files = {p.split("/")[-1] for p, _, _ in secs}
idx = {m.group(1) for m in re.finditer(r"^\| `([\w./]+\.py)` \|", doc, re.M)}
disk = {p.name for p in (web / "models").glob("*.py") if p.name != "__init__.py"}
bad = 0
for path, _, body in secs:
    f = web / path
    if not f.exists():
        bad += 1
        continue
    defined = {n.name for n in ast.walk(ast.parse(f.read_text()))
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    bad += sum(1 for m in re.finditer(r"^- `([a-zA-Z_]\w*)\(", body, re.M)
               if m.group(1) not in defined)
print(len(disk - sec_files), len(sec_files - idx), bad)
PYEOF
)"
assert_eq "MODEL_MAP.md documents every models/*.py" "${mm_undoc:-PARSE_FAILED}" "0"
assert_eq "MODEL_MAP.md index row exists for every section" "${mm_noidx:-PARSE_FAILED}" "0"
assert_eq "MODEL_MAP.md documents no method that does not exist" "${mm_badmethod:-PARSE_FAILED}" "0"
assert_eq "MODEL_MAP.md inp row documents the P100 running max" \
    "$(grep -c 'worst-observed interaction duration' "$WEB/machine_doc_v1/MODEL_MAP.md")" "1"

# navigator.sendBeacon() call sites (4 files). This counts hand-rolled beacon
# copies, not beacon senders: `boot/start.js` was the fifth until its
# boot-mount-failure report moved to `core/errors/boot_failure_overlay.js` and
# started going through `reportJsError` instead of its own sendBeacon. That is a
# copy retired, so the number ratchets DOWN and stays there — raising it again
# means someone hand-rolled a fourth copy of the payload contract rather than
# importing `error_beacon`. `module_loader.js` is the one permitted duplicate:
# the pre-ESM shim cannot import.
sendbeacon_files=$(grep -rlE "sendBeacon[?.]*\\(" "$WEB/static/src" --include="*.js" 2>/dev/null | wc -l)
# 4 -> 3 on 2026-08-17: `core/errors/error_beacon.js` no longer hand-rolls one.
# It is now purely the typed facade its own header describes -- `reportJsError`
# forwards to `odoo.loader._beacon` and sends nothing itself. That is a copy
# retired, which is the direction this number is allowed to move.
assert_eq "sendBeacon call sites (module_loader + web_vitals + record_save)" "$sendbeacon_files" "3"

# Verify the observability controller is wired in.
observability_controller=$([ -f "$WEB/controllers/observability.py" ] && echo 1 || echo 0)
assert_eq "observability.py controller exists" "$observability_controller" "1"
observability_registered=$(grep -c "from . import observability" "$WEB/controllers/__init__.py" 2>/dev/null)
assert_eq "observability registered in controllers/__init__.py" "$observability_registered" "1"

# Phase 2: queryable model + dashboard view.
cwv_model=$([ -f "$WEB/models/web_cwv_metric.py" ] && echo 1 || echo 0)
assert_eq "web.cwv.metric model exists (Phase 2)" "$cwv_model" "1"
cwv_views=$([ -f "$WEB/views/web_cwv_metric_views.xml" ] && echo 1 || echo 0)
assert_eq "cwv views XML exists" "$cwv_views" "1"
cwv_model_registered=$(grep -c "from . import web_cwv_metric" "$WEB/models/__init__.py" 2>/dev/null)
assert_eq "web_cwv_metric registered in models/__init__.py" "$cwv_model_registered" "1"
cwv_views_in_manifest=$(grep -c "web_cwv_metric_views.xml" "$WEB/__manifest__.py" 2>/dev/null)
assert_eq "cwv views XML registered in manifest" "$cwv_views_in_manifest" "1"
cwv_acl=$(grep -c "model_web_cwv_metric" "$WEB/security/ir.model.access.csv" 2>/dev/null)
assert_eq "cwv ACL row in ir.model.access.csv" "$cwv_acl" "1"

# Phase 3: sampling + retention.
# Anchored on `def ` like every neighbour here: the bare identifier also matched
# the two prose mentions of the cron, so the figure moved when the prose did.
cwv_gc_method=$(grep -c "def _remove_old_metrics" "$WEB/models/web_cwv_metric.py" 2>/dev/null)
assert_eq "_remove_old_metrics retention method" "$cwv_gc_method" "1"
cwv_cron_data=$([ -f "$WEB/data/web_cwv_metric_data.xml" ] && echo 1 || echo 0)
assert_eq "cwv cron data file exists" "$cwv_cron_data" "1"
cwv_cron_in_manifest=$(grep -c "web_cwv_metric_data.xml" "$WEB/__manifest__.py" 2>/dev/null)
assert_eq "cwv cron registered in manifest" "$cwv_cron_in_manifest" "1"
cwv_session_param=$(grep -c '"cwv_sample_rate":' "$WEB/models/ir_http.py" 2>/dev/null)
assert_eq "cwv_sample_rate key present in session_info dict" "$cwv_session_param" "1"
cwv_js_sampling=$(grep -c "session.cwv_sample_rate" "$WEB/static/src/core/network/web_vitals/web_vitals_service.js" 2>/dev/null)
assert_eq "JS service reads sample_rate from session" "$cwv_js_sampling" "1"

# ------- Accessibility instrumentation -------
assert_eq "axe-core references" \
    "$(grep -rln "axe-core\|axeCore" "$WEB/static/src" "$WEB/static/tests" 2>/dev/null | wc -l)" "0"

css_decls=$(grep -rh "^\s*--[a-zA-Z]" "$WEB/static/src" --include="*.scss" 2>/dev/null | wc -l)
assert_range "CSS custom property declarations" "$css_decls" 300 600
css_uses=$(grep -rh "var(--" "$WEB/static/src" --include="*.scss" 2>/dev/null | wc -l)
assert_range "var(--*) usages" "$css_uses" 500 650

assert_eq "form_controller distinct top-level dirs" \
    "$(grep "^import" "$WEB/static/src/views/form/form_controller.js" \
        | grep -oE "@web/[a-z_]+" | sort -u | wc -l)" "6"

assert_eq "legacy/ namespace deleted" \
    "$([ -d "$WEB/static/src/legacy" ] && echo 1 || echo 0)" "0"
assert_eq "early-boot lazyloader+minimal_dom relocated to public/" \
    "$(ls "$WEB/static/src/public/lazyloader.js" "$WEB/static/src/public/minimal_dom.js" 2>/dev/null | wc -l)" "2"
assert_eq "frontend boot extracted to public/public_boot(.js/_instance.js)" \
    "$(ls "$WEB/static/src/public/public_boot.js" "$WEB/static/src/public/public_boot_instance.js" 2>/dev/null | wc -l)" "2"

# Phase 1 added a `_pl(count, forms)` helper in core/l10n/translation.js that
# uses Intl.PluralRules to select the right singular/plural form for the
# active locale's CLDR rules.  Each form is an independent `_t()` result, so
# the existing .pot extractor still finds every msgid.  This delivers
# correct one/other behavior (en, es, fr, …) and degrades gracefully to the
# "other" form for unprovided categories on richer-plural locales (ru, pl,
# ar).  Real msgid_plural / msgstr[N] gettext extraction needs Python tooling
# work in core/odoo/tools/translate.py and is tracked as Phase 2 — the
# `ngettext functions` assertion stays at 0 until that lands.
assert_eq "Intl.PluralRules used by the _pl helper" \
    "$(grep -rln "Intl\.PluralRules" "$WEB/static/src/core/translation.js" 2>/dev/null | wc -l)" "1"
assert_eq "ngettext functions (Phase 2 deferred — needs Python extractor)" \
    "$(grep -rln "ngettext\|\bngt\b" "$WEB/static/src" 2>/dev/null | wc -l)" "0"
# `_pl` is the canonical export name; lock both the export and the call-site
# convention so a future rename trips a CI assertion.
assert_eq "translation.js exports _pl" \
    "$(grep -c "^export function _pl(" "$WEB/static/src/core/translation.js")" "1"
assert_eq "formatX2many uses _pl" \
    "$(grep -c "_pl(count, {" "$WEB/static/src/core/formatters.js")" "1"
# The plural categories come from Intl.LDMLPluralRule, not a hand-maintained
# list, so assert the type binding rather than the six category names.
assert_eq "_pl forms are typed by Intl.LDMLPluralRule" \
    "$(grep -c 'Intl.LDMLPluralRule' "$WEB/static/src/core/translation.js")" "1"
assert_eq "_pl selects via Intl.PluralRules with an 'other' fallback" \
    "$(grep -c 'forms\[category\] ?? forms.other' "$WEB/static/src/core/translation.js")" "1"

# ------- OWL bundle -------
assert_eq "OWL bundle bytes" "$(stat -c '%s' "$WEB/static/lib/owl/owl.es.js")" "233543"
assert_eq "OWL version string" \
    "$(grep -oE 'version = "[0-9]+\.[0-9]+\.[0-9]+"' "$WEB/static/lib/owl/owl.es.js" | head -1)" \
    'version = "2.8.3"'
assert_eq "OWL ships ESM only (UMD build dropped)" \
    "$(ls "$WEB/static/lib/owl/" | tr '\n' ' ')" "owl.es.js "

# ------- Service worker -------
# The constant was renamed; the strategy is what matters, so assert the
# handler and its dispatch rather than a since-renamed identifier.
assert_range "stale-while-revalidate strategy wired in SW" \
    "$(grep -cE "^(const staleWhileRevalidate|[[:space:]]+event.respondWith\(staleWhileRevalidate|[[:space:]]+staleWhileRevalidate,)" "$WEB/static/src/service_worker.js")" 2 3

# ------- Security: XSS surface (NEW assertions) -------
assert_eq ".innerHTML = usages (gated: isMarkup() in html.js, instanceof Markup in colibri.js)" \
    "$(grep -rhE "\.innerHTML[[:space:]]*=[^=]" "$WEB/static/src" --include="*.js" 2>/dev/null | wc -l)" "2"
assert_eq ".outerHTML = usages" \
    "$(grep -rhE "\.outerHTML[[:space:]]*=[^=]" "$WEB/static/src" --include="*.js" 2>/dev/null | wc -l)" "0"
assert_eq "eval()/new Function() usages" \
    "$(grep -rE "\beval\(|new Function\(" "$WEB/static/src" --include="*.js" 2>/dev/null | wc -l)" "0"
markup_importers=$("$VENV_PY" - "$WEB/static/src" <<'PYEOF' 2>/dev/null
import re, pathlib, sys
imp = re.compile(r'import\s*\{([^}]*)\}\s*from\s*["\']([^"\']+)["\']', re.S)
n = 0
for p in sorted(pathlib.Path(sys.argv[1]).rglob("*.js")):
    t = p.read_text(errors="ignore")
    for m in imp.finditer(t):
        if "markup" in [x.strip().split(" as ")[0].strip() for x in m.group(1).split(",")]:
            n += 1
            break
print(n)
PYEOF
)
assert_eq "markup() trust-hatch import sites" "${markup_importers:-PARSE_FAILED}" "14"

# startViewTransition cannot wrap OWL's render; lock its absence so the
# feature cannot half-return without the docs moving with it.
assert_eq "ActionContainer no longer calls document.startViewTransition" \
    "$(grep -cE 'document\.startViewTransition\(' "$WEB/static/src/webclient/actions/action_container.js")" "0"
assert_eq "No startViewTransition call anywhere in static/src" \
    "$(grep -rE 'startViewTransition\(' "$WEB/static/src" --include="*.js" 2>/dev/null | wc -l)" "0"

# CONVENTIONS.md gotcha #13 (never patch a frozen ES-module namespace) carries
# no assertion: the "import * as + patch()" grep produced 44 false positives.

# orm.retry() must default to the documented boot-path budget of 1: a bare
# orm.retry().call(...) otherwise caps user-perceived delay well above the
# one-backoff-interval (~200 ms) rationale in CONVENTIONS.md.
assert_eq "orm.retry() default value [1]" \
    "$(grep -c 'retry(options = 1)' "$WEB/static/src/core/network/orm_service.js")" "1"
assert_eq "orm.retry() does NOT default to 3" \
    "$(grep -c 'retry(options = 3)' "$WEB/static/src/core/network/orm_service.js")" "0"

# ------- Production bundle sizes (NEW — from DB ir_attachment) -------
FACTCHECK_DB="${FACTCHECK_DB:-hoot_web}"
if psql -d "$FACTCHECK_DB" -c "SELECT 1" >/dev/null 2>&1; then
    : # bundle-size assertions removed: they measured a prod-restore DB,
      # not this source tree, and the ESM split made the figure meaningless.
else
    echo "SKIP: bundle size assertions (DB $FACTCHECK_DB unavailable; set FACTCHECK_DB=...)"
    SKIP=$((SKIP+1))
fi

# Each pair below locks both directions: the new wording must be present AND
# the stale wording gone, so a fix that lands in code without moving its cited
# doc fails here instead of misleading the next reader.

# 1. Optimistic locking is field-scoped (known_values baseline map). The client
#    does not send last_write_date; the server keeps it as a legacy fallback.
assert_eq "STATE_MANAGEMENT urgent-save: stale 'divergence' wording removed" \
    "$(grep -c 'Optimistic-locking divergence' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "0"
assert_eq "STATE_MANAGEMENT urgent-save: optimistic-locking parity documented" \
    "$(grep -c 'Optimistic-locking parity' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "1"
# The builder was extracted to concurrency_baseline.js so record_save.js and
# dynamic_list.js cannot drift; assert the shared module + its consumer.
assert_eq "concurrency_baseline.js exports getConcurrencyBaseline" \
    "$(grep -c 'export function getConcurrencyBaseline' "$WEB/static/src/model/relational_model/concurrency_baseline.js")" "1"
assert_eq "record_save.js uses the shared concurrency baseline builder" \
    "$(grep -c 'getConcurrencyBaseline(' "$WEB/static/src/model/relational_model/record_save.js")" "1"
assert_eq "record_save.js sends known_values on BOTH paths (urgent + normal)" \
    "$(grep -c 'known_values' "$WEB/static/src/model/relational_model/record_save.js")" "2"
assert_eq "record_save.js no longer sends last_write_date" \
    "$(grep -c 'last_write_date' "$WEB/static/src/model/relational_model/record_save.js")" "0"
assert_eq "server: web_read.py implements the _check_concurrent_field_changes family" \
    "$(grep -c 'def _check_concurrent_field_changes' "$WEB/models/web_read.py")" "4"
assert_eq "CONVENTIONS gotcha #9 documents known_values (field-scoped locking)" \
    "$(grep -c 'known_values' "$WEB/machine_doc_v1/CONVENTIONS.md")" "2"
assert_eq "STATE_MANAGEMENT documents known_values" \
    "$(grep -c 'known_values' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "3"

# 2. FormSaveCoordinator — CONVENTIONS.md gotcha #12 must reflect it.
assert_eq "CONVENTIONS gotcha #12: stale '5 \`true\` call sites' wording removed" \
    "$(grep -c '5 \`true\` call sites' "$WEB/machine_doc_v1/CONVENTIONS.md")" "0"
assert_eq "CONVENTIONS gotcha #12: mentions FormSaveCoordinator" \
    "$(grep -c 'FormSaveCoordinator' "$WEB/machine_doc_v1/CONVENTIONS.md")" "2"
# Cite-fingerprint: the doc cites form_save_coordinator.js; verify the file
# exists and exports a FormSaveCoordinator class extending StateMachine.
assert_eq "form_save_coordinator.js exports FormSaveCoordinator class" \
    "$(grep -c 'export class FormSaveCoordinator extends StateMachine' "$WEB/static/src/views/form/form_save_coordinator.js")" "1"
# Target the canonical typedef line: counting raw occurrences of the mode
# strings overcounts (8) across JSDoc, defaults and dispatch arms.
assert_eq "FormSaveCoordinator errorMode typedef declares three modes" \
    "$(grep -cE '^\s\*\s+errorMode\?: "dialog" \| "rethrow" \| "silent"' "$WEB/static/src/views/form/form_save_coordinator.js")" "1"

assert_eq "ARCHITECTURE.md no stale JS file counts (615/621/649/657)" \
    "$(grep -cE '(615|621|649|657) (JavaScript|JS)' "$WEB/machine_doc_v1/ARCHITECTURE.md")" "0"
assert_doc_cites "ARCHITECTURE.md JS count cited in prose" "$SRC_JS" '%s JavaScript' ARCHITECTURE.md
# The other site is a markdown table cell `| JavaScript (src) | N (M carry
# @ts-check ...)`. BOTH numbers are pinned: N was gated and M was bare, so the
# same cell carried one figure the harness maintained and one nobody did, and M
# sat two years' worth of files out of date beside a correct N.
assert_doc_cites "ARCHITECTURE.md JS table cell" "$SRC_JS $((SRC_JS - 2))" \
    '\| JavaScript \(src\) \| %s \(%s carry' ARCHITECTURE.md

# 4. Pattern 4 inventory — STATE_MANAGEMENT.md should enumerate verified sites
#    rather than implying an open population.
assert_eq "STATE_MANAGEMENT lists Pattern 4 sites table" \
    "$(grep -c 'Pattern 4 sites' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "1"

#    - reactive.js exports SignalStore only (no `export const Reactive`)
#    - reactive.test.js references SignalStore, not Reactive. The suite sits
#      beside the module it tests, under tests/core/utils/ (ee7e885cf89); the
#      old tests/core/ path made both greps read an empty string, not 0.
#    - eslint.config.mjs has no Reactive-import rule (rule is now unenforceable
#      anyway: the export does not exist, so the import fails at module-load)
assert_eq "reactive.js does not export Reactive (alias dropped)" \
    "$(grep -c 'export const Reactive' "$WEB/static/src/core/utils/reactive.js")" "0"
assert_eq "reactive.js still exports SignalStore" \
    "$(grep -c 'export class SignalStore' "$WEB/static/src/core/utils/reactive.js")" "1"
assert_eq "reactive.test.js imports SignalStore (not Reactive)" \
    "$(grep -c 'import.*SignalStore.*@web/core/utils/reactive' "$WEB/static/tests/core/utils/reactive.test.js")" "1"
assert_eq "reactive.test.js does not import Reactive" \
    "$(grep -cE 'import\s*\{[^}]*\bReactive\b[^}]*\}\s*from\s*"@web/core/utils/reactive"' "$WEB/static/tests/core/utils/reactive.test.js")" "0"
if skip_missing "$REPO/eslint.config.mjs" "eslint Reactive-import rule assertion" 1; then :; else
    assert_eq "eslint.config.mjs no longer carries the Reactive-import rule" \
        "$(grep -c "imported.name='Reactive'" "$REPO/eslint.config.mjs")" "0"
fi

# 6. Per-layer JS subtotals are not pinned to literals here: the layer loop in
#    section 15 asserts ARCHITECTURE.md cites whatever the filesystem reports,
#    so there is no second copy of the numbers to go stale.

# 7. Gotcha #10 cite-fingerprint: archiveEnabled consolidated into
#    view_utils.computeArchiveEnabled(readonlySource, presenceSource).
#    Form gates presence on model.root.activeFields; multi-record passes
#    only props.fields.  The x_active fallback now lives in the shared
#    helper, not in form_controller.
assert_eq "view_utils exports computeArchiveEnabled(fields, { presentIn })" \
    "$(grep -c 'export function computeArchiveEnabled(fields, { presentIn = fields } = {})' "$WEB/static/src/views/view_utils.js")" "1"
assert_eq "computeArchiveEnabled has the x_active fallback" \
    "$(grep -cE 'for \(const fieldName of \["active", "x_active"\]\)' "$WEB/static/src/views/view_utils.js")" "1"
assert_eq "form_controller has archiveEnabled getter" \
    "$(grep -c 'get archiveEnabled()' "$WEB/static/src/views/form/form_controller.js")" "1"
assert_eq "form_controller delegates with the activeFields presence gate" \
    "$(grep -c 'presentIn: this.model.root.activeFields' "$WEB/static/src/views/form/form_controller.js")" "1"
assert_eq "multi_record_controller delegates to computeArchiveEnabled" \
    "$(grep -c 'computeArchiveEnabled(this.props.fields)' "$WEB/static/src/views/multi_record_controller.js")" "1"
assert_eq "CONVENTIONS gotcha #10 names the computeArchiveEnabled form call" \
    "$(grep -c 'presentIn: this.model.root.activeFields' "$WEB/machine_doc_v1/CONVENTIONS.md")" "1"
assert_eq "CONVENTIONS gotcha #10 carries no stale form_controller.js line cites" \
    "$(grep -cE 'form_controller.js:[0-9]' "$WEB/machine_doc_v1/CONVENTIONS.md")" "0"

# Gotcha #5 cites 17 /web/image URL patterns and 7 /web/content. Count DECLARED
# ROUTE URLs, not grep hits: the old raw grep counted 20 because docstrings and
# helper strings mention the prefix too, and it would have passed at any value.
read -r IMG_URLS CONTENT_URLS <<<"$("$VENV_PY" - "$WEB/controllers" <<'PYEOF'
import ast, pathlib, sys
urls = set()
for f in sorted(pathlib.Path(sys.argv[1]).glob("*.py")):
    for node in ast.walk(ast.parse(f.read_text())):
        for dec in getattr(node, "decorator_list", []):
            if isinstance(dec, ast.Call) and getattr(
                    dec.func, "attr", getattr(dec.func, "id", "")) == "route":
                for a in dec.args:
                    if isinstance(a, ast.Constant):
                        urls.add(a.value)
                    elif isinstance(a, (ast.List, ast.Tuple)):
                        urls |= {e.value for e in a.elts if isinstance(e, ast.Constant)}
print(sum(1 for u in urls if u.startswith("/web/image")),
      sum(1 for u in urls if u.startswith("/web/content")))
PYEOF
)"
assert_eq "/web/image declared route URLs" "${IMG_URLS:-PARSE_FAILED}" "17"
assert_eq "/web/content declared route URLs" "${CONTENT_URLS:-PARSE_FAILED}" "7"
assert_eq "CONVENTIONS gotcha #5 cites both numbers" \
    "$(grep -c 'has 17 declared URL patterns' "$DOC/CONVENTIONS.md")" "1"

# 9. Gotcha #6 cite-fingerprint: Chart.js is lazy-loaded as a real ES module
#     via core/lib/chartjs.js (dynamic import of the `chart.js` import-map
#     specifier + live-bound `Chart` export).  The old
#     loadBundle("web.chartjs_lib") classic-script path is gone, as is the
#     manifest bundle itself.  FullCalendar follows the same pattern.
assert_eq "graph_renderer.js awaits loadChartJS()" \
    "$(grep -c 'await loadChartJS()' "$WEB/static/src/views/graph/graph_renderer.js")" "1"
assert_eq "graph_renderer.js imports from @web/core/lib/chartjs" \
    "$(grep -c '@web/core/lib/chartjs' "$WEB/static/src/views/graph/graph_renderer.js")" "1"
assert_eq "core/lib/chartjs.js dynamic-imports chart.js" \
    "$(grep -c 'import("chart.js")' "$WEB/static/src/core/lib/chartjs.js")" "1"
# `async` is incidental: since 8a9e5971f53 the loader returns makeLazyLib's
# promise directly. Pin the export and the await at its call site, not the
# keyword.
assert_eq "core/lib/fullcalendar.js exports loadFullCalendar" \
    "$(grep -cE 'export (async )?function loadFullCalendar\(\)' "$WEB/static/src/core/lib/fullcalendar.js")" "1"
assert_eq "full_calendar_hook.js awaits loadFullCalendar()" \
    "$(grep -c 'await loadFullCalendar()' "$WEB/static/src/views/calendar/hooks/full_calendar_hook.js")" "1"
assert_eq "manifest no longer declares web.chartjs_lib / web.fullcalendar_lib" \
    "$(grep -cE 'chartjs_lib|fullcalendar_lib' "$WEB/__manifest__.py")" "0"
assert_eq "no loadBundle(chartjs_lib) call sites remain in static/src" \
    "$(grep -rc 'loadBundle("web.chartjs_lib")' "$WEB/static/src" --include="*.js" 2>/dev/null | awk -F: '{s+=$NF} END {print s+0}')" "0"
assert_eq "CONVENTIONS gotcha #6 documents loadChartJS" \
    "$(grep -c 'loadChartJS' "$WEB/machine_doc_v1/CONVENTIONS.md")" "1"
# The `set groupId` setter is the canonical Pattern 4 exception: it must clear
# sample data on the same microtask as the mutation. The source carries only a
# self-contained eslint-disable; STATE_MANAGEMENT.md is the rationale of record.
KANBAN_JS="$WEB/static/src/views/kanban/kanban_controller.js"
assert_eq "kanban_controller.js groupId setter (canonical Pattern 4 exception)" \
    "$(grep -c 'set groupId(groupId)' "$KANBAN_JS")" "1"
assert_eq "kanban_controller.js keeps the no-restricted-syntax pragma" \
    "$(grep -c 'eslint-disable-next-line no-restricted-syntax' "$KANBAN_JS")" "1"
assert_eq "kanban pragma is self-contained (no dangling 'see comment above')" \
    "$(grep -c 'see comment above' "$KANBAN_JS")" "0"
assert_eq "kanban pragma points at the rationale of record" \
    "$(grep -c 'STATE_MANAGEMENT.md' "$KANBAN_JS")" "1"
assert_eq "STATE_MANAGEMENT.md carries the reverted-migration commit" \
    "$(grep -c '19fb5d01bb81' "$DOC/STATE_MANAGEMENT.md")" "1"
assert_eq "STATE_MANAGEMENT.md no longer points at a source comment block" \
    "$(grep -c 'comment block above the setter' "$DOC/STATE_MANAGEMENT.md")" "0"

# The typo'd `effetcs` key in @types/registries/registries.d.ts had zero
# consumers fork-wide. Locked so a copy/paste from old history cannot revive it.
assert_eq "registries.d.ts: typo'd 'effetcs' key removed" \
    "$(grep -c "^\s*effetcs:" "$WEB/static/src/@types/registries/registries.d.ts")" "0"
assert_eq "registries.d.ts: 'effects' key still declared" \
    "$(grep -c "^\s*effects: EffectsRegistryItemShape;" "$WEB/static/src/@types/registries/registries.d.ts")" "1"
# Excludes machine_doc_v1/ and .git/, which may legitimately name the typo.
assert_eq "no 'effetcs' consumers across active repos" \
    "$(grep -rln "effetcs" \
        "$ADDONS/odoo" \
        "$ADDONS/enterprise" \
        "$ADDONS/agromarin" \
        --exclude-dir=machine_doc_v1 \
        --exclude-dir=.git 2>/dev/null | wc -l)" "0"

# 11. dedup proxy on ORM — ARCHITECTURE.md must document it; rpc.js must
#     whitelist the setting.
assert_eq "orm_service.js exports 'get dedup' proxy" \
    "$(grep -cE '^\s+get dedup\(\)' "$WEB/static/src/core/network/orm_service.js")" "1"
# RPC_SETTINGS is a multi-line Set literal; match the "dedup" member directly.
assert_eq "rpc.js RPC_SETTINGS whitelist includes 'dedup'" \
    "$(grep -cE '^\s*"dedup",' "$WEB/static/src/core/network/rpc.js")" "1"
assert_eq "ARCHITECTURE.md documents orm.dedup proxy" \
    "$(grep -cE '\*\*`orm\.dedup`\*\*' "$WEB/machine_doc_v1/ARCHITECTURE.md")" "1"
assert_eq "ARCHITECTURE.md rpc.js whitelist mentions all 6 keys" \
    "$(grep -cE 'cache, silent, headers, timeout, retry, dedup' "$WEB/machine_doc_v1/ARCHITECTURE.md")" "1"

# 12. Vendored versions are owned by static/lib/versions.json; the doc must
#     defer to it rather than keep a second copy that can drift.
assert_eq "ARCHITECTURE.md defers to versions.json" \
    "$(grep -c 'versions.json' "$WEB/machine_doc_v1/ARCHITECTURE.md")" "3"
# The directory list IS the population, so the manifest is held against it
# rather than against a literal count -- `17` here was a second copy of the
# tree and went stale the day joint/ was vendored (2cca79e2baa) with its pin
# already in place.
read -r LIB_DIRS LIB_VENDORED LIB_UNPINNED <<<"$("$VENV_PY" - "$WEB/static/lib" <<'PYEOF' 2>/dev/null
import json, pathlib, sys
lib = pathlib.Path(sys.argv[1])
dirs = {p.name for p in lib.iterdir() if p.is_dir()}
libs = json.load(open(lib / "versions.json"))["libs"]
unpinned = sorted(dirs ^ set(libs))
print(len(dirs), sum(1 for v in libs.values() if v.get("version") != "generated"),
      ",".join(unpinned) or 0)
PYEOF
)"
assert_eq "versions.json pins every static/lib library dir, and nothing else" \
    "${LIB_UNPINNED:-PARSE_FAILED}" "0"
assert_doc_cites "ARCHITECTURE.md static/lib row: directories and vendored libraries" \
    "$LIB_DIRS $LIB_VENDORED" '\| `static/lib/` \| %s directories \(%s vendored libraries' ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE.md vendored-libs paragraph: directories and vendored libraries" \
    "$LIB_DIRS $LIB_VENDORED" '^%s directories: %s vendored libraries plus' ARCHITECTURE.md
assert_eq "ARCHITECTURE.md no stale fullcalendar 6.1.20 / 7.0.0-rc.3" \
    "$(grep -cE 'fullcalendar.{0,30}(6\.1\.20|7\.0\.0-rc)' "$WEB/machine_doc_v1/ARCHITECTURE.md")" "0"
assert_eq "fullcalendar vendored bundle is v7 (final 7.0.0 present in source)" \
    "$(grep -c 'FullCalendar v7' "$WEB/static/lib/fullcalendar/fullcalendar.esm.js"):$(grep -m1 -coE 'v7\.0\.0' "$WEB/static/lib/fullcalendar/fullcalendar.esm.js")" "1:1"

# 13. AppEvent.FORM_DIALOG_* never existed in core/events.js; the stack is
#     driven by direct push()/pop() calls. Lock the phantom rows out.
assert_eq "STATE_MANAGEMENT.md no phantom FORM_DIALOG_ADD row" \
    "$(grep -c 'AppEvent.FORM_DIALOG_ADD' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "0"
assert_eq "STATE_MANAGEMENT.md no phantom FORM_DIALOG_REMOVE row" \
    "$(grep -c 'AppEvent.FORM_DIALOG_REMOVE' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "0"
assert_eq "core/events.js does not export FORM_DIALOG_ADD" \
    "$(grep -cE 'FORM_DIALOG_ADD\s*:' "$WEB/static/src/core/events.js")" "0"

# 14. ARCHITECTURE.md File Counts table.
PY_TESTS=$(find "$WEB/tests" -name "test_*.py" | wc -l)
PY_TESTS_ALL=$(find "$WEB/tests" -name "*.py" | wc -l)
assert_doc_cites "ARCHITECTURE.md File Counts: Python tests" "$PY_TESTS $PY_TESTS_ALL" \
    '\| Python \(tests\) \| %s \(`test_\*\.py`; %s files incl' ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE.md tests/ row: Python test files" "$PY_TESTS" \
    '\| `tests/` \| %s Python test files' ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE.md File Counts: JS tests total" "$TESTS_JS" '\| JavaScript \(tests\) \| %s \(incl' ARCHITECTURE.md
# Anchored on the File Counts row. `incl\. %s ...` alone also matched the
# `static/tests/` row 350 lines earlier, so the figure was ambiguous: two lines
# claimed the count and satisfying either one passed the gate.
assert_doc_cites "ARCHITECTURE.md File Counts: Hoot suites" "$HOOT_JS" \
    '\| JavaScript \(tests\) \| [0-9]+ \(incl\. %s ' ARCHITECTURE.md
# The `static/tests/` row 350 lines earlier states the SAME two figures. The
# comment above disambiguated the gate away from it and stopped there, which
# left that row checked by nothing -- it still said 680/622 against a real
# 735/674 when this assertion was added. Anchor it on its own row so both
# copies are pinned; the rule is one measurement, asserted wherever it
# is cited, not one measurement and one copy nobody reads.
assert_doc_cites "ARCHITECTURE.md static/tests row: JS files and Hoot suites" \
    "$TESTS_JS $HOOT_JS" \
    '\| `static/tests/` \| %s `\.js` \(incl\. %s `\*\.test\.js`' ARCHITECTURE.md
LIB_JS=$(find "$WEB/static/lib" -name "*.js" -type f | wc -l)
assert_doc_cites "ARCHITECTURE.md File Counts: vendored libs" "$LIB_JS" \
    '\| JavaScript \(vendored libs\) \| %s \|' ARCHITECTURE.md
# Every one of those files belongs to a directory versions.json pins; a stray
# top-level file would be counted above and governed by nothing.
assert_eq "every static/lib JS file sits inside a pinned library dir" \
    "$(find "$WEB/static/lib" -maxdepth 1 -name "*.js" -type f | wc -l)" "0"

# 15. Every Layer row must cite the count the filesystem reports for its
#     directory.
for layer_spec in "Primitives:core" "Components:components" \
                  "UI:ui" "Fields:fields" "Views:views" "Webclient:webclient" \
                  "Search:search" "Model:model" "Public:public"; do
    lname="${layer_spec%:*}"; ldir="${layer_spec##*:}"
    lcount=$(find "$WEB/static/src/$ldir" -name "*.js" -type f -not -name ".*" | wc -l)
    assert_doc_cites "ARCHITECTURE.md Layer: $lname ($ldir/)" "$lcount" \
        "\\| \\*\\*$lname\\*\\* \\| .$ldir/. \\|.*\\| %s JS \\|" ARCHITECTURE.md
done
assert_eq "services/ layer is dissolved (no static/src/services)" \
    "$([ -d "$WEB/static/src/services" ] && echo 1 || echo 0)" "0"
assert_eq "no doc still describes a services/ layer" \
    "$(grep -lE '^\| \*\*Services\*\* \|' "$DOC"/*.md | wc -l)" "0"
assert_eq "ARCHITECTURE.md Layer table covers libs/" \
    "$(grep -cE '\| .libs/. \|' "$WEB/machine_doc_v1/ARCHITECTURE.md")" "1"

# 16. DIRECTORY_MAP.md header count and row set.
SRC_DIRS=$(find "$WEB/static/src" -mindepth 1 -type d -not -path '*/.claude*' | wc -l)
assert_doc_cites "DIRECTORY_MAP.md header states the entry count" "$((SRC_DIRS + 1))" \
    '\\*\\*%s entries\\*\\*' DIRECTORY_MAP.md
# Set equality, not just cardinality: a phantom row plus a missing row cancel
# out in a count (they did — contact_statistics/ vs core/file_upload/).
map_only=$(comm -23 \
    <(grep -oE '^\| `[^`]+`' "$DOC/DIRECTORY_MAP.md" | sed 's/^| `//;s/`$//;s:/$::' | grep -v '^(root)$' | LC_ALL=C sort -u) \
    <(cd "$WEB/static/src" && find . -mindepth 1 -type d | sed 's:^\./::' | LC_ALL=C sort -u) | tr '\n' ' ')
disk_only=$(comm -13 \
    <(grep -oE '^\| `[^`]+`' "$DOC/DIRECTORY_MAP.md" | sed 's/^| `//;s/`$//;s:/$::' | grep -v '^(root)$' | LC_ALL=C sort -u) \
    <(cd "$WEB/static/src" && find . -mindepth 1 -type d | sed 's:^\./::' | LC_ALL=C sort -u) | tr '\n' ' ')
# Whole-table validation: every row's Files column must equal `ls <dir>/*.js`.
# Set equality alone let 39 wrong counts survive undetected.
# Under --update the Files column is rewritten the same way a doc_cites
# figure is: the row already names its directory, so the count is derivable
# and nobody should be retyping 239 of them by hand. A row whose directory
# does NOT exist is left alone and still fails -- a phantom row is a
# structural claim, not a stale digit, and the set-equality checks above are
# what should speak to it.
_dirmap_out=$("$VENV_PY" - "$WEB" "$FACTCHECK_UPDATE" <<'PYEOF' 2>/dev/null
import re, pathlib, sys
web = pathlib.Path(sys.argv[1]); src = web / "static/src"
update = sys.argv[2] == "1"
doc = web / "machine_doc_v1/DIRECTORY_MAP.md"
row = re.compile(r"\|\s*`([^`]+)`\s*\|\s*[^|]+\|\s*(\d+)\s*\|")
bad = fixed = 0
lines = open(doc, encoding="utf-8").read().splitlines(keepends=True)
for i, ln in enumerate(lines):
    m = row.match(ln)
    if not m:
        continue
    d, files = m.group(1), int(m.group(2))
    p = src if d == "(root)" else src / d.rstrip("/")
    if not p.is_dir():
        bad += 1
        continue
    actual = sum(1 for f in p.glob("*.js") if not f.name.startswith("."))
    if actual == files:
        continue
    if update:
        start, end = m.span(2)
        lines[i] = ln[:start] + str(actual) + ln[end:]
        fixed += 1
    else:
        bad += 1
if fixed:
    open(doc, "w", encoding="utf-8").writelines(lines)
print(bad, fixed)
PYEOF
)
dirmap_bad=${_dirmap_out%% *}
_dirmap_fixed=${_dirmap_out##* }
if [ "${_dirmap_fixed:-0}" -gt 0 ] 2>/dev/null; then
    echo "UPDATED: DIRECTORY_MAP.md Files column — $_dirmap_fixed row(s) rewritten"
    UPDATED=$((UPDATED+_dirmap_fixed))
fi
# Every backticked source path in the docs must resolve to a real file.
# Scope is the whole workspace (docs cite enterprise and workspace-relative
# paths too). Excluded: route URLs, upstream package paths (dist/...), and
# load_coordinator.js, which is deliberately cited as absent.
if skip_missing "$REPO/odoo" "doc source-path resolution sweep" 1; then :; else
dead_refs=$("$VENV_PY" - "$DOC" "$WORKSPACE" "$REPO" "$WEB" "$SIBLINGS_ABSENT" <<'PYEOF' 2>/dev/null
import re, pathlib, sys, collections, os
doc_dir, ws, repo, web = (pathlib.Path(a) for a in sys.argv[1:5])
index = collections.defaultdict(list)
# The tree under test is the one BASH_SOURCE resolved to, whatever its directory
# is called: a detached worktree is `wt-<topic>/`, a CI checkout is whatever
# actions/checkout was handed, and only the shared workspace checkout is
# literally `odoo/`. Keying the fork on that NAME -- `ws / "odoo"` -- made every
# other layout ROOT_MISRESOLVED, and made the guard below fail on precisely the
# isolated trees §1.4 says to measure in. The siblings keep their names, which
# is the workspace convention (direct children of <ws>, never under an
# `addons/` directory -- looking there once built an EMPTY index and reported
# 557 dead references, none of which were dead). A second `odoo/` beside a
# worktree is somebody else's checkout and is deliberately not indexed: a
# reference that resolves only there is dead in the tree these docs describe.
roots = [repo] + [ws / s for s in ("enterprise", "agromarin", "design-themes")
                  if (ws / s).is_dir()]
for b in roots:
    for p in b.rglob("*"):
        if p.is_file():
            index[p.name].append(str(p))
# THE TREE UNDER TEST MUST BE IN THE INDEX. Without this, a misresolved root
# degrades to "everything is unjudged" and the sweep PASSES having compared
# nothing -- which is how the `unjudged` allowance below, added to stop absent
# siblings reading as drift, once silently swallowed 565 references. An escape
# hatch for "cannot decide" needs a floor, or it becomes an escape hatch for
# "did not look". The floor: the harness must find itself.
if str(doc_dir / "factcheck.sh") not in index.get("factcheck.sh", []):
    print("ROOT_MISRESOLVED", 0)
    raise SystemExit(0)
# Deliberately-absent references: load_coordinator.js is cited AS deleted;
# jsconfig.json is a gitignored hand copy of the committed
# addons/web/tooling/_jsconfig.json template (the enable.sh that once copied it
# went in c07b2caf69a). The three search_* names are cited by
# COMPONENT_DIAGRAM.md's rename note precisely to say they are gone -- the note
# names each pre-rename file next to what replaced it, so resolving them would
# mean the rename had not happened.
SKIP_BASE = {
    "load_coordinator.js",
    "jsconfig.json",
    "search_properties.js",
    "search_query_mutations.js",
    "search_split_domain.js",
}
# Scan INSIDE every backtick span rather than only spans that are a bare path.
# The pattern used to anchor the path to the opening backtick, so a span holding
# a COMMAND -- `bash addons/web/doc/factcheck.sh` -- matched nothing at all:
# `bash` is not a path, and the scan never looked past it. That blind spot hid a
# stale directory (`addons/web/doc/`, which has never existed under that name)
# through every previous green run. A path is no less a path for having a verb
# in front of it.
_EXT = r"(?:py|js|mjs|xml|json|yml|scss|csv|rst|md|sh)"
_WHOLE = re.compile(rf"`([\w./\-]+\.{_EXT})`")
# Inside a span, require a `/`. A bare dotted token is not decidable as a path:
# `web.js.error` is a MODEL NAME, `import("chart.js")` a bare specifier,
# `await response.json()` a method call, `*.test.js` a glob -- each of which
# resolves to nothing and would report as drift. Requiring a separator keeps the
# real quarry (`bash addons/web/.../factcheck.sh`, `odoo/http/helpers.py:290`)
# and drops all four. `@` is excluded so `@web/...` import specifiers, which are
# module ids and not filesystem paths, are not resolved as paths.
_INSPAN = re.compile(rf"(?<![\w./\-@])([\w\-]+(?:/[\w.\-]+)+\.{_EXT})(?![\w])")

def _refs(text):
    seen = set()
    for span in re.finditer(r"`([^`\n]+)`", text):
        body = span.group(1)
        for ref in _WHOLE.findall("`" + body + "`") + _INSPAN.findall(body):
            if ref not in seen:
                seen.add(ref)
                yield ref

# A ref this environment cannot decide is not a dead ref. With the siblings
# absent -- CI's normal shape -- `fsm_task_template_dropdown.js` lives in
# `enterprise` and resolves to nothing here; counting it as drift would fail the
# sweep over a tree the runner was never given. In the CI layout that is ONE
# reference, so almost nothing is given up: refs whose basename IS indexed stay
# judgeable either way, which keeps the real quarry in scope -- the stale
# addons/web/doc path was caught by exactly that branch. The much larger counts
# that show up when this goes wrong (565 in a trial run here, 557 in the
# incident above) are never absent siblings; they are a misresolved root, which
# the ROOT_MISRESOLVED guard now fails outright rather than excusing.
absent = bool(sys.argv[5]) if len(sys.argv) > 5 else False
bad = 0
unjudged = 0
dead_paths = []
for doc in sorted(doc_dir.glob("*.md")):
    for ref in _refs(doc.read_text()):
        base = ref.split("/")[-1]
        if ref.startswith(("/", ".", "dist/")) or base in SKIP_BASE:
            continue
        if (ws / ref).exists():
            continue
        # A ref beginning with a repo-root directory unambiguously means the
        # repo root, so a suffix match elsewhere must NOT satisfy it (that is
        # how `tooling/enable.sh` hid at addons/web/tooling/enable.sh).
        # `doc/` is ambiguous: the repo root has doc/, and the web module has
        # its own doc/ (COMPONENT_DIAGRAM, FLOW_DIAGRAM). Accept either root for
        # it; the rest are unambiguously repo-root.
        top = ref.split("/")[0]
        if top == "doc":
            if not ((repo / ref).exists() or (web / ref).exists()):
                bad += 1
                dead_paths.append(ref)
            continue
        if top in {"tooling", "odoo", ".github"}:
            if not (repo / ref).exists():
                bad += 1
                dead_paths.append(ref)
            continue
        if base not in index:
            # Undecidable only when a checkout that could hold it is missing.
            if absent:
                unjudged += 1
            else:
                bad += 1
                dead_paths.append(ref)
        elif "/" in ref and not any(q.endswith(ref) for q in index[base]):
            bad += 1
            dead_paths.append(ref)
print(bad, unjudged, ",".join(sorted(set(dead_paths))[:12]))
PYEOF
)
# The sweep names what it rejected. It used to print a bare count, and finding
# the single offending path behind "expected [0] got [1]" meant instrumenting
# the gate by hand -- which is how a blocking gate becomes one people route
# around rather than answer.
read -r dead_n unjudged_n dead_list <<<"${dead_refs:-PARSE_FAILED 0 }"
assert_eq "docs reference no source path that does not exist" "${dead_n:-PARSE_FAILED}" "0"
[ "${dead_n:-0}" != "0" ] && [ -n "${dead_list:-}" ] && \
    echo "       dead: ${dead_list//,/, }"
[ "${unjudged_n:-0}" -gt 0 ] 2>/dev/null && \
    echo "NOTE: ${unjudged_n} reference(s) not judged — they resolve only in absent checkouts:$SIBLINGS_ABSENT"
fi

# Every service registered in web must appear in ARCHITECTURE.md (as a table row
# or in the catch-all note), and every documented row must name the real file.
read -r svc_undoc svc_badpath <<<"$("$VENV_PY" - "$WEB" <<'PYEOF' 2>/dev/null
import re, pathlib, sys
web = pathlib.Path(sys.argv[1])
truth = {}
for p in (web / "static/src").rglob("*.js"):
    t = p.read_text(errors="ignore")
    aliases = {m.group(1) for m in re.finditer(
        r'(?:const|let|var)\s+(\w+)\s*=\s*registry\s*\.\s*category\(\s*["\']services["\']\s*\)', t)}
    pats = [r'registry\s*\.\s*category\(\s*["\']services["\']\s*\)\s*\.\s*add\(\s*["\']([^"\']+)["\']']
    pats += [rf'\b{re.escape(a)}\s*\.\s*add\(\s*["\']([^"\']+)["\']' for a in aliases]
    for pat in pats:
        for m in re.finditer(pat, t):
            truth[m.group(1)] = str(p.relative_to(web / "static/src"))
doc = (web / "machine_doc_v1/ARCHITECTURE.md").read_text()
rows = dict(re.findall(r'^\|\s*`([\w.]+)`\s*\|\s*`([^`]+)`\s*\|', doc, re.M))
note = re.search(r'> Additional webclient-level services:(.*?)\n\n', doc, re.S)
note = set(re.findall(r'`(\w+)`', note.group(1))) if note else set()
covered = set(rows) | note
print(len(set(truth) - covered),
      sum(1 for n, f in rows.items() if n in truth and f != truth[n]))
PYEOF
)"
# Registry schema coverage: CONVENTIONS gotcha #11 must cite the real
# validated/total split rather than a snapshot that silently rots.
read -r reg_val reg_tot <<<"$("$VENV_PY" - "$WEB/static/src" <<'PYEOF' 2>/dev/null
import re, pathlib, sys
cats, validated = set(), set()
for p in pathlib.Path(sys.argv[1]).rglob("*.js"):
    t = p.read_text(errors="ignore")
    cats |= set(re.findall(r'registry\s*\.\s*category\(\s*["\']([^"\']+)["\']\s*\)', t))
    al = dict(re.findall(
        r'(?:const|let|var)\s+(\w+)\s*=\s*registry\s*\.\s*category\(\s*["\']([^"\']+)["\']\s*\)', t))
    validated |= set(re.findall(
        r'registry\s*\.\s*category\(\s*["\']([^"\']+)["\']\s*\)\s*\.\s*addValidation\(', t))
    for a, c in al.items():
        if re.search(rf'\b{re.escape(a)}\s*\.\s*addValidation\(', t):
            validated.add(c)
print(len(validated), len(cats))
PYEOF
)"
# Graph/Pivot VIEWS are eagerly bundled (assets_backend globs views/**); only
# the Chart.js/FullCalendar LIBRARIES are lazy. The docs contradicted
# themselves on this, so pin both the manifest fact and the wording.
assert_eq "assets_backend eagerly globs views/** (graph+pivot are not lazy)" \
    "$("$PY" -c "import ast;m=ast.literal_eval(open('$WEB/__manifest__.py').read());print(sum(1 for i in m['assets']['web.assets_backend'] if isinstance(i,str) and 'static/src/views/**' in i))")" "1"
assert_eq "no backend lazy bundle exists" \
    "$("$PY" -c "import ast;m=ast.literal_eval(open('$WEB/__manifest__.py').read());print(sum(1 for b in m['assets'] if 'lazy' in b and 'frontend' not in b))")" "0"
assert_eq "ARCHITECTURE.md does not call the graph/pivot views lazy-loaded" \
    "$(grep -cE '^\| (Graph|Pivot) \|.*— lazy loaded' "$DOC/ARCHITECTURE.md")" "0"

# Was a hand-rolled `grep -c` wrapped in assert_eq — the same derive-and-cite
# shape as assert_doc_cites, written out by hand, which meant it reported
# "expected [1] got [0]" instead of naming the figure and could not be rewritten
# by --update. Both halves of the ratio are pinned.
assert_doc_cites "CONVENTIONS #11 cites the real registry schema coverage" \
    "$reg_val $reg_tot" '\*\*%s of %s web-module categories\*\*' CONVENTIONS.md

assert_eq "ARCHITECTURE.md covers every service registered in web" "${svc_undoc:-PARSE_FAILED}" "0"
assert_eq "ARCHITECTURE.md service rows name the real file" "${svc_badpath:-PARSE_FAILED}" "0"
assert_eq "DIRECTORY_MAP.md Files column matches the filesystem on every row" \
    "${dirmap_bad:-PARSE_FAILED}" "0"
assert_eq "DIRECTORY_MAP.md has no stale Lines column" \
    "$(grep -c '^| Directory | Layer | Files | Primary Responsibility |' "$DOC/DIRECTORY_MAP.md")" "1"
assert_eq "DIRECTORY_MAP.md lists no directory that does not exist" "${map_only:-none}" "none"
assert_eq "DIRECTORY_MAP.md omits no directory that does exist" "${disk_only:-none}" "none"
# Cite-fingerprint: confirm the underlying count.
assert_eq "static/src directory entries incl. root (excl. gitignored .claude cruft)" \
    "$((SRC_DIRS + 1))" "249"
assert_eq "polyfills/ directory deleted" \
    "$([ -d "$WEB/static/src/polyfills" ] && echo 1 || echo 0)" "0"
assert_eq "DIRECTORY_MAP.md dropped the polyfills row" \
    "$(grep -c 'polyfills' "$WEB/machine_doc_v1/DIRECTORY_MAP.md")" "0"
assert_eq "DIRECTORY_MAP.md has a core/lib row" \
    "$(grep -cE '^\| .core/lib/. \|' "$WEB/machine_doc_v1/DIRECTORY_MAP.md")" "1"
assert_eq "DIRECTORY_MAP.md has a search/embedded_actions_bar row" \
    "$(grep -cE '^\| .search/embedded_actions_bar/. \|' "$WEB/machine_doc_v1/DIRECTORY_MAP.md")" "1"

# 17. Test files carrying no web_* topic tag, derived from the AST.
untagged=$("$VENV_PY" - "$WEB/tests" <<'PYEOF' 2>/dev/null
import ast, pathlib, sys
n = 0
for p in sorted(pathlib.Path(sys.argv[1]).glob("test_*.py")):
    tags = set()
    for node in ast.walk(ast.parse(p.read_text())):
        if isinstance(node, ast.ClassDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(
                        dec.func, "id", getattr(dec.func, "attr", "")) == "tagged":
                    tags |= {a.value for a in dec.args if isinstance(a, ast.Constant)}
    if not any(str(t).startswith("web_") for t in tags):
        n += 1
print(n)
PYEOF
)
assert_eq "test files with no web_* topic tag" "${untagged:-AST_FAILED}" "5"
assert_eq "TEST_TAGS.md tabulates all five" \
    "$(grep -cE '^\| .test_(fontawesome|pdfjs_dist|ir_asset_scope|js_addons|scss_design_system)\.py. \|' "$WEB/machine_doc_v1/TEST_TAGS.md")" "5"

# 18. ESM pipeline moved to the declarative registry (odoo/tools/assets/):
#     the assetsbundle frozensets (_ESM_APP_BUNDLES / ESM_BUNDLES /
#     DYNAMIC_ESM_BUNDLES / IMPORT_MAP_INCLUDES) are GONE — bundle membership
#     is declared per-module under the manifest 'esm' key and aggregated by
#     esm_registry().  Assert the symbols by existence, not line number
#     (assetsbundle.py is now the assetsbundle/ package; native-node helpers
#     moved to ir_qweb_assets.py).
if skip_missing "$REPO/odoo/tools/assets" "ESM pipeline (esm_registry/esbuild/assetsbundle) assertions" 9; then :; else
PYBASE="$REPO/odoo/addons/base/models"
PYTOOLS="$REPO/odoo/tools/assets"
assert_eq "assetsbundle: hardcoded ESM frozensets are gone" \
    "$(grep -rE '_ESM_APP_BUNDLES|DYNAMIC_ESM_BUNDLES|IMPORT_MAP_INCLUDES = ' "$PYBASE/assetsbundle" | wc -l)" "0"
assert_eq "esm_registry.py exports esm_registry()" \
    "$(grep -c 'def esm_registry' "$PYTOOLS/esm_registry.py")" "1"
assert_eq "esm_registry.py defines the EsmRegistry NamedTuple" \
    "$(grep -c 'class EsmRegistry' "$PYTOOLS/esm_registry.py")" "1"
assert_eq "esm_registry.py defines check_esm_config" \
    "$(grep -c 'def check_esm_config' "$PYTOOLS/esm_registry.py")" "1"
assert_eq "esm_registry.py derives the library aliases from the manifests" \
    "$(grep -c 'def external_lib_aliases' "$PYTOOLS/esm_registry.py")" "1"
assert_eq "no second specifier table survives beside esm.external_libs" \
    "$(grep -rcE '_LIB_CANDIDATES|EXTERNAL_LIB_ALIASES' "$PYTOOLS/esbuild.py")" "0"
assert_eq "esm_graph.py defines is_native_module" \
    "$(grep -c 'def is_native_module' "$PYTOOLS/esm_graph.py")" "1"
assert_eq "assetsbundle/bundle.py gates ESM via esm_registry().bundles" \
    "$(grep -c 'esm_registry().bundles' "$PYBASE/assetsbundle/bundle.py")" "1"
assert_eq "assetsbundle/bundle.py defines esbuild_native_bundle" \
    "$(grep -c 'def esbuild_native_bundle' "$PYBASE/assetsbundle/bundle.py")" "1"
assert_eq "ir_qweb_assets.py defines _get_native_module_nodes" \
    "$(grep -cE 'def _get_native_module_nodes\(' "$PYBASE/ir_qweb_assets.py")" "1"
fi
# (The "documents the manifest 'esm' key" assertion that lived here counted
# occurrences of the literal `dynamic_children` against a hardcoded 4 — a
# restated number that broke the moment a row was added, and that said nothing
# about coverage. Superseded by the derived key-coverage assertion below, which
# reads _ESM_MANIFEST_KEYS and requires a row per key.)

# 19. Symbols named in STATE_MANAGEMENT.md "Key files".
assert_eq "form_controller.js defines save()" \
    "$(grep -cE 'async save\(' "$WEB/static/src/views/form/form_controller.js")" "1"
assert_eq "form_controller.js defines discard()" \
    "$(grep -cE 'async discard\(' "$WEB/static/src/views/form/form_controller.js")" "1"
assert_eq "form_controller.js defines beforeLeave()" \
    "$(grep -cE 'async beforeLeave\(' "$WEB/static/src/views/form/form_controller.js")" "1"
assert_eq "record.js defines applyChanges()" \
    "$(grep -cE '^    applyChanges\(' "$WEB/static/src/model/relational_model/record.js")" "1"
assert_eq "record.js defines discard()" \
    "$(grep -cE 'async discard\(' "$WEB/static/src/model/relational_model/record.js")" "1"
# CLEAR-CACHES emission/listener inventory (STATE_MANAGEMENT "emission sites").
assert_eq "invalidator service emits CLEAR_CACHES" \
    "$(grep -c 'CLEAR_CACHES' "$WEB/static/src/core/network/result_set_cache_invalidator_service.js")" "2"
assert_eq "invalidator service subscribes to base.language.install" \
    "$(grep -cF '["base.language.install"]' "$WEB/static/src/core/network/result_set_cache_invalidator_service.js")" "1"
assert_eq "invalidator service handles action_install_lang full clear" \
    "$(grep -cF 'methods: ["action_install_lang"]' "$WEB/static/src/core/network/result_set_cache_invalidator_service.js")" "1"
assert_eq "base.language.install defines action_install_lang" \
    "$(grep -cE '^    def action_install_lang\(' "$REPO/odoo/addons/base/wizards/base_language_install.py")" "1"
assert_eq "action_cache_invalidation.js emits CLEAR_CACHES" \
    "$(grep -c 'CLEAR_CACHES' "$WEB/static/src/webclient/actions/action_cache_invalidation.js")" "1"
assert_eq "service_worker_service.js emits CLEAR_CACHES on SW hard refresh" \
    "$(grep -c 'CLEAR_CACHES' "$WEB/static/src/webclient/service_worker_service.js")" "1"
assert_eq "rpc.js is the CLEAR_CACHES listener" \
    "$(grep -c 'addEventListener(RpcEvent.CLEAR_CACHES' "$WEB/static/src/core/network/rpc.js")" "1"

# 21. TEST_TAGS.md test counts, collected through prepare_suite() — what
#     --test-tags actually selects, including methods inherited from untagged
#     base classes. A `def test_` grep gets both of those wrong.
count_tag_tests() {
    # $1 = topic tag; emits the number of tests prepare_suite() collects for it.
    # No database required — collection only.
    #
    # stderr is kept, not discarded: swallowing it is what turned a wrong
    # ODOO_CONF path into eight identical LOADER_FAILED lines that named
    # neither the cause nor the file. The caller reports the last line.
    local tag="$1"
    (cd "$REPO" && "$VENV_PY" - "$tag" "$ODOO_CONF" "$REPO" <<'PY' 2>"$LOADER_ERR"
import sys
tag, conf, repo = sys.argv[1], sys.argv[2], sys.argv[3]
from odoo.tools import config
# The addons path is PINNED to this checkout, and the flag is what pins it:
# passing it here beats the conf, and it has to be in this one parse_config
# call because `initialize_sys_path` runs inside it and only ever APPENDS --
# assigning config["addons_path"] afterwards and calling it again leaves the
# path exactly as it was, silently, which is how this was first "verified".
#
# Without the pin the figure is a property of whoever ran the harness. `web`'s
# three own counts do not move, but `addon_js` generates one method per addon
# on the path that bundles unit tests no runner selects: 75 for this fork,
# 163 in a workspace that also has enterprise, agromarin and design-themes
# checked out beside it. The doc can hold one number, and the number it should
# hold is the one this repository determines.
config.parse_config([
    "-c", conf,
    f"--addons-path={repo}/odoo/addons,{repo}/addons",
])
config["test_tags"] = tag
from odoo.tests.loader import prepare_suite
print(len(list(prepare_suite(["web"], tag))))
PY
    )
}
LOADER_ERR="$(mktemp)"
trap 'rm -f "$LOADER_ERR"' EXIT
if [ -z "${ODOO_CONF:-}" ] || [ ! -f "$ODOO_CONF" ]; then
    echo "SKIP: TEST_TAGS prepare_suite counts — no Odoo config found" \
         "(looked for <env>.conf beside a matching venv under $WORKSPACE;" \
         "set ODOO_CONF/VENV_PY to override)"
    SKIP=$((SKIP+8))
elif ! (cd "$REPO" && "$VENV_PY" -c "import odoo" >/dev/null 2>&1); then
    echo "SKIP: TEST_TAGS prepare_suite counts — odoo not importable with $VENV_PY"
    SKIP=$((SKIP+8))
else
    # `prepare_suite` is the only source of truth here. This loop used to carry a
    # hardcoded expected count per tag AND assert the doc cited it — two copies
    # of one number, and the comment that stood here admitted the doc said 159
    # against 158 real. `addon_js` is generated (one method per uncovered addon)
    # and `web_unit` moves with every added test, so both drift by design; the
    # only durable assertion is that the DOC agrees with the LOADER.
    for tag in \
        web_unit web_http web_tour web_js web_perf web_benchmark click_all addon_js; do
        actual=$(count_tag_tests "$tag")
        if [ -z "$actual" ]; then
            assert_eq "TEST_TAGS $tag test count (prepare_suite)" \
                "LOADER_FAILED: $(tail -n 1 "$LOADER_ERR")" "a number"
            continue
        fi
        assert_doc_cites "TEST_TAGS.md cites the real $tag count" \
            "$actual" "\`$tag\`.*\| %s tests" TEST_TAGS.md
    done
fi

# 20. (removed) JS_FILE_INDEX body-header assertions — JS_FILE_INDEX.md deleted

# 23. Conditional /web/webclient/load_menus (X-Menus-Hash round-trip).
assert_eq "home.py sends X-Menus-Hash" \
    "$(grep -c '"X-Menus-Hash"' "$WEB/controllers/home.py")" "1"
assert_eq "home.py returns empty 304 on hash match" \
    "$(grep -c 'status=304' "$WEB/controllers/home.py")" "1"
assert_eq "menu_service.js echoes the hash back as ?hash=" \
    "$(grep -c '?hash=' "$WEB/static/src/webclient/menus/menu_service.js")" "1"
assert_eq "ROUTE_MAP.md load_menus row documents the conditional fetch" \
    "$(grep -c 'X-Menus-Hash' "$WEB/machine_doc_v1/ROUTE_MAP.md")" "1"
assert_eq "CONVENTIONS gotcha #14 covers the load_menus hash round-trip" \
    "$(grep -c 'X-Menus-Hash' "$WEB/machine_doc_v1/CONVENTIONS.md")" "1"

# 24. useReactiveModel + Model._updateEpoch + reactiveRenderers opt-out.
assert_eq "model.js exports useReactiveModel" \
    "$(grep -c 'export function useReactiveModel' "$WEB/static/src/model/model.js")" "1"
assert_eq "model.js notify() bumps _updateEpoch" \
    "$(grep -c 'this._updateEpoch++' "$WEB/static/src/model/model.js")" "1"
# No model can ask for a forced render: the hook has no such branch, and neither
# the old `reactiveRenderers` opt-out nor the transitional `forceRenderOnUpdate`
# opt-in exists anywhere in the tree.
assert_eq "the model hook has no forced-render branch" \
    "$(grep -c 'render(true)' "$WEB/static/src/model/model.js")" "0"
assert_eq "no model uses the removed reactiveRenderers flag" \
    "$(grep -rl 'reactiveRenderers' "$WEB/static/src" | wc -l)" "0"
assert_eq "no model uses the removed forceRenderOnUpdate flag" \
    "$(grep -rl 'forceRenderOnUpdate' "$WEB/static/src" | wc -l)" "0"
assert_eq "calendar renderers subscribe with useReactiveModel" \
    "$(grep -rl 'useReactiveModel' "$WEB/static/src/views/calendar" | wc -l)" "3"
# The pivot and graph RENDERERS subscribe; their models do not.
assert_eq "pivot renderer uses useReactiveModel" \
    "$(grep -c 'useReactiveModel(this.props.model)' "$WEB/static/src/views/pivot/pivot_renderer.js")" "1"
assert_eq "graph renderer uses useReactiveModel" \
    "$(grep -c 'useReactiveModel(this.props.model)' "$WEB/static/src/views/graph/graph_renderer.js")" "1"
assert_eq "STATE_MANAGEMENT documents useReactiveModel" \
    "$(grep -c 'useReactiveModel' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "3"
assert_eq "STATE_MANAGEMENT documents that the escape hatch is gone" \
    "$(grep -c 'forceRenderOnUpdate' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "1"

# 24b. A bare `reactive()` passed as a prop subscribes nobody. Both instances are
# fixed; these pin the fixes rather than the prose, so a regression fails here.
assert_eq "progress bar syncs activeBar instead of closing over the seeding proxy" \
    "$(grep -c '_syncActiveBar' "$WEB/static/src/views/kanban/progress_bar_hook.js")" "4"
assert_eq "progress bar no longer builds activeBar as a self-closure getter" \
    "$(grep -c 'get activeBar()' "$WEB/static/src/views/kanban/progress_bar_hook.js")" "0"
assert_eq "no component skips useState when a reactive prop is supplied" \
    "$(grep -rc '|| useState(' "$WEB/static/src" | grep -v ':0$' | wc -l)" "0"
assert_eq "kanban renderer wraps the quick-create state in useState" \
    "$(grep -c 'this.quickCreateState = useState(' "$WEB/static/src/views/kanban/kanban_renderer.js")" "1"
assert_eq "kanban renderer re-targets progressBarState with useState" \
    "$(grep -c 'useState(this.props.progressBarState)' "$WEB/static/src/views/kanban/kanban_renderer.js")" "1"
# Anchored to the SECTION, not to any mention of it: the rule is documented
# once, but prose elsewhere in the file legitimately points at that section, and
# counting bare mentions turned a useful cross-reference into a gate failure.
assert_eq "STATE_MANAGEMENT documents the bare-reactive-as-prop rule" \
    "$(grep -c '^### .*subscribes NOBODY' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "1"

# 25. _updateConfig is now _patchConfig / _reloadWithConfig.
assert_eq "no _updateConfig left in model/" \
    "$(grep -rc '_updateConfig' "$WEB/static/src/model" --include='*.js' 2>/dev/null | awk -F: '{s+=$NF} END {print s+0}')" "0"
assert_eq "docs do not cite _updateConfig" \
    "$(grep -rc '_updateConfig' "$WEB/machine_doc_v1"/*.md "$WEB/doc"/*.md 2>/dev/null | awk -F: '{s+=$NF} END {print s+0}')" "0"

# 26. ListRecordRow extraction (per-row component, renderer-delegation contract).
assert_eq "list_record_row.js exports ListRecordRow" \
    "$(grep -c 'export class ListRecordRow extends Component' "$WEB/static/src/views/list/list_record_row.js")" "1"
assert_eq "row body template keeps its historical t-name (compat contract)" \
    "$(grep -rc 'web.ListRenderer.RecordRow' "$WEB/static/src/views/list/list_renderer.xml" 2>/dev/null | awk -F: '{s+=$NF} END {print s+0}')" "1"
assert_eq "CONVENTIONS gotcha #15 covers ListRecordRow" \
    "$(grep -c 'ListRecordRow' "$WEB/machine_doc_v1/CONVENTIONS.md")" "1"

# 27. Scoped re-validation dep-maps.
assert_eq "record_utils.js exports computeRevalidationScope" \
    "$(grep -c 'export function computeRevalidationScope' "$WEB/static/src/model/relational_model/record_utils.js")" "1"
assert_eq "record.js passes scopedFields to the removeInvalidOnly re-check" \
    "$(grep -c 'removeInvalidOnly: true, scopedFields' "$WEB/static/src/model/relational_model/record.js")" "1"
assert_eq "STATE_MANAGEMENT documents computeRevalidationScope" \
    "$(grep -c 'computeRevalidationScope' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "1"

# 28. Kanban progress bars: local drag-move reconcile.
assert_eq "progress_bar_hook has registerRecordMove" \
    "$(grep -c 'registerRecordMove(recordId, sourceGroupId, targetGroupId)' "$WEB/static/src/views/kanban/progress_bar_hook.js")" "1"
assert_eq "progress_bar_hook has _reconcileMove (JSDoc + definition)" \
    "$(grep -c '_reconcileMove(record, move)' "$WEB/static/src/views/kanban/progress_bar_hook.js")" "2"
assert_eq "CONVENTIONS gotcha #16 covers the local reconcile" \
    "$(grep -c '_reconcileMove' "$WEB/machine_doc_v1/CONVENTIONS.md")" "1"

# 29. Every constant in core/events.js must be documented with its real string
#     value. A cardinality check on one group is not enough — it passed while
#     14 of 33 were missing.
read -r ev_undoc ev_badval <<<"$("$VENV_PY" - "$WEB" <<'PYEOF' 2>/dev/null
import re, pathlib, sys
web = pathlib.Path(sys.argv[1])
src = (web / "static/src/core/events.js").read_text()
truth = {}
for gm in re.finditer(r"export const (\w+) = Object\.freeze\(\{(.*?)\}\);", src, re.S):
    for m in re.finditer(r'(\w+):\s*"([^"]+)"', gm.group(2)):
        truth[f"{gm.group(1)}.{m.group(1)}"] = m.group(2)
doc = (web / "machine_doc_v1/STATE_MANAGEMENT.md").read_text()
documented = {}
for m in re.finditer(
        r"^\| `(\w+)\.(\w+)`(?: / `?(\w+)`?)* \| `([^`]+)`(?: / `([^`]+)`)*(?: / `([^`]+)`)* \|",
        doc, re.M):
    grp = m.group(1)
    names = [g for g in (m.group(2), m.group(3)) if g]
    vals = [g for g in (m.group(4), m.group(5), m.group(6)) if g]
    for i, n in enumerate(names):
        documented[f"{grp}.{n}"] = vals[i] if i < len(vals) else vals[0]
# groups documented as a single slash row (ADDED / LOADED / ERROR)
for m in re.finditer(r"^\| `(\w+)\.(\w+)` / `(\w+)` / `(\w+)` \| `([^`]+)` / `([^`]+)` / `([^`]+)` \|", doc, re.M):
    g = m.group(1)
    for n, v in zip(m.group(2, 3, 4), m.group(5, 6, 7)):
        documented[f"{g}.{n}"] = v
undoc = [k for k in truth if k not in documented]
badval = [k for k in documented if k in truth and documented[k] != truth[k]]
print(len(undoc), len(badval))
PYEOF
)"
assert_eq "STATE_MANAGEMENT documents every core/events.js constant" "${ev_undoc:-PARSE_FAILED}" "0"
assert_eq "STATE_MANAGEMENT event string values are correct" "${ev_badval:-PARSE_FAILED}" "0"

assert_eq "core/events.js exports SearchModelEvent" \
    "$(grep -c 'export const SearchModelEvent' "$WEB/static/src/core/events.js")" "1"
assert_eq "STATE_MANAGEMENT typed-events table has the 4 SearchModelEvent rows" \
    "$(grep -c 'SearchModelEvent\.' "$WEB/machine_doc_v1/STATE_MANAGEMENT.md")" "4"

# 30. rpc_cache 'immutable' option — deep-frozen shared payloads, adopted by
#     field_service's fields_get disk cache.
assert_eq "rpc_cache.js implements the immutable option (deepFreeze)" \
    "$(grep -c 'immutable ? deepFreeze : deepCopy' "$WEB/static/src/core/network/rpc_cache.js")" "1"
# Counts the CALL, not the phrase. `grep -c 'immutable: true'` also matched the
# JSDoc that explains what the option does to the payload, so the assertion read
# 2 the moment the contract was documented -- and, worse, would have read 1 and
# passed with the call deleted and only the prose left.
assert_eq "field_service uses cache({type:'disk', immutable:true})" \
    "$(grep -cE '\.cache\(\{ *type: *"disk", *immutable: *true *\}\)' \
        "$WEB/static/src/core/field_service.js")" "1"

# 31. EmbeddedActionsBar extracted out of ControlPanel.
assert_eq "embedded_actions_bar component exists" \
    "$([ -f "$WEB/static/src/search/embedded_actions_bar/embedded_actions_bar.js" ] && echo 1 || echo 0)" "1"

# 31b. ROUTE_MAP totals + removed QUnit runner route.
assert_eq "webclient.py no longer serves /web/tests/legacy" \
    "$(grep -c '/web/tests/legacy' "$WEB/controllers/webclient.py")" "0"
# Count route-decorated FUNCTIONS, not @route occurrences: one handler carries
# two decorators, so occurrence-counting over-reports handlers by one. URLs are
# the distinct route strings those decorators declare.
read -r ROUTE_HANDLERS ROUTE_URLS <<<"$("$VENV_PY" - "$WEB/controllers" <<'PYEOF'
import ast, pathlib, sys
n = 0; urls = set()
for f in sorted(pathlib.Path(sys.argv[1]).glob("*.py")):
    for node in ast.walk(ast.parse(f.read_text())):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            hit = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(
                        dec.func, "attr", getattr(dec.func, "id", "")) == "route":
                    hit = True
                    for a in dec.args:
                        if isinstance(a, ast.Constant):
                            urls.add(a.value)
                        elif isinstance(a, (ast.List, ast.Tuple)):
                            urls |= {e.value for e in a.elts if isinstance(e, ast.Constant)}
            if hit:
                n += 1
print(n, len(urls))
PYEOF
)"
# The per-category rows must SUM to the AST truth: cardinality-only checking
# let the openapi row go missing while the total still read 75.
route_sum=$("$VENV_PY" - "$DOC/ROUTE_MAP.md" <<'PYEOF' 2>/dev/null
import re, sys
h = u = 0
for ln in open(sys.argv[1]):
    m = re.match(r"\|\s*([^|]+?)\s*\|\s*(\d+)\s*/\s*(\d+)\s*\|", ln)
    if m and "Total" not in m.group(1):
        h += int(m.group(2)); u += int(m.group(3))
print(f"{h}/{u}")
PYEOF
)
assert_eq "ROUTE_MAP category rows sum to the handler/URL truth" \
    "${route_sum:-PARSE_FAILED}" "$ROUTE_HANDLERS/$ROUTE_URLS"
assert_doc_cites "ROUTE_MAP total row cites the handler count" "$ROUTE_HANDLERS" \
    '\\*\\*%s handlers' ROUTE_MAP.md

# 32. Per-HANDLER coverage. The sum check above is still cardinality-only one
#     level down: /web/metrics and openapi_json were both absent from every
#     table while the category rows and the total stayed correct, because the
#     Bootstrap row said "11 handlers" and only 10 were tabulated. Name each
#     handler, or it is not documented.
route_undoc="$("$VENV_PY" - "$WEB" <<'PYEOF' 2>/dev/null
import ast, pathlib, re, sys
web = pathlib.Path(sys.argv[1])
handlers = set()
for f in sorted((web / "controllers").glob("*.py")):
    tree = ast.parse(f.read_text())
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for fn in (n for n in cls.body if isinstance(n, ast.FunctionDef)):
            for dec in fn.decorator_list:
                if isinstance(dec, ast.Call) and getattr(
                        dec.func, "attr", getattr(dec.func, "id", "")) == "route":
                    handlers.add(fn.name)
doc = (web / "machine_doc_v1/ROUTE_MAP.md").read_text()
# A handler counts as documented only from a real table row citing `name()`.
documented = set(re.findall(r"\|\s*`?(\w+)\(\)`?\s*\|", doc))
print(len(handlers - documented))
PYEOF
)"
assert_eq "ROUTE_MAP has a table row for every route handler" \
    "${route_undoc:-PARSE_FAILED}" "0"

# 33. session_info() key coverage. MODEL_MAP calls its list the "Full key list";
#     has_unaccent was added to _base_session_info and the list never grew.
sess_undoc="$("$VENV_PY" - "$WEB" <<'PYEOF' 2>/dev/null
import ast, pathlib, re, sys
web = pathlib.Path(sys.argv[1])
src = (web / "models/ir_http.py").read_text()
tree = ast.parse(src)
keys = set()
for fn in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
    if fn.name not in ("_base_session_info", "session_info", "_get_config_limits"):
        continue
    for node in ast.walk(fn):
        # info = {...} / return {...}
        if isinstance(node, ast.Dict):
            keys |= {k.value for k in node.keys
                     if isinstance(k, ast.Constant) and isinstance(k.value, str)}
        # info["x"] = ...
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            if isinstance(node.value, ast.Name) and node.value.id == "info":
                keys.add(node.slice.value)
        # info.update(x=..., y=...)
        elif isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "update":
            keys |= {kw.arg for kw in node.keywords if kw.arg}
# Nested keys reached by walking into value dicts; documented in prose on
# their parent's row (bundle_params, groups) rather than as keys in their own
# right, so a bare-token match would report them missing forever.
keys -= {"lang", "debug"}
doc = (web / "machine_doc_v1/MODEL_MAP.md").read_text()
# Substring, not a backticked-token match: `groups` is documented as the
# literal {"base.group_allow_export": bool}, which no token regex sees.
missing = sorted(k for k in keys if k not in doc)
print(len(missing), ",".join(missing))
PYEOF
)"
read -r sess_n sess_list <<<"${sess_undoc:-PARSE_FAILED }"
assert_eq "MODEL_MAP cites every session_info() key" "${sess_n:-PARSE_FAILED}" "0"
[ "${sess_n:-0}" != "0" ] && [ -n "${sess_list:-}" ] && \
    echo "       undocumented: ${sess_list//,/, }"

# 34. Field coverage for the models MODEL_MAP gives a Fields list for.
#     pageview_id was added to web.cwv.metric — changing the table from
#     append-only to upsert-keyed — and the field list never mentioned it.
#     base_document_layout is exempt: the doc marks it "not exhaustive" on
#     purpose (a wizard of related company fields).
read -r field_undoc field_scanned <<<"$("$VENV_PY" - "$WEB" <<'PYEOF' 2>/dev/null
import ast, pathlib, re, sys
web = pathlib.Path(sys.argv[1])
doc = (web / "machine_doc_v1/MODEL_MAP.md").read_text()
cited = set(re.findall(r"`([\w.]+)`", doc))
EXEMPT = {"base_document_layout.py"}
missing = 0
scanned = 0
for f in sorted((web / "models").glob("*.py")):
    if f.name in EXEMPT:
        continue
    # Only models the doc actually gives a "**Fields:**" block for.
    if f"models/{f.name} —" not in doc:
        continue
    section = doc.split(f"models/{f.name} —", 1)[1].split("\n### ", 1)[0]
    # "**Fields:**", "**Fields** (30):", "**Fields** (numeric vitals ...)" all
    # introduce a list. Matching only the colon form skipped web.cwv.metric —
    # the one model this gate was written for — and reported a clean pass.
    if "**Fields" not in section:
        continue
    scanned += 1
    tree = ast.parse(f.read_text())
    for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
        for node in cls.body:
            if not isinstance(node, ast.Assign):
                continue
            v = node.value
            if not (isinstance(v, ast.Call) and getattr(
                    getattr(v.func, "value", None), "id", "") == "fields"):
                continue
            for t in node.targets:
                if isinstance(t, ast.Name) and f"`{t.id}`" not in section:
                    missing += 1
print(missing, scanned)
PYEOF
)"
assert_eq "MODEL_MAP Fields lists name every field on those models" \
    "${field_undoc:-PARSE_FAILED}" "0"
# Empty-tree refusal: unlike the route/session gates (which count doc MISSES and
# so blow up on an empty doc), this one iterates doc sections — nothing to scan
# reads as nothing missing. Pin the section count so a heading rename that
# silently drops a model out of scope fails instead of passing.
assert_eq "MODEL_MAP field gate actually scanned its models" \
    "${field_scanned:-PARSE_FAILED}" "7"

# 35. Module faces. The count is a filesystem property (a directory with a
#     sibling <name>.js), so derive it; the doc said 38 against a real 39,
#     which tooling/architecture/js_face_boundary.py had right all along.
FACES=$("$VENV_PY" - "$WEB/static/src" <<'PYEOF' 2>/dev/null
import pathlib, sys
src = pathlib.Path(sys.argv[1])
print(sum(1 for d in src.rglob("*")
          if d.is_dir() and (d.parent / f"{d.name}.js").exists()))
PYEOF
)
assert_doc_cites "ARCHITECTURE cites the real module-face count" \
    "${FACES:-PARSE_FAILED}" '^%s directories are fronted' ARCHITECTURE.md

# 36. registerField / registerFallbackField call sites, fork-wide. Repeated in
#     four places across three docs, so it rots four times over: it read 107/76
#     against a real 110/79 (the spec-form 31 stayed correct).
if skip_without_siblings "registerField fork-wide counts" 5; then :; else
read -r RF_TOTAL RF_PLAIN RF_SPEC <<<"$("$VENV_PY" - "$ADDONS" <<'PYEOF' 2>/dev/null
import pathlib, re, sys
call = re.compile(r"(?<!function )\b(registerField|registerFallbackField)\(\s*")
tot = plain = spec = 0
for p in pathlib.Path(sys.argv[1]).rglob("*.js"):
    if "machine_doc" in str(p) or "node_modules" in str(p) or ".worktrees" in p.parts:
        continue
    try:
        t = p.read_text(errors="ignore")
    except OSError:
        continue
    for m in call.finditer(t):
        tot += 1
        if t[m.end()] == "{":
            spec += 1
        else:
            plain += 1
print(tot, plain, spec)
PYEOF
)"
# One assertion per RESTATEMENT, not per file. A bare `%s fork-wide` matched two
# lines in each of these docs, so satisfying either one passed the gate while
# the other rotted — and an ambiguous locator is one --update refuses outright,
# which is how these two survived a sweep that fixed twenty-one of their
# neighbours.
assert_doc_cites "ARCHITECTURE Fields row cites the registerField site count" \
    "${RF_TOTAL:-PARSE_FAILED}" '^\| \*\*Fields\*\* .*; %s fork-wide' ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE prose cites the registerField site count" \
    "${RF_TOTAL:-PARSE_FAILED}" '^Field widgets .*; %s fork-wide' ARCHITECTURE.md
assert_doc_cites "CONVENTIONS field-widget prose cites the registerField site count" \
    "${RF_TOTAL:-PARSE_FAILED}" 'widget directories and %s fork-wide' CONVENTIONS.md
assert_doc_cites "CONVENTIONS rename-guidance prose cites the registerField site count" \
    "${RF_TOTAL:-PARSE_FAILED}" 'inside .fields/., %s fork-wide' CONVENTIONS.md
# The split is restated three times; only ARCHITECTURE's copy was pinned, so
# CONVENTIONS and JSDOC kept saying 79/31 under a total they had been rewritten
# to 113 -- a sum that does not add up, in a sentence that names the total.
assert_doc_cites "JSDOC cites the real plain-form share of the registerField sites" \
    "${RF_PLAIN:-PARSE_FAILED} ${RF_TOTAL:-PARSE_FAILED}" '%s of the %s fork-wide' JSDOC_TYPE_TIGHTENING.md
assert_doc_cites "JSDOC cites the real spec-form count" \
    "${RF_SPEC:-PARSE_FAILED}" 'the other %s already use the spec object' JSDOC_TYPE_TIGHTENING.md
assert_doc_cites "CONVENTIONS field-widget prose cites the real plain/spec split" \
    "${RF_PLAIN:-PARSE_FAILED} ${RF_SPEC:-PARSE_FAILED}" '\(%s plain, %s through the typed spec form\)' CONVENTIONS.md
assert_doc_cites "ARCHITECTURE cites the real plain/spec split" \
    "${RF_PLAIN:-PARSE_FAILED}" '%s plain and' ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE cites the real spec-form count" \
    "${RF_SPEC:-PARSE_FAILED}" 'and %s through the typed spec form' ARCHITECTURE.md
fi

# ------- ESM_BUNDLING: the doc had drifted to symbols that no longer exist -------
# Every one of these was cited by ESM_BUNDLING.md while resolving nowhere in the
# tree, and nothing here checked it. A map that names a symbol the reader cannot
# find is worse than no map: CLAUDE.md makes machine_doc the FIRST thing to read.
for sym in ODOO_EXTERNAL_LIBS EXTERNAL_BARE_SPECIFIERS _validate_esm_config; do
    cited=$(grep -c "$sym" "$DOC/ESM_BUNDLING.md" 2>/dev/null); cited=${cited:-0}
    exists=$(grep -rl "$sym" --include="*.py" "$REPO" 2>/dev/null | grep -cv machine_doc); exists=${exists:-0}
    if [ "$cited" -ge 1 ] && [ "$exists" -eq 0 ]; then
        echo "FAIL: ESM_BUNDLING cites $sym, which exists nowhere in the tree"; FAIL=$((FAIL+1))
    else
        echo "PASS: ESM_BUNDLING does not cite a vanished $sym [$cited/$exists]"; PASS=$((PASS+1))
    fi
done

# Every `esm` manifest key the registry accepts must be documented, and the doc
# must name no key the registry would reject. Derived from the source both ways,
# so neither side can drift alone.
ESM_KEYS="$("$VENV_PY" - "$REPO" <<'PYEOF' 2>/dev/null
import ast, sys, pathlib
src = pathlib.Path(sys.argv[1], "odoo/tools/assets/esm_registry.py").read_text()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "_ESM_MANIFEST_KEYS":
        print(" ".join(sorted(ast.literal_eval(ast.unparse(node.value.args[0])))))
        break
PYEOF
)"
if [ -z "$ESM_KEYS" ]; then
    echo "SKIP: could not parse _ESM_MANIFEST_KEYS"; SKIP=$((SKIP+1))
else
    missing=""
    for key in $ESM_KEYS; do
        grep -qF -- "\`$key\`" "$DOC/ESM_BUNDLING.md" || missing="$missing $key"
    done
    if [ -n "$missing" ]; then
        echo "FAIL: ESM_BUNDLING documents no row for:$missing"; FAIL=$((FAIL+1))
    else
        echo "PASS: ESM_BUNDLING documents every accepted esm key [$(echo $ESM_KEYS | wc -w)]"; PASS=$((PASS+1))
    fi
fi

# The route's predicate, named in prose. `use_esm` moved from
# `dynamic_bundle_names` to `runtime_bundle_names`; the doc explaining the
# manifest keys must not describe the old one.
ROUTE_PRED=$(grep -oE 'use_esm = bundle_name in esm_registry\(\)\.[a-z_]+' \
    "$WEB/controllers/webclient.py" | sed 's/.*\.//')
assert_doc_cites "ESM_BUNDLING names the predicate /web/bundle actually reads" \
    "${ROUTE_PRED:-PARSE_FAILED}" '%s' ESM_BUNDLING.md

# EXTENSION_ARCHITECTURE_REVIEW argues that odoo's CI cannot see enterprise
# breakage, because no checkout step names another repo. Gate the CLAIM only.
#
# The step COUNT was gated here too, for one revision, and broke inside the hour:
# adding machine_doc.yml took it 19 -> 20. That is §1.4's "prefer omitting an
# incidental figure to gating it" demonstrating itself -- the number shapes no
# decision, the zero does, and gating scale just relocates the rot into a gate.
# The doc now states the invariant without a count.
#
# `^[[:space:]]*repository:` is anchored to a YAML KEY. Unanchored, this counted
# the word wherever it appeared -- including the comment in machine_doc.yml that
# explains the invariant -- so a gate went red over prose describing it. Same
# error as the unanchored `ratchet.py tsc` match this file fixed two blocks up:
# a substring is not a declaration.
if skip_missing "$REPO/.github/workflows" "CI checkout-scope assertion" 1; then :; else
    assert_eq "no workflow checks out a second repository" \
        "$(grep -hE '^[[:space:]]*repository:' "$REPO"/.github/workflows/*.yml 2>/dev/null | wc -l)" "0"
fi

# VIEW_TEARDOWN_COST cites a profiler stack as `owl.es.js:<line>`. Resolve each
# one: a re-vendored OWL shifts them silently, and they were ALREADY wrong once
# in a way no reading caught -- every frame off by exactly one, because CDP
# reports `CallFrame.lineNumber` 0-based and the profile was transcribed raw.
# Uniformly-off line numbers still land on plausible code, so only a resolver
# catches this. Assert the cited line IS the frame the doc names.
OWL_JS="$WEB/static/lib/owl/owl.es.js"
if skip_missing "$OWL_JS" "VIEW_TEARDOWN_COST owl frame assertions" 1; then :; else
    owl_bad=""
    while read -r fn line; do
        [ -n "$line" ] || continue
        sed -n "${line}p" "$OWL_JS" | grep -qE "^\s*${fn}\s*\(" || owl_bad="$owl_bad ${fn}:${line}"
    done <<< "$(grep -oE '^ *(└─ )?(remove|patch) +\[owl\.es\.js:[0-9]+\]' \
        "$DOC/VIEW_TEARDOWN_COST.md" | sed -E 's/.*(remove|patch) +\[owl\.es\.js:([0-9]+)\]/\1 \2/')"
    if [ -n "$owl_bad" ]; then
        echo "FAIL: VIEW_TEARDOWN_COST owl.es.js frames do not resolve:$owl_bad"; FAIL=$((FAIL+1))
    else
        echo "PASS: VIEW_TEARDOWN_COST owl.es.js frames all resolve [$(grep -cE '\[owl\.es\.js:[0-9]+\]' "$DOC/VIEW_TEARDOWN_COST.md")]"; PASS=$((PASS+1))
    fi
fi

# ------- OBSERVABILITY: the campaign's logger and probe surface -------
#
# Temporary by design -- every assertion here is deleted with the surface it
# describes, at the end of the JS-improvement campaign. They are DERIVED rather
# than literal so the page cannot drift while the campaign is still moving.

OBS_NAMESPACES=$(grep -cE '^(export )?const \w+Log = _makeNamespacedLog' \
    "$WEB/static/src/core/utils/asset_log.js")
assert_doc_cites "OBSERVABILITY cites the trace namespace count" \
    "$OBS_NAMESPACES" '%s namespaces, each with its own flag' OBSERVABILITY.md

# Every namespace must appear as a row of the doc's table, so a namespace added
# without documenting it fails here rather than going unmentioned.
# Anchored on the FULL header: the page carries a second "| Namespace |" table
# (what HOOT cannot see), and a range matching the short prefix counts both.
OBS_ROWS=$(awk '/^\| Namespace \| Flag substring \|/,/^$/' "$DOC/OBSERVABILITY.md" \
    | grep -cE '^\| `')
assert_eq "OBSERVABILITY documents every trace namespace" \
    "$OBS_ROWS" "$OBS_NAMESPACES"

# Category factories are exposed only where callers need them. Count them
# separately from namespaces, including namespaces with private loggers.
OBS_FACTORIES=$(grep -cE '^export (const|function) make\w+Log' \
    "$WEB/static/src/core/utils/asset_log.js")
assert_doc_cites "OBSERVABILITY cites the category factory count" \
    "$OBS_FACTORIES" '%s category factories' OBSERVABILITY.md

# The round-trip claim is about the whole scanned tree, so it is pinned to the
# same src JS count ARCHITECTURE.md cites rather than to a second copy of it.
assert_doc_cites "OBSERVABILITY cites the src JS count for the stamp round-trip" \
    "$SRC_JS" 'all %s files' OBSERVABILITY.md

# Files carrying a hand-placed useRenderCounter. The stamper must skip exactly
# these; if one is added or removed, the doc's guard paragraph is stale.
OBS_HAND=$(grep -rl 'useRenderCounter(' "$WEB/static/src" --include=*.js | wc -l)
assert_doc_cites "OBSERVABILITY cites the hand-instrumented file count" \
    "$OBS_HAND" '%s files place' OBSERVABILITY.md

# addons/web must stay on the no-console list, or the doc's gate posture is wrong.
# Scoped to that array: "addons/web", also appears in the module list above it,
# so an unscoped grep reads 2 and says nothing about the no-console rollout.
assert_eq "web is still on COMMUNITY_NO_CONSOLE_MODULES" \
    "$(awk '/^const COMMUNITY_NO_CONSOLE_MODULES = \[/,/^\];/' "$REPO/eslint.config.mjs" \
        | grep -cE '^\s*"addons/web",')" "1"

# asset_log.js is the one sanctioned console exception in web.
assert_eq "asset_log.js carries the file-level no-console disable" \
    "$(grep -c 'eslint-disable no-console' "$WEB/static/src/core/utils/asset_log.js")" "1"

# The doc's "HOOT cannot see these" table is only trustworthy while the test that
# asserts their absence exists and still asserts it. Bind the claim to its guard.
OBS_TEST="$WEB/static/tests/core/utils/trace_choke_points.test.js"
assert_eq "trace_choke_points suite exists" \
    "$([ -f "$OBS_TEST" ] && echo yes || echo no)" "yes"
assert_eq "trace_choke_points asserts component.mount does NOT fire in HOOT" \
    "$(grep -cE 'trace\["component\.mount"\]\)\.toBe\(.*undefined\)' "$OBS_TEST")" "1"
# rpc.* DOES fire in HOOT, once its guards ask active() rather than enabled().
# Pinned as a positive so the correction cannot silently revert.
assert_eq "trace_choke_points asserts rpc.request DOES fire in HOOT" \
    "$(grep -c 'trace\["rpc.request"\]).toBeGreaterThan(0)' "$OBS_TEST")" "1"
# "at least once", not "exactly once": the Removal plan names every suite a
# second time, and how OFTEN the page mentions a file was never the question.
assert_eq "OBSERVABILITY names the suite that guards its HOOT-visibility table" \
    "$(grep -c 'trace_choke_points.test.js' "$DOC/OBSERVABILITY.md" \
        | awk '{print ($1>0)?1:0}')" "1"

# The service invariant the suite pins: a service entering a wave must resolve.
assert_eq "trace_choke_points pins the service start/started invariant" \
    "$(grep -c 'trace\["service.started"\]).toBe(trace\["service.start"\])' "$OBS_TEST")" "1"

# The doc explains that ?debug=<namespace> cannot work by quoting the server's
# allowlist. Derive it, so the day a mode is added the explanation is re-checked.
# Matched with grep -F: the value is a bracketed list, and rendering it through
# assert_doc_cites' regex would need escaping that hides what is being compared.
OBS_DEBUG_MODES=$(grep -oE '^ALLOWED_DEBUG_MODES = .*' "$WEB/models/ir_http.py")
assert_eq "OBSERVABILITY quotes the real ALLOWED_DEBUG_MODES verbatim" \
    "$(grep -cF "$OBS_DEBUG_MODES" "$DOC/OBSERVABILITY.md")" "1"

# The sink arms off location.search, NOT odoo.debug, precisely because of that
# allowlist. If the arming moves back, the explanation above is wrong.
assert_eq "the sink arms from location.search" \
    "$(grep -c 'globalThis.location?.search?.includes("odoo-trace")' \
        "$WEB/static/src/core/utils/asset_log.js")" "1"

# Every namespace must expose active(); a call site guarding on enabled() alone
# is invisible to the sink, which is what silently killed rpc.* .
assert_eq "asset_log exposes active() alongside enabled()" \
    "$(grep -c 'log.active = () =>' "$WEB/static/src/core/utils/asset_log.js")" "1"
assert_eq "rpc.js guards on active(), not enabled()" \
    "$(grep -c 'rpcLog.enabled()' "$WEB/static/src/core/network/rpc.js")" "0"
assert_eq "rpc.js has both listener guards on active()" \
    "$(grep -c 'if (!rpcLog.active()) {' "$WEB/static/src/core/network/rpc.js")" "2"

# The frozen boot reading must stay pinned to its base commit, never "corrected".
assert_eq "OBSERVABILITY freezes the boot reading to a named base commit" \
    "$(grep -c 'FROZEN at `6216a09c231`' "$DOC/OBSERVABILITY.md")" "1"
assert_eq "OBSERVABILITY freezes the interaction reading to a named base commit" \
    "$(grep -c 'FROZEN at `d9ff46405c9`' "$DOC/OBSERVABILITY.md")" "1"
assert_eq "the interaction reading names the suite that reproduces it" \
    "$(grep -c 'test_what_opening_a_list_view_costs' "$DOC/OBSERVABILITY.md")" "1"
assert_eq "the interaction suite settles boot before resetting the sink" \
    "$(grep -c 'Let boot.s in-flight RPCs settle BEFORE the reset' \
        "$WEB/tests/test_trace_probes.py")" "1"

# The call-site table is what makes a count interpretable: one category bound per
# MODULE means N counts events, not domain objects. Derived per module, because a
# new log() line silently changes what an existing figure means.
OBS_SITES_JS=$(grep -c 'log(' "$WEB/static/src/core/assets.js")
OBS_SITES_TPL=$(grep -c 'log(' "$WEB/static/src/core/templates.js")
OBS_SITES_REG=$(grep -c 'log(' "$WEB/static/src/core/registry.js")
OBS_SITES_ENV=$(grep -c 'log(' "$WEB/static/src/env.js")
OBS_SITES_BOOT=$(grep -c 'log(' "$WEB/static/src/boot/start.js")
assert_doc_cites "OBSERVABILITY cites assets.js's call-site count" \
    "$OBS_SITES_JS" '\| .asset. js \| %s \|' OBSERVABILITY.md
assert_doc_cites "OBSERVABILITY cites templates.js's call-site count" \
    "$OBS_SITES_TPL" '\| .asset. templates \| %s \|' OBSERVABILITY.md
assert_doc_cites "OBSERVABILITY cites registry.js's call-site count" \
    "$OBS_SITES_REG" '\| .asset. registry \| %s \|' OBSERVABILITY.md
assert_doc_cites "OBSERVABILITY cites env.js's call-site count" \
    "$OBS_SITES_ENV" '\| .asset. env \| %s \|' OBSERVABILITY.md
assert_doc_cites "OBSERVABILITY cites boot/start.js's call-site count" \
    "$OBS_SITES_BOOT" '\| .asset. boot \| %s \|' OBSERVABILITY.md

# The campaign namespaces must keep one category per EVENT KIND, which is what
# makes their counts readable without the source open.
assert_eq "service exposes distinct start/started categories" \
    "$(grep -c 'serviceLog("start"\|serviceLog("started"' "$WEB/static/src/env.js")" "2"
assert_eq "view exposes distinct load/loadViews categories" \
    "$(grep -c 'viewLog("load"\|viewLog("loadViews"' "$WEB/static/src/views/view.js")" "2"

# The session double-evaluation LEAD rests on two derivable facts; if either
# moves, the lead has changed and the paragraph must be re-read.
OBS_SESSION_SITES=$(grep -c 'assetLog(' "$WEB/static/src/session.js")
assert_eq "session.js has exactly one assetLog call site (so the count is evaluations)" \
    "$OBS_SESSION_SITES" "1"
# MEMBERSHIPS only. The manifest mentions session.js three times and one is a
# ("remove", ...) directive; counting mentions reads 3 and calls a removal a
# membership, which is the opposite of what that line does.
OBS_SESSION_BUNDLES=$(awk 'prev !~ /"remove"/ && /"web\/static\/src\/session\.js"/ {c++} \
    {prev=$0} END {print c+0}' "$WEB/__manifest__.py")
assert_doc_cites "OBSERVABILITY cites how many bundles session.js is a MEMBER of" \
    "$OBS_SESSION_BUNDLES" 'member of \*\*%s\*\* of web' OBSERVABILITY.md
assert_eq "the third session.js mention is still a remove directive" \
    "$(grep -B2 'web/static/src/session.js' "$WEB/__manifest__.py" | grep -c '"remove"')" "1"
assert_eq "esbuild registers only declared members (the blind spot's mechanism)" \
    "$(grep -c 'for i, asset in enumerate(modules):' \
        "$REPO/odoo/tools/assets/esbuild.py")" "1"

assert_doc_cites "OBSERVABILITY cites the stamped jsfunclen delta" \
    "77 78" '%s -> %s' OBSERVABILITY.md
assert_eq "OBSERVABILITY freezes the full render profile to a base commit" \
    "$(grep -c 'FROZEN at `92a83f0b495`' "$DOC/OBSERVABILITY.md")" "1"

# The control-panel double render is characterised in prose and pinned by a
# suite; bind the two so the prose cannot outlive its guard.
OBS_CP_TEST="$WEB/static/tests/views/control_panel_render_budget.test.js"
assert_eq "control_panel_render_budget suite exists" \
    "$([ -f "$OBS_CP_TEST" ] && echo yes || echo no)" "yes"
assert_eq "it pins the chain at two renders" \
    "$(grep -c 'expect(renders).toBe(2)' "$OBS_CP_TEST")" "1"
assert_eq "it pins that both passes precede every mount" \
    "$(grep -c 'expect(lastRender).toBeLessThan(firstMount)' "$OBS_CP_TEST")" "1"
assert_eq "it pins the empty-then-full model sequence" \
    "$(grep -c '"rows=0",' "$OBS_CP_TEST")" "1"
assert_eq "OBSERVABILITY names the suite that pins the double render" \
    "$(grep -c 'control_panel_render_budget.test.js' "$DOC/OBSERVABILITY.md" \
        | awk '{print ($1>0)?1:0}')" "1"
# SearchBarMenu must stay unconditional, or fact 3 above means something else.
assert_eq "SearchBarMenu is still unconditional in search_bar.xml" \
    "$(grep -c '<SearchBarMenu dropdownState="searchBarDropdownState">' \
        "$WEB/static/src/search/search_bar/search_bar.xml")" "1"

# The double render is the designed cost of lazy model loading. Both halves of
# that mechanism are pinned: if either moves, the explanation above is stale.
assert_eq "useModelWithSampleData still skips the await when lazy" \
    "$(grep -c 'if (options.lazy) {' "$WEB/static/src/model/model.js")" "1"
assert_eq "lazy is still keyed on the view HAVING a control panel" \
    "$(grep -c '!!display.controlPanel' "$WEB/static/src/views/view_utils.js")" "1"
assert_eq "OBSERVABILITY names computeModelOptions as the switch" \
    "$(grep -c 'computeModelOptions' "$DOC/OBSERVABILITY.md")" "1"
# Both latency cases are measured, not argued; the suite must keep covering both.
assert_eq "the budget suite covers the SLOW-load payoff too" \
    "$(grep -c 'a SLOW load mounts the shell first' "$OBS_CP_TEST")" "1"
assert_eq "the slow-load case asserts the shell MOUNTS before the data" \
    "$(grep -c 'e === "MOUNTED:ControlPanel"' "$OBS_CP_TEST")" "1"

# The teardown plan must keep naming every artefact that actually exists, or a
# removal following it leaves orphans behind and a red lane.
for _obs_artefact in \
    "core/utils/asset_log.js" \
    "core/network/rpc.js" \
    "trace_choke_points.test.js" \
    "test_trace_probes.py" \
    "control_panel_render_budget.test.js"; do
    assert_eq "Removal plan names $_obs_artefact" \
        "$(grep -c "$_obs_artefact" "$DOC/OBSERVABILITY.md" | awk '{print ($1>0)?1:0}')" "1"
done
# Scoped to the esm "bundles" list: the name also appears elsewhere in the
# manifest, so an unscoped grep reads 2 and says nothing about ESM membership.
# The duplication is test-mode-only because the bundle is conditionally rendered.
# If that guard moves, the "does not reach production" claim above is stale.
assert_eq "web.assets_tests is still rendered only in test/debug mode" \
    "$(grep -c "'tests' in debug or test_mode_enabled" \
        "$WEB/views/webclient_templates.xml")" "1"
assert_eq "OBSERVABILITY points at the Failure modes row that already owns this" \
    "$(grep -c 'add fingerprint' "$DOC/OBSERVABILITY.md" | awk '{print ($1>0)?1:0}')" "1"
# The lazy-render diagnosis leans on a rule STATE_MANAGEMENT.md owns; if that
# sentence goes, the diagnosis is quoting a doc that no longer says it.
assert_eq "STATE_MANAGEMENT still states that a controller subscribes via useState" \
    "$(grep -c 'installs \*\*no\*\* listener of its own' "$DOC/STATE_MANAGEMENT.md")" "1"
assert_eq "OBSERVABILITY cites that rule rather than restating the mechanism" \
    "$(grep -c 'installs no listener of its own' "$DOC/OBSERVABILITY.md")" "1"
# ESM_BUNDLING documents ?debug=assets, the one namespace that survives the
# server-side allowlist. Pinned so nobody "corrects" it toward the broken form.
assert_eq "ESM_BUNDLING still documents ?debug=assets specifically" \
    "$(grep -c '?debug=assets' "$DOC/ESM_BUNDLING.md" | awk '{print ($1>0)?1:0}')" "1"
assert_eq "ESM_BUNDLING still carries the duplicate-copy failure mode" \
    "$(grep -c 'each load their own copy of the same' "$DOC/ESM_BUNDLING.md")" "1"
assert_eq "web.assets_web is still declared an ESM bundle" \
    "$(awk '/"esm"[[:space:]]*:/,/"dynamic_children"/' "$WEB/__manifest__.py" \
        | grep -c '"web.assets_web",')" "1"
assert_eq "the real-page suite exists and is registered" \
    "$([ -f "$WEB/tests/test_trace_probes.py" ] \
        && grep -c 'from . import test_trace_probes' "$WEB/tests/__init__.py" || echo 0)" "1"

echo ""
echo "================================================================"
if [ "$UPDATED" -gt 0 ]; then
    echo "TOTAL: $PASS passed, $FAIL failed, $SKIP skipped, $UPDATED updated"
    echo "Re-run without --update to confirm the rewrites hold."
else
    echo "TOTAL: $PASS passed, $FAIL failed, $SKIP skipped"
fi
echo "================================================================"
exit $FAIL
