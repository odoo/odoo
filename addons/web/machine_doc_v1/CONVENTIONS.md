# Web Module Conventions

Module-specific patterns, rules, and gotchas for working in `core/addons/web/`.

> **See also**: `doc/COMPONENT_DIAGRAM.md` — 18 audit areas with key invariants
> to verify per area. `doc/FLOW_DIAGRAM.md` — 14 end-to-end sequence diagrams.

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

**x2Many commands from JS follow this encoding:**

| Command | Tuple | Meaning |
|---------|-------|---------|
| CREATE | `[0, virtualID, {values}]` | Create new related record |
| UPDATE | `[1, id, {values}]` | Update existing related record |
| DELETE | `[2, id, false]` | Delete and unlink |
| UNLINK | `[3, id, false]` | Unlink without deleting |
| LINK | `[4, id, false]` | Link existing record |
| CLEAR | `[5, false, false]` | Clear all relations |
| SET | `[6, false, [ids]]` | Replace all with id list |

## Specification Pattern

The `web_read`, `web_save`, and `web_search_read` methods accept a `specification`
dict that mirrors the view's field tree. This controls which fields are fetched and
how relational fields are recursively resolved:

```python
# Example specification for a form view
specification = {
    "name": {},                           # scalar field
    "partner_id": {"fields": {            # many2one: fetch sub-fields
        "display_name": {},
        "email": {},
    }},
    "line_ids": {"fields": {              # one2many: fetch sub-fields
        "product_id": {"fields": {"display_name": {}}},
        "quantity": {},
        "price_unit": {},
    }, "limit": 40, "order": "sequence"},
}
```

When modifying view definitions, the specification must match or the frontend
will receive incomplete data.

## Controller Patterns

### Auth Types
- `auth='user'` — Requires authenticated session (most RPC endpoints)
- `auth='public'` — Works with or without session (images, assets, frontend)
- `auth='none'` — No session handling at all (health, login, database ops)
- `auth='bearer'` — Bearer token (JSON API only)

### Readonly Flag
Many routes declare `readonly=True` which routes them to a read replica if configured.
Write operations (create, write, unlink, button clicks) use `readonly=False` (default).

The `call_kw` route uses a dynamic `readonly=_call_kw_readonly` function that
inspects the method being called to determine read vs write.

### JSONRPC vs HTTP
- `type='jsonrpc'` (JSONRPC): Request/response wrapped in JSON-RPC 2.0 envelope. Used for data operations.
- `type='http'` (HTTP): Standard HTTP. Used for file downloads, page renders, binary content.

> Note: Routes without `methods=[...]` accept ALL HTTP methods (GET, POST, etc.).
> Only routes with explicit `methods=['GET']` or `methods=['POST']` are method-restricted.

## JavaScript Patterns

### Service Injection
```javascript
setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
}
```

### Registry System
Components, views, fields, services are all registered in named registries:
- `registry.category("services")` — Service definitions
- `registry.category("views")` — View type implementations
- `registry.category("fields")` — Field widget implementations
- `registry.category("actions")` — Client action components

### Field Widgets
Field widgets live in `static/src/fields/` (top-level, organized into 7 subcategories:
`basic/`, `display/`, `media/`, `relational/`, `selection/`, `specialized/`, `temporal/`).
Each field type (char, integer, many2one, etc.) has a directory with its component,
extractors, and optional variants. There are 67 widget directories (~95 registry entries
counting view-specific variants like `list.text`, `form.phone`).
Import path: `@web/fields/*` (e.g. `@web/fields/basic/char/char_field`).

## Test Conventions

### Tag Structure
Every test class uses `@tagged()` with:
1. **Layer tag** (required): `web_unit`, `web_http`, `web_tour`, `web_js`, `web_perf`, `web_benchmark`
2. **Topic tag** (required): `web_health`, `web_login`, `web_image`, etc.
3. **Install phase**: `at_install` (default) or `post_install` + `-at_install`

```python
@tagged('web_http', 'web_health')           # at_install (default)
class TestHealth(HttpCase): ...

@tagged('post_install', '-at_install', 'web_tour', 'web_login')
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
    _inherit = 'base'

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
- `static/src/core/` — Framework primitives: registry, utils, browser, l10n, network, py_js
- `static/src/components/` — Reusable OWL UI components (dropdown, colorpicker, etc.)
- `static/src/services/` — Data & input services (orm, hotkey, field, file_upload, etc.)
- `static/src/ui/` — UI overlay services & components (dialog, popover, tooltip, notification, effects, block)
- `static/src/fields/` — 67 field widget types in 7 subcategories (basic, display, media, relational, selection, specialized, temporal)
- `static/src/views/` — View type implementations (form, list, kanban, calendar, graph, pivot) + view utilities
- `static/src/webclient/` — App shell (navbar, menus, action container)
- `static/src/search/` — Search bar and filter components
- `static/src/model/` — Client-side relational data model (Record, StaticList, DynamicList, etc.)
- `static/src/public/` — Public (anonymous) page features

### Static Libraries (DO NOT MODIFY)
Everything under `static/lib/` is vendored third-party code.
Never edit these files. If a library needs updating, replace the entire directory.

## Gotchas

1. **`web_read` is NOT `read`** — `read()` returns raw field values. `web_read()` recursively
   resolves relational fields per specification. Frontend always uses `web_read`.

2. **`onchange` happens server-side** — The JS form view sends the entire form state to
   `onchange()` which simulates the change in a pseudo-record, computes dependents,
   and returns a diff. It does NOT save to the database.

3. **Asset bundles are order-sensitive** — Files in `__manifest__.py` asset lists are
   concatenated in order. SCSS variables must come before rules that reference them.
   Adding a file in the wrong position can break compilation.

4. **`readonly=True` on routes** — This is not about user permissions. It tells the
   load balancer/proxy to route to a read replica. A `readonly=True` route that
   accidentally writes will corrupt data on replicated setups.

5. **Image URL variants** — `/web/image/` has 17 URL patterns that all resolve to
   `content_image()`. `/web/content/` has another 7. When matching or rewriting image
   URLs, account for all variants (by xmlid, by id, by model/id/field, with/without
   dimensions, with/without filename).

6. **Lazy-loaded bundles** — Graph and Pivot views are in `assets_backend_lazy`, not
   `assets_backend`. They load on first access. Code that imports from these views
   must handle the lazy loading boundary.

7. **`CLEAR-CACHES` on unlink is global** — Any `unlink()` RPC broadcasts
   `CLEAR-CACHES` for all three cache keys (`web_read`, `web_search_read`,
   `web_read_group`) globally across all models. This invalidates caches in
   every open list/form view, even unrelated models. See `relational_model.js:129`
   and `doc/FLOW_DIAGRAM.md` Flow 14 for the full invalidation chain.

8. **Session info embedded in HTML** — `session_info()` is JSON-serialized into a
   `<script>` tag during page load. It contains HMAC keys (`registry_hash`,
   `browser_cache_secret`) and company hierarchy. The JS captures and deletes it
   from the global immediately. Never add sensitive data (passwords, API keys)
   to `session_info()` — it's visible in page source.
