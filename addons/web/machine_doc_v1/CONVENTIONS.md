# Web Module Conventions

Module-specific patterns, rules, and gotchas for working in `addons/web/`.

> **See also**: `COMPONENT_DIAGRAM.md` — 18 audit areas with key invariants
> to verify per area. `FLOW_DIAGRAM.md` — 14 end-to-end sequence diagrams.

## RPC Convention

**ORM calls from JavaScript go through two gateways:**

```
JS: orm.call(model, method, args, kwargs)
  → POST /web/dataset/call_kw/{model}/{method}
    → Python: dataset.py:DataSet.call_kw()
      → ORM method dispatch

JS: button click in views
  → POST /web/dataset/call_button/{model}/{method}
    → Python: dataset.py:DataSet.call_button()
      → ORM method dispatch + clean_action() on result
```

`call_kw` handles all standard ORM operations (`orm.read()`, `orm.write()`,
`orm.create()`, `orm.search()`, `orm.unlink()`). `call_button` is the second
path, used specifically for UI button actions — it wraps the result through
`clean_action()` before returning.

**x2Many commands from JS follow this encoding** (see `odoo/orm/primitives.py` `Command` IntEnum):

| Command | Tuple | Meaning |
|---------|-------|---------|
| CREATE | `[0, 0, {values}]` | Create new related record (2nd element is always `0`) |
| UPDATE | `[1, id, {values}]` | Update existing related record |
| DELETE | `[2, id, 0]` | Delete and unlink (3rd element is integer `0`, not `false`) |
| UNLINK | `[3, id, 0]` | Unlink without deleting |
| LINK | `[4, id, 0]` | Link existing record |
| CLEAR | `[5, 0, 0]` | Clear all relations |
| SET | `[6, 0, [ids]]` | Replace all with id list |

The canonical Python spelling of the unused slots is the integer `0` (`orm/primitives.py` `Command` helpers). The JS client (`core/network/commands.js` and the command engine) emits `false` in those slots; this is **safe by construction** — the server-side command parser reads slot 2/3 only for CREATE/UPDATE/SET, and ignores the unused slots entirely for DELETE/UNLINK/LINK/CLEAR — and is pinned by ~115 HOOT test expectations, so do not "normalize" it. New Python code should still use the `Command` helpers (integer `0`).

## Specification Pattern

The `web_read`, `web_save`, and `web_search_read` methods accept a `specification`
dict that mirrors the view's field tree. This controls which fields are fetched and
how relational fields are recursively resolved:

```python
# Example specification for a form view
specification = {
    "name": {},  # scalar field
    "partner_id": {
        "fields": {  # many2one: fetch sub-fields
            "display_name": {},
            "email": {},
        }
    },
    "line_ids": {
        "fields": {  # one2many: fetch sub-fields
            "product_id": {"fields": {"display_name": {}}},
            "quantity": {},
            "price_unit": {},
        },
        "limit": 40,
        "order": "sequence",
    },
}
```

When modifying view definitions, the specification must match or the frontend
will receive incomplete data.

## Controller Patterns

### Auth Types (web module)
- `auth='user'` — Requires authenticated session (most RPC endpoints)
- `auth='public'` — Works with or without session (images, assets, frontend)
- `auth='none'` — No session handling at all (health, login, database ops)
- `auth='bearer'` — Bearer token (JSON API only)

Other addons register additional auth methods via `_auth_method_*` (e.g.
`outlook` in mail_plugin, `calendar` in calendar). The web module itself
uses only the four above.

### Readonly Flag
Many routes declare `readonly=True` which routes them to a read replica if configured.
Write operations (create, write, unlink, button clicks) use `readonly=False` (default).

The `call_kw` route uses a dynamic `readonly=_call_kw_readonly` function
(`controllers/dataset.py`) that walks the target model's MRO looking
for a `_readonly` attribute on the named method (set by the `@api.readonly`
decorator). Defaults to `False` when the attribute is absent. Callers adding
new read-only ORM methods must decorate them with `@api.readonly` for the
route to route to a replica.

### JSONRPC vs HTTP
- `type='jsonrpc'` (JSONRPC): Request/response wrapped in JSON-RPC 2.0 envelope. Used for data operations.
- `type='http'` (HTTP): Standard HTTP. Used for file downloads, page renders, binary content.

> Note: Routes without `methods=[...]` accept ALL HTTP methods (GET, POST, etc.).
> Only routes with explicit `methods=['GET']` or `methods=['POST']` are method-restricted.

## JavaScript Patterns

### List column sizing

Field definitions declare sizing through `listViewWidth`: a fixed number, a
minimum/maximum array, or `"content"` to fit the rendered column rather than
share spare table width. The existing callback form can choose from these using
field metadata. An explicit view `width` takes precedence.

The many2one field-description builder selects `"content"` for relations to
`res.company`, whose display label can be a short code or a full name. This also
applies when a view explicitly names the many2one widget; derived widgets can
override the sizing declaration. The list sizing algorithm consumes the policy
without knowing the relation or field name. It retains the usual minimum width
and empty-list fallback. Intrinsic widths exclude cell padding and survive a
container shrink, so expanding the container can restore the full label. Other
columns yield spare width before content-sized labels are truncated.

Displayed text changes (paging, filters, or opening groups) invalidate automatic
content widths. Editing freezes widths; a manual drag keeps them frozen until a
reset, column-layout change, or window resize. If every visible column requests
content sizing, the table still fills its container, so those columns share the
otherwise unused space.

### Service Injection
```javascript
setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
}
```

### ORM proxy idioms

