# Web Module — Component Diagram

Subsystem map. Each section is an **audit area**: a file group reviewable in one
session.

Measured at base `b48ae612546`, 2026-08-01.
Lines = `wc -l`. Directory counts = `find <dir> -type f | wc -l`, all extensions.

Guard: `bash addons/web/machine_doc_v1/factcheck.sh` — read-only, exits 1 on
drift. Checks line counts, directory counts, cited paths, quoted constants, and
claims of absence.

There is **one** harness, and it is not scoped to `machine_doc_v1/` — it reads
`static/`, `controllers/`, `models/` and the repo's `.github/workflows/` too.
This header used to name a second guard under a since-deleted addons/web/doc
directory and call the two separate. That was true until `b6c0619c571`
dissolved that directory, folding its 164 lines into this one; the sentence
outlived the split it described. Nothing caught it because the path sat inside
a backticked *command*, which the harness's own cited-path scan did not look
inside — fixed there, so a stale path in a `bash …` span now fails.

The dead path is spelled without backticks on purpose: in these docs a
backticked path is an assertion that the file exists, and the guard resolves
every one of them. Naming a deliberately-absent file is the one case where
prose must not reach for them.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BROWSER                                        │
│                                                                             │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────────────────────┐   │
│  │   BOOT      │  │   WEBCLIENT      │  │   MAIN COMPONENTS             │   │
│  │   SEQUENCE  │──▶   SHELL          │──▶   CONTAINER                   │   │
│  │             │  │                  │  │  (Dialog, Notification, ...)  │   │
│  └─────────────┘  └──────┬───────────┘  └───────────────────────────────┘   │
│                          │                                                  │
│           ┌──────────────┼───────────────────────┐                          │
│           ▼              ▼                       ▼                          │
│  ┌──────────────┐ ┌─────────────┐  ┌─────────────────────┐                  │
│  │   NAVBAR     │ │   ACTION    │  │   SEARCH SYSTEM     │                  │
│  │   + MENUS    │ │   SERVICE   │  │   (SearchModel,     │                  │
│  │   + SYSTRAY  │ │   + STACK   │  │    ControlPanel,    │                  │
│  └──────────────┘ └──────┬──────┘  │    SearchPanel)     │                  │
│                          │         └──────────┬──────────┘                  │
│                          ▼                    │                             │
│              ┌───────────────────────┐        │                             │
│              │   VIEW LAYER          │◀───────┘                             │
│              │  ┌──────┬──────┐      │                                      │
│              │  │ Form │ List │ ...  │                                      │
│              │  └──┬───┴──┬───┘      │                                      │
│              └─────┼──────┼──────────┘                                      │
│                    │      │                                                 │
│           ┌────────┘      └────────┐                                        │
│           ▼                        ▼                                        │
│  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────────────┐  │
│  │   FIELD WIDGETS  │  │   DATA MODEL      │  │   UI SYSTEM              │  │
│  │  (68 dirs)       │  │  (RelationalModel │  │  (Dialog, Notification,  │  │
│  │                  │  │   Record, Lists)  │  │   Popover, Tooltip,      │  │
│  └──────────────────┘  └────────┬──────────┘  │   Overlay, Effects)      │  │
│                                 │             └──────────────────────────┘  │
│                                 ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │   CORE SERVICES                                                      │   │
│  │  ┌─────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐ ┌────────────────┐    │   │
│  │  │ ORM │ │ HTTP │ │ User │ │ Hotkey │ │ Menu │ │ Localization   │    │   │
│  │  └──┬──┘ └──┬───┘ └──────┘ └────────┘ └──────┘ └────────────────┘    │   │
│  └─────┼───────┼────────────────────────────────────────────────────────┘   │
│        │       │                                                            │
│  ┌─────┴───────┴────────────────────────────────────────────────────────┐   │
│  │   CORE INFRASTRUCTURE                                                │   │
│  │  ┌──────────┐ ┌────────┐ ┌───────┐ ┌────────┐ ┌──────────────────┐   │   │
│  │  │ Registry │ │ Router │ │ RPC   │ │ py_js  │ │ Utils            │   │   │
│  │  │          │ │        │ │ Cache │ │ (Eval) │ │ (hooks, timing)  │   │   │
│  │  └──────────┘ └────────┘ └───┬───┘ └────────┘ └──────────────────┘   │   │
│  └──────────────────────────────┼───────────────────────────────────────┘   │
│                                 │                                           │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │ JSON-RPC 2.0
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVER (Python)                                │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │   CONTROLLERS (HTTP Routing)                                         │   │
│  │  ┌──────────┐ ┌─────────┐ ┌────────┐ ┌────────┐ ┌───────────────┐    │   │
│  │  │ dataset  │ │ session │ │ home   │ │ binary │ │ webclient     │    │   │
│  │  │ (RPC GW) │ │ (Auth)  │ │ (Boot) │ │ (Files)│ │ (Assets/i18n) │    │   │
│  │  └────┬─────┘ └────┬────┘ └────┬───┘ └────┬───┘ └───────────────┘    │   │
│  │       │            │           │          │                          │   │
│  │  ┌────┴─────┐ ┌────┴────┐ ┌────┴───┐ ┌────┴───┐ ┌───────────────┐    │   │
│  │  │ action   │ │ export  │ │ report │ │ domain │ │ json (API)    │    │   │
│  │  │ (Load)   │ │ (CSV/XL)│ │ (PDF)  │ │ (Valid)│ │ (Bearer)      │    │   │
│  │  └──────────┘ └─────────┘ └────────┘ └────────┘ └───────────────┘    │   │
│  │  ┌──────────┐ ┌─────────┐ ┌────────┐ ┌─────────────────────────┐     │   │
│  │  │ database │ │ pivot   │ │ vcard  │ │ profiling, webmanifest  │     │   │
│  │  │ (DB Mgmt)│ │ (XLSX)  │ │        │ │ settings, model, view   │     │   │
│  │  └──────────┘ └─────────┘ └────────┘ └─────────────────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                 │                                           │
│  ┌──────────────────────────────┼───────────────────────────────────────┐   │
│  │   MODELS (ORM Extensions)    │                                       │   │
│  │                              ▼                                       │   │
│  │  ┌──────────────────────────────────────────────┐                    │   │
│  │  │  WEB DATA ACCESS (extends 'base')            │                    │   │
│  │  │  ┌──────────┐ ┌──────────────┐ ┌───────────┐ │                    │   │
│  │  │  │ web_read │ │web_read_group│ │web_onchange│ │                   │   │
│  │  │  │ web_save │ │read_progress │ │  snapshot  │ │                   │   │
│  │  │  │ web_sread│ │  _bar        │ │            │ │                   │   │
│  │  │  └──────────┘ └──────────────┘ └───────────┘ │                    │   │
│  │  │  ┌───────────────┐ ┌──────────────────────┐  │                    │   │
│  │  │  │web_search_panel│ │ record_snapshot      │  │                   │   │
│  │  │  └───────────────┘ └──────────────────────┘  │                    │   │
│  │  └──────────────────────────────────────────────┘                    │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────┐                    │   │
│  │  │  FRAMEWORK EXTENSIONS                        │                    │   │
│  │  │  ┌────────┐ ┌──────────┐ ┌────────────────┐  │                    │   │
│  │  │  │ ir_http│ │ir_ui_menu│ │ ir_ui_view     │  │                    │   │
│  │  │  │(session│ │(load_web │ │ (get_view_info)│  │                    │   │
│  │  │  │ _info) │ │ _menus)  │ │                │  │                    │   │
│  │  │  └────────┘ └──────────┘ └────────────────┘  │                    │   │
│  │  │  ┌──────────┐ ┌───────────────────────────┐  │                    │   │
│  │  │  │ ir_model │ │ ir_qweb_fields            │  │                    │   │
│  │  │  │(_get_def)│ │ (image rendering)         │  │                    │   │
│  │  │  └──────────┘ └───────────────────────────┘  │                    │   │
│  │  └──────────────────────────────────────────────┘                    │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────┐                    │   │
│  │  │  BUSINESS MODELS                             │                    │   │
│  │  │  ┌───────────┐ ┌─────────────────┐           │                    │   │
│  │  │  │ res_users  │ │res_users_settings│         │                    │   │
│  │  │  │ (captcha,  │ │(density, embedded│         │                    │   │
│  │  │  │  bootstrap)│ │ actions)         │         │                    │   │
│  │  │  └───────────┘ └─────────────────┘           │                    │   │
│  │  │  ┌──────────────┐ ┌────────────────────────┐ │                    │   │
│  │  │  │ res_company  │ │ base_document_layout   │ │                    │   │
│  │  │  │ res_partner  │ │ res_config_settings    │ │                    │   │
│  │  │  │ properties   │ │                        │ │                    │   │
│  │  │  └──────────────┘ └────────────────────────┘ │                    │   │
│  │  └──────────────────────────────────────────────┘                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│                         ┌──────────────┐                                    │
│                         │  PostgreSQL  │                                    │
│                         │  (+ PostGIS) │                                    │
│                         └──────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Audit Areas — Detailed Breakdown


