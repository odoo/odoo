# Web Module Route Map

Complete mapping of HTTP endpoints to Python handlers and JavaScript callers.

> **See also**: `FLOW_DIAGRAM.md` traces each route category end-to-end:
> Flow 1 (Bootstrap), Flow 2 (Login), Flow 3 (RPC), Flow 9 (Binary), Flow 10
> (Assets), Flow 11 (Export). `COMPONENT_DIAGRAM.md` maps routes to audit areas.

Legend: `JSONRPC` = POST JSON-RPC 2.0 | `HTTP` = standard HTTP (all methods unless noted) | `HTTP GET`/`POST` = method-restricted | `auth` = authentication type | `readonly` = routed to read replica if configured

## Core Data (RPC)

These are the primary backend APIs consumed by the JS ORM service (`core/network/rpc.js` + `core/network/orm_service.js`).

### controllers/dataset.py — DataSet

| Method | Route | Auth | Handler | JS Caller | Purpose |
|--------|-------|------|---------|-----------|---------|
| JSONRPC | `/web/dataset/call_kw` | user (readonly=dynamic) | `call_kw()` | `orm.call()`, `orm.read()`, `orm.write()`, `orm.create()`, `orm.unlink()`, `orm.search()` | Execute any model method via RPC |
| JSONRPC | `/web/dataset/call_kw/<path:path>` | user (readonly=dynamic) | `call_kw()` | Same (path = `model/method`) | Same, URL-path variant |
| JSONRPC | `/web/dataset/call_button` | user (readonly=dynamic) | `call_button()` | `action_service.js` button handler | Execute button action, clean returned action |
| JSONRPC | `/web/dataset/call_button/<path:path>` | user (readonly=dynamic) | `call_button()` | Same | Same, URL-path variant |

> `call_kw` is the primary gateway for ORM operations from JS. The ORM service builds URLs as
> `/web/dataset/call_kw/{model}/{method}` and POSTs `{model, method, args, kwargs}`.
> `call_button` is a second RPC path specifically for button actions — it wraps results through `clean_action()`.
> Both use `readonly=_call_kw_readonly` which inspects the method's `_readonly` attribute dynamically.

### controllers/model.py — Model

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP POST | `/web/model/get_definitions` | user | `get_model_definitions()` | Field definitions for webclient schema introspection |

### controllers/action.py — Action

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/web/action/load` | user (readonly) | `load()` | Load action definition by ID or XML path |
| JSONRPC | `/web/action/run` | user | `run()` | Execute server action, return result |
| JSONRPC | `/web/action/load_breadcrumbs` | user (readonly) | `load_breadcrumbs()` | Load breadcrumb chain for action navigation |

### controllers/domain.py — Domain

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/web/domain/validate` | user (readonly) | `is_domain_valid()` | Validate domain expression against model schema |

### controllers/view.py — View

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/web/view/edit_custom` | user | `edit_custom()` | Save user-customized view arch |

## Session and Authentication

### controllers/session.py — Session

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/web/session/authenticate` | none (readonly=False) | `authenticate()` | Login: validate credentials, return session info |
| JSONRPC | `/web/session/get_session_info` | user (readonly) | `get_session_info()` | Current session state (user, lang, company, etc.) |
| JSONRPC | `/web/session/check` | user (readonly) | `check()` | Verify session is still valid |
| JSONRPC | `/web/session/modules` | user (readonly) | `modules()` | List installed modules |
| JSONRPC | `/web/session/account` | user (readonly) | `account()` | OAuth2 URL for Odoo account linking |
| JSONRPC | `/web/session/destroy` | user (readonly) | `destroy()` | Logout (JSON-RPC) |
| HTTP | `/web/session/logout` | none (readonly) | `logout()` | Logout (HTTP redirect) |

## Web Client Bootstrap