The ORM exposes three composable proxy modifiers (`silent`, `cache`, `retry`)
that thread settings through to `rpc()`. Each returns a fresh
`Object.create(this)` view; the base ORM is never mutated.

```javascript
// Suppress error dialogs for a single call
await orm.silent.read("res.partner", [id], ["name"]);

// Disk-cache a fields_get with one retry on transient failure
await orm.cache({ type: "disk" }).retry(1).call(model, "fields_get", []);

// Compose all three for a boot-path read
await orm.silent.cache({ type: "disk" }).retry(1)
    .webSearchRead("res.partner", domain, {});
```

**Composition rules**:
- Order-independent: `cache(opts).retry(1)` and `retry(1).cache(opts)`
  produce identical settings.
- Reusable: store the chain in a variable to apply identical settings
  to many calls.
- `silent` is a getter; `cache(options)` and `retry(options)` are methods
  taking either a primitive (`retry(2)`) or a partial config
  (`retry({ retries: 2, baseMs: 100, maxMs: 1000 })`).

### When to use `retry`

Apply only to **idempotent reads** where transient failure (proxy hiccup,
brief 503, pool exhaustion, worker restart during deploy) cascades into
broken UX with no user recovery action. Never apply to writes — a partial
server-side mutation could be re-applied.

The three `.retry(1)` call sites in `static/src`:

| Call site | Reason | Budget |
|---|---|---|
| `core/field_service.js` (2 sites) | Cold-cache `fields_get` failure prevents any view from rendering for the model | `retry: 1` |
| `views/view_service.js loadViews` | Cold-cache `get_views` failure prevents any view from rendering | `retry: 1` |

**Default budget rationale** (`retry: 1`): caps user-perceived delay on
persistent outage at one backoff interval (~200ms). Higher budgets can
chain into multi-second hangs visible as "the app feels frozen". Tune
upward (`retry: { retries: 3 }`) only when the call is on a background
path the user doesn't see directly.

### Model Coordinators

Lifecycle axes are formalized via small SignalStore-extending coordinator
classes rather than bare boolean flags. Each owns its state machine, exposes
``isActive`` / ``isLoading`` / ``status`` getters, and centralizes entry/exit
in a single ``run(fn)`` / ``enter()`` / ``exit()`` API so consumers cannot leak
the flag past the operation's lifetime.

(There is no load coordinator: the load axis is covered by `model.keepLast`
+ the reactive `model.isReady` flag; see STATE_MANAGEMENT.md
"Model Load Lifecycle".)

| Coordinator | File | Replaces | Used by |
|---|---|---|---|
| `UrgentSaveCoordinator` | `model/relational_model/urgent_save_coordinator.js` | the `model._urgentSave` bool + `_withUrgentSaveScope` helper | `record.update`, `record.updateLocked`, `record.checkValidity`, `record_save.save`, `model.askChanges`, `record.urgentSave` |
| `SampleDataCoordinator` | `model/sample_data_coordinator.js` | the `model.useSampleModel` bool (kept as backward-compat getter/setter) | pivot_controller, list_renderer, list_keyboard_nav, list_controller, list_styling, kanban renderer (read); PivotModel, GraphModel (write) |
| `FormSaveCoordinator` | `views/form/form_save_coordinator.js` | per-controller `isSaving` + `record.isDirty` plumbing | form_controller (9 entry points), settings_form_controller (Apply / discard-then-save); FormStatusIndicator (reads `status`/`isSaving`) |

**`multiEdit` is NOT a coordinator** — it is a config-time-only
boolean assigned once during model construction (from
`list_arch_parser.multiEdit` in `list_controller.modelParams`) and
read at 4 sites in views/list/ (`list_keyboard_edit`,
`list_styling`, `list_keyboard_nav`) for readonly evaluation. It never
mutates at runtime, so there is no state machine to formalize.

### Feature Flags

Pure-function API at `@web/core/feature_flags` for gating
behaviour without bespoke `odoo.debug` / `localStorage.getItem` /
`?debug=...` plumbing scattered across the codebase.

**Resolution cascade** — first source wins:

| # | Source | Purpose |
|---|---|---|
| 1 | URL `?features=name:value,name2,-name3` | One-off A/B / reproduction; highest priority |
| 2 | `localStorage["feature.<name>"]` | Per-device persistent override (dev / on-call) |
| 3 | `session.feature_flags[<name>]` | Server default, from `ir.config_parameter` rows with `web.feature.` prefix |
| 4 | `options.default` | Call-site fallback (defaults to `false`) |

**Usage**:

```js
import { featureFlag } from "@web/core/feature_flags";

if (featureFlag("perf_marks", { default: false })) {
    performance.mark("model:load:start");
}
```

**Server config**: set an `ir.config_parameter` row keyed
`web.feature.<flag_name>`. The value string is parsed with the same
literal set as URL / localStorage tokens (`true` / `false` / `null` /
signed integer / float / otherwise string).

**Convention**: flag names are `snake_case` without `.`, `:`, `,`, or
`;` (those are reserved for the URL parser). Names are free-form —
registration is not required — but consider documenting any
production-load-bearing flag in this section once introduced.

### Registry System
Components, views, fields, services are all registered in named registries.
The 4 most frequently-used categories are:

- `registry.category("services")` — Service definitions
- `registry.category("views")` — View type implementations
- `registry.category("fields")` — Field widget implementations
- `registry.category("actions")` — Client action components