---

### AREA 1: Boot Sequence & Environment Setup

**Risk**: Incorrect initialization order, race conditions, missing services.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| JS | `static/src/boot/main.js` | 12 | Entry point — imports WebClient, calls `startWebClient()`. No `.catch`: the failure boundary lives INSIDE `startWebClient`, so an addon that replaces this entry file keeps it |
| JS | `static/src/boot/start.js` | 183 | `startWebClient()` — `publishOdooInfo()`, `applyUserTimezone()` (validated: an unknown IANA zone makes every luxon DateTime invalid, silently), RPC cache, `whenReady()`, `mountComponent()`. Wraps its whole body: paints `paintBootFailureOverlay()` with the failing phase and never rejects. `applyBootBodyClasses()` runs via `mountComponent`'s `beforeMount`, i.e. BEFORE the first render |
| JS | `static/src/env.js` | 410 | `makeEnv()`, `startServices()`, `startMissingServices()`, `mountComponent()`, `customDirectives`, `globalValues` |
| JS | `static/src/session.js` | 19 | Reads `odoo.__session_info__` into the exported `session`. **Does not delete it**: no `delete` exists in the tree; the raw payload stays on the `odoo` global for the page lifetime. |
| JS | `static/src/module_loader.js` | 187 | Two jobs. (1) Installs `globalThis.odoo.loader` = `OdooModuleLoader`, 5 members: `modules` Map, `bus`, `registerNativeModules`, `handleAssetLoadError`, `_reloadPage`. Sibling esbuild bundles share singletons through `modules`; conflicting re-register → `module_rebind`. Not an ES module loader (AMD loader removed in the 2026 ESM migration). (2) JS error telemetry: global `error` / `unhandledrejection` → deduped beacon to `/web/observability/js_error`; failed `/web/assets/` tag → one page reload, guarded by a 60 s `sessionStorage` key. |
| PY | `controllers/home.py` | 324 | `/`, `/web`, `/odoo`, `/odoo/<path:subpath>`, `/scoped_app/<path:subpath>`, `/web/webclient/load_menus`, `/web/login`, `/web/login_successful`, `/web/become`, `/robots.txt` |
| PY | `controllers/health.py` | 111 | `/web/health`, `/web/healthz`, `/web/readyz`, `/web/metrics` — process probes, no session, no request database |
| PY | `models/ir_http.py` | 385 | `session_info()`, `webclient_rendering_context()`, `lazy_session_info()`, `color_scheme()` (returns `"light"`), `content_density()` |
| XML | `views/webclient_templates.xml` | 406 | HTML shell, `t-call-assets`, inline session JSON. Contains `web.layout` with `<!DOCTYPE html>`, `<meta>`, `<link rel="icon">`, and inline `<script id="web.layout.odooscript">` that writes `window.odoo = {csrf_token, debug}`. Frontend layout injects `odoo.__session_info__` via `json.dumps(get_frontend_session_info())`. |

