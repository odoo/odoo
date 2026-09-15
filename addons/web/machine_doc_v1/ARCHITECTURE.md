# Web Module Architecture

High-level structure, data flow, and component organization for `addons/web/`.

> **See also**: `COMPONENT_DIAGRAM.md` — 18 audit areas with file lists,
> invariants, and cross-cutting concerns. `FLOW_DIAGRAM.md` — 14 end-to-end
> sequence diagrams (bootstrap, RPC, auth, view loading, onchange, save, etc.).
> `DIRECTORY_MAP.md` — All 239 directory entries (238 subdirectories + the `(root)` row) mapped to FSD layers and responsibilities.
> `STATE_MANAGEMENT.md` — Decision tree for state patterns, record architecture, typed events.

## Module Identity

- **Name:** Web
- **Technical name:** `web`
- **Category:** Hidden (auto-installed with `base`)
- **Role:** Core webclient — the entire Odoo backend UI

## Layer Diagram

```
Browser
  |
  |  HTTP GET /odoo (SPA bootstrap)
  v
┌─────────────────────────────────────────────────────────┐
│  JavaScript (OWL Components + Services)                 │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐   │
│  │ Views    │  │ Model    │  │ UI       │  │Webcli- │   │
│  │ form     │  │ Record   │  │ dialog   │  │ent     │   │
│  │ list     │  │ lists    │  │ popover  │  │ navbar │   │
│  │ kanban   │  │ groups   │  │ tooltip  │  │ menus  │   │
│  │ calendar │  │ save     │  │ notif.   │  │ user   │   │
│  │ graph    │  │ ...      │  │ effects  │  │ menu   │   │
│  │ pivot    │  │          │  │ overlay  │  │        │   │
│  └────┬─────┘  └────┬─────┘  └──────────┘  └────────┘   │
│       │             │                                   │
│       └──────┬──────┘                                   │
│              │ orm.call(model, method, args, kwargs)    │
│              v                                          │
│  ┌───────────────────────────────────┐                  │
│  │ core/network/ (rpc.js, orm)       │                  │
│  │ POST /web/dataset/call_kw/{m}/{f} │                  │
│  └───────────────┬───────────────────┘                  │
└──────────────────│──────────────────────────────────────┘
                   │ JSON-RPC 2.0
                   v
┌──────────────────────────────────────────────────────────┐
│  Python (Controllers → ORM → Database)                   │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │ Controllers  │───>│ Models       │───>│ PostgreSQL │  │
│  │ dataset.py   │    │ web_read.py  │    │            │  │
│  │ action.py    │    │ web_read_    │    │            │  │
│  │ session.py   │    │  group.py    │    │            │  │
│  │ binary.py    │    │ web_onchg.py │    │            │  │
│  │ export.py    │    │ ir_http.py   │    │            │  │
│  │ report.py    │    │ ir_model.py  │    │            │  │
│  └──────────────┘    └──────────────┘    └────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Request Flow

1. **Component** calls `orm.create()` / `orm.read()` / `orm.call(model, method, args, kwargs)`
2. **ORM Service** builds URL `/web/dataset/call_kw/{model}/{method}`, merges user context
3. **RPC function** sends JSON-RPC 2.0 POST, optional caching via `rpcCache`
4. **Python controller** (`dataset.py:call_kw`) dispatches to ORM method
5. **ORM model** executes business logic, returns result
6. **RPC** resolves Promise (or rejects with `RPCError`)
7. **Component** updates state, OWL re-renders

## Directory Structure

Top-level layout of `addons/web/` (detailed maps are separate docs):

| Path | Contents | Map |
|------|----------|-----|
| `controllers/` | 24 `.py` — HTTP endpoints (22 Controller classes, 76 route handlers) | `ROUTE_MAP.md` |
| `models/` | 28 `.py` — ORM extensions (27 model files: web_read, web_read_group, ir_http, …) | `MODEL_MAP.md` |
| `static/src/` | 873 JavaScript/OWL source files across 249 directories (FSD layers) | `DIRECTORY_MAP.md` |
| `static/lib/` | 18 directories (17 vendored libraries + generated `popper_compat/`) — DO NOT MODIFY | `static/lib/versions.json` |
| `static/tests/` | 812 `.js` (incl. 746 `*.test.js` Hoot suites), mirroring the `static/src/` tree | `TEST_TAGS.md` |
| `tests/` | 68 Python test files (`test_*.py`) | `TEST_TAGS.md` |
| `machine_doc_v1/` | This directory: `COMPONENT_DIAGRAM.md` (18 audit areas) · `FLOW_DIAGRAM.md` (14 sequence diagrams) · `LAZY_VIEW_LOADING.md` · `VIEW_TEARDOWN_COST.md` (both decision records: investigated, not pursued) · `LIST_EDIT_RENDER_COST.md` (decision record: row-level waste fixed, renderer-level amplification measured and not pursued) · the maps below · `factcheck.sh` | — |
| `views/` · `data/` · `security/` · `i18n/` | XML templates, data fixtures, `ir.model.access.csv`, translations | — |

The `static/src/` JS layers are summarized in **JavaScript Architecture** below; the full per-directory layer + responsibility map is in `DIRECTORY_MAP.md`.

## JavaScript Architecture

Layered organization under `static/src/`:

| Layer | Directory | Purpose | Files |
|-------|-----------|---------|-------|
| **Boot** | `boot/` | Backend entry points: `main.js`, `start.js` (`env.js`, `session.js`, `module_loader.js`, `service_worker.js` sit at `src/` root) | 2 JS |
| **Primitives** | `core/` | Registry, utils, reactivity, browser abstraction, l10n, network + ORM, errors, py_js, tree, debug, hotkeys, navigation, `lib/` lazy ESM loaders | 193 JS |
| **Components** | `components/` | Reusable OWL UI components (dropdown, pickers, editors, file handling) | 111 JS |
| **UI** | `ui/` | Overlay layer and its services: dialog, popover, tooltip, notification, overlay, effects, block, alert, carousel, collapse, offcanvas, bottom sheet, command palette, PWA prompt | 47 JS |
| **Fields** | `fields/` | 68 widget directories in 7 subcategories (basic, display, media, relational, selection, specialized, temporal); 116 fork-wide `registerField` / `registerFallbackField` sites | 129 JS |
| **Views** | `views/` | View types: form, list, kanban, calendar, graph, pivot + view utilities + settings | 180 JS |
| **Webclient** | `webclient/` | App shell: home menu, navbar, menus, actions, user menu, colour scheme, density, debug/profiling, Studio upsell | 96 JS |
| **Search** | `search/` | Search model and mixins, search bar, facets, filters, group-by, favorites, embedded actions bar | 40 JS |
| **Model** | `model/` | Client-side relational data model (`RelationalRecord`, `StaticList`, groups, save orchestration) | 52 JS |
| **Public** | `public/` | Public (anonymous) page features; all run on `public.interactions`. Frontend app boot is `public/public_boot.js` (+ `public_boot_instance.js`, kept out of the test bundles via a `remove` directive); early-boot `lazyloader.js` / `minimal_dom.js` also live here. | 17 JS |
| **Vendored-in-src** | `libs/` | FontAwesome 7 icon CSS/webfonts + its JS glue, and `popper_compat.js` — vendored inside `src/` (unlike `static/lib/`) | 2 JS |

There is no `services/` layer. Every service is filed with the concern it serves,
so `orm` lives under `core/network/`, `dialog` under `ui/dialog/`, `action` under
`webclient/actions/`.

## Module faces

62 directories are fronted by a sibling `<name>.js` one level up — the module's
**published interface**. The face re-exports exactly what other addons import;
the files behind it are private and may be renamed, split, or moved without
touching a consumer. `@web/ui/dialog` is the face, `ui/dialog/dialog_service.js`
is an internal.

Was enforced by the architecture gates of the tooling tree, deleted in `7b0f58cb517f`, so these rules are now stated rather than checked: js_face_boundary.py (no import reaches
past a face into a fronted directory), js_component_face.py (which directories
under `components/` must HAVE one — a face is discovered rather than declared, so
the boundary gate says nothing about that), js_component_data_access.py
(no component acquires data at runtime — the pinned sites can only shrink;
so the debt cannot be paid once and re-spent), js_public_surface.py (the pinned surface
in `public_surface_web.txt` can only shrink), js_layer_cohesion.py,
js_import_resolution.py, js_private_access.py, js_cycle_check.py,
js_self_bridge.py (no module resolves itself through the loader — a generated
ESM bridge written over its own source exports only `undefined`, and every
name-based and graph-based gate above stays green on it),
js_shadow_root.py (every shadow root is attached through `attachShadowRoot`,
which marks its host: there is no `:has-shadow-root` selector and no event on
attach, so an unmarked host is one that `getTabableElements` and every other
root-crossing helper steps over in silence),
js_suite_parity.py (every source directory has a matching test directory),
js_context_narrowing.py (a `Pick<>` over a context bag names exactly what its
file reaches — over-declaring is invisible to tsc, so a consumer otherwise keeps
claiming a dependency it dropped) and
js_function_length.py, js_class_length.py (the mass a per-function budget
cannot see: `flow_editor.js` carries a 1,267-line component over 63 methods and
not one of them is a `jsfunclen` offender), js_unreached_assertions.py (an
assertion inside a callback the test never proves ran, which is
js_vacuous_assertions.py's defect one level down: that gate catches an
assertion that cannot fail, this one an assertion that may never execute),
js_layer_check.py (the Feature-Sliced layering above),
js_registry_layering.py (the same contract for dependencies mediated by a
registry rather than an import), js_deployment_layers.py (which bundle a module
may be reached from), js_extension_surface.py (the methods downstream
subclasses override, and the members they `patch()`), js_forced_render.py (core
must not sweep a subtree with `render(true)` — a forced render hides reads that
subscribe to nothing), js_patch_blind_facade.py (a service's own callers go
through its facade), js_service_shape.py (a service hands back an instance,
not a literal), js_class_length.py (the mass a per-function budget cannot see:
a class of short methods is invisible to js_function_length.py, and the unit is
excess lines above 400 rather than offender count, so splitting one huge class
into two large ones registers as the improvement it is),
js_unreached_assertions.py (an assertion that may never EXECUTE, one level down
from the vacuous assertion js_vacuous_assertions.py catches: an `expect()`
inside a handler the test never invokes stays green through the whole life of the
defect it names) and js_dead_icon_class.py (a test naming an icon class that
neither FontAwesome 7 nor any non-test source declares — a one-count assertion on
a renamed icon reads as a defect in the feature, and a negated one cannot fail).
Each shipped an empty-tree refusal test, so a gate that scanned nothing failed
instead of reporting a pass; none of them runs now.

## The contracts this module declares

Four of this addon's widest seams are not imports and not class members, so the
gates above are blind to every one of them: an object handed across a boundary
leaves no edge to check. Each is a declared list in the source. The gates that
measured who reaches each list, and the test that pinned this section against
them, went with the tooling tree in `7b0f58cb517f`: the lists are now read by
reviewers, not enforced.

| Contract | Declared in | Gate (deleted) | What it bounds |
|---|---|---|---|
| `env.config` | `views/view_config.js` | js_env_config_surface.py | The ambient per-action bag `View` installs with `useSubEnv`, inherited by every component beneath it. Five writers in this addon alone; three keys are written only by `enterprise` and are recorded, not owned. |
| `archInfo` | `views/arch_info.js` | js_arch_info_surface.py | The `ArchParser` output. Two of its keys (`fieldNodes`, `widgetNodes`) are compiled into generated OWL template *source*, where no type, linter or member gate can follow them; the gate also holds each view type's parser against what its own directory reads. |
| `props.record` | `fields/field_record_contract.js` | js_field_record_surface.py | What a field widget may reach on the record it is handed — 21 members, measured by resolving the binding rather than by grep. It also classifies each widget by what it *needs*, which is the worklist below. |
| `env.services.action` | `webclient/actions/action_service_contract.js` | js_action_surface.py | What a consumer may reach on the `ActionManager` instance. Same blindness as the rows above — the instance is handed out by name off `env.services`, so it is neither an import nor a class member. The contract under-declared until the gate existed: four members were classified internal while consumers reached them at 45 call sites. |
| OWL templates | the component's own `static template` | js_template_binding.py | Every name a template calls, against the class that owns it. Neither `tsc` nor `eslint` reads `.xml`, so a template is the one place a member reference has no static check at all — and Owl answers a missing one by destroying the root component. |
| `SearchModel` / `ListRenderer` mixins | — | js_mixin_coupling.py | Two `this`-collaborating compositions, each split this round (`search_properties_mixin.js` / `search_split_domain_mixin.js` out of `SearchModel`; `list_group_rendering.js` out of `ListRenderer`) — max SCC is now 4 units per composition, 12 of 17 edges cyclic; the gate ratchets against the SCCs regrowing rather than asking for further decomposition. |

### `fieldHandle` — a field widget's own field

`fields/field_handle.js` gives a widget `field.value`, `field.definition`,
`field.type` and `field.update(v)` in place of
`props.record.data[props.name]` and its two siblings. It is a **prototype
getter**, not a prop and not a `setup()` assignment, and both constraints are
load-bearing:

- **Not a prop.** OWL keys a subscription on the proxy a read travels through, at
  the moment of the read, so a handle built by the parent carries the *parent's*
  subscription — the child renders once with a correct value and never updates.
  See *There is no free-standing computed* in `STATE_MANAGEMENT.md`.
- **Not `this.field = ...` in `setup()`.** These widgets are subclassed heavily,
  and many subclasses override `setup()` without calling `super.setup()`. A
  prototype getter resolves regardless of what the subclass did.

Both are mounted as tests in `static/tests/fields/field_handle.test.js` rather
than argued about, because each fails silently.

`standardFieldProps` is deliberately unchanged: 155 widgets live across four
checkouts that cannot be committed atomically, so a widget adopts the handle one
at a time and the ones that genuinely need the record keep it. Do not restate the
counts here. The gate that measured them went with the tooling tree in
`7b0f58cb517f`, so re-measure from the source when a number matters.

## JavaScript Services

46 services are registered in `registry.category("services")` and injected via
`useService()`.

### Data services
| Service | File | Purpose |
|---------|------|---------|
| `orm` | `core/network/orm_service.js` | ORM gateway — see full API table below |
| `http` | `core/network/http_service.js` | Low-level HTTP fetch wrapper (GET/POST) |
| `field` | `core/field_service.js` | Field metadata loader (calls `fields_get` via `orm.cache({type:"disk", immutable:true})` — warm hits share one deep-frozen payload instead of deep-copying per caller) |
| `name` | `core/name_service.js` | Display name caching with microtask batching; clears cache on `ACTION_MANAGER:UPDATE` AND on `ACTIVE_COMPANIES_CHANGED` (load-bearing: a company switch via `recoverFromSaveError` uses `reload:false`, firing no `ACTION_MANAGER:UPDATE`, yet can flip record visibility). Not CLEAR-CACHES. Negative lookups (inaccessible/missing) are cached, so correctness depends on exactly these two visibility-change events — see the INVARIANT block in the source. |

#### `orm` full public API

18 methods on the `ORM` class (`orm_service.js` onward): the 16 RPC methods
tabulated below, all returning a Promise, plus the two proxy builders `cache()`
and `retry()` documented after the table — those return a derived `ORM`, not a
Promise.

| Method | Python call | Notes |
|---|---|---|
| `call(model, method, args=[], kwargs={})` | any | Lowest level; direct dispatch |
| `create(model, records[], kwargs)` | `create` | |
| `read(model, ids, fields, kwargs)` | `read` | **Short-circuits on empty ids** — no RPC |
| `search(model, domain, kwargs)` | `search` | |
| `searchRead(model, domain, fields, kwargs)` | `search_read` | |
| `searchCount(model, domain, kwargs)` | `search_count` | |
| `unlink(model, ids, kwargs)` | `unlink` | **Short-circuits on empty ids** |
| `write(model, ids, data, kwargs)` | `write` | |
| `webRead(model, ids, kwargs)` | `web_read` | |
| `webSave(model, ids, data, kwargs)` | `web_save` | |
| `webSaveMulti(model, ids, data[], kwargs)` | `web_save_multi` | |
| `webSearchRead(model, domain, kwargs)` | `web_search_read` | |
| `webReadGroup(model, domain, groupby, aggregates, kwargs)` | `web_read_group` | |
| `webResequence(model, ids, kwargs)` | `web_resequence` | **Forces `specification: {}`** if caller omits |
| `formattedReadGroup` / `formattedReadGroupingSets` | same | Result is mutated: each group gets `__domain` built from `Domain.and([domain, __extra_domain])` |

**Methods NOT on `orm`**: `nameSearch`, `name_create`, `readGroup` (use `orm.call(model, "name_search", ...)` etc.). `UPDATE_METHODS` constant (create/write/unlink/web_save/web_save_multi/action_archive/action_unarchive) is exported for cache-invalidation consumers AND used inside orm_service itself: it seeds the private `NON_IDEMPOTENT_METHODS` superset (`orm_service.js`, = `UPDATE_METHODS` + `web_resequence` + `name_create`), which `call()` checks to hard-reject `retry`/`dedup`/`cache` on write-class methods (throws before anything reaches the network).

**`orm.cache({type:"disk"})`** — proxy pattern (`orm_service.js`): `Object.assign(Object.create(this), {_cache: options})`. Every `call()` passes `cache: this._cache` to `rpc()`, where `rpcCache.read(table, key, fetcher, options)` is invoked. **table** = python method name (e.g. `"fields_get"`). **key** = the canonical, property-order-independent JSON identity of the route and captured parameters (`rpc_dedup.js`). Options pass through — `{type:"disk"}` and `{type:"ram"}` both valid; `cache:true` uses defaults. `{immutable:true}` makes warm hits share a single deep-frozen cached payload (`rpc_cache.js` — `immutable ? deepFreeze : deepCopy`) instead of deep-copying per read; only for consumers that never mutate the result (adopted by `field_service`).

**`orm.silent`** — same proxy pattern (`orm_service.js`) adds `_silent:true` to the RPC settings. It suppresses the **loading indicator** (`webclient/loading_indicator/loading_indicator.js`) and the **slow-rpc patience toast** (`core/network/slow_rpc_service.js`) — the only two `RPC:REQUEST`/`RPC:RESPONSE` consumers that check `settings.silent`. **It does NOT suppress error dialogs**: neither `core/errors/error_service.js` nor `components/errors/error_handlers.js` reads `silent`, so a failing `orm.silent` call still opens the normal error dialog. **Composable but not chainable with itself**: `orm.silent.cache({type:"disk"})` works; re-invoking `.silent` or `.cache()` re-creates, doesn't stack.

**`orm.dedup`** — same proxy pattern (`orm_service.js`) adds `_dedup: true` to subsequent calls. Concurrent callers issuing the same `(url, params)` key share a single in-flight fetch (stampede prevention for **uncached** reads). Redundant when chained onto `.cache(...)` — the cache layer already prevents duplicate fires. Each caller owns its subscription: aborting one rejects that caller with `ConnectionAbortedError`; the underlying fetch is cancelled when its last subscriber detaches. Never apply to writes.

**`orm.retry(options)`** — same proxy pattern (`orm_service.js`) adds `_retry: options` to subsequent calls. Accepts a number (interpreted as retries with default backoff) or a partial config `{retries, baseMs, maxMs}`. Composes with `silent` and `cache`: `orm.silent.cache({type:"disk"}).retry(1).call(...)` is the canonical boot-path-resilient idiom (see `core/field_service.js`, `views/view_service.js`). Caller is responsible for ensuring the call is idempotent — never apply to writes (create/write/unlink/web_save/web_save_multi/web_resequence/name_create).

**Context merging rule** (`orm_service.js`): `fullContext = {...user.context, ...(kwargs.context||{})}`. Spread order means **caller keys win on collision** — `user.context` values can be overridden, though the keys themselves cannot be deleted (omit from caller context to inherit, set to a new value to override).

**rpc.js settings whitelist** (`rpc.js`): `cache, silent, headers, timeout, retry, dedup, signal`. Unknown enumerable own keys throw. `cache` + `retry` compose: cache wraps retry so warm hits skip the retry layer entirely. `timeout` (milliseconds) installs an `AbortSignal.timeout()` that combines with the caller-controlled abort signal via `AbortSignal.any()`. No `credentials`.

RPC interception runs once per logical call, before parameters are serialized.
The captured JSON value supplies both cache/dedup identity and every transport
attempt. Stateful getters, `toJSON`, caller mutations during retry backoff, and
RPC event listeners cannot change a retry's body. `toJSON` receives the real
`params` property name; omitted parameters remain omitted. Each attempt still
has a fresh request ID and separate event data. Null or omitted parameters do
not change a server error into a retryable transport failure.
Header values and cache/retry option containers are captured before parameter
serialization too. Mutating caller options cannot change a retry's header
identity or poison the cache variant chosen for the original call. Each request
and response event gets its own settings copy; abort signals and callbacks keep
their identity internally. Synchronous transport setup failures in a retry chain
reject its promise, including when setup fails inside a backoff timer.
Supported top-level settings are read by name once, including non-enumerable
and inherited accessors. If a transport wrapper throws synchronously after
request notification, the normal failure path still emits the matching response
and applies transport-error classification and retry policy.

Cached responses with custom headers are isolated by canonical header values in
RAM, even when disk caching is requested. The transport's forced JSON Content-Type
does not create a variant. Opaque, never-reused scope IDs keep header values out
of stored cache keys; the bounded scope index can evict an identity without
assigning its old cached response to another identity. Header-free requests retain
disk caching. Synchronous fallback failures follow the normal rejection cleanup,
so corrected requests can retry and a failed background refresh preserves warm data.

Response envelopes must contain exactly one of `result` or a structured `error`.
Falsy results are valid. Malformed successful responses are non-retryable
`InvalidResponseError`s; malformed 5xx responses retain server-overload retry behavior.

**Error class hierarchy** (`rpc.js`):
- `NetworkError` (base) — all network/RPC failures
- `RPCError extends NetworkError` — server-returned errors; `{name:"RPC_ERROR", type:"server", code, data, exceptionName, subType}`. **Never retryable** (server-deterministic).
- `ConnectionLostError extends NetworkError` — HTTP 502/503/504, a JSON parse failure on a **5xx** response, or a fetch network failure (DNS, CORS, server unreachable). Frontend never sees a status code for these. **Retryable**.
- `ServerOverloadError extends ConnectionLostError` — Server returned a non-JSON content-type (typically werkzeug HTML traceback from ``PoolError`` / ``OperationalError``). Carries ``status`` so callers can branch on the actual HTTP code; the message embeds it. Backward-compatible with existing ``instanceof ConnectionLostError`` catchers. **Retryable with a 1000ms backoff floor** so retries don't pile onto an overloaded backend (``SERVER_OVERLOAD_BACKOFF_FLOOR_MS`` in ``rpc.js``). The floor is applied **after** the caller's ``maxMs`` cap and therefore outranks it: ``retry({ maxMs: 500 })`` still waits 1000ms against an overloaded server. Backing off harder is the entire purpose of the branch, so a caller asking for a shorter ceiling does not get to shorten it.
- `InvalidResponseError extends NetworkError` — a non-5xx response that is not valid JSON-RPC (canonically a **session-expired POST redirected to the login page as an HTTP 200 HTML body**). Carries `status` and `url`. It extends `NetworkError` **directly, NOT `ConnectionLostError`**: a well-formed HTTP response did arrive, the connection is fine, and retrying returns the same non-JSON — so it is `retryable = false`. Consumers that must react to it (the session-expired handler, spreadsheet collaboration, POS sync) name it explicitly rather than relying on a `ConnectionLostError` is-a they would then all have to carve back out. `lostConnectionHandler` (`components/errors/error_handlers.js`) still owns it, and says so in a comment: it admits the class alongside `ConnectionLostError` and branches to `handleInvalidResponse` **before** the reconnect path, routing by HTTP status — only a **status-200** invalid response (the session-expired POST redirected to the HTML login page) opens `SessionExpiredDialog` (deduped by a module-level guard so concurrent failures don't stack modals); a **non-200** status (e.g. the multi-db HTML 404 when no database matches, a captive portal) opens `NetworkErrorDialog` instead, since re-authenticating cannot help there. Neither path enters the version_info reconnect poll. Note the classification only fires once the response body is read: an `abort()` that lands mid-body is re-checked (`aborted` guard around `await response.json()`) so a silently-aborted RPC is never mis-tagged as this error.
- `ConnectionAbortedError extends NetworkError` — caller invoked `promise.abort(true)` or an external `AbortController` aborted the signal. `abort(false)` silently cancels without rejection. **Never retryable** (caller intent).
- `ConnectionTimeoutError extends NetworkError` — `AbortSignal.timeout(ms)` fired (settings.timeout exhausted). Carries `url` and `timeoutMs` so callers can decide whether to retry, alert, or escalate. **Retryable**.
- `RequestEntityTooLargeError extends NetworkError` — HTTP 413: the request body exceeded the max size accepted by the server or a fronting proxy (e.g. nginx `client_max_body_size`). Surfaced so a save can block/warn instead of silently failing. **Never retryable** (the payload is what's rejected).

### UI Overlay Services (`ui/`)
| Service | File | Purpose |
|---------|------|---------|
| `ui` | `ui/ui_service.js` | Viewport size tracking, active element management, block UI |
| `dialog` | `ui/dialog/dialog_service.js` | Modal dialog stack management |
| `overlay` | `ui/overlay/overlay_service.js` | Base overlay layer manager (dialogs, popovers, tooltips) |
| `popover` | `ui/popover/popover_service.js` | Positioned popover with escape/clickaway |
| `tooltip` | `ui/tooltip/tooltip_service.js` | Data-attribute tooltip system |
| `notification` | `ui/notification/notification_service.js` | Toast notifications |
| `bottom_sheet` | `ui/bottom_sheet/bottom_sheet_service.js` | Mobile bottom sheet |
| `effect` | `ui/effects/effect_service.js` | Visual effects (rainbow_man, etc.) |
| `dismiss_alert` | `ui/alert/dismiss_alert_service.js` | One delegated click listener dismissing alerts declared in view arch (replaces Bootstrap's `data-bs-dismiss="alert"`; arch compiles to a template, so there is no component to hold the handler) |

### Input services
| Service | File | Purpose |
|---------|------|---------|
| `hotkey` | `core/hotkeys/hotkey_service.js` | Keyboard shortcut registration |
| `command` | `ui/commands/command_service.js` | Command palette (Ctrl+K) |
| `file_upload` | `core/file_upload/file_upload_service.js` | XHR file upload with progress |
| `datetime_picker` | `components/datetime/datetime_picker_service.js` | Date/time picker popover |

### Infrastructure Services
| Service | File | Purpose |
|---------|------|---------|
| `localization` | `core/l10n/localization_service.js` | Translation loader (IndexedDB cached, versioned by `registry_hash`) |
| `error` | `core/errors/error_service.js` | Global error handler (`sequence: 1` — starts first, only sequenced service in core) |
| `scss_error_display` | `ui/scss_error_display.js` | SCSS compilation error display. Detects a `css_error_message` marker rule in same-origin backend stylesheets and shows a sticky danger notification. **Gated to admins / debug mode** — the service early-returns unless `user.isAdmin` or `odoo.debug` is truthy (`scss_error_display.js:28`), so a regular user in a non-debug session never sees the toast (matching the message text, which addresses an administrator/developer). |
| `title` | `core/browser/title_service.js` | Document title management |
| `pwa` | `ui/pwa/pwa_service.js` | PWA install prompt |
| `sortable` | `core/utils/dnd/sortable_service.js` | Drag-and-drop sorting |
| `tree_processor` | `core/tree/tree_processor_service.js` | Tree data structure processor (deps: `field`, `name`) |
| `web.frequent.emoji` | `components/emoji_picker/frequent_emoji_service.js` | Emoji frequency tracking (dotted namespace key) |
| `service_worker` | `webclient/service_worker_service.js` | Registers `/web/service-worker.js` (scope `/odoo`), promotes waiting workers via `SKIP_WAITING`, polls for updates, and exposes `activated` — a promise that settles on EVERY exit path (mail's push (un)subscribe awaits it inside a `Mutex`, so a pending one wedges that mutex for the session). Deliberately under `webclient/` and not `core/` or `ui/`: `web.assets_frontend` globs `core/**` and `ui/**`, so a service placed there would register this backend worker on every public page. |
| `home_menu` | `webclient/home_menu/home_menu_service.js` | Registers the `menu` client action that renders `HomeMenu` (the app drawer the client lands on) and exposes reactive `hasHomeMenu` / `hasBackgroundAction` flags plus `toggle(show)`, which `WebClient._loadDefaultApp` and the navbar toggle call; serialised by a `Mutex` so a double click cannot interleave `doAction("menu")` with `restore()` |
| `enterprise_subscription` | `webclient/home_menu/enterprise_subscription_service.js` | `SubscriptionManager` over `session.expiration_date` / `expiration_reason` / `warning` / `sysadmin_message` (set by `ir_http._get_expiration_info`): drives the `ExpirationPanel` banner and `SysAdminPanel` on the home menu, blocks the UI once `daysLeft <= 0`, and talks to `publisher_warranty.contract` to register or recheck a subscription code |
| `color_scheme` | `webclient/color_scheme/color_scheme_service.js` | Resolves the active light/dark scheme from the user's `res.users.settings` preference and the `(prefers-color-scheme:dark)` media query; drives the `dark_mode_toggle` systray item |
| `lazy_session` | `webclient/session_service.js` | Lazy-loaded session info (profile_session, profile_collectors, etc.). Consumed by `profiling` service — refactoring this breaks profiling startup. |
| `template_compile_cache` | `core/template_compile_cache.js` | OWL's compiled templates cached in the browser (deps: `localization`): the root app's `_compileTemplate` is routed through a content-addressed store of the compiler's output (IndexedDB versioned by the registry hash; key = OWL version / lang / translations hash / template text hash), read once at boot, written behind on a miss; off in dev and test mode. `seed(key, code)` is the seam a server-side compiler would fill. |
| `multi_company_recovery` | `core/multi_company_recovery_service.js` | Recovers from `AccessError` when the server context carries `suggested_company`. `recoverFromLifecycleError` reloads after activating; `recoverFromSaveError` mutates the model context and activates with `reload:false` to preserve input. Used by FormController's onError paths. |
| `form_dialog_stack` | `views/form/form_dialog_stack_service.js` | Single global counter of open form-in-dialog instances, mutated by direct `push()`/`pop()` calls from `useFormViewInDialog`; exposes `count`/`isEmpty` getters (`pop()` floors at 0 and warns in debug on an unbalanced call). Read by `beforeVisibilityChange` to suppress tab-switch auto-save while a child form dialog is active. |
| `result_set_cache_invalidator` | `core/network/result_set_cache_invalidator_service.js` | Emits `CLEAR-CACHES` on `unlink`/`action_archive`/`action_unarchive` and on `action_install_lang` (see `STATE_MANAGEMENT.md`) |
| `web_vitals` | `core/network/web_vitals/web_vitals_service.js` | Core Web Vitals RUM collection; beacons to `/web/observability/cwv` on pagehide |
| `connection_recovery` | `core/network/connection_recovery_service.js` | Owns the reconnect notification/poll driven by `lostConnectionHandler`, which lives in `components/errors/error_handlers.js` and only consumes it |
| `allowed_qweb_expressions` | `mail/static/src/core/common/allowed_qweb_expressions_service.js` | Async service (deps: `orm`) resolving the allowed QWeb expression list per model. **Owned by `mail`, not `web`** — `web` only consumes it, through `useOptionalService` in `fields/dynamic_placeholder_popover.js`, which is why that call site is the optional variant. The path cited here was core/allowed_qweb_expressions_service.js (deliberately unbackticked: it is a file this module has never had, and factcheck resolves every backticked path). |
| `public.interactions` | `public/interaction_service.js` | Public-page interaction registry/lifecycle (frontend equivalent of the backend component tree) |
| `demo_data` | `views/settings/widgets/demo_data_service.js` | Caches whether demo data is active (Settings widgets) |
| `user_invite` | `views/settings/widgets/user_invite_service.js` | Caches the user-invite panel payload (Settings widgets) |
| `fillTemporalService` | `views/fill_temporal_service.js` | `FillTemporal`: one memoised `FillTemporalPeriod` per model + date field + granularity, whose `getDomain()` widens a group-by domain to a whole cycle so `_read_group_fill_temporal` can emit the empty periods. Moved here from `crm` on 2026-08-28 (the ORM feature is core; nothing in it is about leads); its only consumer is still crm's forecast views, reached through the registry |
| `slow_rpc` | `core/network/slow_rpc_service.js` | Patience-UX: shows a sticky `notification.add(_t("This is taking longer than usual…"))` toast when a non-silent RPC exceeds `SLOW_RPC_CONFIG.thresholdMs` (default 5 s, mutable). Listens on `rpcBus` for `RPC:REQUEST`/`RPC:RESPONSE`; success, error, abort, and timeout all clear the timer. Silent RPCs opt out, as with error dialogs. |

> Additional webclient-level services: `action`, `menu`, `view`, `currency`,
> `density`, `profiling`, `reloadCompany`, `shareTarget`. These live in `webclient/` or `views/`.

## View Types

Each view type lives in `static/src/views/<type>/`:

| Type | Directory | Multi-record | Purpose |
|------|-----------|-------------|---------|
| Form | `views/form/` | No | Single record editing |
| List | `views/list/` | Yes | Tabular browsing, inline edit, sorting |
| Kanban | `views/kanban/` | Yes | Card columns, drag-drop |
| Calendar | `views/calendar/` | Yes | Event calendar (day/week/month) |
| Graph | `views/graph/` | Yes | Charts (bar, line, pie). The view is in `assets_backend`; only the Chart.js *library* is lazy (`core/lib/chartjs.js` `loadChartJS()`) — see CONVENTIONS gotcha #6 |
| Pivot | `views/pivot/` | Yes | Crosstab analysis. In `assets_backend`; not lazy-loaded |

Field widgets (68 widget directories across 7 subcategories; 116 fork-wide `registerField` / `registerFallbackField` sites, 82 plain and 34 through the typed spec form) live in `fields/` (top-level). Import path: `@web/fields/*`. Registration goes through `registerField()` / `registerFallbackField()` in `fields/_registry.js`, never `registry.category("fields").add()` directly.

## Controller Utilities (`views/view_utils.js`)

Shared logic extracted from form, list, and kanban controllers to eliminate duplication:

| Export | Purpose |
|--------|---------|
| `useControllerServices()` | Returns `{ action, dialog, notification, orm, uiHooks }` — replaces 4 `useService()` calls + `makeModelUIHooks()` in each controller |
| `makeModelUIHooks({ action, dialog, notification })` | Builds 8 hook implementations so model/record/list never import UI services directly |
| `computeArchiveEnabled(fields, { presentIn = fields })` | Shared active/x_active writability check. `presentIn` decides *which* of `active`/`x_active` is consulted; writability is always read from `fields`. `multi_record_controller` passes `props.fields` alone; `form_controller` passes `{ presentIn: this.model.root.activeFields }` so a field absent from the arch does not enable archiving. |
| `getActionMenuItems(staticItems, actionMenus)` | Shared filter-sort-map pipeline for action menu items |

**Model UI Hooks** (injected via `makeModelUIHooks`):
`onDisplayOnchangeWarning`, `onDisplayInvalidFields`, `onDisplayUrgentSave`, `onDisplayPropertyWarning`, `onDisplayArchiveAction`, `onConfirmArchive`, `onConfirmDuplicate`, `onDisplayLimitNotification`

> The data layer (`RelationalModel`, `Record`, `DynamicList` in `model/`) calls these hooks
> instead of importing dialog/notification/action services directly. Controllers wire the
> hooks via `useControllerServices()`. This decouples the data layer from UI concerns.

## Asset Pipeline (ESM + esbuild)

The web module ships **native ES modules**, delivered to the browser via an inline `module_loader.js` shim plus an esbuild-bundled `<script type="module">`. Marker convention: every native source carries `/** @odoo-module native */`; **zero** `odoo.define()` calls remain. ESM bundle membership is **declarative**: each module lists its bundles under an `esm` manifest key, aggregated and validated by `odoo.tools.assets.esm_registry.esm_registry()`. Full pipeline — loader contract, the `esm` manifest schema (`bundles` / `dynamic_children` / `import_map_includes` / `secondary_import_map_includes`), esbuild flags, import-map bridging, failure modes, and tunable `web.esbuild.*` params — is in **`ESM_BUNDLING.md`**.

### `remove` and `after` directives (manifest bundle composition)

The manifest uses 24 `remove` tuples to strip files from parent bundles, plus `after` directives for position-sensitive SCSS insertion. Load-bearing for refactors — removing a file from a `remove` list silently re-enables it in every bundle that composes the parent.
- `web.assets_backend` removes `clickbot.js`, `**/*.dark.scss`, all of `actions/reports/**/*` (re-adds `.js`/`.xml` only), `button_box/*.scss`
- `web.assets_frontend` globs `ui/**`, `components/**` and `core/**`, then removes `ui/commands/**` (re-adding `default_providers.js` + `command_palette.js`), `emoji_data.js`, `database_manager.js`
- `web.report_assets_common` swaps `utilities_custom_backend.scss` + `bootstrap_review_backend.scss` for `utilities_custom_report.scss` via `after`

### Module metadata (`__manifest__.py`)
- `depends: ["base"]` · `auto_install: True` · `bootstrap: True` (loaded during server bootstrap, before regular addons)
- `data:` — 19 XML/CSV files (`webclient_templates.xml`, `report_templates.xml`, `web_menus.xml`, `ir.model.access.csv`, `web_cwv_metric_views.xml`, `web_cwv_metric_data.xml`, …)
- `external_dependencies`: none declared (vobject imported inline in `res_partner.py`); no demo data

## Asset Bundles

Defined in `__manifest__.py`. Bundles group JS/CSS/SCSS for specific contexts.

### Main Bundles (served to browser via `t-call-assets`)

| Bundle | Context | Includes |
|--------|---------|----------|
| `web.assets_web` | Full backend | `assets_backend` + `main.js` + `start.js` entry points |
| `web.assets_backend` | Backend components | Bootstrap, OWL, every service, **all views including graph + pivot**, webclient shell |
| `web.assets_frontend` | Public pages | OWL, Bootstrap, `core/**` + `ui/**` + `components/**` (no backend views) |
| `web.assets_frontend_minimal` | Early bootstrap | Session bootstrap (session.js), cookies (core/browser/cookie.js), minimal DOM helpers (core/utils/dom/ui.js), lazyloader + minimal_dom (static/src/public/). **Does NOT contain `module_loader.js`** — the loader shim is emitted inline, not via any bundle. |
| `web.assets_frontend_lazy` | Frontend extended | Full frontend with all components |
| `web.assets_web_dark` | Dark mode | CSS overrides for backend |
| `web.assets_web_print` | Print | Print stylesheet overrides |
| `web.assets_emoji` | Emoji picker | Emoji data (lazy loaded) |
| `web.report_assets_common` | Reports | Common report assets |
| `web.report_assets_pdf` | PDF reports | PDF-specific report assets |

### Internal Sub-Bundles (composition via `include`)

| Bundle | Purpose |
|--------|---------|
| `web._assets_core` | `session.js`, `env.js`, `ui/**`, `components/**`, `core/**` (minus `emoji_data.js` and every `*.dark.scss`) — bundled as native ESM via esbuild. **OWL is NOT in this bundle** — it is loaded separately via a non-deferred `<script src="@odoo/owl">` resolved through the import map before the ESM bundle evaluates (see `ESM_BUNDLING.md`). The `module_loader.js` shim is also NOT part of this bundle; it is emitted separately by `ir.qweb._build_loader_shim_js()` as an inline `<script>`. Included only by `web.assets_backend`. |
| `web._assets_helpers` | SCSS functions, mixins, variable definitions |
| `web._assets_bootstrap` | Bootstrap SCSS (shared base) |
| `web._assets_bootstrap_backend` | Bootstrap SCSS (backend variant) |
| `web._assets_bootstrap_frontend` | Bootstrap SCSS (frontend variant) |
| `web._assets_backend_helpers` | Backend-specific SCSS overrides |
| `web._assets_frontend_helpers` | Frontend-specific SCSS overrides |
| `web._assets_primary_variables` | SCSS color/size variables |
| `web._assets_secondary_variables` | SCSS derived variables |

### Test Bundles

| Bundle | Purpose |
|--------|---------|
| `web.assets_unit_tests_setup` | HOOT framework + all backend assets + clickbot |
| `web.assets_unit_tests_setup_ui` | HOOT framework + minimal UI (no backend) — mobile/public test subset |
| `web.assets_unit_tests` | All JS test files (except tours) — the HOOT unit-test bundle |
| `web.assets_tests` | Tour test utilities and tour definitions (loaded on backend + frontend pages via `web.conditional_assets_tests`) |
| `web.assets_clickbot` | Click-everywhere automated UI testing bot |

### Library Bundles

| Bundle | Library | Version |
|--------|---------|---------|
| `web.ace_lib` | ACE code editor (Python, XML, QWeb, JS, SCSS, JSON modes) | 1.44.0 |

Chart.js (+ its luxon adapter), FullCalendar, signature_pad, DOMPurify and
pdf.js carry **no bundle**: they are ES modules resolved through import-map bare
specifiers (`chart.js`, `chartjs-adapter-luxon`, `@fullcalendar/core`,
`signature_pad`, `dompurify`, `pdfjs-dist`) and lazy-loaded via dynamic
`import()` — `core/lib/chartjs.js` (`loadChartJS()`), `core/lib/fullcalendar.js`
(`loadFullCalendar()`), `components/signature/name_and_signature.js`,
`core/utils/pdfjs.js` (`loadPDFJS()`). No `<script>` injection and no
`window.Chart` / `window.FullCalendar` globals — importers read the live-bound
exports after the loader resolves. See CONVENTIONS.md gotcha #6.

### Vendored libraries (`static/lib/`)

**`static/lib/versions.json` is the single source of truth** for what is vendored
and at which version.

It was machine-checked by a drift and advisory checker in the tooling tree,
deleted in `7b0f58cb517f`; nothing re-derives the versions from the shipped bytes now.

Do not restate versions here — read `versions.json`, and see
`static/lib/README.md` for the per-library update procedure, the `AgroMarin:`
in-file divergence markers, and the libraries needing extra care (`dompurify`,
`fullcalendar`, `pdfjs`, `popper_compat`, `zxing-library`).

18 directories: 17 vendored libraries plus `popper_compat/`, which is **not a
vendored library** but a generated self-contained build of
`@web/libs/popper_compat.js` (it replaced Popper; Bootstrap was Popper's only
importer). Bundles inline the source module instead — only import-map pages (the
IoT box homepage, the database manager, the error page) load the built copy.
`owl` is upstream `dist/owl.es.js` verbatim, a published npm release rather than
an in-tree fork; only `hoot` and `hoot-dom` are internal, versioned with the fork.

## File Counts

| Category | Count |
|----------|-------|
| Python (controllers) | 24 (22 Controller classes across 20 route-bearing files + `__init__.py`, `export_writers.py`, `json_helpers.py`, `utils.py`) |
| Python (models) | 28 (27 model files + `__init__.py`) |
| Python (tests) | 68 (`test_*.py`; 69 files incl. `__init__.py`) |
| JavaScript (src) | 873 (871 carry `@ts-check`; `module_loader.js` + `service_worker.js` are the two exclusions) |
| JavaScript (tests) | 812 (incl. 746 `*.test.js` Hoot suites) |
| JavaScript (vendored libs) | 94 |
| SCSS/CSS | 213 (34 in `static/src/scss/` shared base; remaining 179 co-located with JS components) |
| XML (views/ + data/ + static/src OWL templates) | 293 (14 views + 5 data + 274 OWL templates) |
| i18n (.po + .pot) | 61 |
| Total | ~2,140 |


Launcher customization uses `HomeMenuLayout` in `webclient/home_menu/home_menu_layout.js` for optimistic edits, serialized saves, failure/retry state and company inheritance. Saves send operations to `res.users.settings.update_homemenu_config`; independent pins/hides merge against a locked record, and lock contention requests a transaction retry. Reset clears personal ownership; an explicitly empty version-2 layout remains personal. Cross-tab storage hints are scoped by database/user and trigger an authoritative read. Home registers the action service’s before-leave hook to drain queued saves, including edits made while navigation waits; browser unload warns while edits remain unsaved. Post-save UI callback failures do not replay committed operations. Badge reload detection includes app module/model metadata, so ownership changes are reflected without changing app IDs.

Home and QuickLauncher share the accessible app catalog and app search keys. App ownership derives from the existing external ID namespace, with an icon-path fallback for legacy entries. Badge providers receive the full catalog in stable order; the loader isolates synchronous/asynchronous failures, rejects non-finite/fractional counts and caps asynchronous provider timeouts at five seconds. Optional subscriptions invalidate the service-environment cache while a launcher is mounted; Mail watches inbox/activity changes. Request generations prevent stale responses from replacing newer counts. Studio places its icon-edit button beside the app link, matching the Home tile's separate customization controls.