The web module registers into 36 categories. The other 32:
`action_handlers`, `cogMenu`, `color_picker_tabs`, `command_categories`,
`command_provider`, `command_setup`, `debug`, `debug_section`, `deserializers`,
`dialogs`, `effects`, `error_dialogs`, `error_handlers`, `error_notifications`,
`favoriteMenu`, `form_compilers`, `formatters`, `group_config_items`,
`home_menu_badges`, `ir.actions.report handlers`, `lazy_components`, `main_components`, `parsers`,
`public.interactions`, `public_components`, `sample_server`, `serializers`,
`share_target_apps`, `shared_components`, `systray`, `user_menuitems`,
`view_widgets`. Re-derive with
`grep -rhoE 'registry\.category\("[^"]+"' static/src | sort -u`.

### Field Widgets
Field widgets live in `static/src/fields/` (top-level, organized into 7 subcategories:
`basic/`, `display/`, `media/`, `relational/`, `selection/`, `specialized/`, `temporal/`).
Each field type (char, integer, many2one, etc.) has a directory with its component,
extractors, and optional variants. There are 68 widget directories and 116 fork-wide `registerField` /
`registerFallbackField` sites (82 plain, 34 through the typed spec form).
Import path: `@web/fields/*` (e.g. `@web/fields/basic/char/char_field`).

**Multi-key registrations — refactor hazard.** A single widget file often
registers under multiple keys. Renaming or moving a widget without grep-
auditing every `.add("<key>", ...)` call can silently break views. Known
multi-key registrations in the base fields:

| File | Registry keys |
|---|---|
| `basic/copy_clipboard/copy_clipboard_field.js` | `CopyClipboardButton` + `CopyClipboardChar` + `CopyClipboardURL` (CamelCase aliases) |
| `basic/email/email_field.js` | `email` + `form.email` |
| `basic/phone/phone_field.js` | `phone` + `form.phone` |
| `basic/text/text_field.js` | `text` + `list.text` |
| `basic/url/url_field.js` | `url` + `form.url` |
| `media/binary/binary_field.js` | `binary` + `list.binary` |
| `relational/many2many_tags/many2many_tags_field.js` | `calendar.many2many_tags` + `calendar.one2many` + `calendar.many2many` + `form.many2many_tags` |
| `relational/many2many_tags_avatar/many2many_tags_avatar_field.js` | `many2many_tags_avatar` + `list.many2many_tags_avatar` + `kanban.many2many_tags_avatar` |
| `relational/many2one/many2one_field.js` | `many2one` + `res_partner_many2one` |
| `relational/x2many/x2many_field.js` | `one2many` + `many2many` (filename misleads) |
| `relational/x2many/list_x2many_field.js` | `list.one2many` + `list.many2many` |
| `specialized/ace/ace_field.js` | `ace` + `code` |
| `specialized/ir_ui_view_ace/ace_field.js` | `code_ir_ui_view` (NOT `ace`) |
| `specialized/properties/card_properties_field.js` | `kanban.properties` + `hierarchy.properties` |
| `temporal/datetime/datetime_field.js` | `date` + `daterange` + `datetime` |
| `temporal/datetime/list_datetime_field.js` | `list.date` + `list.daterange` + `list.datetime` |
| `display/percent_pie/percent_pie_field.js` | `percentpie` (no underscore) |
| `display/stat_info/stat_info_field.js` | `statinfo` (no underscore) |
| `display/progress_bar/progress_bar_field.js` | `progressbar` (no underscore) |
| `selection/badge_selection/badge_selection_field.js` | `selection_badge` (word order reversed) |

Extra keys come from a spec's `aliases` array
(`registerField({ name: "one2many", aliases: ["many2many"] }, x2ManyField)`), so a
grep for the key string alone finds nothing — read the spec object.

Before renaming a widget file, run `grep -rn 'registerField(' addons/` to enumerate every key a file registers. Registration goes exclusively through `registerField()` / `registerFallbackField()` from `@web/fields/_registry` (97 call sites inside `fields/`, 116 fork-wide); `registry.category("fields").add(...)` appears only inside `_registry.js` itself, so grepping for it finds nothing.

## Test Conventions

### Tag Structure
Every test class uses `@tagged()` with:
1. **Layer tag** (required): `web_unit`, `web_http`, `web_tour`, `web_js`, `web_perf`, `web_benchmark`
2. **Topic tag** (required): `web_health`, `web_login`, `web_image`, etc.
3. **Install phase**: `at_install` (default) or `post_install` + `-at_install`

```python
@tagged("web_http", "web_health")  # at_install (default)
class TestHealth(HttpCase): ...


@tagged("post_install", "-at_install", "web_tour", "web_login")
class TestLoginTour(HttpCase): ...
```

### Test Base Classes
- `TransactionCase` — For unit tests (`web_unit`). Rolled-back transaction per test.
- `HttpCase` — For HTTP tests (`web_http`). Has `url_open()` for request testing.
- `HttpCase` + `start_tour()` — For browser tours (`web_tour`). Runs JS tour in headless browser.

### Running Tests
```bash
# Fast feedback (~30s)
--test-tags='web_unit' -u web

# Single topic
--test-tags='web_image' -u web

# All except slow JS/tours
--test-tags='/web,-web_js,-web_tour,-click_all'
```

See `machine_doc_v1/TEST_TAGS.md` for full reference.

## Model Extension Pattern

The web module extends `base` (the abstract base model) with methods that
ALL models inherit. This is how `web_read()`, `web_save()`, `onchange()`, etc.
become available on every Odoo model:

```python
class Base(models.AbstractModel):
    _inherit = "base"

    def web_read(self, specification):
        """Available on every model because base is inherited."""
        ...
```

When adding a new web-facing method, extend `base` in the appropriate file
under `models/` (group by concern: CRUD in `web_read.py`, grouping in
`web_read_group.py`, etc.).