**Key invariants to check**:
- Service dependency order is acyclic
- `session_info()` never leaks sensitive data to public users
- `select_db()` correctly redirects when no DB selected
- RPC cache secret tied to correct session

---

### AREA 2: Authentication & Session Management

**Risk**: Session fixation, auth bypass, cookie handling bugs.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/session.py` | 125 | `get_session_info`, `authenticate`, `modules`, `check`, `account`, `destroy`, `logout` |
| PY | `controllers/home.py:web_login` | 178–250 | Login form + CAPTCHA |
| PY | `models/res_users.py` | 128 | `name_search()`, `_on_webclient_bootstrap()`, `_is_captcha_login_required()`, `web_create_users()` |
| PY | `models/ir_http.py` | 385 | `_handle_debug()`, `_update_cookies()`, `session_info()` |
| JS | `static/src/webclient/session_service.js` | 61 | Client-side session |
| JS | `static/src/public/login.js` | 44 | Login form component |

**Key invariants to check**:
- `authenticate()` never returns session_info for invalid credentials
- Session cookies have correct flags (HttpOnly, Secure, SameSite)
- `_update_cookies()` removes stale company IDs correctly
- CAPTCHA check cannot be bypassed by omitting parameter
- Debug mode restricted to internal users

---

### AREA 3: RPC Gateway (dataset.py + call_kw)

**Risk**: Method access bypass, readonly mismatch, injection via model/method names.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/dataset.py` | 64 | `call_kw()`, `call_button()`, readonly detection |
| PY | `controllers/utils.py` | 287 | `clean_action()`, `select_db()`, `update_action_views()`, `get_action()`, `get_action_triples()`, `_get_login_redirect_url()`, `is_user_internal()` |
| JS | `static/src/core/network/orm_service.js` | 428 | `ORM.call()`, `read()`, `write()`, etc. Builds `/web/dataset/call_kw/<model>/<method>`. |
| JS | `static/src/core/network/rpc.js` | 768 | JSON-RPC envelope, error handling. Transport is **`fetch`**, not `XMLHttpRequest`. |
| JS | `static/src/core/network/rpc_cache.js` | 672 | Dual-layer (RAM Map + IndexedDB) RPC cache with AES-GCM encryption (no HMAC — relies on GCM auth tag). Per-table `pendingRequests` Map dedups concurrent fetches of the same cache key; `modelIndex` is the O(1) model→keys reverse index used by model-scoped invalidation. For general concurrent-RPC deduplication (same URL+params across all callers), see `core/network/rpc_dedup.js`. |
| JS | `static/src/core/network/rpc_dedup.js` | 51 | Shares a single promise across identical concurrent RPC requests (URL+params key). Wraps any `rpcFn` with a `Map<string, Promise>`. |

**Key invariants to check**:
- `_call_kw_readonly()` correctly inspects `_readonly` attribute
- `call_button()` always passes result through `clean_action()`
- Model/method names validated before dispatch
- RPC cache invalidation triggered on write/unlink/create

> **Error serialization** (`odoo/http/_error_serialization.py`). Gate:
> `_is_exception_detail_hidden()` = `bool(request) and not config["dev_mode"]`.
>
> - `data.debug` = full traceback in `dev_mode`, else `_TRACEBACK_HIDDEN`.
>   Full trace always reaches the server log via `Application.__call__`.
> - `_OPAQUE_EXCEPTION_TYPES` (`psycopg.Error`, `OSError`) when gated:
>   `message` → `"Internal Server Error"`, `arguments` → `()`. Explicit
>   `message=` / `arguments=` opt out.
> - Callers: `dispatcher.py:405, 516, 519, 527`; `base/models/ir_cron.py:244`.
> - `rpc_cache` does not filter `data.debug`. Server output reaches the browser
>   verbatim; keep `_is_exception_detail_hidden()` the single decision point.

---

### AREA 4: Web Data Access (web_read / web_save / web_search_read)

**Risk**: N+1 queries, specification traversal bugs, ACL bypass in nested reads.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `models/web_read.py` | 904 | `web_name_search()`, `web_search_read()`, `web_save()`, `web_save_multi()`, `web_read()`, `web_resequence()`; concurrency helpers `_check_concurrent_field_changes()` / `_check_concurrent_field_changes_multi()` |
| PY | `models/web_read_group.py` | 905 | `web_read_group()`, `formatted_read_grouping_sets()`, `formatted_read_group()`, `read_progress_bar()` |
| PY | `models/web_read_group_helpers.py` | 533 | Temporal fill, formatters |
| PY | `models/web_search_panel.py` | 453 | `search_panel_select_range/multi_range` |
| PY | `models/web_search_panel_helpers.py` | 272 | Panel filter formatters |

