#!/bin/bash
# Website module architecture fact-check (round 1 — 2026-07-21)
# Run from any cwd. Read-only. CI-safe.
# Verifies the counts and structural claims made in this machine_doc_v1/ set
# (ARCHITECTURE, DIRECTORY_MAP, MODEL_MAP, ROUTE_MAP, CONVENTIONS, INTERACTIONS,
# TEST_TAGS) against the live source tree. Symbol citations are existence checks,
# not pinned line numbers, so they survive refactors.

set -u
# Derive the root from this script's own location. It was hardcoded to
# `/home/marin/Odoo/addons/odoo/addons/website`, a path that exists in no
# checkout -- one `addons/` too many -- so every path-based assertion resolved
# against nothing and the run reported 42 failures with 1 pass. A harness whose
# root is a literal validates the tree it was written on, or, as here, no tree
# at all; `addons/web/machine_doc_v1/factcheck.sh` carries the same note for the
# same reason.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB="$(dirname "$SCRIPT_DIR")"                 # <repo>/addons/website
PASS=0
FAIL=0

DOC="$SCRIPT_DIR"

assert_eq() {
    local name="$1" actual="$2" expected="$3"
    if [ "$actual" = "$expected" ]; then
        echo "PASS: $name [$actual]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — expected [$expected] got [$actual]"; FAIL=$((FAIL+1))
    fi
}
# Derive the expected value from the tree and assert the DOCS cite it, instead
# of holding a second copy here. `assert_eq <measured> <literal>` makes this
# script a place figures rot: the two below read 45 and 217 against a real 47
# and 218, and the same numbers were restated across six doc sites, so one fact
# had eight copies and no owner. With this, the measurement lives once.
assert_doc_cites() {
    # $1 = human name, $2 = actual value, $3 = printf pattern with %s, $4 = doc
    local name="$1" actual="$2" pat="$3"
    local rendered; rendered=$(printf "$pat" "$actual")
    local hits; hits=$(grep -cE "$rendered" "$DOC/$4" 2>/dev/null); hits=${hits:-0}
    if [ "$hits" -ge 1 ]; then
        echo "PASS: $name [doc cites $actual]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — filesystem says $actual, $4 does not cite it"; FAIL=$((FAIL+1))
    fi
}
assert_range() {
    local name="$1" actual="$2" lo="$3" hi="$4"
    if [ "$actual" -ge "$lo" ] && [ "$actual" -le "$hi" ]; then
        echo "PASS: $name [$actual in $lo..$hi]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — expected $lo..$hi got [$actual]"; FAIL=$((FAIL+1))
    fi
}
assert_file() {
    local name="$1" path="$2"
    if [ -e "$path" ]; then
        echo "PASS: $name [exists]"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — missing [$path]"; FAIL=$((FAIL+1))
    fi
}
assert_grep() {
    # assert_grep <name> <pattern> <file>  — pattern must be found
    local name="$1" pat="$2" file="$3"
    if grep -qE "$pat" "$file" 2>/dev/null; then
        echo "PASS: $name"; PASS=$((PASS+1))
    else
        echo "FAIL: $name — pattern not found: $pat in $file"; FAIL=$((FAIL+1))
    fi
}

# ------- Module identity / manifest -------
assert_grep "Manifest depends on html_builder" '"html_builder"' "$WEB/__manifest__.py"
assert_grep "Manifest declares geoip2 external dep" 'geoip2' "$WEB/__manifest__.py"
assert_grep "web.assets_frontend bundle present" 'web.assets_frontend' "$WEB/__manifest__.py"
assert_grep "builder-iframe bundle present" 'website.assets_inside_builder_iframe' "$WEB/__manifest__.py"

# ------- Python surface -------
assert_eq "Controller files (incl __init__)" \
    "$(ls "$WEB"/controllers/*.py | wc -l)" "9"
assert_eq "Controller files (excl __init__)" \
    "$(ls "$WEB"/controllers/*.py | grep -vc __init__)" "8"
assert_eq "Model files" \
    "$(ls "$WEB"/models/*.py | wc -l)" "45"
assert_eq "Wizard py files (excl __init__)" \
    "$(ls "$WEB"/wizards/*.py | grep -vc __init__)" "4"
