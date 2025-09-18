# Web Module Architecture

High-level structure, data flow, and component organization for `core/addons/web/`.

> **See also**: `doc/COMPONENT_DIAGRAM.md` — 18 audit areas with file lists,
> invariants, and cross-cutting concerns. `doc/FLOW_DIAGRAM.md` — 14 end-to-end
> sequence diagrams (bootstrap, RPC, auth, view loading, onchange, save, etc.).
> `JS_FILE_INDEX.md` — Complete index of all 602 JS files with purpose descriptions.
> `DIRECTORY_MAP.md` — All 231 directories mapped to FSD layers and responsibilities.
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
│  JavaScript (OWL Components + Services)                  │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ Views    │  │ Services │  │ UI       │  │Webcli- │  │
│  │ form     │  │ orm      │  │ dialog   │  │ent     │  │
│  │ list     │  │ rpc      │  │ popover  │  │ navbar │  │
│  │ kanban   │  │ field    │  │ tooltip  │  │ menus  │  │
│  │ calendar │  │ hotkey   │  │ notif.   │  │ user   │  │
│  │ graph    │  │ ...      │  │ effects  │  │ menu   │  │
│  │ pivot    │  │          │  │ overlay  │  │        │  │
│  └────┬─────┘  └────┬─────┘  └──────────┘  └────────┘  │
│       │              │                                   │
│       └──────┬───────┘                                   │
│              │ orm.call(model, method, args, kwargs)     │
│              v                                           │
│  ┌───────────────────────────────────┐                  │
│  │ RPC Layer (core/network/rpc.js)   │                  │
│  │ POST /web/dataset/call_kw/{m}/{f} │                  │
│  └───────────────┬───────────────────┘                  │
└──────────────────│──────────────────────────────────────┘
                   │ JSON-RPC 2.0
                   v
┌──────────────────────────────────────────────────────────┐
│  Python (Controllers → ORM → Database)                    │
│                                                           │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐  │
│  │ Controllers  │───>│ Models       │───>│ PostgreSQL │  │
│  │ dataset.py   │    │ web_read.py  │    │            │  │
│  │ action.py    │    │ web_read_    │    │            │  │
│  │ session.py   │    │  group.py   │    │            │  │
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

