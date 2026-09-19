# test_lint — map

The fork's own gates: the rules no general linter knows. 9410 lines and no map
until now, which is why `CLAUDE.md` §10 makes a module's machine doc the first
pre-work step.

Every figure below is derived by `odoo/addons/test_lint/machine_doc_v1/factcheck.sh` from the tree, never restated
here as a literal that can drift.

## Two halves

| | |
|---|---|
| **`_rules.py`** | the vocabulary: what a rule *is* -- name, short code, advice -- and which checker emits it. Adding a rule is an entry here and nothing else. |
| **`_py_scan.py`** | the engine: corpus, parallel scan, caching, suppression. Owns nothing about any individual rule. |

A rule used to be spelled in six places and three tests existed only to keep the
copies agreeing. `test_python_lint.py` iterates the registry.

## Where the floors live

**Not in Python.** `LintCase.assert_ratchet` takes a *gate name* and reads
`tests/floors.json` -- one integer per gate, hand-edited, no entry meaning zero;
handed an integer it raises. The ratchet is exact: above the floor fails, below
it fails until the floor is lowered in the same change.

This module was edited as a shared ledger: 24 of its last 40 commits changed
nothing in it but an integer and the comment above it.

Five gates carry a floor: `lint_docstring` (a one-sided ratchet that
reads 32 only on a fuller install), `bundle_double_eval` (ESM bundles that
evaluate twice), the migration ledger `lint_credential_storage`, whose floor
is the columns still to move into the vault, `lint_receiver_fail_open`, whose
floor is the machine routes still to put behind an inbound gate, and
`lint_stored_related`, the stored copies of a related value still to convert
-- the one AST rule with a floor. Everything else -- every other AST rule,
every XML rule, the manifest and record-order gates -- is a hard zero. `n-plus-one-query` reached
zero on 2026-09-12 by reading each of its 295 sites: a loop over the records
is hoisted, a loop that runs one query per distinct key (company, model,
timezone, merged domain, a single-record wizard) carries `# noqa: E8507 -
<why>` naming the key.

## The checkers

Pure AST, stdlib only, no odoo import — so they are unit-testable without a
database, and `test_checkers.py` does exactly that.

| file | rule(s) |
|---|---|
| `_checker_sql.py` | `sql-injection` |
| `_checker_gettext.py` | `gettext-variable`, `gettext-placeholders`, `gettext-repr`, `missing-gettext`, `gettext-developer-error` |
| `_checker_batch.py` | `n-plus-one-query` |
| `_checker_unlink.py` | `raise-unlink-override` |
| `_checker_orm_import.py` | `orm-import` |
| `_checker_onchange.py` | `onchange-domain` |
| `_checker_config_patch.py` | `config-chainmap-patch` |
| `_checker_shadowed_def.py` | `shadowed-definition` |
| `_checker_noqa_rationale.py` | `noqa-rationale` |
| `_checker_translated_unique.py` | `unique-over-translated-column` (cross-unit) |
| `_checker_null_unique.py` | `null-exempt-composite-unique` (cross-unit) |
| `_checker_manifest.py` | the manifest value rules behind `lint_manifest_value`; not in `_rules.py`, because a manifest is a dict, not a Python unit |
| `_checker_pep649.py` | annotation resolution, used by `test_pep649` |
| `_checker_tax_company.py` | `tax-company-singular` |
| `_checker_http_json.py` | `http-json-string` |
| `_checker_egress.py` | `raw-egress`, `secret-in-environ` |
| `_checker_credential_storage.py` | `credential-storage` |
| `_checker_receiver.py` | `receiver-fail-open` |
| `_checker_row_counter.py` | `row-counter-in-test` |
| `_checker_field_declaration.py` | `field-redeclared`, `default-evaluated-at-import`, `selection-duplicate-key`, `field-hook-prefix`, `field-positional-argument`, `field-attribute-order`, `dead-field-attribute`, `stored-related` |

