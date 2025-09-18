# Web Module Model Map

Every Python model defined or extended by the `web` module, with fields, key methods, and purpose.

> **See also**: `doc/COMPONENT_DIAGRAM.md` maps models to audit areas:
> Area 4 (Web Data Access: web_read, web_read_group, web_search_panel),
> Area 5 (Onchange: web_onchange, record_snapshot),
> Area 2 (Auth: ir_http, res_users).
> `doc/FLOW_DIAGRAM.md` traces model methods through: Flow 3 (RPC), Flow 5 (Onchange),
> Flow 6 (Save), Flow 7 (List Data Loading).

## Frontend Data Layer

These models provide the core CRUD and data-fetching APIs consumed by the JS webclient.

### models/web_read.py — Base (`_inherit = 'base'`)

Core web CRUD operations: the primary data interface between JS and Python.

**Key Methods:**
- `web_read(specification)` — Main frontend data fetcher. Recursively resolves relational fields (m2o, x2m, reference, properties) per a specification tree. Handles NewId, co-record prefetch, x2many ordering/limiting.
- `web_save(vals, specification)` — Create or write + web_read in one call. Returns formatted record.
- `web_save_multi(vals_list, specification)` — Batch write grouped by identical vals. Returns formatted records.
- `web_search_read(domain, specification, ...)` — search + web_read. Reuses search query for count optimization.
- `web_name_search(name, specification, ...)` — name_search + formatting per specification. Batches display_name fetches.
- `web_resequence(specification, field_name='sequence', offset=0)` — Reorder records (from self) by sequence field.

> `specification` is a nested dict describing which fields and sub-fields to fetch,
> mirroring the view's field tree. This avoids over-fetching and enables recursive
> resolution of relational data in a single RPC call.

### models/web_read_group.py — Base (`_inherit = 'base'`)

Grouped data retrieval for list, kanban, pivot, and graph views.

**Key Methods:**
- `web_read_group(domain, groupby, aggregates, ...)` — Main RPC entry. Returns `{groups: [...], length: N}` with optional subgroup/record expansion. Accepts `unfold_read_specification` and `groupby_read_specification` as keyword args.
- `formatted_read_group(domain, groupby, aggregates, ...)` — High-level: calls `_read_group` + formatters + temporal fill + group expansion.
- `formatted_read_grouping_sets(domain, grouping_sets, aggregates, ...)` — Multi-groupby variant with multiple aggregate sets in one SQL query.
- `read_progress_bar(domain, group_by, progress_bar)` — Kanban column progress bar data (field value distribution per group).

### models/web_read_group_helpers.py — Base (`_inherit = 'base'`)

Helper formatters extracted from web_read_group.

**Key Methods:**
- `_web_read_group_fill_temporal(groups, groupby, ...)` — Fill date/datetime gaps with zero-value groups for chart continuity.
- `_web_read_group_expand(domain, groups, groupby_spec, aggregates, order)` — Call field's `group_expand` to show empty groups (e.g., all kanban stage columns).
- `_web_read_group_groupby_formatter(groupby_spec, values)` — Returns formatter function for a groupby spec (handles m2o, m2m, date granularities, properties).

### models/web_onchange.py — Base (`_inherit = 'base'`)

Client-side form processing.

**Key Methods:**
- `onchange(values, field_names, fields_spec)` — Main RPC for form changes. `values` = current form state dict, `field_names` = list of changed fields, `fields_spec` = specification tree. Simulates change, applies onchange methods, returns value diffs + warnings. Handles x2many prefetch, dependent field recomputation, snapshot-based diffing.
- `web_override_translations(values)` — Bulk override translatable field values in current language + en_US. `values` is a dict mapping field names to new values.

### models/record_snapshot.py — RecordSnapshot (utility class)

Dict subclass for snapshot-based form state tracking. Not an ORM model.

**Key Methods:**
- `__init__(record, fields_spec)` — Capture record state per form specification tree.
- `diff(other, force=False)` — Compare two snapshots, return dict of changed values + x2many commands (CREATE, UPDATE, LINK, DELETE/UNLINK). `force=True` includes all fields regardless of changes.
- `has_changed(field_name)` — Check if specific field changed between snapshots.

### models/web_search_panel.py — Base (`_inherit = 'base'`)

Search-panel RPC methods for sidebar filtering in list/kanban views.