## File Organization Rules

### Controllers
- One controller class per file (occasionally two for export format subclasses)
- File name matches the URL namespace: `session.py` → `/web/session/*`
- Helper functions and utilities go in `controllers/utils.py`

### Models
- Grouped by concern, not by ORM model name
- `web_read.py` = CRUD, `web_read_group.py` = grouping, `web_onchange.py` = form changes
- `ir_*.py` files extend framework models (views, menus, HTTP, QWeb)
- `res_*.py` files extend user/company/partner models

### JavaScript
- `static/src/boot/` — App entry points (env, main, session, start)
- `static/src/core/` — Framework primitives: registry, utils, reactivity, browser, l10n, network + ORM, errors, py_js, tree
- `static/src/components/` — Reusable OWL UI components (dropdown, pickers, editors, file handling)
- `static/src/ui/` — Overlay layer and its services (dialog, popover, tooltip, notification, overlay, effects, block, command palette)
- `static/src/fields/` — 68 widget directories in 7 subcategories (basic, display, media, relational, selection, specialized, temporal)
- `static/src/views/` — View type implementations (form, list, kanban, calendar, graph, pivot) + view utilities
- `static/src/webclient/` — App shell (navbar, menus, action container)
- `static/src/search/` — Search bar and filter components
- `static/src/model/` — Client-side relational data model (Record, StaticList, DynamicList, etc.)
- `static/src/public/` — Public (anonymous) page features

### Static Libraries (DO NOT MODIFY)
Everything under `static/lib/` is vendored third-party code.
Never edit these files. If a library needs updating, replace the entire directory.

### OWL component file convention

An OWL component is a co-located trio:

```
static/src/<layer>/<name>/
    <name>.js       # Component class (`this.static.template = "<module>.<Name>"`)
    <name>.xml      # QWeb template matching the `static.template` key
    <name>.scss     # Optional component-scoped styles
```

261 of the 743 JS files in `static/src/` (35.1%) have a sibling `.xml`.
Templates are registered by the asset pipeline — the manifest's glob
patterns (e.g. `web/static/src/fields/**/*`) pull `.js`, `.xml`, `.scss`
together, and `ir.qweb` collects every `.xml` into the template registry
so OWL can resolve `static.template = "web.CharField"` to the XML file's
`<t t-name="web.CharField">`.

When refactoring a widget:
1. Move/rename the `.js`, `.xml`, and `.scss` together
2. Update `this.static.template` in the `.js` if the template name changes
3. Update the `t-name` attribute in the `.xml`
4. Search all XML files for `t-name="<oldname>"` — templates can inherit
   across file boundaries

## Gotchas

1. **`web_read` is NOT `read`** — `read()` returns raw field values. `web_read()` recursively
   resolves relational fields per specification. Frontend always uses `web_read`.

2. **`onchange` happens server-side** — The JS form view sends the entire form state to
   `onchange()` which simulates the change in a pseudo-record, computes dependents,
   and returns a diff. It does NOT save to the database.

3. **SCSS order matters; JS order mostly doesn't** — SCSS files in `__manifest__.py`
   asset lists are concatenated in order, so variable definitions must come before rules
   that reference them. ESM bundles (nearly every webclient bundle: `assets_web`,
   `assets_backend`, `assets_frontend`, report/test bundles, most addon asset bundles)
   are built by **esbuild**, which derives load order from `import` statements, not
   manifest order. Non-ESM bundles still concatenate JS in order. ESM membership is
   **declarative**: each module lists its bundles under an `esm` key in its own
   `__manifest__.py` (`bundles` / `dynamic_children` / `import_map_includes` /
   `secondary_import_map_includes`), aggregated by
   `odoo.tools.assets.esm_registry.esm_registry()` (`esm_registry.py`). Check a
   bundle's membership there before relying on positional placement.

4. **`readonly=True` on routes** — This is not about user permissions. It tells the
   load balancer/proxy to route to a read replica. A `readonly=True` route that
   accidentally writes will corrupt data on replicated setups.

5. **Image URL variants** — `/web/image/` has 17 declared URL patterns, all resolving to
   `content_image()`; `/web/content/` has another 7 on `content_common()`. When matching or rewriting image
   URLs, account for all variants (by xmlid, by id, by model/id/field, with/without
   dimensions, with/without filename).