**Key invariants to check**:
- `web_read()` respects ACLs on nested relational traversals
- Specification `limit` on x2many is enforced
- `web_search_read()` count_limit prevents full table scans
- `web_read_group()` temporal fill doesn't create phantom groups
- `read_progress_bar()` domain composition is correct

---

### AREA 5: Form Onchange & Record Snapshot

**Risk**: State diff errors, x2many command generation bugs, side effects in simulation.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `models/web_onchange.py` | 293 | `onchange()`, `web_override_translations()` |
| PY | `models/record_snapshot.py` | 142 | `RecordSnapshot(dict)` — `update_field()`, `has_changed()`, `diff()` |

**Key invariants to check**:
- `onchange()` never persists data (pure simulation)
- Snapshot diff correctly handles x2many CREATE/UPDATE/DELETE commands
- NewId records handled correctly in onchange context
- `web_override_translations()` validates field is translatable

---

### AREA 6: Action Service & Navigation

**Risk**: Action injection, breadcrumb corruption, controller stack leaks.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/action.py` | 162 | `/web/action/load`, `/run`, `/load_breadcrumbs` |
| JS | `static/src/webclient/actions/action_service.js` | 903 | `doAction()`, controller stack (per-type executors extracted to `action_executors/`; cache invalidation to `action_cache_invalidation.js`) |
| JS | `static/src/webclient/actions/action_loader.js` | 126 | `loadAction()`, `resolveClientAction()`, `makeController()`, `preprocessAction()` |
| JS | `static/src/webclient/actions/action_constants.js` | 62 | `CTX_KEY_REGEX`, `MAX_ACTION_DEPTH` (= 20) + `nextActionDepth()`, `DIALOG_SIZES`, `EMBEDDED_ACTIONS_CTX_KEYS` |
| JS | `static/src/webclient/actions/action_executors/` | 5 files | `act_url`, `act_window`, `client`, `close`, `server` |
| JS | `static/src/webclient/actions/action_cache_invalidation.js` | 42 | Bus-driven invalidation of the cached `/web/action/load` results |
| JS | `static/src/webclient/actions/action_storage.js` | — | `sessionStorage` keys `current_action`, `current_state`, `current_lang` |
| JS | `static/src/webclient/actions/action_container.js` | 37 | Render current action |
| JS | `static/src/webclient/actions/action_dialog.js` | 34 | Action in modal |
| JS | `static/src/webclient/actions/action_state.js` | 175 | Serialize/deserialize URL state |
| JS | `static/src/webclient/actions/action_info_builders.js` | 228 | Build view props from action |
| JS | `static/src/webclient/actions/action_button_executor.js` | 209 | Button action dispatch; sole `CTX_KEY_REGEX` consumer |
| JS | `static/src/webclient/actions/breadcrumb_manager.js` | 277 | Breadcrumb trail logic |

**Key invariants to check**:
- `load()` validates action type before returning
- Server actions (`/run`) check execution permissions
- Breadcrumb restore doesn't replay stale actions
- Controller stack properly cleaned on navigation
- `clean_action()` strips all internal fields

> **Refactor hazards**:
>
> - **6 dispatched types**: `act_window`, `act_window_close`, `client`,
>   `server`, `act_url`, `report`. Extension point:
>   `registry.category("action_handlers")`.
> - **Controller stack is a plain array, not reactive.** Each controller's
>   `config.breadcrumbs` *is* `reactive()`. `nextStack` commits after
>   `onMounted`; state does not settle synchronously.
> - **`stackPosition`**: `replaceCurrentAction` | `replacePreviousAction`.
>   Orthogonal: `clearBreadcrumbs`, `index`, `newStack` (replaces
>   `controllerStack` wholesale before `_computeStackIndex`).
> - **Non-component client actions** run as `(env, action, options)` functions.
>   Guard: `MAX_ACTION_DEPTH` = 20 via `nextActionDepth()`, throws past it.
>   Return value re-enters `doAction` with incremented `_actionDepth`.
> - **`/web/action/load` caches on disk** (`orm.cache({type:"disk"})`).
>   `installActionCacheInvalidation()` fires `onModelMutation` for **any
>   `ir.actions.*` model**, not just `act_window`, and clears
>   `/web/action/load`. Only the breadcrumb half is `act_window`-scoped: resets
>   `am.breadcrumbCache`, re-runs `refreshBreadcrumbDisplayNames`, splices the
>   tip's `config.breadcrumbs` — re-checking the stack tip after the await.
> - **`sessionStorage` side-channels**: `current_action`, `current_state`,
>   `current_lang`, written on every stack commit, used to restore the action on
>   reload. Moving state to the router alone breaks `_openActionInNewWindow`.
> - **Breadcrumb filter**: `prepareBreadcrumbs` drops controllers where
>   `action?.tag === "menu" || action?.id === "menu"`
>   (`breadcrumb_manager.js:20` — either key, not just `tag`). `loadBreadcrumbs`
>   drops controllers whose server-side `load_breadcrumbs` errors (ACL/missing).
> - **Button context order**: `currentCtx + buttonContext + activeCtx +
>   action.context`; `action.context` wins. `CTX_KEY_REGEX` strips `default_*`,
>   `search_default_*`, `show_*`, `*_view_ref`, `group_by`, `active_id`,
>   `active_ids`, `orderedBy`. **Applied only in `action_button_executor.js`**,
>   not `_preprocessAction`: direct `doAction()` calls are not scrubbed.
> - **`preprocessAction` does not mutate the cached action.** Lives in
>   `action_loader.js`; `action_service.js:_preprocessAction` delegates. The
>   shallow copy `{ ...action }` happens first, so `_originalAction`, `context`
>   merge, `domain` coercion, `help` drop and `views` rebuild all land on a
>   fresh object. Do not reintroduce mutation above the copy.
> - **`call_button` sentinel** (`dataset.py`): server returning
>   `{type: ""}` → JS receives `False` (no action). Absent `type` →
>   `setdefault("type", "ir.actions.act_window_close")` at `utils.py`.
>   Normalizing falsy returns will break Python buttons that rely on this.
> - **`action_handlers` registry extension point** (registry at `action_service.js`, dispatched via `actionHandlersRegistry.get(action.type)`):
>   zero registrations in core web — pure addon hook. Shape:
>   `(params: {env, action, options}) => void | Promise<void>`. Register with
>   `registry.category("action_handlers").add("my.type", handler)`.

---

### AREA 7: View System (Form, List, Kanban, Calendar)

**Risk**: Arch compilation bugs, field binding errors, event handler misrouting.

Directory counts are all files in the subtree; `.js`-only in parentheses.

| Layer | File | Lines / Files | Role |
|-------|------|-------|------|
| JS | `static/src/views/view.js` | 500 | Base View component + arch loading |
| JS | `static/src/views/view_compiler.js` | 780 | XML arch → OWL template |
| JS | `static/src/views/view_service.js` | 139 | `get_views` RPC behind `orm.cache({type: "disk"})` |
| JS | `static/src/views/form/` | 29 (16 js), 7 subdirs | Form controller, renderer, compiler |
| JS | `static/src/views/list/` | 31 (22 js), 1 subdir | List controller, renderer, group |
| JS | `static/src/views/kanban/` | 39 (19 js), 0 subdirs | Kanban controller, renderer, column |
| JS | `static/src/views/calendar/` | 39 (20 js), 7 subdirs | Calendar view (FullCalendar, lazy via `loadFullCalendar()`). Calendar + graph + pivot view code all ship in `assets_backend`. |
| JS | `static/src/views/graph/` | 10 (7 js) | Graph/chart view. Chart.js library is lazy-loaded via `loadChartJS()` (`core/lib/chartjs.js`, dynamic `import("chart.js")` through the import map), but view code itself ships in `assets_backend`. |
| JS | `static/src/views/pivot/` | 15 (12 js) | Pivot table view. XLSX export uses lazy-loaded library; pivot view code ships in `assets_backend`. |

**Key invariants to check**:
- Arch compiler handles all XML node types (field, button, group, notebook, page)
- `invisible`/`readonly`/`required` bracket-free expressions evaluate at render time via `evaluateBooleanExpr(expr, record.evalContextWithVirtualIds)` — NOT the legacy `attrs="{'invisible': [...]}"` format
- List view selection state consistent across page navigation
- Kanban drag-drop correctly generates resequence commands
- Calendar event creation maps dates correctly to record fields

> **Compiler asymmetry**: Form and Kanban have compilers
> (`form_compiler.js`, `kanban_compiler.js`). **List does not** — `list_view.js`
> parses arch via `ListArchParser` and hands `archInfo` straight to
> `ListRenderer`. Deliberate; account for it before unifying compiler behaviour.

> **View registry entries are objects, not components**:
> `{ type, Controller, Renderer, ArchParser, Model, buttonTemplate, ... }`.
> Canonical shape: `list_view.js`.

> **Form compiler extension point**: `registry.category("form_compilers")`.
> mail registers `chatter_compiler` and `attachment_preview_compiler`.
>
> `form_compiler.js` registers exactly 10 selectors: `div[name='button_box']`,
> `footer`, `form`, `group`, `header`, `label`, `notebook`, `setting`,
> `separator`, `sheet`. `<field>`, `<widget>`, `<button>`, `a[type]` are **not**
> among them — inherited from `ViewCompiler` (`view_compiler.js:269-278`).
>
> Match order: `ViewCompiler`'s constructor seeds `this.compilers`
> (`view_compiler.js:251`) before `setup()`; `FormCompiler.setup()` then pushes
> `...compilersRegistry.getAll()` ahead of its own 10. Dispatch is
> `this.compilers.find((cp) => node.matches(cp.selector))` — **first match
> wins**. A registry compiler can override `sheet`/`group`/`notebook`; it cannot
> override `field`/`widget`/`button`, seeded earlier by the base.

> **Kanban button SPECIAL_TYPES** (`kanban_compiler.js`):
> `["action", "object", "open", "delete", "url", "set_cover", "archive", "unarchive"]`.
> `action`/`object` route to ViewButton with `debounce=300`; the rest become
> direct `__comp__.triggerAction({...})` calls. `set_cover` extracts
> `auto-open` + `data-field` attributes for the cover-image picker.

> **Modifier evaluation context**:
> `invisible`/`readonly`/`required`/`column_invisible` evaluate against
> `record.evalContextWithVirtualIds` (form, render-time) or `record.evalContext`
> (field-attr helpers, `record_utils.js`). `evalContextWithVirtualIds`
> substitutes virtual IDs for unsaved x2many rows and exposes `parent` as a
> getter walking the nesting chain. Change virtual-ID generation and modifiers
> break silently on new rows.

> **`<header>` / `<sheet>` / `<footer>` / `<notebook>` rendering**:
> - `<header>` → `o_form_statusbar` wrapping `StatusBarButtons`.
> - `<sheet>` → `o_form_sheet_bg > o_form_sheet`. `FormCompiler.compile()` then
>   prepends a zero-height `div.o_form_sheet_scroll_sentinel`
>   (`t-ref="stickySentinel"`) as first child of `.o_form_sheet_bg`; the
>   statusbar shadow tracks it. The header and anything before `<sheet>` move
>   into that container afterwards — keep the sentinel first.
> - `<footer>` emits `web.DefaultButtonsSlot` only when `replace` is present and
>   falsy (`replace="false"`). Omitting the attribute adds no slot.
> - `<notebook>` tracks `defaultPage` via `__comp__.props.activeNotebookPages`,
>   keyed by per-compiler `noteBookId`; a `record.isNew` branch starts fresh
>   records on the declared default instead of the remembered page.

---

### AREA 8: Field Widgets (68 directories)

**Risk**: Parser/formatter mismatches, type coercion bugs, relational field binding.

| Layer | Directory | Files | Types |
|-------|-----------|-------|-------|
| JS | `static/src/fields/basic/` | 21 | boolean, char, float, html, integer, text, url, ... |
| JS | `static/src/fields/display/` | 8 | badge, gauge, handle, progress_bar, statusbar |
| JS | `static/src/fields/media/` | 7 | binary, image, pdf_viewer, signature |
| JS | `static/src/fields/relational/` | 11 | many2one, many2many_tags, x2many, reference |
| JS | `static/src/fields/selection/` | 7 | selection, radio, priority, state_selection |
| JS | `static/src/fields/specialized/` | 11 | domain, properties, ace, color_picker |
| JS | `static/src/fields/temporal/` | 3 | datetime, remaining_days, timezone_mismatch |
| JS | `static/src/core/formatters.js` | 445 | All value → display formatters. **In `core/`, not `fields/`.** |
| JS | `static/src/core/parsers.js` | 317 | All input → value parsers. **In `core/`, not `fields/`.** |

Counts are **subdirectories only** (one per widget). Loose sibling `.js` files
(`many2x_autocomplete.js`, `special_data.js`, `x2many_crud.js`,
`selection_like_field.js`, …) are excluded. 21+8+7+11+7+11+3 = **68**.

**Key invariants to check**:
- `core/formatters.js` ↔ `core/parsers.js` are true inverses (round-trip)
- Monetary fields respect currency decimal places
- Many2one correctly handles NewId references
- x2many generates correct ORM commands for all operations
- HTML field sanitizes content (XSS prevention)

---

### AREA 9: Search System

**Risk**: Domain composition errors, facet state inconsistency, saved filter corruption.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| JS | `static/src/search/search_model.js` | 817 | Core search state machine. `_getDomain()` at **:613** delegates to `computeDomain()` in `search_domain.js`. |
| JS | `static/src/search/search_arch_parser.js` | 521 | Parse search view XML → `{labels, preSearchItems, searchPanelInfo, sections}` |
| JS | `static/src/search/search_domain.js` | 274 | Domain from facets (`computeDomain`, `computeFieldDomain`, `computeFilterDomain`) |
| JS | `static/src/search/search_group_by.js` | 186 | GroupBy from selections |
| JS | `static/src/search/search_context.js` | 66 | Context dict builder |
| JS | `static/src/search/search_favorites.js` | 227 | Save/load filters |
| JS | `static/src/search/search_enrichment.js` | 79 | Apply dynamic context/domain enrichment to raw search items |
| JS | `static/src/search/search_facets.js` | 155 | Facet data structures + render helpers (`getFacets`) |
| JS | `static/src/search/search_state.js` | 151 | Reactive shared state consumed by ControlPanel + WithSearch |
| JS | `static/src/search/search_query_mixin.js` | 338 | URL ↔ search state round-trip + CLEAR-CACHES emission on saved-favorite mutations |
| JS | `static/src/search/search_split_domain_mixin.js` | 158 | Split composite domains back into atomic facets |
| JS | `static/src/search/search_properties_mixin.js` | 257 | Lazy property-field support in search model |
| JS | `static/src/search/search_favorites_mixin.js` | 141 | Favorite persistence mixed into SearchModel |
| JS | `static/src/search/control_panel/` | 6 files | ControlPanel component (top-level search UI) |
| JS | `static/src/search/embedded_actions_bar/` | 3 files | EmbeddedActionsBar (extracted from ControlPanel): embedded-action tabs, visibility/order via res.users.settings |
| JS | `static/src/search/search_bar/` | 6 files | Search input + suggestions |
| JS | `static/src/search/search_panel/` | 7 files | Sidebar filter panel |

> **Renamed in `71a61f27888` (2026-07-24)**, pre-rename names gone:
> `search_query_mutations.js` → `search_query_mixin.js`;
> `search_split_domain.js` → `search_split_domain_mixin.js`;
> `search_properties.js` → `search_properties_mixin.js`.

**Key invariants to check**:
- Domain ANDs/ORs nest correctly with multiple active facets
- GroupBy + comparison mode composes correctly
- Saved favorites restore full state (domain + groupby + context)
- Date range facets respect user timezone
- Search panel category filters produce valid domains

---

### AREA 10: Data Model Layer (Client-side)

**Risk**: Cache stale reads, relational traversal errors, record lifecycle bugs.

All 37 files under `static/src/model/relational_model/` are listed.

| Layer | File (`static/src/model/…`) | Lines | Role |
|-------|------|-------|------|
| JS | `model.js` | 366 | Base Model class |
| JS | `relational_model/relational_model.js` | 761 | Core data model — coordinates all sub-components |
| JS | `relational_model/record.js` | 986 | Single record lifecycle, dirty tracking, save |
| JS | `relational_model/record_lifecycle.js` | 91 | Record creation/discard lifecycle hooks |
| JS | `relational_model/record_edit_state.js` | 169 | Edit-mode / dirty-flag state machine |
| JS | `relational_model/record_savepoint.js` | 63 | Rollback point for aborted edits |
| JS | `relational_model/record_save.js` | 222 | Save orchestration (new/edit/delete) |
| JS | `relational_model/record_preprocessors.js` | 234 | Incoming data normalisation |
| JS | `relational_model/record_value_transforms.js` | 228 | Field value coercion before save |
| JS | `relational_model/record_validator.js` | 243 | Required/constraint validation |
| JS | `relational_model/record_utils.js` | 224 | Shared record helpers; modifier eval via `evaluateBooleanExpr` |
| JS | `relational_model/record_properties.js` | 118 | Properties-field support on records |
| JS | `relational_model/concurrency_baseline.js` | 72 | Builds the `known_values` baseline sent with `web_save` |
| JS | `relational_model/urgent_save_coordinator.js` | 136 | Save-on-unload / beforeunload coordination |
| JS | `relational_model/dynamic_list.js` | 635 | Paginated, sortable record list |
| JS | `relational_model/dynamic_group_list.js` | 415 | Grouped record list (kanban/list group-by) |
| JS | `relational_model/dynamic_record_list.js` | 173 | Flat filtered record list |
| JS | `relational_model/list_membership.js` | 71 | Add/remove bookkeeping for list datapoints |
| JS | `relational_model/static_list.js` | 1226 | x2many list datapoint: fixed record set, not domain-backed. "static" ≠ immutable — fully editable. |
| JS | `relational_model/static_list_command_engine.js` | 398 | ORM command generation for x2many edits |
| JS | `relational_model/static_list_sort.js` | 87 | Client-side sort for static lists |
| JS | `relational_model/static_list_utils.js` | 167 | Shared static list helpers |
| JS | `relational_model/x2many_tree.js` | 151 | Nested x2many tree traversal |
| JS | `relational_model/group.js` | 148 | Single group wrapper |
| JS | `relational_model/group_postprocessor.js` | 185 | Post-read group shaping (folding, aggregates) |
| JS | `relational_model/read_group_builder.js` | 87 | Builds `web_read_group` params |
| JS | `relational_model/datapoint.js` | 65 | Base class for record/group/list |
| JS | `relational_model/field_metadata.js` | 423 | Field descriptor resolution |
| JS | `relational_model/field_values.js` | 389 | Typed field value containers |
| JS | `relational_model/field_spec.js` | 140 | Specification tree builder |
| JS | `relational_model/field_context.js` | 103 | Per-field context computation |
| JS | `relational_model/command_builder.js` | 137 | Write command construction |
| JS | `core/network/commands.js` | 39 | ORM command constants |
| JS | `relational_model/config_transitions.js` | 117 | Model config diffing between loads |
| JS | `relational_model/resequence.js` | 135 | Handle field resequencing |
| JS | `relational_model/special_data_cache.js` | 66 | Cache for widget-specific side data |
| JS | `relational_model/errors.js` | 38 | Model-specific error classes |
| JS | `sample_server.js` | 732 | Mock ORM for demos |

**Key invariants to check**:
- Record dirty state tracked correctly across relational edits
- x2many record ordering preserved across save/reload
- `rpcBus.trigger("CLEAR-CACHES")` truly clears all stale data in `rpc_cache.js`
- `static_list_command_engine` generates minimal correct ORM commands (no spurious UPDATE)
- Sample server mock responses match real ORM structure

---

### AREA 11: Binary & Asset Serving

**Risk**: Path traversal, access token bypass, cache poisoning, image resize DoS.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/binary.py` | 571 | `/web/image`, `/web/content`, `/web/assets`, `/web/assets/esm`, `/web/filestore` (unconditional 404), upload |
| PY | `controllers/report.py` | 225 | `/report/<format>/<name>`, barcode generation |
| PY | `controllers/pivot.py` | 158 | `/web/pivot/export_xlsx` |