### controllers/home.py — Home

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/` | none | `index()` | Redirect to `/odoo` or login |
| HTTP | `/odoo`, `/odoo/<path>`, `/web`, `/scoped_app/<path>` | none (readonly=dynamic) | `web_client()` | Main webclient SPA bootstrap page |
| HTTP GET | `/web/webclient/load_menus` | user (readonly) | `web_load_menus()` | Sidebar menu tree. Conditional fetch: 200 responses carry `X-Menus-Hash` (SHA-256 of JSON body); client echoes it back as `?hash=` and gets an empty `304` when unchanged. Always `Cache-Control: no-store` (payload is session-dependent) |
| HTTP | `/web/login` | none (readonly=False) | `web_login()` | Login page (GET = form, POST = authenticate) |
| HTTP | `/web/login_successful` | user (readonly) | `login_successful_external_user()` | External user landing page |
| HTTP | `/web/become` | user (readonly) | `switch_to_admin()` | Switch session to admin (debug) |
| HTTP | `/robots.txt` | none | `robots()` | Search engine robots file |

### controllers/health.py — Health

Process probes and the metrics scrape. No session, no database: every route is `auth="none"` with `save_session=False`, and `/web/readyz` opens its own cursor on `postgres` instead of the request's.

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/web/health` | none (save_session=False) | `health()` | Legacy health check (DB status optional). Prefer `/web/healthz` + `/web/readyz` for K8s probes. |
| HTTP | `/web/healthz` | none (save_session=False) | `healthz()` | Kubernetes-style liveness probe (no I/O, returns 200 if the process is up) |
| HTTP | `/web/readyz` | none (save_session=False) | `readyz()` | Kubernetes-style readiness probe (checks DB + data_dir, returns 503 on failure) |
| HTTP | `/web/metrics` | none (save_session=False) | `metrics()` | Prometheus exposition of this process's counters. Off unless the `ODOO_METRICS_TOKEN` **env var** (not a config key — it must not be writable into a saved `.conf`) is set, and answers **404** rather than 401 when unset, so an unenabled surface is indistinguishable from one never built. Token travels as `Authorization: Bearer` and is compared with `consteq`; a bad token gets 401. Gated because the payload names every database this process serves |

### controllers/webclient.py — WebClient

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/web/webclient/translations` | public (CORS, readonly) | `translations()` | Module translations with hash validation |
| JSONRPC | `/web/webclient/version_info` | none | `version_info()` | Odoo version metadata |
| HTTP GET | `/web/bundle/<bundle_name>` | public (readonly) | `bundle()` | JS/CSS bundle definition |
| HTTP | `/web/tests` | user (readonly) | `unit_tests_suite()` | HOOT test runner page |

## Binary Content (Images, Files, Assets)

### controllers/binary.py — Binary

| Method | Route | Auth | Handler | JS Caller | Purpose |
|--------|-------|------|---------|-----------|---------|
| HTTP | `/web/content/<variants>` | public (readonly) | `content_common()` | `useFileViewer`, direct links | Serve attachment/binary by xmlid, id, or model/id/field (7 URL variants) |
| HTTP | `/web/image/<variants>` | public (readonly, save_session=False) | `content_image()` | `<img>` tags, `core/utils/urls.js`, `components/file_viewer/file_model.js` | Serve resized/cropped image (17 URL variants). `save_session=False` prevents session writes on image requests. |
| HTTP | `/web/assets/<unique>/<filename>` | public (readonly) | `content_assets()` | Asset loader | Compiled CSS/JS bundles with cache headers |
| HTTP | `/web/assets/scope/<scope>/<unique>/<filename>` | public (readonly) | `content_assets_scoped()` | HOOT runner page links | Same bundle resolved for one addon's dependency closure. The scope is in the PATH because `unique` hashes the *result*: without it the route re-resolves unscoped and 303s to the wrong bundle. Unknown scope → 404. See `TEST_TAGS.md` |
| HTTP | `/web/assets/esm/<unique>/<filename>` | public (readonly) | `content_esm_assets()` | ESM `<script type="module">`, import map | Content-addressed ESM bundles, sidecars, bridge shims — immutable long-lived cache headers, no on-the-fly rebuild |
| HTTP | `/web/assets/lib/<unique>/<path>` | public (readonly) | `content_esm_lib()` | import map (`esm.external_libs`) | The minified copy of one vendored library file, content-addressed over the library's relative-import closure; persisted by the render that built the import map, so a missing row is a 404 |
| HTTP | `/web/binary/upload_attachment` | user | `upload_attachment()` | `file_input.js`, `attach_document.js` | Upload file(s), create attachment records |
| HTTP | `/web/binary/company_logo`, `/logo`, `/logo.png` | none (CORS) | `company_logo()` | Login page, emails | Company logo or default Odoo logo |
| HTTP | `/web/filestore/<path:_path>` | none | `content_filestore()` | x-sendfile | Error handler for direct filestore access |
| JSONRPC | `/web/sign/get_fonts`, `/web/sign/get_fonts/<fontname>` | none | `get_fonts()` | Signature widget | Available signature fonts (base64) |

## Export

### controllers/export.py — Export / CSVExport / ExcelExport

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/web/export/formats` | user (readonly) | `formats()` | List available export formats |
| JSONRPC | `/web/export/get_fields` | user (readonly) | `get_fields()` | Exportable fields for a model |
| JSONRPC | `/web/export/namelist` | user (readonly) | `namelist()` | Field names from saved export preset |
| HTTP | `/web/export/csv` | user (readonly) | `web_export_csv()` | Export records as CSV |
| HTTP | `/web/export/xlsx` | user (readonly) | `web_export_xlsx()` | Export records as XLSX with grouping |