```
core/addons/web/
├── __manifest__.py           # Module metadata + asset bundle definitions
├── controllers/              # 20 controller classes across 21 .py files (HTTP endpoints)
│   ├── dataset.py            #   call_kw + call_button: gateway for ORM RPC
│   ├── session.py            #   authenticate, session_info, logout
│   ├── home.py               #   /, /odoo, /web/login, /web/health
│   ├── binary.py             #   /web/image, /web/content, /web/assets
│   ├── action.py             #   /web/action/load, /run, /load_breadcrumbs
│   ├── export.py             #   /web/export (CSV, XLSX)
│   ├── report.py             #   /report (HTML, PDF, barcode)
│   ├── database.py           #   /web/database (manager, create, drop, backup)
│   ├── webclient.py          #   translations, version_info, bundles, test runners
│   ├── json.py               #   /json/1/ (bearer-auth JSON API)
│   ├── model.py              #   /web/model/get_definitions
│   ├── domain.py             #   /web/domain/validate
│   ├── view.py               #   /web/view/edit_custom
│   ├── pivot.py              #   /web/pivot/export_xlsx
│   ├── profiling.py          #   /web/set_profiling, /web/speedscope
│   ├── webmanifest.py        #   PWA manifest, service worker, offline page
│   ├── vcard.py              #   vCard download
│   ├── settings.py           #   /base_setup/data, /base_setup/demo_active
│   ├── export_writers.py     #   Export format base class
│   ├── json_helpers.py       #   JSON API helpers
│   └── utils.py              #   clean_action() and shared helpers
├── models/                   # 20 Python model files (ORM extensions)
│   ├── web_read.py           #   web_read, web_save, web_search_read (core CRUD)
│   ├── web_read_group.py     #   web_read_group (grouped data for views)
│   ├── web_onchange.py       #   onchange() (form change simulation)
│   ├── record_snapshot.py    #   Snapshot diffing for onchange
│   ├── web_search_panel.py   #   Sidebar filter panels
│   ├── ir_http.py            #   session_info(), bootstrap context
│   ├── ir_ui_menu.py         #   load_web_menus() (sidebar)
│   ├── ir_ui_view.py         #   View type metadata
│   ├── ir_model.py           #   Schema introspection
│   ├── ir_qweb_fields.py     #   QWeb image rendering
│   ├── res_users.py          #   User search priority, CAPTCHA
│   ├── res_users_settings.py #   UI density, embedded actions
│   ├── res_users_settings_embedded_action.py # Per-user action config
│   ├── base_document_layout.py # Report layout wizard
│   ├── res_company.py        #   Report style regeneration
│   ├── res_config_settings.py #  web_app_name config
│   ├── res_partner.py        #   vCard export
│   ├── web_read_group_helpers.py # Temporal fill, group expansion formatters
│   ├── web_search_panel_helpers.py # Filter panel helpers
│   └── properties_base_definition.py # Property field definitions
├── static/
│   ├── src/                  # 602 JavaScript/OWL source files
│   │   ├── boot/             #   App entry points: main.js, start.js (env.js and session.js are at src/ root)
│   │   ├── core/             #   Framework primitives: registry, utils, browser, l10n, network, py_js
│   │   ├── components/       #   Reusable OWL UI components (dropdown, colorpicker, etc.)
│   │   ├── services/         #   Data & input services (orm, hotkey, field, etc.)
│   │   ├── ui/               #   UI overlay services & components (see UI Layer below)
│   │   │   ├── block/        #     Block UI overlay + ui_service
│   │   │   ├── bottom_sheet/ #     Mobile bottom sheet
│   │   │   ├── dialog/       #     Modal dialog + confirmation_dialog + dialog_service
│   │   │   ├── effects/      #     Visual effects (rainbow_man) + effect_service
│   │   │   ├── notification/ #     Toast notifications + notification_service
│   │   │   ├── overlay/      #     Base overlay layer manager + overlay_service
│   │   │   ├── popover/      #     Positioned popover + popover_service
│   │   │   └── tooltip/      #     Data-attribute tooltips + tooltip_service
│   │   ├── fields/           #   67 field widget types (7 subcategories)
│   │   │   ├── basic/        #     21 widgets: boolean, char, float, html, integer, text, url, ...
│   │   │   ├── display/      #     8 widgets: badge, gauge, handle, progress_bar, statusbar, ...
│   │   │   ├── media/        #     7 widgets: binary, image, image_url, pdf_viewer, signature, ...
│   │   │   ├── relational/   #     11 widgets + 5 utilities: many2one, many2many_tags, x2many, reference, ...
│   │   │   ├── selection/    #     7 widgets: selection, radio, priority, state_selection, ...
│   │   │   ├── specialized/  #     10 widgets: domain, properties, ace, color_picker, ...
│   │   │   └── temporal/     #     3 widgets: datetime, remaining_days, timezone_mismatch
│   │   ├── views/            #   View types: form, list, kanban, calendar, graph, pivot
│   │   ├── webclient/        #   App shell: navbar, menus, user menu, burger menu
│   │   ├── search/           #   Search bar, facets, filters, group-by, favorites
│   │   ├── model/            #   Client-side relational data model
│   │   ├── public/           #   Public (anonymous) page features
│   │   ├── libs/             #   Internal utility libraries
│   │   ├── polyfills/        #   Browser polyfills
│   │   ├── legacy/           #   Legacy compatibility code
│   │   ├── @types/           #   TypeScript type declarations
│   │   └── scss/             #   ~197 SCSS stylesheets
│   ├── lib/                  # Vendored JS libraries (DO NOT MODIFY)
│   │   ├── owl/              #   OWL component framework
│   │   ├── luxon/            #   DateTime library
│   │   ├── bootstrap/        #   CSS framework
│   │   ├── Chart/            #   Chart.js
│   │   ├── fullcalendar/     #   Calendar library
│   │   └── ...               #   19 vendored libraries total
│   ├── tests/                # JS test files (~377 files)
│   └── fonts/                # Web fonts (Google, Inter, Lato, Sign)
├── tests/                    # 33 Python test files (see machine_doc_v1/TEST_TAGS.md)
├── views/                    # XML templates (backend UI, reports)
├── data/                     # XML data fixtures
├── security/                 # Access control (ir.model.access.csv)
├── i18n/                     # Translation files
├── doc/                      # Architecture diagrams for correctness audits
│   ├── COMPONENT_DIAGRAM.md  #   18 audit areas with files, invariants, cross-cutting concerns
│   └── FLOW_DIAGRAM.md       #   14 end-to-end sequence diagrams (bootstrap → save → cache)
├── tooling/                  # ESLint, JSConfig, git hooks
└── machine_doc_v1/           # Machine-consumable documentation (this directory)
```