**Key Methods:**
- `search_panel_select_range(field_name, ...)` — Returns `{parent_field, values}` for category filter with optional hierarchy and counters.
- `search_panel_select_multi_range(field_name, ...)` — Multi-select filter (m2o/m2m/selection); optimizes m2m counters via single `_read_group` query.

### models/web_search_panel_helpers.py — Base (`_inherit = 'base'`)

Internal helpers for search panel.

**Key Methods:**
- `_search_panel_field_image(field_name, ...)` — Returns `{value: {count, display_name}}` dict for filter options.
- `_search_panel_global_counters(values_range, parent_name)` — Aggregate child counts to parent for hierarchical filters.
- `_search_panel_sanitized_parent_hierarchy(records, parent_name, ids)` — Filter to maximal ancestor-closed subset.

## Session and UI Bootstrap

### models/ir_http.py — IrHttp (`_inherit = 'ir.http'`)

Webclient context setup, session info, and request handling.

**Constants:**
- `ALLOWED_DEBUG_MODES`: `''`, `'1'`, `'assets'`, `'tests'`
- `CRAWLER_USER_AGENTS`: tuple of bot/crawler identifiers

**Key Methods:**
- `session_info()` — Main bootstrap RPC. Returns comprehensive dict: uid, is_system, is_admin, user_context, registry_hash, user_settings, server_version, company tree, currencies, groups, etc.
- `get_frontend_session_info()` — Lightweight variant for public/website pages (no company hierarchy).
- `lazy_session_info()` — Hook for expensive session data loaded after bootstrap (override point).
- `webclient_rendering_context()` — Context dict for webclient HTML template.
- `color_scheme()` — Returns `"light"` (override point for dark mode).
- `content_density()` — Priority: cookie > user setting > `'default'`.
- `is_a_bot()` — Check if request matches known crawler user agents.

### models/ir_ui_menu.py — IrUiMenu (`_inherit = 'ir.ui.menu'`)

Webclient menu loader.

**Key Methods:**
- `load_web_menus(debug)` — Enriches `load_menus()` output with `appID`, `actionID`, `actionModel`, `actionPath`, `webIcon`, `webIconData` for each menu item. Consumed by sidebar and app switcher.

### models/ir_ui_view.py — IrUiView (`_inherit = 'ir.ui.view'`)

View type metadata for webclient.

**Key Methods:**
- `get_view_info()` — Returns cached dict of view types with `display_name`, `icon`, `multi_record` flag.
- `_get_view_info()` — Hardcoded metadata for list, form, graph, pivot, kanban, calendar, search, etc.

### models/ir_model.py — IrModel (`_inherit = 'ir.model'`)

Model metadata for webclient schema introspection.

**Key Methods:**
- `display_name_for(models)` — Display names for accessible models (hides access-denied vs nonexistent).
- `get_available_models()` — All accessible, non-transient, non-abstract models with display names.
- `_get_definitions(model_names)` — Field/relation/inverse metadata for a set of models (used by field_service.js).

### models/ir_qweb_fields.py — IrQwebFieldImage (`_inherit = 'ir.qweb.field.image'`)

Enhanced image rendering for QWeb templates.

**Key Methods:**
- `record_to_html(record, field_name, options)` — Renders `<img>` tag with `/web/image/` URL, alt text, classes, responsive, zoom, itemprop.
- `_get_src_urls(record, field_name, options)` — Builds image URL with max_size, unique hash, optional zoom URL.

Also: **IrQwebFieldImageUrl** (`_inherit = 'ir.qweb.field.image_url'`) for URL-based image fields.

## User Preferences

### models/res_users.py — ResUsers (`_inherit = 'res.users'`)

Web-specific user behavior.

**Key Methods:**
- `name_search(name, ...)` — Override: bubbles current user to top of search results.
- `_on_webclient_bootstrap()` — Hook for webclient-specific initialization (override point).
- `_should_captcha_login(credential)` — Check if CAPTCHA should block this credential (inspects `credential['type']`).

### models/res_users_settings.py — ResUsersSettings (`_inherit = 'res.users.settings'`)

Webclient user preferences.

**Fields:**
- `density` (Selection): UI density — `default` / `compact` / `condensed`
- `embedded_actions_config_ids` (One2many → `res.users.settings.embedded.action`)

**Key Methods:**
- `get_embedded_actions_settings()` — Current user's embedded action config.
- `set_embedded_actions_setting(action_id, res_id, ...)` — Create/update embedded action visibility and order.

### models/res_users_settings_embedded_action.py — ResUsersSettingsEmbeddedAction (`_name`)