### controllers/pivot.py — TableExporter

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/web/pivot/export_xlsx` | user (readonly) | `export_xlsx()` | Export pivot table to XLSX |

## Reports

### controllers/report.py — ReportController

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/report/<converter>/<reportname>` | user (readonly) | `report_routes()` | Render report (HTML/PDF/text) |
| HTTP | `/report/<converter>/<reportname>/<docids>` | user (readonly) | `report_routes()` | Same, with document IDs |
| HTTP | `/report/barcode` | public (readonly) | `report_barcode()` | Generate barcode image (PNG) |
| HTTP | `/report/barcode/<barcode_type>/<path:value>` | public (readonly) | `report_barcode()` | Same, URL-path variant |
| HTTP | `/report/download` | user | `report_download()` | Download report with filename header |

## Database Management

### controllers/database.py — Database

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/web/database/selector` | none | `selector()` | Database selector page |
| HTTP | `/web/database/manager` | none | `manager()` | Database manager page |
| HTTP POST | `/web/database/create` | none (csrf=False) | `create()` | Create new database |
| HTTP POST | `/web/database/duplicate` | none (csrf=False) | `duplicate()` | Duplicate database |
| HTTP POST | `/web/database/drop` | none (csrf=False) | `drop()` | Delete database |
| HTTP POST | `/web/database/backup` | none (csrf=False) | `backup()` | Export database (ZIP/SQL) |
| HTTP POST | `/web/database/restore` | none (csrf=False, max_content_length=None) | `restore()` | Import database backup. `max_content_length=None` means uploads are unbounded — relies on reverse proxy to cap request size. |
| HTTP POST | `/web/database/change_password` | none (csrf=False) | `change_password()` | Change master password |
| JSONRPC | `/web/database/list` | none | `list()` | List databases (mobile API) |

> **Database POST footgun** (`database.py` `_handle_insecure_password`): on first successful POST with a non-"admin" `master_pwd`, the helper auto-upgrades the stored master password to whatever was submitted — browser autofill of the form can silently replace the default. The helper is invoked from five POST handlers (`create`, `duplicate`, `drop`, `backup`, `restore`), so any of those routes is a trigger surface. Any refactor hardening master-pwd handling should remove this auto-upgrade.

> **Restore / upload safety gaps** — `/web/database/restore` has `max_content_length=None` (unbounded upload) and no MIME/magic-byte check; `/web/binary/upload_attachment` has no size cap beyond the framework default and no MIME validation; `/report/barcode` accepts arbitrary `width`/`height`/`value` (reportlab can allocate large images). All three are known limitations — consumers must enforce limits at the reverse proxy.

## PWA and Manifest

### controllers/webmanifest.py — WebManifest

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP GET | `/web/manifest.webmanifest` | public (readonly) | `webmanifest()` | PWA manifest.json |
| HTTP GET | `/web/service-worker.js` | public (readonly) | `service_worker()` | Service Worker script |
| HTTP GET | `/odoo/offline` | public (readonly) | `offline()` | Offline fallback page |
| HTTP GET | `/scoped_app` | public | `scoped_app()` | Scoped PWA install page |
| HTTP GET | `/scoped_app_icon_png` | public | `scoped_app_icon_png()` | App icon with padding |
| HTTP GET | `/web/manifest.scoped_app_manifest` | public | `scoped_app_manifest()` | Scoped PWA manifest |

## Profiling

### controllers/profiling.py — Profiling

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/web/set_profiling` | public | `profile()` | Start/stop profiling with collectors |
| HTTP | `/web/speedscope/<profile>` | user (readonly) | `speedscope()` | View speedscope profile JSON |
| HTTP | `/web/profile_config/<profile>` | user (readonly) | `profile_config()` | Profile config and memory view |