6. **Lazy-loaded libraries (not views)** — Graph and Pivot view code lives in the
   main `assets_backend` bundle; there is NO `assets_backend_lazy` bundle. What IS
   lazy-loaded is the *Chart.js library*: `views/graph/graph_renderer.js` (and the
   gauge / journal-dashboard fields) call `loadChartJS()` from
   `core/lib/chartjs.js`, which dynamic-`import()`s the `chart.js` +
   `chartjs-adapter-luxon` import-map bare specifiers on first graph render and
   populates the live-bound `Chart` export (one shared runtime fetch; no
   `<script>` injection, no `window.Chart` global). FullCalendar follows the same
   pattern via `core/lib/fullcalendar.js` `loadFullCalendar()`. The old
   `web.chartjs_lib` / `web.fullcalendar_lib` classic-script bundles are gone.
   Pivot export has no analogous lazy-load (no `loadBundle` / `loadJS` in
   `views/pivot/` or `views/list/export_all/`); XLSX export is server-side via the
   `/web/pivot/export_xlsx` controller. When adding code that depends on a heavy
   library: if the library is a real ES module, prefer the `core/lib/` lazy-ESM
   loader pattern (import-map entry + dynamic `import()` + live-bound export);
   for classic scripts, prefer `loadBundle()` over adding to the main bundle.

   **`loadBundle` vs `loadJS` — which to use?** `core/assets.js` exports both;
   they are *not* alternatives. `loadBundle` fetches `/web/bundle/<name>`, parses
   the manifest's CSS/JS/ESM list, and dispatches each non-ESM JS file through
   `loadJS`. The decision is about **whether the asset belongs in the manifest at all**:

   - **Internal vendored libraries** (anything under `<addon>/static/lib/...`
     or `<addon>/static/src/.../libs/...`): declare a bundle in
     `__manifest__.py` and call `loadBundle("<addon>.assets_<lib>_lib")`.
     Benefits: asset hashing for cache-busting, integration with the asset
     pipeline's circuit breaker and observability log
     (`makeAssetLog("js")`), single source of truth in the manifest.
     Examples: `web.ace_lib`.
     (Libraries that ship as real ES modules — Chart.js, FullCalendar,
     DOMPurify, signature_pad — are import-map bare specifiers instead of
     classic bundles: eager `import` or dynamic `import()`; see above.)

   - **External SDKs delivered via vendor CDN** (payment processors, Maps
     APIs, video player APIs, reCAPTCHA, etc.): use `loadJS(url)` directly.
     The vendor handles caching, hashing, version updates, and licensing
     attribution. Examples: PayPal SDK, Adyen SDK, Google Maps, YouTube
     IFrame API, Vimeo player, Leaflet from unpkg.

   **Edge cases**:

   - `delivery_mondialrelay` vendors a slim jQuery (`jquery.slim.min.js`)
     because the external Mondial Relay widget requires the global
     `window.jQuery` and the fork has otherwise removed jQuery. Loaded via
     `loadJS` of a static path — exception because the consumer is a
     third-party widget contract.

   - `im_livechat/embed/external/emoji_loader_patch` calls
     `loadJS(url("/im_livechat/emoji_bundle", undefined, {origin: livechatData.serverUrl}))`
     — cross-origin to the embedded site's livechat server, not our
     `/web/bundle/...` endpoint, so `loadBundle` cannot resolve it.

   **Don't `loadJS` something that is already eager-loaded.** A library already
   declared in `web.assets_backend` (or its ancestors) is in the page's initial
   bundle; calling `loadJS(url)` on it after page load is a no-op at best and a
   re-evaluation hazard at worst. Example:
   `mail/static/lib/selfie_segmentation/selfie_segmentation.js` ships in
   `web.assets_backend` (mail/__manifest__.py).