`tax-company-singular` (E8514) catches `.tax_ids.filtered(lambda t: t.company_id)`
and the five other tax field names. `account.tax` carries `company_ids`, a
many2many, so the singular reads `AttributeError` at runtime rather than an empty
recordset — the checker only fires inside a `filtered` lambda over a tax field,
where the parameter is known to be a tax.

`row-counter-in-test` (E8516) catches a read of `cr.sql_log_count` in a test file.
That counter is incremented by the ROW count (`odoo/db/metrics.py`, `count=` from the COPY
path) beside `sql_statement_count += 1`, so a correctly batched insert of N rows scores
N and a per-record budget measured with it carries headroom proportional to the rows
each record writes -- which is the regression the budget exists to catch. The rule is
syntactic on purpose: an AST predicate for "measures a batch write" missed the case that
matters, because the write is usually inside the method under measurement rather than in
the test body. Stores are skipped, so a fake cursor defining the attribute is not a
finding, and the five tests that assert the counter itself carry
`# noqa: E8516`.

`raw-egress` (E8518) counts every call that leaves Odoo without `ir.egress`, base's
one outbound pipeline: `requests` verbs and sessions, `httpx`,
`urllib.request.urlopen`, zeep's `Transport` and `boto3` clients, with import aliases
followed. It skips tests and nothing else: `integration` builds its sessions on
`ir.egress` like any other addon, and the pipeline's own transport lives in
`odoo/libs/guarded_http.py`, outside every addon. It reached zero on 2026-09-13: a call
that cannot take an `ir.egress` session -- a script run beside the server, the IoT box,
botocore, a zeep transport handed that session -- carries `# noqa: E8518 - <why>`.
`secret-in-environ` (E8519) is
held at zero: a secret-named key written into `os.environ`, which every later
subprocess of the worker inherits, instead of into the child's own `env=`.

`credential-storage` (E8520) is the credential_storage gate that went with
`tooling/`, ported: a stored `Char`/`Text` field whose name reads as a third-party
secret, outside `credential`, with the old per-field judgements for share tokens,
published keys, identifiers, hashes and cursors kept. It adds what the old gate
never saw: a settings field with `config_parameter=`, which keeps its value in
clear in `ir.config_parameter`. The floor is the backlog of fields still to move
into the vault.

`receiver-fail-open` (E8528) counts routes that take calls from machines without
resolving the caller: `auth="public"` or `"none"` with `csrf=False`, whose handler --
following the controller's own `self.` calls -- reaches none of the inbound gate's
entry points (`inspect_inbound_request`, `_check_inbound_request`, `check_inbound_auth`,
`_check_webhook_request`, `admit`, `_admit_mini_app_call`). Such a route answers an
unknown caller without refusing it, throttles nobody and records nothing. The floor
is P3 and P5 of the external-connections plan still to do: payment provider and POS terminal callbacks, Peppol and the other EDI
webhooks, IoT, SMS. A route that must stay open carries `# noqa: E8528 - <why>`.

`http-json-string` (E8515) catches `return json.dumps(...)` inside a route whose
`type` is `"http"` or absent. The string goes out as `text/html`, and the client's
`post()`/`get()` helpers in `@web/core/network` refuse JSON typed that way, so the
route works from Python and fails from every browser -- the website form was one.
`type="jsonrpc"` routes are not its business; the spelling it wants is
`request.prepare_json_response(payload)`.

`shadowed-definition` (E8513) runs `_anywhere` rather than inside addons, because
a member defined twice is dead code wherever it sits: Python keeps the last
definition and the earlier one still reads as live. `stock.product_template` is
the case it was written for — two `_search_variant_quantity`, the live one calling
a `_get_domain_locations` that no longer existed, so every quantity search on a
template raised while a correct implementation sat 60 lines above it, unreachable.
Four repetitions are legitimate and exempt: a `@typing.overload` stack, a
`@property` group with its setter/deleter, a `@singledispatchmethod` and its
`@x.register` implementations, and definitions guarded by `if`/`try` such as
`if TYPE_CHECKING`, which are alternatives rather than overwrites.