PY_TESTS=$(ls "$WEB"/tests/*.py | wc -l)
assert_doc_cites "ARCHITECTURE cites the real Python test-file count" \
    "$PY_TESTS" '%s Python test files' ARCHITECTURE.md
assert_doc_cites "TEST_TAGS cites the real Python test-file count" \
    "$PY_TESTS" '%s `.py` files' TEST_TAGS.md
# ARCHITECTURE.md states this twice -- a directory row and a File Counts row.
# Pin BOTH: guarding one leaves the other free to drift, which is how a mutation
# of the File Counts row passed a green run while the number was wrong.
assert_doc_cites "ARCHITECTURE File Counts row cites the real Python test count" \
    "$PY_TESTS" '\| Python \(tests\) \| %s \|' ARCHITECTURE.md

# ------- ORM model class count (all ^class in models/ + wizards/, minus the two
# non-ORM classes: PageCannotBeCached(Exception) + ModelConverter) -------
#
# DERIVED, NOT DECLARED. This was a literal 62 in the script while three doc
# sites restated the same 62, so the script was a fourth copy of the tree and
# the only one that failed when the tree moved -- it went red at 61 saying
# nothing about which of the three restatements was now wrong. The measurement
# lives here once and the three sites are each pinned to it, the same shape
# `PY_TESTS` already uses above.
MODEL_CLASSES=$(grep -rhE '^class ' "$WEB"/models/*.py "$WEB"/wizards/*.py \
    | grep -vcE 'Exception\)|ModelConverter\)')
assert_doc_cites "MODEL_MAP cites the real ORM model-class count" \
    "$MODEL_CLASSES" '\*\*%s model' MODEL_MAP.md
assert_doc_cites "ARCHITECTURE models/ row cites the real model-class count" \
    "$MODEL_CLASSES" '%s model classes \(website, mixins' ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE File Counts row cites the real model-class count" \
    "$MODEL_CLASSES" '\| Python \(models\) \| [0-9]+ files \(%s model classes\) \|' ARCHITECTURE.md

# ------- Signature model / methods exist -------
assert_grep "website model _name" '_name = ["'\'']website["'\'']' "$WEB/models/website.py"
assert_grep "website_domain() helper exists" 'def website_domain' "$WEB/models/website.py"
assert_grep "get_current_website() exists" 'def get_current_website' "$WEB/models/website.py"
# COW/COU engine lives in ir_ui_view.py write/unlink
assert_grep "ir_ui_view extends seo.metadata (COW host)" 'website.seo.metadata' "$WEB/models/ir_ui_view.py"
# Published mixin
# mixins.py was split one-model-per-file and the models renamed mixin.<what
# they add> (coding_guidelines.rst 5.37 / §2.2.1), so each is asserted where it
# now lives rather than in the file that used to hold them all.
assert_grep "mixin.website.published defined" 'mixin.website.published' "$WEB/models/mixin_website_published.py"
assert_grep "mixin.website.searchable defined" 'mixin.website.searchable' "$WEB/models/mixin_website_searchable.py"
# Full-page cache
assert_grep "website.page full-page cache" '_get_response_cached' "$WEB/models/website_page.py"
# Cookie barrier in ir_qweb
assert_grep "ir_qweb cookie/url post-processing" '_post_processing_att' "$WEB/models/ir_qweb.py"
# Visitor UTC-explicit SQL
assert_grep "visitor SQL is UTC-explicit" "at time zone 'UTC'" "$WEB/models/website_visitor.py"

# ------- Routes -------
assert_grep "form-builder route present" '/website/form' "$WEB/controllers/form.py"
assert_grep "sitemap route present" '/sitemap.xml' "$WEB/controllers/main.py"
assert_grep "model-page route present" '/model/' "$WEB/controllers/model_page.py"

# ------- JS surface -------
# Derived and asserted against every site that states them, never a literal
# here: a literal only ever pins the script to itself, and says
# nothing about whether the documents still agree with the tree. Each citation
# gets its own anchored pattern, for the reason spelled out below: the check is
# an EXISTENCE test, so a loose pattern is satisfied by whichever site is still
# right while the other rots.
JS_SRC=$(find "$WEB/static/src" -name '*.js' -type f | wc -l)
JS_SRC_DIRS=$(find "$WEB/static/src" -type d | wc -l)
assert_doc_cites "DIRECTORY_MAP cites the real static/src JS count" \
    "$JS_SRC" '\*\*%s `\.js` files\*\*' DIRECTORY_MAP.md
assert_doc_cites "ARCHITECTURE cites the real static/src JS count (subsystem row)" \
    "$JS_SRC" '%s JS across' ARCHITECTURE.md
assert_doc_cites "ARCHITECTURE cites the real static/src JS count (figures table)" \
    "$JS_SRC" 'JavaScript \(src\) \| %s across' ARCHITECTURE.md
assert_doc_cites "DIRECTORY_MAP cites the real static/src directory count" \
    "$JS_SRC_DIRS" '\*\*%s directories\*\*' DIRECTORY_MAP.md
assert_doc_cites "ARCHITECTURE cites the real static/src directory count" \
    "$JS_SRC_DIRS" 'across %s directories' ARCHITECTURE.md
JS_TESTS=$(find "$WEB/static/tests" -name '*.js' -type f | wc -l)
assert_doc_cites "ARCHITECTURE cites the real static/tests JS count" \
    "$JS_TESTS" '%s `.js` \(HOOT suites' ARCHITECTURE.md
# TEST_TAGS states it TWICE, and each pattern is anchored to its own sentence.
# `assert_doc_cites` is an EXISTENCE check -- it asks whether the document
# mentions the value anywhere -- so a pattern loose enough to match either site
# is satisfied by the one that is still right, and mutating the other passes a
# green run. Verified: with a bare '%s `.js`' pattern, changing line 5 to 217
# did not fail. A pin per site, or the pin is a coin flip over which site rots.
assert_doc_cites "TEST_TAGS header cites the real static/tests JS count" \
    "$JS_TESTS" '\(`static/tests/`, %s `\.js`\)' TEST_TAGS.md
assert_doc_cites "TEST_TAGS body cites the real static/tests JS count" \
    "$JS_TESTS" '^%s `\.js` files\.' TEST_TAGS.md
assert_eq "tour definitions (static/tests/tours)" \
    "$(find "$WEB/static/tests/tours" -name '*.js' -type f | wc -l)" "86"
assert_doc_cites "ARCHITECTURE cites the real *.edit.js variant count" \
    "$(find "$WEB/static/src" -name '*.edit.js' -type f | wc -l)" \
    '^\| JavaScript \(`\.edit\.js` variants\) \| %s \|' ARCHITECTURE.md
assert_range "snippet s_* directories" \
    "$(find "$WEB/static/src/snippets" -maxdepth 1 -type d -name 's_*' | wc -l)" "60" "72"

# ------- Interaction framework -------
assert_grep "Interaction base imported from @web/public/interaction" \
    'from "@web/public/interaction"' "$WEB/static/src/interactions/anchor_slide.js"
assert_range "public.interactions registrations" \
    "$(grep -rho 'registry.category("public.interactions").add(' "$WEB/static/src" | wc -l)" "30" "45"
assert_range "public.interactions.edit registrations" \
    "$(grep -rho 'registry.category("public.interactions.edit").add(' "$WEB/static/src" | wc -l)" "35" "50"
assert_grep "edit-service builds editable interactions" \
    'buildEditableInteractions' "$WEB/static/src/core/website_edit_service.js"
assert_file "systray JS lives in website_preview (not systray_items/)" \
    "$WEB/static/src/client_actions/website_preview/website_systray_item.js"
assert_eq "systray_items/ has no JS (SCSS only)" \
    "$(find "$WEB/static/src/systray_items" -name '*.js' 2>/dev/null | wc -l)" "0"

# ------- Builder / client action -------
assert_grep "WebsiteBuilder extends html_builder Builder" \
    'website_builder' "$WEB/__manifest__.py"
assert_file "website_preview client action exists" \
    "$WEB/static/src/client_actions/website_preview/website_builder_action.js"

# ------- machine_doc_v1 self-consistency -------
MD="$WEB/machine_doc_v1"
for doc in ARCHITECTURE DIRECTORY_MAP MODEL_MAP ROUTE_MAP CONVENTIONS INTERACTIONS TEST_TAGS; do
    assert_file "machine_doc_v1/$doc.md present" "$MD/$doc.md"
done

echo
echo "======================================"
echo "PASS=$PASS  FAIL=$FAIL"
echo "======================================"
[ "$FAIL" -eq 0 ]