**Key invariants to check**:
- `/web/image` validates model/field before serving (no arbitrary field reads)
- Access tokens validated before serving private attachments
- Image resize dimensions bounded (no 99999x99999 requests)
- `/web/filestore` always returns 404 (nginx handles it)
- Asset unique hash prevents cache serving stale bundles
- Report converter validated (only html/pdf/text)

---

### AREA 12: Export System

**Risk**: Memory exhaustion on large exports, formula injection in CSV/XLSX.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/export.py` | 549 | CSV/XLSX export, field enumeration. `Export` controller + `ExportFormat` base (`base()`, `base_response()`) inherited by `CSVExport` and `ExcelExport`. |
| PY | `controllers/export_writers.py` | 405 | XLSX formatting, grouped export |

**Key invariants to check**:
- Export respects `ir.rule` security domains
- CSV values escaped to prevent formula injection (`=`, `+`, `-`, `@`)
- Field nesting depth bounded (prevent infinite recursion on circular relations)
- XLSX writer handles special characters in sheet/cell names
- Grouped export tree structure terminates correctly

---

### AREA 13: Database Management

**Risk**: Privilege escalation, backup disclosure, master password bypass.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/database.py` | 367 | Create, drop, backup, restore, change_password. Six routes carry `csrf=False`. |