`_checker_field_declaration.py` reads every `name = fields.X(...)` in a class
body, outside tests. `field-redeclared` (E8521) is the assignment twin of
`shadowed-definition`: the same name bound twice in one class body, the first
declaration dead. `default-evaluated-at-import` (E8522) is `default=` handed
the *result* of a clock or a random source -- `fields.Date.today()`,
`datetime.now()`, `uuid4()`, `_("...")` -- which ran once when the module was
imported, so every record gets the value the server started with; the enterprise
tree carried five. `selection-duplicate-key` (E8523) is a literal selection
list repeating a key: `Selection.__init__` turns the list into a dict, so the
last label wins and the others are dead (`l10n_co_edi` shipped `"23"` twice,
the second marked inactive and never shown). `field-hook-prefix` (E8524) is
`compute=`, `inverse=`, `search=` or `selection=` naming a method outside the
family §2.4.1 of `doc/coding_guidelines.rst` reserves for it, so a reader --
and the naming gates -- can tell a hook from a helper; the hook exists, the
name does not say so.

The same file is the vocabulary for how a declaration is *written*:
`POSITIONAL_PARAMETERS` names each field class's positional parameters and
`FIELD_ATTRIBUTE_ORDER` the order its keywords are read in (what the field is,
what it says, its shape, how its value is produced, how it is stored, what it
points at, who tracks it, then `groups=` second to last and `help=` last). `field-positional-argument` (E8525) is any positional
argument -- a bare string that only the signature can tell is a label, a
comodel or a selection; `field-attribute-order` (E8526) is keywords out of
that order, or two or more sharing a line; `dead-field-attribute` (E8527) is
an attribute setup ignores: `index=` where there is no column, `precompute=`
without `store=True`, `compute=` beside `related=`; `stored-related` (E8529) is
`related=` with `store=True` on anything but a Binary or an Image -- the one
floored rule of this checker, since the copies exist and are converted module by
module. The fixer is
`_sort_field_attributes.py`, in the table below. `doc/coding_guidelines.rst` §2.3
states the rule.

