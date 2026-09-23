#!/bin/bash
# partner machine-doc fact-check. Run from any cwd. Read-only.
#
# Assertions DERIVE their expected value from the source tree and check that the
# docs agree, rather than keeping a second copy of every fact that can go stale
# independently. A doc that cites a model, a menu or a test class which no longer
# exists is worse than no doc: it is read as current.
#
# Roots come from this script's own location, so the run always validates the
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

MOD="$(dirname "$SCRIPT_DIR")"                  # <repo>/addons/partner
REPO="$(dirname "$(dirname "$MOD")")"           # <repo>
DOCS=("$SCRIPT_DIR"/*.md)

fail=0
pass=0
skip=0

ok()   { pass=$((pass + 1)); }
bad()  { fail=$((fail + 1)); printf '  FAIL  %s\n' "$1"; }
note() { skip=$((skip + 1)); printf '  SKIP  %s\n' "$1"; }

# Assert every doc mentioning a name uses one that exists in the source.
#
# Matching is word-BOUNDED, not substring: `res_partner_menu` must be cited in
# its own right, and is not satisfied by `res_partner_menu_config` happening to
# contain it. \Q..\E quotes the needle so dotted model names are literal.
assert_doc_cites() {  # <needle> <human description>
    if grep -qP -- "\\b\\Q$1\\E\\b" "${DOCS[@]}"; then ok
    else bad "docs never cite $2 ($1)"; fi
}

printf '== partner machine_doc_v1 factcheck ==\n'

# ---------------------------------------------------------------- structure --
for f in ARCHITECTURE.md TRAPS.md TEST_MAP.md; do
    [ -f "$SCRIPT_DIR/$f" ] && ok || bad "missing $f"
done

# ------------------------------------------------------------------- models --
# Every model this module declares must be documented.
while read -r model; do
    [ -z "$model" ] && continue
    assert_doc_cites "$model" "model $model"
done < <(grep -hoP '_name = "\K[a-z._]+' "$MOD"/models/*.py | sort -u)

# The cohort model is built on mixin.band; ARCHITECTURE.md leans on that.
if grep -q '"mixin.band"' "$MOD/models/res_partner_age_range.py"; then
    assert_doc_cites "mixin.band" "the mixin.band base of the cohort model"
else
    bad "res.partner.age.range no longer inherits mixin.band; ARCHITECTURE.md says it does"
fi

# ------------------------------------------------------------------- fields --
# Every field this module adds to res.partner must be documented.
while read -r fname; do
    [ -z "$fname" ] && continue
    assert_doc_cites "$fname" "field res.partner.$fname"
done < <(grep -oP '^    \K[a-z_]+(?= = fields\.)' "$MOD/models/res_partner.py")

# age_range_id must stay STORED and age must stay UNSTORED -- ARCHITECTURE.md
# explains the asymmetry, and it is the whole reason a cohort may be stored.
if grep -Pzoq 'age_range_id = fields\.Many2one\((?s).*?store=True' "$MOD/models/res_partner.py"; then ok
else bad "ARCHITECTURE.md says age_range_id is stored; it no longer is"; fi
if grep -Pzoq 'age = fields\.Integer\((?s:(?!\).).)*store=True' "$MOD/models/res_partner.py"; then
    bad "ARCHITECTURE.md says age is not stored; it now is"
else ok; fi

# The menu override the module exists for.
if grep -q "def _get_backend_root_menu_ids" "$MOD/models/res_partner.py"; then
    assert_doc_cites "_get_backend_root_menu_ids" "the backend root menu override"
else
    bad "_get_backend_root_menu_ids is gone from models/res_partner.py"
fi

# ------------------------------------------------------------------- xmlids --
# Every action and menu this module declares must be named by the docs.
while read -r xmlid; do
    [ -z "$xmlid" ] && continue
    assert_doc_cites "$xmlid" "xmlid $xmlid"
done < <(grep -hoP '<record id="\K(action_partner|res_partner_age_range)[a-z_0-9]*' \
            "$MOD"/views/*.xml | sort -u)
while read -r xmlid; do
    [ -z "$xmlid" ] && continue
    assert_doc_cites "$xmlid" "menu $xmlid"
done < <(grep -hoP '^\s+id="\K[a-z_0-9]+' "$MOD/views/ir_ui_menu_views.xml" | sort -u)

# The action's own shape, as ARCHITECTURE.md describes it.
view_mode=$(grep -oP '<field name="view_mode">\K[a-z,]+' "$MOD/views/res_partner_views.xml" | head -1)
if [ -n "$view_mode" ]; then
    assert_doc_cites "$view_mode" "action_partner's view_mode"
else
    bad "action_partner has no view_mode in views/res_partner_views.xml"
fi
if grep -q "default_is_company" "$MOD/views/res_partner_views.xml"; then
    assert_doc_cites "default_is_company" "the action context default"
else
    bad "action_partner no longer sets default_is_company; TRAPS.md trap 2 rests on it"
fi

# --------------------------------------------------------------------- data --
# Every demo file registered in the manifest must be documented.
while read -r f; do
    [ -z "$f" ] && continue
    assert_doc_cites "$(basename "$f")" "demo file $f"
done < <(grep -oP "['\"]\Kdata/[a-z_]+\.xml(?=['\"])" "$MOD/__manifest__.py" | sort -u)

# ------------------------------------------------------------ test coverage --
# TEST_MAP must list every test class, and must not list one that is gone.
mapfile -t classes < <(grep -hoP '^class \K(Test\w+)' "$MOD"/tests/test_*.py | sort -u)
for cls in "${classes[@]}"; do
    if grep -qF "$cls" "$SCRIPT_DIR/TEST_MAP.md"; then ok
    else bad "TEST_MAP.md does not list test class $cls"; fi
done
while read -r cited; do
    [ -z "$cited" ] && continue
    if printf '%s\n' "${classes[@]}" | grep -qx "$cited"; then ok
    else bad "docs cite test class $cited, which no longer exists"; fi
done < <(grep -hoP '\bTest[A-Z]\w+' "${DOCS[@]}" | sort -u)

# ------------------------------------------- claims that must stay verified --
# TRAPS trap 2: context defaults are read before ir.default.
create_py="$REPO/odoo/orm/models/mixins/create.py"
if grep -q "if name in context_defaults:" "$create_py"; then ok
else bad "TRAPS.md trap 2 claims context defaults win in default_get; that branch changed"; fi

# TRAPS trap 3: the debug dialog skips falsy values.
debug_js="$REPO/addons/web/static/src/views/debug_items.js"
if grep -q "getDefaultFields()" "$debug_js"; then ok
else bad "TRAPS.md trap 3 names getDefaultFields, which is gone from web's debug_items.js"; fi

# TRAPS trap 3 / TEST_MAP: the tour must target a field the action does not default.
tour="$MOD/static/tests/tours/debug_menu_set_defaults.js"
# Quote-agnostic: 5e691e7d30e reformatted this tour from single to double
# quotes and the assertion, which spelled the literal one way, went red on a
# tour that had not changed what it targets.
if grep -qE "element_field\.value = [\"']website[\"']" "$tour"; then ok
else bad "the set-defaults tour no longer targets website; TRAPS.md trap 2 and TEST_MAP.md say it does"; fi

# TRAPS trap 4: phone_validation supplies the phone entry of _rec_names_search.
pv="$REPO/addons/phone_validation/models/res_partner.py"
if grep -q "phone_mobile_search" "$pv"; then ok
else bad "TRAPS.md trap 4 says phone_validation adds phone_mobile_search to _rec_names_search; it no longer does"; fi

# TRAPS trap 1: demo installability cascades through dependencies.
if grep -q "all(p.demo for p in self.depends)" "$REPO/odoo/modules/module_graph.py"; then ok
else bad "TRAPS.md trap 1 describes demo_installable as all-dependencies; that rule changed"; fi

# TRAPS trap 10: agromarin's cohort file hides under a key the loader ignores.
if grep -qF '"data": []' "$REPO/odoo/modules/module.py"; then ok
else bad "TRAPS.md trap 10 rests on 'data' being the loader's key; it is no longer there"; fi

# ARCHITECTURE: act_window.view records, not view_mode order, drive the mode list.
if grep -q "missing_modes" "$REPO/odoo/addons/base/models/ir_actions_act_window.py"; then ok
else bad "ARCHITECTURE.md describes _compute_views merging view_ids with view_mode; it changed"; fi

# ------------------------------------------- the ACL must reach a screen -----
# A right nobody can be drawn is not a right. This module shipped
# base.group_partner_manager create/write/unlink on the cohorts while the
# Configuration branch holding their menu was gated on base.group_system, so the
# branch was pruned for exactly the group the ACL was written for. Neither the
# ACL nor the menu was wrong alone, which is why only a check spanning both
# catches it.
acl_report=$("$PY" - "$MOD" <<'ACL'
import csv, pathlib, sys
import xml.etree.ElementTree as ET

mod = pathlib.Path(sys.argv[1])
MODEL = "model_res_partner_age_range"
LEAF = "res_partner_age_range_menu"

with (mod / "security/ir.access.csv").open() as fh:
    writers = {
        row["group_id/id"]
        for row in csv.DictReader(fh)
        if MODEL in row["model_id/id"]
        and row["kind"] == "permission"
        and "u" in row["operation"]
    }
if not writers:
    print("BAD|no group is granted write on the cohorts; this check is blind")
    raise SystemExit(0)

root = ET.parse(mod / "views/ir_ui_menu_views.xml").getroot()
menus = {m.get("id"): m for m in root.iter("menuitem")}
if LEAF not in menus:
    print("BAD|%s is gone from views/ir_ui_menu_views.xml" % LEAF)
    raise SystemExit(0)

node, chain = LEAF, []
while node in menus:
    chain.append(node)
    node = menus[node].get("parent")

for name in chain:
    declared = menus[name].get("groups")
    if not declared:
        continue
    allowed = {g.strip() for g in declared.split(",")}
    for writer in sorted(writers - allowed):
        print(
            "BAD|menu %s is gated on %s, which does not admit %s -- the group "
            "ir.access.csv grants write on the cohorts is drawn no screen "
            "to exercise it" % (name, declared, writer)
        )
print("OK|%d menus on the cohort path admit %s" % (len(chain), sorted(writers)))
ACL
)
while IFS='|' read -r verdict detail; do
    [ -z "$verdict" ] && continue
    [ "$verdict" = "OK" ] && ok || bad "$detail"
done <<< "$acl_report"

# --------------------------------------------------- backticked path sweep ----
# odoo/CLAUDE.md holds these directories to an invariant: a backticked path
# asserts that one particular file exists, so a deliberately-absent file -- or
# one in a sibling repo CI never checks out -- is named in PLAIN PROSE instead.
path_report=$("$PY" - "$SCRIPT_DIR" "$MOD" "$REPO" <<'PY'
import pathlib, re, sys

doc_dir, mod, repo = (pathlib.Path(p) for p in sys.argv[1:4])
TOKEN = re.compile(r"`([A-Za-z0-9_./-]+\.(?:py|xml|js|csv|sh))`")
SIBLINGS = ("agromarin/", "agromarin-knowledge/", "enterprise/", "design-themes/")

if not (repo / "odoo-bin").exists():
    print("BAD|repo root misresolved (no odoo-bin at %s) -- sweep would be blind" % repo)
    raise SystemExit(0)

for doc in sorted(doc_dir.glob("*.md")):
    for token in sorted({m.group(1) for m in TOKEN.finditer(doc.read_text())}):
        if token.startswith(SIBLINGS):
            print(f"BAD|{doc.name} backticks {token}, which lives in a sibling "
                  f"checkout CI does not have -- name it in plain prose")
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

printf '\n%d passed, %d failed, %d skipped\n' "$pass" "$fail" "$skip"
[ "$fail" -eq 0 ]