**Key invariants to check**:
- Master password validated on every destructive operation
- `list_db` config respected (no listing when disabled)
- Backup format validated before restore
- CSRF protection (currently disabled with `csrf=false` — intentional?)
- Database names sanitized (no SQL injection in createdb)

---

### AREA 14: JSON API (Bearer Token)

**Risk**: Auth bypass, over-permissive data exposure, action eval injection.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/json.py` | 280 | `/json/1/<subpath>` REST-like API |
| PY | `controllers/json_helpers.py` | 178 | View/domain resolution helpers |

**Key invariants to check**:
- Bearer token auth correctly validates API keys
- Route only active in demo mode or with config param
- Action evaluation context doesn't allow arbitrary code execution
- Domain filtering cannot be bypassed via URL manipulation
- Response doesn't leak fields user has no access to

---

### AREA 15: UI System (Overlays)

**Risk**: Z-index stacking bugs, scroll lock leaks, XSS in notifications.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| JS | `static/src/ui/dialog/` | 6 files | Modal dialog service |
| JS | `static/src/ui/notification/` | 6 files | Toast notification service |
| JS | `static/src/ui/overlay/` | 5 files | Overlay layer manager |
| JS | `static/src/ui/popover/` | 6 files | Positioned popover |
| JS | `static/src/ui/tooltip/` | 4 files | Data-attribute tooltip |
| JS | `static/src/ui/block/` | 3 files | Block UI overlay |
| JS | `static/src/ui/effects/` | 4 files | Visual effects |
| JS | `static/src/ui/bottom_sheet/` | 5 files | Mobile bottom sheet |
| JS | `static/src/ui/alert/` | 1 file | Dismissable alert service |
| JS | `static/src/ui/carousel/` | 1 file | Carousel component |
| JS | `static/src/ui/collapse/` | 2 files | Collapse component |
| JS | `static/src/ui/offcanvas/` | 3 files | Offcanvas panel |
| JS | `static/src/ui/ui_service.js` | 212 | `ui` service — active element, `isSmall`, block/unblock |
| JS | `static/src/ui/viewport.js` | — | Viewport size breakpoints |

**Key invariants to check**:
- Dialog close always unblocks UI (no phantom overlays)
- Notification content sanitized (no HTML injection)
- Popover positioning accounts for viewport boundaries
- Scroll lock released on all dialog close paths (including errors)

---

### AREA 16: Core Infrastructure (Registry, Router, py_js)

**Risk**: Registry pollution, route hijacking, Python eval injection in domains.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| JS | `static/src/core/registry.js` | 310 | Central plugin registry |
| JS | `static/src/core/browser/` | 7 files | `router.js` (556), browser shims, feature detection |
| JS | `static/src/core/network/` | 6 files | `rpc.js`, `rpc_cache.js`, `rpc_dedup.js`, `model_mutation.js` |
| JS | `static/src/core/py_js/` | 16 files | Python expression evaluator |
| JS | `static/src/core/utils/` | 49 files (46 js) | Hooks, timing, DOM, collections, `indexed_db.js` |
| JS | `static/src/core/l10n/` | 13 files | Localization, date/number formats |

**Key invariants to check**:
- `py_js` evaluator sandboxed (no access to `window`, `document`, `fetch`)
- Registry `add()` with `force: true` required to overwrite existing entries
- Router state serialization doesn't allow prototype pollution
- `useService()` returns same instance across component lifecycle

---

### AREA 17: PWA & Service Worker

**Risk**: Cache serving stale content, offline mode data leaks.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/webmanifest.py` | 248 | Manifest, service worker, offline page |
| JS | `static/src/service_worker.js` | 367 | SW caching strategy |
| JS | `static/src/services/pwa/` | 4 files (2 js) | PWA install prompt |