**What the AST cannot see, `test_field_declarations.py` reads off the
registry** (post-install): whether the method a hook names exists at all
(`lint_field_hook_missing`; `resolve_mro` finds nothing at setup and the first
read raises `AttributeError`, which is how three fork-made mixins declared
seventeen computed fields whose computes only their hosts supply), whether an
`@api.onchange` or `@api.constrains` parameter is a field of a concrete model
(`lint_field_trigger_unknown`; the ORM logs one warning and never fires the
method for that name), and whether a `string=` restates the label
`Field._setup_attrs__` derives from the name -- strip `_id`/`_ids`, `_` to a
space, title-case -- with no lower definition in the MRO saying otherwise
(`lint_field_string_restates_label`). That last one is MRO-aware on purpose: an
`_inherit` class may restate the auto label to override a base class's
different string, and four did (`res.users.create_date` in `website_forum`
over `base`'s "Created on" among them). A syntactic reading cannot tell those
from the 4,205 that said nothing, so the registry decides and the syntactic
scanner is not given the rule.

`unreadable-source` has no checker file of its own: the engine emits it when a
file cannot be parsed or tokenised. Both used to be swallowed, and a file whose
comments cannot be read is one whose every waiver is silently inert.

## The XML rules

The same two halves, for data files. **`_xml_rules.py`** is the vocabulary: an
`XmlRule` is a name, an advice and a check -- a function over one parsed
`DataFile` and a cross-file `Context` (the `_name`s every module's Python
declares, the module names on the addons path). **`_xml_scan.py`** parses every
`core_data_files()` entry whose root is `<odoo>`, `<data>` or `<openerp>` once,
records whether a manifest lists it and whether the module's Python names it,
and runs every rule. `test_xml_lint.py` iterates the registry against
`lint_xml_<rule>` in `floors.json`, and carries a planted positive and a clean
negative for every rule, so no rule can go vacuous unnoticed.

| rule | what it catches |
|---|---|
| `attributes-spec-child` | an element other than `<attribute>` under `position="attributes"`. `_apply_attributes` iterates `spec.iter("attribute")`, so a `<field>` there is never added and a `<t t-if>` around an attribute guards nothing -- `website_sale` applied its accordion classes on mobile because of one. |
| `duplicate-field` | one `<field name>` twice in a record. The loader keeps the last; the first is dead. 34 records carried one. |
| `expression-syntax` | `domain`, `context`, `options`, `invisible`, `readonly`, `required`, `column_invisible`, `filter_domain` inside a model-backed view arch that do not parse as Python, or are empty. `%(xmlid)d` is substituted before parsing; QWeb templates are out of scope, because `required=""` is an HTML boolean there. |
| `eval-syntax` | an `eval=` that does not parse. `eval=""` is the case: the loader treats it as absent and reads the element text. |
| `xpath-syntax` | an `expr=` lxml cannot compile (`hasclass()` shimmed). |
| `tree-view` | a `<tree>` element, or `tree` in a `view_mode`. |
| `removed-attribute` | `attrs=` or `states=` inside a view arch. |
| `kanban-box` | `t-name="kanban-box"`, the pre-17.0 card name. |
| `search-item-name` | a `<filter>` without `name`, or a search `<group>` with `string`/`expand`. |
| `deprecated-output-directive` | `t-esc` / `t-raw`; `ir.qweb` logs a deprecation per compile. Fixer: `_modernize_output_directives.py`. |
| `legacy-x2many-command` | an `eval` list holding `(6, 0, ...)`-style tuples; `Command` is in the eval context. Fixer: `_modernize_commands.py`. |
| `menuitem-placement` | a `<menuitem>` in a file whose name does not say `menu`. Fixer: `_relocate_menus.py`. |
| `data-root` | a root element other than `<odoo>`. |
| `orphan-data-file` | a data file no manifest lists and no Python of its module names by path. `addons/marketing_card/data/utm_source_data.xml` was one: the record it declares never existed, and two `env.ref(..., raise_if_not_found=False)` degraded silently around it. |
| `unknown-model` | `<record model>`, a view's `model`, an action's `res_model` naming no `_name` in the tree. |
| `optional-value` | `optional=` outside `show` / `hide` / `conditional`. |
| `kanban-template-scope` | a kanban entry template reading a `t-set` from a sibling template. |
| `groupby-filter-domain` | any `domain` on a group-by `<filter>`; `classifyByContext()` promotes it and `visitFilter()` never reads the domain again. |
| `duplicate-arch-name` | two definitions (not inheritance locators) sharing a `name` in one arch, for `filter`, `page`, `group`, `notebook`. An xpath by that name reaches only the first; two filters with one name are toggled together by `search_default_<name>` -- `maintenance`'s dashboard "Done" link activated a "Done" and a "Ready" filter in different groups and ANDed to nothing. |
| `special-button-type` | `special=` with `type=`: the special is handled first, the type is dead. `name=` stays, it is an xpath and tour target. |
| `readonly-duplicates-invisible` | `invisible="X" readonly="X"`: a field is never edited while hidden, so the readonly is dead. |
| `nolabel-outside-group` | `nolabel=` on a form field outside a `<group>` or a `<setting>`, the only two places `form_compiler.js` reads it. |
| `column-invisible-outside-list` | `column_invisible=` in a form: a literal is promoted to `invisible=`, an expression is never evaluated and the field shows. |
| `boolean-spelling` | `invisible="true"` and friends: py.js aliases `true`, Python does not; the guide writes conditions as Python. |

The last three moved here from `test_view_hygiene.py`, which keeps the two
gates that need the registry (`OrphanLabelLinter`, `ActWindowViewOrderLinter`).

`test_record_refs.py` judges every reference shape `odoo/tools/convert.py`
resolves at load: `ref=`, `ref()` inside `eval`, `context`, `search` and
`t-value`, a bare `uid=`, `<menuitem parent/action/groups>`, `<template
inherit_id/website_id/groups>`, `<delete id>`, and `%(xmlid)d` inside a
`type="xml"`/`type="html"` field or a `<template>` (with `%%` honoured). Its
declaring tags are the loader's -- `record`, `template` (by `id` or `t-name`),
`menuitem`, `asset`. What the ORM mints is derived, not skipped: a record of a
model with `_inherits` also declares `<xmlid>_<parent_model>`, every manifest
`category` declares its `base.module_category_*` chain the way
`odoo/modules/db.py` does, and `model_<x>` / `module_<x>` resolve only when
`<x>` is a declared model or a module on the path. `field_`, `selection_` and
`constraint_` still need the registry and stay undecidable.

## The fixers, and what they may not change

| | invariant | why |
|---|---|---|
| `_pretty_xml.py` | `_xml_identity.is_faithful` | order-**preserving**: it reindents, wraps, and writes the XML declaration on line 1 -- the one thing it adds, which is why `comparable` no longer counts the declaration as identity (136 files gained it on 2026-09-12) |
| `_sort_xml_records.py` | `_xml_identity.preserves_content` | order-**insensitive**: reordering is the job. Inside a model-backed view arch it also orders the attributes of every view-semantic element (`ARCH_TAGS`, HTML left alone) by `ARCH_ATTRIB_ORDER`: what it is (`name`, `for`, `expr`, `position`, `special`, `type`), what it says (`string`, `placeholder`, `help`, `confirm`), how it renders (`widget`, `icon`, `col`, `nolabel`, `optional`, ...), what data it takes (`domain`, `context`, `options`, `default_order`, `editable`, ...), when it applies (`groups`, `invisible`, `column_invisible`, `readonly`, `required`), then `class`/`style`, then the rest alphabetically -- so the conditions a reviewer scans for sit together. Core had no such order (26,384 of 26,848 arch fields put `name` first and agreed on nothing else); the sweep moved 17,394 lines in 1,272 files. `FIELD_ORDER` is one list per technical model (22, `ir.ui.view` to `mail.message.subtype`), every name pinned to the registry by `test_fixers.py` -- the canon carried four fields a rename had deleted (`groups_id` three times, `print_wizard`, `filter`, `mobile_view_filter`) and sorted nothing for them. A comment travels with the field it precedes; any other child keeps its place after the fields, so the sorter settles every record `test_xml_records.py` reports. |
| `_sort_manifests.py` | `normalize` then a round-trip: the rendered dict must equal `normalize(data)` | value-**normalising**: see below |
| `_modernize_output_directives.py` | `is_rename_only`: the two documents, walked in parallel, differ in nothing but the renamed attribute keys | value-**renaming**: `t-esc` becomes `t-out` in place, which is what `ir.qweb` and Owl both compile it to. `t-raw` is not renamed -- it skips escaping, so `t-out` could change output -- and an element carrying both is left for a human. Swept 2026-09-12: 115 files, `deprecated-output-directive` 500 -> 0; one inheritance locator (`sale_timesheet`, `td[t[@t-esc=...]]`) followed the rename by hand. |
| `_relocate_menus.py` | a fresh install before and after produces the same `ir.ui.menu` rows (xmlid, name, parent, action, sequence, groups) -- checked by installing every changed module from two worktrees and diffing the dump, not by the script | structure-**moving**: every top-level `<menuitem>` of a module, with its subtree and the comments before it, goes to the module's `views/` menus file, named after the module with a `_menus` suffix, in manifest load order (an existing menu file's own menus interleaved by their original position). The file is listed after every file that defines an action a menu names and before the first staying file that needs a menu -- a `ref()` to it, an `ir.ui.menu` record redefining it by `id` -- which is the end of `data` when nothing does. Refuses a module when no such position exists, when a menuitem sits under `noupdate`, or when the module's Python names a menu (`--python-refs-verified <module>` once you have read that none runs while data loads). A source file left with no element is deleted with its manifest line. Swept 2026-09-12: 98 modules; `event`'s six `ir.ui.menu` action patches became the menuitems' own `action=`, `point_of_sale` and `website` carry their menu-bound client actions in the menus file, `hr` swapped two manifest lines; `menuitem-placement` 333 -> 0. |
| `_sort_field_attributes.py` | the module's AST with every field call normalised -- positionals mapped to their keywords, keywords sorted by name -- is identical before and after, checked per file before it is written | spelling-**normalising**: every positional argument becomes the keyword `POSITIONAL_PARAMETERS` names, keywords take `FIELD_ATTRIBUTE_ORDER`, two or more go one per line with a trailing comma and `ruff format` lays the file out. A comment trailing an argument travels with it, one on a line of its own with the argument that follows; a `*args`, a `**kwargs` or a comment after the last argument is declined and reported. Swept 2026-09-13: 12,060 declarations in 2,024 core files, none declined; `field-positional-argument` 5,948 -> 0, `field-attribute-order` 7,525 -> 0. |
| `_drop_field_labels.py` | the registry's `field.string` for every installed field, before and after, is identical -- the fixer removes only what `get_attrs` would have derived anyway, and the check is a fresh registry over the rewritten source | value-**dropping**: `string=` (or the positional label) whose value equals the auto label and whose every lower MRO definition says nothing else, located through the built registry (`-d <db>`), so it is exact rather than syntactic; touched files are re-run through `ruff format`. Swept 2026-09-13 on a 645-module community install: `lint_field_string_restates_label` 4,205 -> 0. |
| `_modernize_commands.py` | `is_equivalent`: both the original and the rewrite are mapped to `(code, id, values)` tuples and compared as `ast.dump` | value-**rewriting**: `(6, 0, ids)` becomes `Command.set(ids)` inside an `eval` list, and the sub-commands inside a `create`/`update` dict with it. No evaluation, so it runs without odoo-bin; a refusal is a rewrite the round-trip would not reproduce. Swept 2026-09-12: 312 files, `legacy-x2many-command` 1,408 -> 0. |