Per-user embedded action configuration storage.

**Fields:**
- `user_setting_id` (Many2one → res.users.settings)
- `action_id` (Many2one → ir.actions.act_window, required)
- `res_model` (Char): Model of the parent record
- `res_id` (Integer): Parent record ID
- `embedded_actions_order` (Char): CSV action IDs for display order
- `embedded_actions_visibility` (Char): CSV action IDs for visibility
- `embedded_visibility` (Boolean): Whether top bar is visible

**Unique constraint:** `(user_setting_id, action_id, res_id)` — one config per user-action-record.

## Document Layout and Branding

### models/base_document_layout.py — BaseDocumentLayout (`_name`, TransientModel)

Transient wizard for live-preview report customization (colors, fonts, logos).

**Fields:**
- `company_id`, `logo`, `report_header`, `report_footer`, `company_details` (all related to company)
- `primary_color`, `secondary_color` (Char): Branding colors
- `logo_primary_color`, `logo_secondary_color` (Char, computed): Auto-extracted from logo
- `custom_colors` (Boolean, computed): True if user overrode auto-extracted colors
- `font` (Selection, related): Font choice
- `report_layout_id` (Many2one → report.layout): Selected layout template
- `preview` (Html, computed): Live QWeb-rendered report preview

**Key Methods:**
- `extract_image_primary_secondary_colors(logo, white_threshold)` — PIL-based color extraction from base64 image.
- `_compute_preview()` — Renders QWeb preview of selected layout.
- `document_layout_save()` — Abstract hook (returns close action by default).

### models/res_company.py — ResCompany (`_inherit = 'res.company'`)

Auto-regenerate report stylesheet on style changes.

**Key Methods:**
- `create(vals_list)` / `write(vals)` — Triggers `_update_asset_style()` if style fields change (font, colors, layout). `create` uses `@api.model_create_multi` (takes list of dicts).
- `_get_asset_style_b64()` — Renders `web.styles_company_report` QWeb template, returns base64 CSS.
- `_update_asset_style()` — Updates `web.asset_styles_company_report` attachment if content changed.

## Properties

### models/properties_base_definition.py — PropertiesBaseDefinition (`_inherit`)

**Key Methods:**
- `get_properties_base_definition(model_name, field_name)` — ACL-checked retrieval of property field definitions via `web_search_read`.

## Config

### models/res_config_settings.py — ResConfigSettings (`_inherit`, TransientModel)

**Fields:**
- `web_app_name` (Char, config_parameter='web.web_app_name'): Application name in browser title bar.

### models/res_partner.py — ResPartner (`_inherit = 'res.partner'`)

vCard export for contact data.

**Key Methods:**
- `_build_vcard()` — Constructs vobject vCard from partner (name, address, email, phone, org, title, photo).
- `_get_vcard_file()` — Returns serialized vCard bytes or False if vobject unavailable.

## Model Index

Quick lookup — file → model → primary role:

| File | Model | Role |
|------|-------|------|
| `web_read.py` | base | Frontend CRUD (web_read, web_save, web_search_read) |
| `web_read_group.py` | base | Grouped data for views (web_read_group) |
| `web_read_group_helpers.py` | base | Temporal fill, group expansion, formatters |
| `web_onchange.py` | base | Form change simulation (onchange) |
| `record_snapshot.py` | _(utility)_ | Snapshot diffing for onchange |
| `web_search_panel.py` | base | Sidebar filter panels |
| `web_search_panel_helpers.py` | base | Filter panel helpers |
| `ir_http.py` | ir.http | Session info, bootstrap, debug mode |
| `ir_ui_menu.py` | ir.ui.menu | Menu tree enrichment |
| `ir_ui_view.py` | ir.ui.view | View type metadata |
| `ir_model.py` | ir.model | Model schema introspection |
| `ir_qweb_fields.py` | ir.qweb.field.image | QWeb image rendering |
| `res_users.py` | res.users | User search priority, bootstrap hook |
| `res_users_settings.py` | res.users.settings | UI density, embedded actions |
| `res_users_settings_embedded_action.py` | res.users.settings.embedded.action | Per-user action config storage |
| `base_document_layout.py` | base.document.layout | Report layout wizard |
| `res_company.py` | res.company | Report style auto-regeneration |
| `properties_base_definition.py` | properties.base.definition | Property field definitions |
| `res_config_settings.py` | res.config.settings | web_app_name config |
| `res_partner.py` | res.partner | vCard export |
