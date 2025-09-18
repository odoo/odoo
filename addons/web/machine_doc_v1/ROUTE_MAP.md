# Web Module Route Map

Complete mapping of HTTP endpoints to Python handlers and JavaScript callers.

> **See also**: `doc/FLOW_DIAGRAM.md` traces each route category end-to-end:
> Flow 1 (Bootstrap), Flow 2 (Login), Flow 3 (RPC), Flow 9 (Binary), Flow 10 (Assets),
> Flow 11 (Export). `doc/COMPONENT_DIAGRAM.md` maps routes to audit areas.

Legend: `JSONRPC` = POST JSON-RPC 2.0 | `HTTP` = standard HTTP (all methods unless noted) | `HTTP GET`/`POST` = method-restricted | `auth` = authentication type | `readonly` = routed to read replica if configured

## Core Data (RPC)

These are the primary backend APIs consumed by the JS ORM service (`core/network/rpc.js` + `core/orm_service.js`).

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
| JSONRPC | `/web/domain/validate` | user | `validate()` | Validate domain expression against model schema |

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
| JSONRPC | `/web/session/get_lang_list` | none | `get_lang_list()` | Available languages |
| JSONRPC | `/web/session/account` | user (readonly) | `account()` | OAuth2 URL for Odoo account linking |
| JSONRPC | `/web/session/destroy` | user (readonly) | `destroy()` | Logout (JSON-RPC) |
| HTTP | `/web/session/logout` | none (readonly) | `logout()` | Logout (HTTP redirect) |

## Web Client Bootstrap

### controllers/home.py — Home

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/` | none | `index()` | Redirect to `/odoo` or login |
| HTTP | `/odoo`, `/odoo/<path>`, `/web`, `/scoped_app/<path>` | none (readonly=dynamic) | `web_client()` | Main webclient SPA bootstrap page |
| HTTP GET | `/web/webclient/load_menus` | user (readonly) | `web_load_menus()` | Sidebar menu tree |
| HTTP | `/web/login` | none (readonly=False) | `web_login()` | Login page (GET = form, POST = authenticate) |
| HTTP | `/web/login_successful` | user | `login_successful_external_user()` | External user landing page |
| HTTP | `/web/become` | user (readonly) | `switch_to_admin()` | Switch session to admin (debug) |
| HTTP | `/web/health` | none | `health()` | Health check (DB status optional) |
| HTTP | `/robots.txt` | none | `robots()` | Search engine robots file |

### controllers/webclient.py — WebClient

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/web/webclient/bootstrap_translations` | none | `bootstrap_translations()` | Login page translations from .po files |
| HTTP | `/web/webclient/translations` | public (CORS, readonly) | `translations()` | Module translations with hash validation |
| JSONRPC | `/web/webclient/version_info` | none | `version_info()` | Odoo version metadata |
| HTTP GET | `/web/bundle/<bundle_name>` | public (readonly) | `bundle()` | JS/CSS bundle definition |
| HTTP | `/web/tests` | user (readonly) | `unit_tests_suite()` | HOOT test runner page |
| HTTP | `/web/tests/legacy` | user (readonly) | `test_suite()` | Legacy QUnit test runner |

## Binary Content (Images, Files, Assets)

### controllers/binary.py — Binary

| Method | Route | Auth | Handler | JS Caller | Purpose |
|--------|-------|------|---------|-----------|---------|
| HTTP | `/web/content/<variants>` | public (readonly) | `content_common()` | `useFileViewer`, direct links | Serve attachment/binary by xmlid, id, or model/id/field (7 URL variants) |
| HTTP | `/web/image/<variants>` | public (readonly) | `content_image()` | `<img>` tags, `image_service.js` | Serve resized/cropped image (17 URL variants) |
| HTTP | `/web/assets/<unique>/<filename>` | public (readonly) | `content_assets()` | Asset loader | Compiled CSS/JS bundles with cache headers |
| HTTP | `/web/binary/upload_attachment` | user | `upload_attachment()` | `file_input.js`, `attach_document.js` | Upload file(s), create attachment records |
| HTTP | `/web/binary/company_logo`, `/logo`, `/logo.png` | none (CORS) | `company_logo()` | Login page, emails | Company logo or default Odoo logo |
| HTTP | `/web/filestore/<path:_path>` | none | `content_filestore()` | x-sendfile | Error handler for direct filestore access |
| JSONRPC | `/web/sign/get_fonts`, `/web/sign/get_fonts/<fontname>` | none | `get_fonts()` | Signature widget | Available signature fonts (base64) |

> `/web/image/` has 17 URL variants for combinations of xmlid/id/model+id+field with optional WxH and filename.
> `/web/content/` has 7 URL variants. All resolve to the same handler per group.

## Export

### controllers/export.py — Export / CSVExport / ExcelExport

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/web/export/formats` | user (readonly) | `formats()` | List available export formats |
| JSONRPC | `/web/export/get_fields` | user (readonly) | `get_fields()` | Exportable fields for a model |
| JSONRPC | `/web/export/namelist` | user (readonly) | `namelist()` | Field names from saved export preset |
| HTTP | `/web/export/csv` | user | `web_export_csv()` | Export records as CSV |
| HTTP | `/web/export/xlsx` | user | `web_export_xlsx()` | Export records as XLSX with grouping |

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
| JSONRPC | `/report/check_wkhtmltopdf` | user (readonly) | `check_wkhtmltopdf()` | Verify PDF renderer availability |

## Database Management

### controllers/database.py — Database

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| HTTP | `/web/database/selector` | none | `selector()` | Database selector page |
| HTTP | `/web/database/manager` | none | `manager()` | Database manager page |
| HTTP POST | `/web/database/create` | none | `create()` | Create new database |
| HTTP POST | `/web/database/duplicate` | none | `duplicate()` | Duplicate database |
| HTTP POST | `/web/database/drop` | none | `drop()` | Delete database |
| HTTP POST | `/web/database/backup` | none | `backup()` | Export database (ZIP/SQL) |
| HTTP POST | `/web/database/restore` | none | `restore()` | Import database backup |
| HTTP POST | `/web/database/change_password` | none | `change_password()` | Change master password |
| JSONRPC | `/web/database/list` | none | `list()` | List databases (mobile API) |

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
| HTTP | `/web/partner/vcard` | user | `download_vcard()` | Download partner vCard |
| HTTP | `/web_enterprise/partner/<model("res.partner"):partner>/vcard` | user | `download_vcard()` | Same, enterprise URL variant |

## Settings

### controllers/settings.py — BaseSetup

| Method | Route | Auth | Handler | Purpose |
|--------|-------|------|---------|---------|
| JSONRPC | `/base_setup/data` | user | `base_setup_data()` | Base setup configuration data |
| JSONRPC | `/base_setup/demo_active` | user | `base_setup_is_demo()` | Check if demo data is active |

## Route Count Summary

| Category | Routes | Controller |
|----------|--------|------------|
| RPC/Data | 9 | dataset, action, domain, view, model |
| Session | 10 | session |
| Bootstrap | 10 | home, webclient |
| Binary/Assets | ~28 | binary (17 image + 7 content + uploads + fonts + logo + filestore) |
| Export | 7 | export, pivot |
| Reports | 6 | report |
| Database | 9 | database |
| PWA | 6 | webmanifest |
| Profiling | 3 | profiling |
| JSON API | 2 | json |
| vCard | 2 | vcard |
| Settings | 2 | settings |
| **Total** | **~94 unique handlers** | **20 controller classes** |