`_xml_sweep.py` runs a fixer over every data file **once**; the gates read the
result rather than each making their own pass.

## Manifests: one vocabulary, one fixer, two gates

`_sort_manifests.MANIFEST_KEY_ORDER` is the whole vocabulary: every key the
loader reads (`_DEFAULT_MANIFEST` plus `author`, `license`, `icon`, the
app-store fields, `oca_data_manual` for agromarin's seed tooling) in canonical
order. `DEPRECATED_KEYS` names the four the loader defaults but nothing reads
(`init_xml`, `update_xml`, `demo_xml`, `test`). A key in neither is unknown.
`test_manifests` pins that the two sets together cover `_DEFAULT_MANIFEST`.

`normalize(module, data)` is what the fixer may change, and all of it is
loader-neutral or a stated `doc/coding_guidelines.rst` §1.2 rule: keys go to
canonical order; a key restating its `_DEFAULT_MANIFEST` value is dropped
(`version` excepted, the guide wants it stated; `auto_install: []` is not the
default, it means *always*); `name`, `category`, `author`, `license` and the
URL keys are stripped; `summary` collapses to one line; a whitespace-only
`description` or `website` goes (a whitespace `description` is truthy and
**blocks the README fallback** -- 37 modules had one); `countries` lowercases
(`ir.module.module._update_countries` uppercases anyway); an `icon` equal to
its own default goes; a `set` bundle under `assets` becomes a sorted list (a
set has no order, and `crm_livechat` shipped one). Strings are written as
they are, not `\uXXXX`-escaped -- the 2026-09-11 sweep escaped 12 manifests'
authors, which the `ensure_ascii` default did silently. What follows the dict
literal is kept.

| gate | reads | floor |
|---|---|---|
| `lint_manifest_shape` | `sort_manifest(path, dry_run=True)` is `True` (would rewrite) or `None` (declines) | hard zero |
| `lint_manifest_value` | `_checker_manifest.ManifestChecker.findings` | hard zero |

The value rules are what no fixer can decide: unknown or deprecated key; a
value of the wrong type; `version` the loader would mark uninstallable
(`_normalize_version`); `license` outside `ir.module.module`'s selection
(pinned against the field); `category` with an empty segment or a root no
`odoo/addons/base/data/ir_module_category_data.xml` -- or a sibling's file of
that name -- declares (the loader creates
any category on the fly, so a typo is a stray category); a URL key without a
scheme; `depends` naming itself, a duplicate, or a module on no addons path;
an `auto_install` trigger outside `depends`; `external_dependencies` with a
kind other than `python`, `bin`, `apt` (`l10n_ec_edi` wrote `deb`, read by
nothing), or an `apt` hint for a dependency `python` does not declare; a
`countries` code that is not two letters, or a single country with no `l10n`
in the module name; a `data`/`demo` entry matching no file, listed twice, a
`demo` entry outside `demo/`, a `data` entry under `demo/` or named `*_demo`;
an `icon` matching no file; a hook name `__init__.py` does not bind (a `from
.x import *` waives it); an `assets` bundle not `<module>.<bundle>`, not a
list, or a directive the asset pipeline does not know or with the wrong arity.

**The sibling repositories are read by the same two scripts, without
odoo-bin.** From the workspace root, with the venv interpreter:

```bash
p314o19m/bin/python odoo/odoo/addons/test_lint/tests/_sort_manifests.py --dry-run enterprise agromarin design-themes
p314o19m/bin/python odoo/odoo/addons/test_lint/tests/_checker_manifest.py odoo/odoo/addons odoo/addons enterprise agromarin design-themes
```

Both locate the `odoo` package from their own path when it is not importable.
The checker resolves `depends` and `icon` across every root it is handed, so
hand it all of them. Measured 2026-09-12 over 1615 manifests: 1194 rewritten,
one value finding left (`partner_relationship_blocklist`, single-country with
no `l10n`, a rename that is not the fixer's call).

## Scope, and what it excludes

`lint_case.is_core_path` scopes every gate to this checkout. `_py_scan.corpus()`
additionally drops `_vendor/`, `upgrades/` and `migrations/`;
`_pretty_xml.is_formattable` drops `_vendor`, `static`, `node_modules` and
`tests`, because a fixture is not a data file.

The reference gates (`test_record_refs.py`, `test_group_refs.py`,
`test_menu_parents.py`, `test_button_targets.py`) read *definitions* from every
manifest on the addons path and judge *references* from this checkout only, so
a run with `enterprise/` on the path reads the same as the narrow scope.

**Nothing gates the sibling repositories any more.** The cross-repo runner
under `tooling/` went on 2026-09-11 with the rest of `tooling/`; the Python
checkers run only here, over this checkout. The manifest scripts above are the
one exception, because they take roots on the command line.

## Running the gates locally

There is no CI any more; every gate below runs by hand.

| run | scope |
|---|---|
| `odoo-bin --addons-path=odoo/addons,addons -d <db> -i test_lint --test-enable --test-tags /test_lint --stop-after-init --no-http` | the whole module, `--addons-path=odoo/addons,addons`, only `test_lint` installed |
| the same command against a fuller `-i`/`--addons-path` install | the registry-dependent classes, against a wider INSTALL set |

**A gate that reads the installed registry cannot be graded at the narrow
scope.** `TestSchemeDuplication` skips there rather than passing, naming the
modules it cannot see; `TestDocstring` is one-sided (`exact=False`) for the same
reason. Do not floor either at a narrow-scope reading.