## JSON API

### controllers/json.py — WebJsonController

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/json/<path:subpath>` | user (readonly) | `web_json()` | Redirect to versioned JSON endpoint |
| HTTP | `/json/1/<path:subpath>` | bearer (readonly) | `web_json_1()` | JSON view API (domain, groupby, pagination) |

## vCard

### controllers/vcard.py — Partner

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/web/partner/vcard` | user (readonly) | `download_vcard()` | Download partner vCard |
| HTTP | `/web_enterprise/partner/<model("res.partner"):partner>/vcard` | user | `download_vcard()` | Same, enterprise URL variant |

## Settings

### controllers/settings.py — BaseSetup

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/base_setup/data` | user (readonly) | `base_setup_data()` | Base setup configuration data |
| JSONRPC | `/base_setup/demo_active` | user (readonly) | `base_setup_is_demo()` | Check if demo data is active |

## Observability

### controllers/observability.py — Observability

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP POST | `/web/observability/cwv` | public (csrf=False, sitemap=False) | `cwv()` | Core Web Vitals beacon (LCP/FCP/CLS/TTFB/INP — INP as worst-observed P100 interaction duration) sent via `navigator.sendBeacon` from `web_vitals_service.js` on `pagehide`. Validates and clamps payload, persists to `web.cwv.metric`, emits `[cwv]`-tagged INFO log. |
| HTTP POST | `/web/observability/js_error` | public (csrf=False, sitemap=False) | `js_error()` | JS error beacon sent via `navigator.sendBeacon` from the inline `module_loader.js` shim's pre-bundle error handler. Throttled JS-side to one beacon per `(message,line,col,hash(stack+cause))` per page lifetime — the stack and cause discriminate because OWL reports every lifecycle failure with one generic message at `0:0`. Clamps payload fields to length caps, emits a `[js_error]` WARNING log, and persists to `web.js.error` (see `MODEL_MAP.md`). |

## OpenAPI

### controllers/openapi.py — OpenAPI

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP GET | `/web/openapi.json` | user (readonly) | `openapi_json()` | OpenAPI 3.1 document generated live from the routing map by `odoo.http.openapi:prepare_openapi_from_map` with `typed_only=True`, so only `@route(typed=True)` endpoints are listed — never the full internal route map. Additionally gated on `base.group_system` inside the handler (403 otherwise): even the curated surface is deployment reconnaissance |

## Route Count Summary

Counts are in **(handler functions) / (URL-pattern variants)**.
A single `@http.route(routes=[...])` counts as one handler but several URL variants.

| Category | Handlers / URLs | Controller |
|----------|-----------------|------------|
| RPC/Data | 8 / 10 | dataset, action, domain, view, model |
| Session | 7 / 7 | session |
| Bootstrap | 15 / 18 | home (7 handlers / 10 URLs; web_client has 4 URLs), health (4), webclient (4) |
| Binary/Assets | 10 / 35 | binary (17 image + 7 content + 3 logo + 2 fonts + upload + assets + scoped assets + esm assets + esm libraries + filestore) |
| Export | 6 / 6 | export (5), pivot (1) |
| Reports | 3 / 5 | report |
| Database | 9 / 9 | database |
| PWA | 6 / 6 | webmanifest |
| Profiling | 3 / 3 | profiling |
| JSON API | 2 / 2 | json |
| vCard | 1 / 2 | vcard (one handler, two URLs) |
| Settings | 2 / 2 | settings |
| Observability | 2 / 2 | observability (CWV beacon + JS error beacon) |
| OpenAPI | 1 / 1 | openapi (`/web/openapi.json`, `base.group_system` only) |
| **Total** | **75 handlers / 108 declared URL paths** | **23 controller classes** (across 21 route-bearing files of 25 in `controllers/`; export.py contains 3: Export, CSVExport, ExcelExport. `json_helpers.py`, `export_writers.py`, `utils.py`, `__init__.py` have no routes.) |