**Key invariants to check**:
- Service worker doesn't cache authenticated responses
- Manifest `start_url` validated against allowed origins
- Scoped app icon generation doesn't allow arbitrary image processing
- Offline page doesn't expose session data

---

### AREA 18: Profiling & Debug

**Risk**: Information disclosure, debug mode persistence.

| Layer | File | Lines | Role |
|-------|------|-------|------|
| PY | `controllers/profiling.py` | 122 | Enable/disable profiling, speedscope |
| JS | `static/src/webclient/debug/` | 11 files (6 js) | Debug menu, providers, `profiling/` |

**Key invariants to check**:
- Profiling restricted to users with `base.group_system`
- Speedscope profiles don't contain credentials or session tokens
- Debug mode cannot be enabled by non-internal users

---

## Cross-Cutting Concerns (Check Across All Areas)

| Concern | What to Look For |
|---------|-----------------|
| **ACL enforcement** | Every data access path goes through `check_access_rights` |
| **SQL injection** | All `cr.execute()` use `%s` parameterization |
| **XSS** | All user content rendered through OWL (auto-escaped) or sanitized |
| **CSRF** | All state-changing routes use `type='jsonrpc'` (implicit CSRF) |
| **Cache coherence** | Write operations trigger `CLEAR-CACHES` appropriately |
| **Error handling** | Errors don't leak stack traces in production |
| **Readonly routing** | `readonly=True` matches actual read-only behavior |
| **Timezone handling** | Dates converted consistently between UTC and user TZ |
| **Concurrency** | `write()` checks `write_date` for optimistic locking |