## JavaScript Architecture

Layered organization under `static/src/`:

| Layer | Directory | Purpose | Files |
|-------|-----------|---------|-------|
| **Boot** | `boot/` | App entry points: main.js, start.js (env.js and session.js at src/ root) | 2 JS |
| **Primitives** | `core/` | Registry, utils, browser abstraction, l10n, network, py_js | 81 JS |
| **Components** | `components/` | Reusable OWL UI components (dropdown, colorpicker, etc.) | 89 JS |
| **Services** | `services/` | Data & input singletons: orm, hotkey, field, file_upload, sortable, debug, etc. | 32 JS |
| **UI** | `ui/` | Overlay services & components: dialog, popover, tooltip, notification, effects, block | 21 JS |
| **Fields** | `fields/` | 67 field widget types in 7 subcategories (basic, display, media, relational, selection, specialized, temporal) | 105 JS |
| **Views** | `views/` | View types: form, list, kanban, calendar, graph, pivot + view utilities | 119 JS |
| **Webclient** | `webclient/` | App shell: navbar, menus, actions, user menu | 70 JS |
| **Search** | `search/` | Search bar, facets, filters, group-by, favorites | 31 JS |
| **Model** | `model/` | Client-side relational data model (Record, StaticList, etc.) | 29 JS |
| **Public** | `public/` | Public (anonymous) page features | 11 JS |

## JavaScript Services

Services are registered in `registry.category("services")` and injected via `useService()`.

### Data Services (`services/`)
| Service | File | Purpose |
|---------|------|---------|
| `orm` | `services/orm_service.js` | ORM gateway: create, read, write, unlink, search, call |
| `http` | `services/http_service.js` | Low-level HTTP fetch wrapper (GET/POST) |
| `field` | `services/field_service.js` | Field metadata loader with caching |
| `name` | `services/name_service.js` | Display name caching and batched loading |

### UI Overlay Services (`ui/`)
| Service | File | Purpose |
|---------|------|---------|
| `ui` | `ui/block/ui_service.js` | Viewport size tracking, active element management, block UI |
| `dialog` | `ui/dialog/dialog_service.js` | Modal dialog stack management |
| `overlay` | `ui/overlay/overlay_service.js` | Base overlay layer manager (dialogs, popovers, tooltips) |
| `popover` | `ui/popover/popover_service.js` | Positioned popover with escape/clickaway |
| `tooltip` | `ui/tooltip/tooltip_service.js` | Data-attribute tooltip system |
| `notification` | `ui/notification/notification_service.js` | Toast notifications |
| `bottom_sheet` | `ui/bottom_sheet/bottom_sheet_service.js` | Mobile bottom sheet |
| `effect` | `ui/effects/effect_service.js` | Visual effects (rainbow_man, etc.) |

### Input Services (`services/`)
| Service | File | Purpose |
|---------|------|---------|
| `hotkey` | `services/hotkeys/hotkey_service.js` | Keyboard shortcut registration |
| `command` | `services/commands/command_service.js` | Command palette (Ctrl+K) |
| `file_upload` | `services/file_upload_service.js` | XHR file upload with progress |
| `datetime_picker` | `components/datetime/datetime_picker_service.js` | Date/time picker popover |

### Infrastructure Services
| Service | File | Purpose |
|---------|------|---------|
| `localization` | `services/localization_service.js` | Translation loader (IndexedDB cached) |
| `error` | `services/error_service.js` | Global error handler |
| `scss_error_display` | `services/scss_error_display.js` | SCSS compilation error display |
| `title` | `services/title_service.js` | Document title management |
| `pwa` | `services/pwa/pwa_service.js` | PWA install prompt |
| `sortable` | `services/sortable_service.js` | Drag-and-drop sorting |
| `tree_processor` | `services/tree_processor_service.js` | Tree data structure processor |
| `web.frequent.emoji` | `services/frequent_emoji_service.js` | Emoji frequency tracking |

> Additional webclient-level services: `action`, `menu`, `view`, `currency`,
> `density`, `profiling`, `reloadCompany`, `shareTarget`, etc. These live in `webclient/` or `views/`.

## View Types

Each view type lives in `static/src/views/<type>/`:

| Type | Directory | Multi-record | Purpose |
|------|-----------|-------------|---------|
| Form | `views/form/` | No | Single record editing |
| List | `views/list/` | Yes | Tabular browsing, inline edit, sorting |
| Kanban | `views/kanban/` | Yes | Card columns, drag-drop |
| Calendar | `views/calendar/` | Yes | Event calendar (day/week/month) |
| Graph | `views/graph/` | Yes | Charts (bar, line, pie) — lazy loaded |
| Pivot | `views/pivot/` | Yes | Crosstab analysis — lazy loaded |

Field widgets (67 widget directories across 7 subcategories, ~95 registry entries counting view-specific variants) live in `fields/` (top-level). Import path: `@web/fields/*`.

## Controller Utilities (`views/view_utils.js`)

Shared logic extracted from form, list, and kanban controllers to eliminate duplication:

| Export | Purpose |
|--------|---------|
| `useControllerServices()` | Returns `{ action, dialog, notification, orm, uiHooks }` — replaces 4 `useService()` calls + `makeModelUIHooks()` in each controller |
| `makeModelUIHooks({ action, dialog, notification })` | Builds 8 hook implementations so model/record/list never import UI services directly |
| `computeArchiveEnabled(fields)` | Shared active/x_active writability check (used by list, kanban) |
| `buildActionMenuItems(staticItems, actionMenus)` | Shared filter-sort-map pipeline for action menu items |

**Model UI Hooks** (injected via `makeModelUIHooks`):
`onDisplayOnchangeWarning`, `onDisplayInvalidFields`, `onDisplayUrgentSave`, `onDisplayPropertyWarning`, `onDisplayArchiveAction`, `onConfirmArchive`, `onConfirmDuplicate`, `onDisplayLimitNotification`

> The data layer (`RelationalModel`, `Record`, `DynamicList` in `model/`) calls these hooks
> instead of importing dialog/notification/action services directly. Controllers wire the
> hooks via `useControllerServices()`. This decouples the data layer from UI concerns.

## Asset Bundles

Defined in `__manifest__.py`. Bundles group JS/CSS/SCSS for specific contexts.

### Main Bundles (served to browser via `t-call-assets`)

| Bundle | Context | Includes |
|--------|---------|----------|
| `web.assets_web` | Full backend | `assets_backend` + `main.js` + `start.js` entry points |
| `web.assets_backend` | Backend components | Bootstrap, OWL, all services, views (except lazy), webclient shell |
| `web.assets_backend_lazy` | On-demand views | Graph + Pivot (loaded when user opens these views) |
| `web.assets_frontend` | Public pages | OWL, Bootstrap, core services (no backend views) |
| `web.assets_frontend_minimal` | Early bootstrap | Module loader, session, cookies, UI helpers |
| `web.assets_backend_lazy_dark` | Lazy dark mode | Dark CSS for graph/pivot views |
| `web.assets_frontend_lazy` | Frontend extended | Full frontend with all components |
| `web.assets_web_dark` | Dark mode | CSS overrides for backend |
| `web.assets_web_print` | Print | Print stylesheet overrides |
| `web.assets_emoji` | Emoji picker | Emoji data (lazy loaded) |
| `web.report_assets_common` | Reports | Common report assets |
| `web.report_assets_pdf` | PDF reports | PDF-specific report assets |

### Internal Sub-Bundles (composition via `include`)

| Bundle | Purpose |
|--------|---------|
| `web._assets_core` | Module loader, OWL, Luxon, env.js, core/ directory |
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
| `web.assets_unit_tests` | All JS test files (except tours and legacy) |
| `web.assets_tests` | Legacy test utilities and tour definitions |

### Library Bundles

| Bundle | Library |
|--------|---------|
| `web.chartjs_lib` | Chart.js + Luxon adapter |
| `web.fullcalendar_lib` | FullCalendar core, daygrid, timegrid, list, luxon |
| `web.ace_lib` | ACE code editor (Python, XML, QWeb, JS, SCSS, JSON modes) |

## File Counts

| Category | Count |
|----------|-------|
| Python (controllers) | 21 |
| Python (models) | 20 |
| Python (tests) | 33 |
| JavaScript (src) | 602 |
| JavaScript (tests) | ~377 |
| JavaScript (vendored libs) | 122 |
| SCSS/CSS | 197 |
| XML (templates) | 260 |
| Total | ~1,607+ |
