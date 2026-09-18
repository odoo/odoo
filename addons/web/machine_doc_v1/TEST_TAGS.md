# Web Module Test Tags

Quick reference for running targeted subsets of `addons/web/tests/`.

> Iterating on JS? Skip to **[Fastest edit/run loop](#fastest-editrun-loop--start-here)** —
> one test file is ~6 s, not one of the whole-tag times below.

## By Speed/Type

| Tag | Type | Tests | Time |
|-----|------|-------|------|
| `web_unit` | TransactionCase (pure Python) | 358 tests | ~45s |
| `web_http` | HttpCase (url_open, no browser) | 141 tests | ~5 min |
| `web_tour` | HttpCase (start_tour/browser_js) | 7 tests | ~2 min |
| `web_js` | Full JS suites (HOOT) | 37 tests | ~1-2 hr † |
| `addon_js` | HOOT suites of addons with no runner of their own | 97 tests | depends on the DB's module set |
| `web_perf` | Query count regression (@warmup) | 26 tests | ~2 min |
| `web_benchmark` | Statistical timing (run_benchmark) | 8 tests | ~5 min |
| `click_all` | Click-everywhere (-standard) | 2 tests (TestMenusAdmin, TestMenusDemo) | ~1+ hr |

> † The `web_js` time is an estimate, not a measurement. Measured: the desktop
> `@web/...` suites are 9339 tests in ~613 s of serial runtime (235 s wall at
> `hoot-shard -j 3`), so the hour-plus is dominated by whatever else the tag
> drags in — `test_hoot` alone carries a 1800 s timeout. Never reach for the
> whole tag to check one change.
>
> Counting basis: **tests as Odoo's loader collects them**
> (`odoo.tests.loader.prepare_suite(['web'], '<tag>')`), which includes methods
> inherited from untagged base classes — deliberately *not* a textual count of
> `def test_` inside `@tagged` classes, which undercounts. To reproduce a *run*:
> `odoo-bin -d <db> --test-enable --test-tags <tag> --stop-after-init` and read
> `odoo.tests.result: … of N tests`. Give the HttpCase tags (`web_http`,
> `web_js`, `click_all`) a real port — under `--no-http` they collect 0.

> Note: `test_res_config_doc_links.py` is the one file a plain `/web` run can
> never reach. It is `@tagged("-standard", "external", …)`, and **an include
> with no tag implies `standard`** (`odoo/tests/tag_selector.py`), so `/web`
> resolves to `standard/web` and skips it. Select it by a tag it actually
> carries:
>
> ```bash
> --test-tags 'external/web'     # or '*/web' for everything regardless of tag
> ```
>
> The same applies to `click_all` (`-standard`): `--test-tags '/web'` excludes
> it silently. Add `click_all/web` to include it.

## Fastest edit/run loop — start here

A single HOOT test **file** costs ~6 s and a single **test** ~5 s. Nothing below
needs a warm server, a special tool, or a full group run; the cost is dominated
by process start, not by the tests.

```bash
# ONE file (78 tests, measured 6.1s)
--test-tags '/web:WebSuite.test_core[@web/core/domain]'

# ONE test inside it
--test-tags '/web:WebSuite.test_core[@web/core/domain/Basic Properties/empty]'

# the same method without the parameter runs the WHOLE group (1803 tests, ~50s)
--test-tags '/web:WebSuite.test_core'
```

The suite/test path is a **bracketed parameter**, not a dotted path. The spec
grammar is `[-][tag][/module][:Class][.method][[params]]`
(`odoo/tests/tag_selector.py`); `_run_hoot` hashes each parameter into the
`&id=` filter HOOT resolves against either a suite **or** a single test.

**Do not pass `-u web`.** It is not needed to pick up JS changes — a fresh
`odoo-bin` process rebuilds asset bundles from source, including brand-new
`*.test.js` files — and it costs ~50%: 9.5 s median against 6.2 s over three
runs each of the same one-file selection.

**A spec that matches nothing fails the run.** `preload_registries` returns
non-zero when an explicit `--test-tags` selects no test; `--test-enable` alone is
unaffected, so installing a module that ships no tests is still legal. Read
`odoo.tests.result: … of N tests` regardless.

**A bracketed suite path that matches nothing also fails**, in headless runs
only: they abort in ~5 s with `HootError: no suite or test matches id "…"`. The
interactive UI still drops an unresolvable `&id=` and warns, because it keeps ids
in the URL across runs and a renamed test would otherwise wedge the page. Note
what that fail-open path costs when it applies: with the last id gone `hasFilter`
is false and the **whole bundle** runs.

### Warm-server runner (deleted)

The `./hoot` warm runner, `./hoot-shard` and `--affected` lived in the tooling
tree and were deleted with it in `7b0f58cb517f`. Run suites through `WebSuite` /
`MobileWebSuite` as described above.

### Driving a suite by hand

One `odoo-bin` of your own with `--dev=xml`, and a browser loading
`/web/tests?headless&loglevel=2&preset=desktop&timeout=15000&id=<hash>&module_scope=<addon>`
where `<hash>` is `HOOTCommon._generate_hash("<suite id>")`; the run ends on a
console line `[HOOT] Test suite succeeded` or `[HOOT] Failed N tests`. Two traps:

- **The mobile preset does not resize the browser.** `MobileWebSuite` sets
  `browser_size = "375x667"` and touch on Chrome itself, plus `&tag=-headless`;
  a page driven at 1366x768 with `preset=mobile` reads `innerWidth 1366`,
  `ui.size 4`, and five `@web/ui` mobile reds that look exactly like an
  `isSmall` regression. They are the harness.
- **An unscoped page on a database with `point_of_sale` is a POS world.**
  `_assets_pos` patches `ConfirmationDialog.setup` to run `usePos()` and
  `utils.isSmall` to `<= MD`, so 27 of `@web/ui` read red for POS's reasons.
  `_run_hoot` sends the scope for a lane, and since `d47df8cfe02e` also for a
  filtered `--test-tags '…[@web/ui/dialog]'` whose positive filters all name one
  addon; a hand-driven URL has to carry it itself.

> **Stale-source warning.** A long-lived `--dev=assets` server can serve the
> *previous* `static/src` with no error — `*.test.js` edits rebuild while
> `static/src` edits do not — when inotify watches are missing on directories
> nested inside a subtree that moved in whole (e.g. a branch switch). If a result
> ever looks impossible, `./hoot --restart` re-registers every watch; a per-run
> `odoo-bin` process is immune by construction.

### Presets and tags

`WebSuite` runs `preset=desktop`, `MobileWebSuite` runs `preset=mobile` **with
`tag=-headless`**. So:

| Tag on a test | Desktop pass | Mobile pass |
|---|---|---|
| *(none)* | runs | runs — but only if its **file** owns a mobile test (see below) |
| `desktop` | runs | skipped |
| `mobile` | skipped | runs |
| `headless` | runs | skipped |

`headless` means DOM-free, not "no browser": it still runs in the desktop pass.

**The mobile pass is scoped to the files that own a mobile test.** The preset
excludes only `desktop`-tagged tests, and 49% of `@web` plus 97% of
`@html_editor` carry no platform tag at all, so an unscoped mobile pass would run
9393 tests to exercise the **198** that actually carry a `mobile` tag.
`MobileWebSuite._run_hoot` narrows each category to the 45 test files that own a
mobile test (`_mobile_suites_under`), keeping every mobile test and the untagged
tests beside it: **2225 tests, 261 s**. A category with no mobile test at all
(`test_core`, `test_public`, `test_model`, `test_misc`) skips
with a message rather than running — an empty id list would otherwise mean *no
filter*, i.e. the whole bundle.

An explicit `--test-tags` suite path bypasses the narrowing: that path is
someone asking for exactly what they typed.

`./hoot --preset mobile` sends `-headless` by default so it matches CI; use
`--tag ''` for the unfiltered superset, or `--tag` for anything else. Note
`--tag mobile` does **not** restrict a run to mobile-tagged tests — a positive
tag include does not exclude untagged jobs (measured: `@web/views/list` gives
421 tests with `--tag mobile` against 358 with CI's `-headless`).

## Granular JS Tests (web_js)

`WebSuite` (desktop) and `MobileWebSuite` (mobile) each have granular test methods
that target specific hoot suite groups via `&id=HASH` URL filters. Use `--test-tags`
to run individual groups instead of the full 1-2 hour suite.

The two classes are not redundant: tests are selected by **tag**, not by
directory, so each platform runs a different (overlapping, neither-a-superset)
set. A change is only verified once both have run.

| Method | Hoot suite(s) | Scope |
|--------|---------------|-------|
| `test_core` | `@web/core` | utils, registries, RPC, ORM, domain |
| `test_components` | `@web/components` | reusable OWL components (dropdown, pickers, etc.) |
| `test_ui` | `@web/ui` | overlay services: dialog, popover, tooltip, notification |
| `test_calendar` | `@web/views/calendar` | calendar view |
| `test_fields` | `@web/fields` | field widgets |
| `test_form` | `@web/views/form` | form view |
| `test_kanban` | `@web/views/kanban` | kanban view |
| `test_list` | `@web/views/list` | list view |
| `test_misc_views` | `MISC_VIEW_SUITES` in `tests/test_js.py` — `@web/views/{graph,pivot,pivot_view,field_arch,view_arch_parser,view_components,view_compiler,view_dialogs,widgets,layout,control_panel_render_budget,view_button,…,multi_record_*,settings}` | every `@web/views/*` suite with no runner of its own |
| `test_search` | `@web/search` | search bar, filters, groupby |
| `test_webclient` | `@web/webclient` | action manager, navbar, settings |
| `test_public` | `@web/public` | public page components |
| `test_html_editor` | `@html_editor` | rich text editor |
| `test_model` | `@web/model` | client-side relational data model (Record, StaticList, DynamicList, etc.) |
| `test_misc` | `MISC_SUITES` in `tests/test_js.py` — `@web/{boot,env,reactivity,t_custom_click,test_isolation,helpers,interactions,l10n,libs,mock_server,modules}` | root-level and helper suites |

```bash
# Single group — desktop only (~30s-2min)
--test-tags '/web:WebSuite.test_calendar' -u web

# Single group — mobile only
--test-tags '/web:MobileWebSuite.test_calendar' -u web

# Multiple groups — both platforms
--test-tags '/web:WebSuite.test_calendar,/web:WebSuite.test_form,/web:MobileWebSuite.test_calendar' -u web

# html_editor desktop
--test-tags '/web:WebSuite.test_html_editor' -u web

# Full suite (existing behavior)
--test-tags 'web_js/web' -u web
```

## By Topic

| Tag | Files | Scope |
|-----|-------|-------|
| `web_action` | test_action | Breadcrumb loading |
| `web_assets` | test_assets, test_design_system, test_esm_pipeline, test_web_bundle_size | Bundle generation, asset cursors, compiled-CSS invariants (incl. `web.assets_frontend`, which no other test compiles) |
| `web_db` | test_db_manager | Database manager UI |
| `web_domain` | test_domain | Domain validation endpoint |
| `web_export` | test_export, test_ir_exports | Export endpoints (XLSX/CSV writers), export preset access |
| `web_favorite` | test_favorite | Favorite management tour |
| `web_health` | test_health | /web/health endpoint |
| `web_image` | test_image | Image serving, resize, access tokens |
| `web_layout` | test_base_document_layout | Document layout colors/logo |
| `web_login` | test_login | Login flow, user switching |
| `web_manifest` | test_webmanifest | PWA manifest routes |
| `web_menu` | test_load_menus, test_perf_load_menu | Menu loading + perf |
| `web_model` | test_ir_model | Model access, field creation |
| `web_partner` | test_partner | Partner access, vCard export |
| `web_pivot` | test_pivot_export | Pivot XLSX export |
| `web_profiler` | test_profiler | Profiling enable/disable |
| `web_promote_studio` | test_promote_studio | Studio upsell tours over the list optional-columns menu (skip without `account` / `knowledge`) |
| `web_properties` | test_res_partner_properties | Properties base definition |
| `web_qweb` | test_ir_qweb | QWeb image field rendering |
| `web_redirect` | test_web_redirect | URL redirect handling |
| `web_report` | test_reports, test_ir_actions_report_audit, test_report_rendering, test_report_introspection, test_report_layout_audit, test_report_modernization | PDF report session/cookies; the WeasyPrint engine, fetcher, layouts, attachments and the two technical reports (from `base` at web 2.3) |
| `web_router` | test_router | Action routing/resolution |
| `web_search` | test_web_search_read | web_search_read, web_name_search |
| `web_metrics` | test_health | `/web/metrics` Prometheus exposition + bearer-token gating |
| `web_session` | test_session_info | Session info endpoint perf |
| `web_settings` | test_res_config_settings, test_res_config_doc_links | Settings view fields + documentation links (the latter is `external`) |
| `web_translate` | test_translate | Translation overrides |
| `web_users` | test_res_users, test_res_users_settings | User settings, name_search |
| `web_controllers_audit` | test_controllers_audit | Controller conventions: docstrings, auth, readonly, methods |
| `web_read_group` | test_web_read_group | `web_read_group` API correctness |
| `web_read` | test_web_read | `web_read` family correctness |
| `web_save` | test_web_save | `web_save` correctness (incl. `known_values` field-scoped concurrency) |
| `web_onchange` | test_onchange | Form onchange simulation |
| `web_search_panel` | test_search_panel_version | Search panel endpoints + `__version` stamps |
| `web_benchmark` | test_web_benchmark | Statistical timing (`run_benchmark`) |
| `web_perf` | test_perf_load_menu, test_web_bundle_size, test_web_perf_regression | Query-count and byte-size regression gates |
| `asset_scope` | test_ir_asset_scope | `&module_scope=` bundle narrowing (see below) |
| `web_cwv` | test_web_cwv_metric | Core Web Vitals beacon model, clamping, retention cron |
| `web_js_error` | test_web_js_error, test_js_error_taxonomy | JS error beacon endpoint + `web.js.error` model, retention cron, and the client/server kind-phase taxonomy agreement |
| `web_feature_flags` | test_feature_flags | Feature flag resolution cascade |
| `web_typed_services` | test_typed_services_consistency | `@types/registries/services.d.ts` ↔ runtime registry consistency |
| `assets_bundle` | test_assets | Bundle generation timings and asset cursors (sub-tag alongside `web_assets`) |
| `web_bundle_size` | test_web_bundle_size | ESM bundle byte-size regression gate; pins upper-bound budgets per bundle (sub-tag alongside `web_perf` and `web_assets`) |

## Addons with no runner of their own (`addon_js`)

`_run_hoot` selects suites by explicit name, so a suite no runner names never
runs — and the page still reports success for the tests it *did* run, so nothing
goes red.

`tests/test_js_addons.py` closes that hole structurally: it walks every addon
that bundles `*.test.js`, subtracts what the explicit `WebSuite` runners already
select, and **generates one test method per remaining addon**
(`AddonSuite.test_<addon>`, tag `addon_js`, `-web_js` to drop the inherited tag).
A new addon is covered the day it lands.

- Selection is per **suite**, not per addon: `point_of_sale` has a runner for
  `@point_of_sale/unit` and bundles one file outside it, so its generated method
  runs only that file.
- A method **skips** when its addon is not installed on the test database —
  coverage follows whatever module set the CI job built.
- `KNOWN_FAILING_ADDONS` in that module is the remaining debt: addons whose
  suites do not pass yet. It is currently **empty**.
  `test_every_addon_unit_suite_is_selected_by_a_runner` asserts it exact in both
  directions, so an addon that starts passing fails the build until it is removed.

```bash
--test-tags 'addon_js'                        # every generated addon runner
--test-tags '/web:AddonSuite.test_web_studio' # one addon
```

For the dev loop use the warm runner instead — it installs the module into its
own DB and needs no CI database: `./hoot '@web_studio/navigation'`.

## HOOT suite scoping (`&module_scope=`)

`web.assets_unit_tests_setup` pulls in `web.assets_backend`, so an unscoped
`/web/tests` page executes the `src` of **every installed addon**. Those side
effects are global and unconditional (registry entries, `patch()` calls), while
mock models are opt-in per suite via `defineModels()`. That asymmetry lets one
addon's `src` reach for a model another addon's suite never defined, which the
mock server can only answer with *"Cannot find a definition for model X"*.

`_run_hoot` appends `&module_scope=<addon>`, derived from the `@<addon>`
prefix its suite names already carry. `ir.asset._get_addons_active`
(`web/models/ir_asset.py`) narrows every bundle on that request to the addon's
**manifest dependency closure** — for `mail` that is `{mail, web_tour,
html_editor, bus, web, base}`. What cannot load cannot register.

A run is not one request but three kinds, and the scope has to reach all of
them or the page loads foreign `src` anyway:

| request | how the scope reaches it |
|---|---|
| the runner page | `&module_scope=` query param, honoured on `/web/tests` |
| the bundles it links | the published URL — `/web/assets/scope/<addon>/<unique>/…` |
| bundles `loadBundle` fetches later | `session_info['bundle_params']`, which `assets.js` copies into `/web/bundle/…` |

- **Inert without the param.** No `module_scope` → `_prepare_assets_params()` is
  unchanged → the ormcache key and the bundle are identical. Only honoured on
  the runner routes, and only for an installed addon, so a stray param cannot
  fragment the asset cache of ordinary pages and the number of variants it can
  mint is bounded by the addons on disk.
- **The URL names the scope.** `unique` is a SHA256 over the *result*, which
  tells a scoped bundle apart from an unscoped one but describes neither —
  and `content_assets` re-resolves from the URL alone. While the scope lived
  only in `unique`, the scoped CSS 303'd to the unscoped bundle on every page
  load: distinct URL, unservable. `_get_asset_bundle_url_segments` puts it in the path
  and `content_assets_scoped` reads it back. Every asset param must contribute
  a segment this way — `web/tests/test_ir_asset_scope.py` asserts the two
  halves agree, so an override that adds one and forgets the other fails.
- **Both directive sources are gated.** `_get_asset_paths` narrows the manifest
  side, but an `ir.asset` row names a path and no addon, so the closure has to
  reach `Resolution.active` — the single point deciding whether a path may
  resolve. Fed from `_get_addons_installed` instead, `website`'s ~100 rows
  aimed at `web.*` bundles walked straight through it.
- **Suites are stricter.** A suite that would pass only because a foreign addon's
  `src` happened to be loaded fails instead. That is the point; treat such a
  failure as a real missing dependency, not as scoping breakage.
- `hoot_filters` (an explicit `--test-tags` path) suppresses scoping: the path
  may select suites from another addon.
- `im_livechat`'s `/web/tests/livechat` external suite passes no scope and
  stays unscoped by design — it is deliberately cross-addon.

Covered by `tests/test_ir_asset_scope.py` (tag `asset_scope`).

## Files not reachable by a topic tag

Five test files carry no `web_*` topic tag, so no `web_<topic>` selection
reaches them:

| File | Tags it does carry |
|---|---|
| `test_fontawesome.py` | *(none)* |
| `test_pdfjs_dist.py` | *(none)* |
| `test_ir_asset_scope.py` | `asset_scope`, `post_install`, `-at_install` |
| `test_js_addons.py` | `addon_js`, `post_install`, `-at_install`, `-web_js` |
| `test_scss_design_system.py` | `post_install`, `-at_install` |

The two untagged ones are reachable only via `/web` (or a path selector).

## Examples

```bash
# Fast feedback (~30s)
--test-tags='web_unit/web' -u web

# Single topic
--test-tags='web_image' -u web

# Multiple topics
--test-tags='web_image,web_login' -u web

# All HTTP tests (~5 min)
--test-tags='web_http/web' -u web

# Everything except slow JS/tours
--test-tags='/web,-web_js,-web_tour,-click_all'

# Only perf regression
--test-tags='web_perf' -u web

# Full suite (nightly)
--test-tags='*/web' -u web
```