7. **`CLEAR-CACHES` on result-set removal is model-scoped on BOTH layers.** Any RPC
   whose method removes records from the model's result sets — `unlink`,
   `action_archive`, `action_unarchive` — broadcasts `CLEAR-CACHES` with
   `model: <affected model>` and
   `tables: ["web_read", "web_search_read", "web_read_group"]`.

   **RAM cache** (`rpc_cache.js:RamCache.invalidateByModel`) uses a
   per-table `model → Set<key>` reverse index populated at
   `write(table, key, value, model)` time; invalidation is O(1) lookup
   + O(matched) delete, independent of the table's total entry count.
   Entries written without a `model` argument (session_info,
   `/web/action/load`, `get_views`, …) are correctly invisible to
   `invalidateByModel` — those flows use `invalidate(table)` instead.

   **IndexedDB cache** (`indexed_db.js:invalidateByModel`) uses
   `openCursor` and checks `cursor.value.model === <model>`. The model
   name is stored plaintext alongside the encrypted ciphertext as
   `{ciphertext, iv, model}` (model names appear in the URL and are
   not secret).

   **Pre-migration IDB entries** lack the `model` property on their value, so
   `invalidateByModel` skips them. They remain reachable for `invalidate(table)`
   and get rewritten as responses come back through the cache.

   Method-set source of truth:
   `core/network/result_set_cache_invalidator_service.js`
   `RESULT_SET_REMOVING_METHODS`. Emission site:
   `core/network/result_set_cache_invalidator_service.js`. The listener
   lives in a dedicated service (not `relational_model.js`) so wiring is owned
   by env lifecycle — one subscription per page, one per Hoot test, torn down
   with the env. See `FLOW_DIAGRAM.md` Flow 14 for the full invalidation chain.

   **Write/create methods are intentionally excluded.** `create` / `write`
   / `web_save` / `web_save_multi` return the updated record and let the
   model self-maintain its cache via the normal response path
   (Plan-C envelope versioning handles freshness on subsequent reads). A
   broad-mutation bridge breaks the create→back-nav stale-then-fresh display
   tested by `list_view.test.js` "cache web_search_read (onUpdate called after
   another load)". The regression guard
   (`list_view_performance.test.js` "non-removing RPC:RESPONSE does not
   emit CLEAR-CACHES") asserts every write-class method stays excluded.

8. **Session info embedded in HTML** — `session_info()` is JSON-serialized into a
   `<script>` tag during page load. It carries the `registry_hash` HMAC and, for
   internal users, the company hierarchy. Note `browser_cache_secret` is **not**
   part of `session_info()`: it is injected separately into the page context by
   `home.py` (`home.py`, whose comment notes it is added "here and not in
   session_info()"). The JS reads `odoo.__session_info__` into a local snapshot
   but **does not delete it** from the global — the test harness re-reads the same
   global (`session.js`). Never add sensitive data (passwords, API keys) to
   `session_info()` — it's visible in page source.

9. **Field-scoped optimistic locking (`known_values`), with urgent-save
   parity** — The client does not send a whole-record `last_write_date`
   (the server accepts that kwarg only as a fallback). Instead
   `record_save.js` builds a `concurrencyBaseline` map (`record_save.js`):
   for each field being written, the originally-loaded value from
   `record._values` — skipping types that can't be compared safely (x2many,
   binary, html, date/datetime, json, properties, reference) and jsonb-backed
   `translate` / `company_dependent` fields. It is sent as
   `kwargs.known_values` on BOTH the normal path (`record_save.js`) and
   the urgent sendBeacon path (`urgentKwargs`, `record_save.js`), for
   existing records only (`resId` truthy). Server side,
   `models/web_read.py:_check_concurrent_field_changes` rejects only a
   genuine per-field conflict and ignores concurrent writes to OTHER fields
   (e.g. background stored-compute recomputations); a field with no baseline
   is skipped — the check **fails open**, so an empty baseline (only x2many
   changed) means no check, which is the right call on tab close where the
   user's work must never be dropped.

10. **`archiveEnabled` is consolidated in
    `view_utils.computeArchiveEnabled(fields, { presentIn = fields } = {})`
    — form and multi-record differ only in the presence source** — the helper
    walks `["active", "x_active"]` (the latter for custom no-active-field
    models), takes the first name present in `presentIn`, and returns
    `Boolean(fields[name]) && !fields[name].readonly`.
    `form_controller.js` calls it as
    `computeArchiveEnabled(this.props.fields, { presentIn: this.model.root.activeFields })` —
    presence is gated on the field actually being **in the view**.
    `multi_record_controller.js` calls
    `computeArchiveEnabled(this.props.fields)` — presence and writability both
    come from the model-level fields definition.

    **Why the form needs the stricter `activeFields` gate**: the form
    conditions archive vs unarchive on `model.root.isActive`
    (`form_controller.js`). If `active` is not in `activeFields`,
    the view never loads it, so `record.data.active` is `undefined` and
    `record.isActive` is falsy. Without the gate, `archiveEnabled` would still
    be true and the form would show "Unarchive" on a record whose active state
    it cannot read.

    **Why multi-record can skip the gate**: list/kanban shows both archive
    AND unarchive simultaneously (multiple selected records, mixed states).
    It does not condition on any single record's state, so the weaker check
    is sufficient.

    Shared known limitation: neither controller checks view-level readonly attrs
    (`<field readonly="..."/>`); both rely on model-level `props.fields[*].readonly`.

11. **Registry schema validation runs in production with a soft warning** —
    `core/registry.js:isValidValue` runs the OWL `validate()` call in every
    environment. In debug mode it throws (fail fast for developers); in production
    it emits a `console.warn` prefixed `[registry]` so a single malformed
    registration cannot crash the page while still surfacing schema mismatches.
    Schema coverage is **36 of 40 web-module categories**; `serializers` and
    `deserializers` (`core/field_codec.js`) and `in_range_providers`
    (`core/tree/in_range_providers.js`) have no schema yet. The `debug` registry IS
    schemable despite being "parent-only": its entries are sub-Registry instances
    created by `category()`, so `entry instanceof Registry` catches accidental
    direct `.add()` calls. Pattern to follow when adding a new registry or
    schema-ing an existing one:

    - Co-locate the `addValidation` call with the **canonical consumer**
      of the registry, not in a central bootstrap file (`env.js` for services,
      `fields/field.js` for fields, `webclient/navbar/navbar.js` for systray) —
      the schema is discoverable when someone changes that consumer.
    - Two schema forms are accepted by `core/registry.js:isValidValue`:
      object form (passed to OWL's `validate()`) for entries shaped like
      `{ key: spec }`, and predicate form (`(entry) => boolean`) for
      entries that are bare callables/classes.
    - When entries forward extra fields to downstream addons, include
      `"*": true` in object schemas so private fields don't trip the
      validator. The contract is "here's what *we* read"; the rest is forwarded.
    - Translated strings (`_t(...)`) return `LazyTranslatedString`
      objects, not plain strings. Any schema field that may hold a
      `_t()` value must accept `[String, Object]`, not `String` alone.
      Affected: `command_categories.name`,
      `command_setup.{emptyMessage,name,placeholder}`,
      `error_notifications.{title,message}`,
      `group_config_items.label`, `color_picker_tabs.name`.
    - When validating "must be a Component class", check
      `entry?.prototype instanceof Component` if `Component` is already
      imported; otherwise fall back to `typeof entry === "function"`
      (class definitions are functions) to avoid a new import.
    - When the canonical consumer carries a typed shape in
      `@types/registries/*.d.ts`, **the runtime schema must match the
      declared shape**.

12. **`FormSaveCoordinator` owns the form save lifecycle** —
    `views/form/form_save_coordinator.js`. Every save / discard / urgent-save entry
    point in `form_controller.js` calls `this.saveCoordinator.requestSave({...})` /
    `requestUrgentSave()` / `requestDiscard()` with named options.
    `settings_form_controller.js` routes its Apply / discard-then-save flows
    through the same API (`requestSave({errorMode: "rethrow"})` and
    `requestDiscard()`).

    The hook signature is `onSaveError(error, callbacks: { discard, retry })`;
    the coordinator dispatches between *render error dialog*, *rethrow*, and
    *swallow* via the named option `errorMode: "dialog" | "rethrow" | "silent"`
    (not a positional boolean). It also exposes `status: "clean" | "dirty" |
    "saving" | "error"` and `isSaving` as a single observable surface
    (SignalStore-reactive). **Consumer**: `FormStatusIndicator` subscribes via
    `useState(props.coordinator)` and derives its *saving* / post-error display
    states from it; the *typing* signal (indicator reacting before a change is
    committed to the record) still comes from the `FIELD_IS_DIRTY` model bus
    event + `record.dirty` — a deliberate two-source design, because the
    coordinator only observes committed changes. Route guards / dialog blockers
    remain potential future readers.

    **Out-of-contract callers**: field widgets that call `model.root.save()`
    directly (e.g. `fields/translation_button.js`, several addon widgets)
    bypass the coordinator; `status` does not reflect those saves. New
    form-level save paths must go through `requestSave`.

    The coordinator has no pre/post-save hooks: pre-save vetoes belong to the
    model-level `onWillSaveRecord` lifecycle hook (fired after validation), and
    `props.onSave` is invoked explicitly by the controller entry points.

13. **`patch()` targets prototypes and plain objects, never namespace
    imports** — `core/utils/patch.js`. Native ES module namespaces
    (`import * as X from "..."`) are **frozen by the ECMAScript spec**:
    properties are non-configurable, so `Object.defineProperty()` (which
    `patch()` uses internally) throws `TypeError`. Use one of:

    - **Class methods / instance behavior** → `patch(MyClass.prototype, {...})`
    - **Static methods** → `patch(MyClass, {...})` (the constructor object
      is configurable; only its `prototype` property is read-only)
    - **Services, env, plain config objects** → `patch(env, {...})`,
      `patch(services, {...})` — the object is mutable so this works directly

    What does NOT work and will throw at module load:

    ```js
    // ❌ WRONG — namespace is frozen
    import * as urlUtils from "@html_editor/utils/url";
    patch(urlUtils, { isAbsoluteURLInCurrentDomain(url) { ... } });
    ```

14. **`/web/webclient/load_menus` is a conditional fetch — don't break the
    hash round-trip** — every 200 response carries an `X-Menus-Hash` header
    (SHA-256 of the exact JSON bytes sent; `controllers/home.py:web_load_menus`).
    `menu_service.js` persists the hash in localStorage
    (`webclient_menus_hash`) alongside the cached menus and echoes it back as
    `?hash=` on the next boot; a match returns an empty `304` (headers only —
    the payload includes base64 app icons, so warm boots skip it entirely).
    `Cache-Control: no-store` is deliberate: the payload is session-dependent
    (access rights, debug mode), so the explicit hash round-trip *replaces*
    HTTP caching. If a mocked route or new code path serves menus without the
    header, the client drops the stored hash and the next boot fetches the
    full payload — degraded, not broken.

15. **`ListRecordRow` renders each list row as a component with an EXPLICIT
    row context** — `views/list/list_record_row.js`. As a component with
    referentially stable props, OWL's `arePropsDifferent` skips unchanged
    rows — a `t-call` inside `ListRenderer` would instead re-evaluate every
    cell of every row on ANY reactive change. The row's props ARE the
    contract: `record`/`group`/`groupId` (the row's own reactive — template
    reads define the row's re-render subscriptions), `api` (bound callbacks
    routing through the renderer instance so subclass overrides catch;
    built once by `ListRenderer.buildRowApi()`), `flags` (one stable
    reactive with the cross-row booleans; reading a flag subscribes that
    row to that key only), plus per-render invalidation keys (`columns`,
    `rowIndex`, `isEdited`, `canResequence`, ...). The row body stays at
    t-name `web.ListRenderer.RecordRow` and subclasses keep overriding
    `static recordRowTemplate`. To expose MORE to a subclass row template:
    extend `buildRowApi()` for methods (template: `api.x(...)`) and
    `getRowProps()` for state and derivations (template: `props.x`). Two
    rules with teeth: action callbacks must resolve record/group arguments
    back to the renderer's context (`resolveRowRecord`/`resolveRowGroup`) —
    the row holds a DIFFERENT reactive over the same record, so object
    identity (and Map keys, `indexOf`) against renderer-side records fails;
    and a per-row derivation whose inputs live outside the row's own record
    (a parent section's collapse state, say) belongs in `getRowProps`, so
    the renderer subscribes to the foreign inputs and prop-flips exactly
    the affected rows.

16. **Kanban progress bars reconcile drag-and-drop moves locally** —
    `views/kanban/progress_bar_hook.js`. A drag between groups registers the
    move up-front (`registerRecordMove(recordId, sourceGroupId,
    targetGroupId)`, capturing the record's progress-field value *before* the
    save can rewrite it); the save-triggered `updateCounts` then calls
    `_reconcileMove` to decrement/increment the two affected groups' bars and
    refetch aggregates for those two groups only — instead of firing
    `read_progress_bar` + `formatted_read_group` over the full domain.
    Falls back to the full refresh when local reconcile is impossible (bars
    not loaded, groups reloaded, progress field not fetched) or ambiguous
    (grouped on the progress field itself). A trailing authoritative refresh
    fires `MOVE_RECONCILE_DELAY` (300 ms) after the last reconciled move, so
    local arithmetic can never drift from the server for long. Failed or
    reverted moves must call `cancelRecordMove(recordId)`.

17. **`py_js` matches CPython on `%` formatting, but still has no int/float
    type** — `core/py_js/`. The evaluator is checked against CPython by a
    differential corpus. The remaining divergences, before you write an
    expression into a view's `domain=` / `context=`:

    **Tuples are distinguishable now (only where it matters).** Tuples and
    lists still both evaluate to plain JS arrays — every consumer (`Domain`,
    the ORM payload builders, ~115 pinned test expectations) depends on that.
    But a tuple literal additionally carries a non-enumerable `PY_TUPLE`
    Symbol, and `%` formatting is the one operator that reads it, because
    CPython's semantics genuinely differ:

    | Expression | CPython | py_js |
    |---|---|---|
    | `'%s' % (1, 2)` | `TypeError` | `TypeError` |
    | `'%s and %s' % (1, 2)` | `"1 and 2"` | `"1 and 2"` |
    | `'%s' % [1, 2]` | `"[1, 2]"` | `"[1, 2]"` |
    | `'abc' % 5` | `TypeError` | `TypeError` |
    | `'abc' % {'a': 1}` | `"abc"` (mappings exempt) | `"abc"` |

    Only `isPyTuple()` can observe the marker: `Array.isArray`,
    `JSON.stringify`, spread, iteration and deep-equality are untouched. Do
    not widen its use to equality or `repr` — `(1,2) == [1,2]` is
    deliberately `true` in py_js, and `Domain` relies on tuple-vs-list being
    interchangeable.

    **Still divergent — py_js has no int/float distinction.** JS has one
    number type, so anything whose Python output depends on int-vs-float
    renders as an int:

    | Expression | CPython | py_js |
    |---|---|---|
    | `str(1.0)` / `'%s' % 1.0` | `'1.0'` | `'1'` |
    | `float(1)` | `1.0` | `1` |
    | `1e3` | `1000.0` | `1000` |
    | `6/3` | `2.0` | `2` |

    Fixing this requires a boxed float type through the parser, interpreter
    and every consumer — do not paper over it in one function. Avoid
    `str()`/`%s` on a float in any expression that is evaluated on BOTH
    sides (a view domain compared against a server-computed string).

    **Unsupported constructs raise loudly** (a wrong *value* never silently
    reaches the server): slicing (`x[1:]`, `x[::-1]`), list comprehensions,
    the set operators `|` / `&`, `str.find/index/count`, `dict.keys()`, the
    builtins `sum` / `sorted` / `any` / `all` / `list`, and the `strftime`
    directives `%j` / `%y`. None currently appear in any `domain=` /
    `context=` attribute across `odoo`, `enterprise`, `agromarin` or
    `design-themes` — but adding one would work server-side and break the
    client, so extend `py_js` first if you need it.

18. **A list-wide derived flag must not round-trip inside one interaction** —
    `views/list/list_renderer.js` `rowFlags`. The flags object is the one place
    a value is shared by every row, and each row subscribes to the single key
    it reads (OWL re-targets a reactive prop to the child in **both** the
    `ComponentNode` constructor and `updateAndRender`, so a `reactive()` created
    with no callback still binds to the row). That is what makes the flags
    cheap — and also what makes a *transient* value expensive: every flip
    re-renders every row.

    `canSelectRecord` was derived from `list.editedRecord`, which is
    momentarily `null` in `enterEditMode` between the outgoing record leaving
    edition and the incoming one entering it. Moving the edited row therefore
    flipped it `false -> true -> false`, repainting all rows twice for a state
    no frame ever shows: **81 row renders on a 40-row list, now 4**. The fix is
    `DynamicList#isEditing` / `StaticList#isEditing`, which spans the handover
    via a `markRaw` holder (`_editHandover`) — `markRaw` so that claiming and
    releasing it notify nobody, otherwise the bookkeeping costs more renders
    than the round-trip it removes.

    The flags object had **two** such booleans, and fixing one left the other
    live. `hasEditedRecord` carried the identical round-trip, and the
    RecordRow template reads it only inside `column.buttons` — so it showed up
    on any list with a button column and on no other, which is why the first
    round of measurements missed it. It is now `isEditing`, named for what it
    means, derived from `list.isEditing` like its sibling. When you fix one
    member of a fan-out object, audit the rest of it.

    Rule: before publishing a derived boolean through `rowFlags` (or any other
    fan-out state), check what it does *during* a transition, not just at the
    endpoints. Endpoint-only tests pass either way — the regression guard in
    `static/tests/views/list/list_edit_handover.test.js` asserts on the value
    SEQUENCE across the interaction, and on a row-render budget, because those
    are the only things that can see it.

    Technique for auditing this: OWL's `ComponentNode.subscriptions` reports
    what a component is actually subscribed to, and
    `node.__owl__.fiber.root.node` tells a self-triggered render from one driven
    by the parent. `render_instrumentation.js` (`__renderTrace` /
    `__renderStats`) counts renders per component label.

### Property definitions and record identity

The field service exposes two representations of property definitions.
`loadPropertyDefinitions(model, fieldName, domain)` returns the name-indexed
mapping used by field-path consumers; duplicate names retain the historical
last-definition behavior. `loadPropertyDefinitionsByRecord(model, fieldName,
domain)` returns records with `definitionRecordId`, `definitionRecordName`, and
`definitions`, preserving properties with the same name in different records.
Both use the same RPC-loading implementation in `static/src/core/field_service.js`.

Search filters use the record-preserving representation because their domains
include the definition record. Group-by paths have no such record discriminator:
search combines compatible duplicate names into one item, and excludes paths
whose definitions disagree on type, relation, or selection/tag choices (including
labels). Choice order alone does not create a conflict. The ORM resolves one
definition for a group-by path: merging choices in the client would still group
values exclusive to another definition as unset. If a conflict appears during a
refresh, the old group-by and synthesized field metadata are retired.

Compatible filter refreshes update active choice labels while preserving criteria.
A removed choice keeps its saved value and label; dropping it would silently
broaden the search.

Property responses are applied only while their search item/view, field metadata
object, and active record still match. A newer expansion supersedes the previous expansion for that
item; group-definition requests coalesce only within the same field and active
record. Superseded failures are ignored, while current failures propagate.
