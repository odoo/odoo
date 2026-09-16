# Web Module Model Map

Every Python model defined or extended by the `web` module, with fields, key methods, and purpose.

> **See also**: `COMPONENT_DIAGRAM.md` maps models to audit areas:
> Area 4 (Web Data Access), Area 5 (Onchange), Area 2 (Auth).
> `FLOW_DIAGRAM.md` traces model methods through Flow 3 (RPC), Flow 5
> (Onchange), Flow 6 (Save), Flow 7 (List Data Loading).

## Frontend Data Layer

Core CRUD and data-fetching APIs consumed by the JS webclient.

### models/web_read.py — Base (`_inherit = 'base'`)

Core web CRUD operations: the primary data interface between JS and Python.

**Key Methods:**
- `web_read(specification)` — Main frontend data fetcher. Recursively resolves relational fields (m2o, x2m, reference, properties) per a specification tree. Handles NewId, co-record prefetch, x2many ordering/limiting.
- `web_save(vals, specification, next_id=None, last_write_date=None, known_values=None)` — Create or write + web_read in one call. Returns formatted record. Optimistic concurrency: `known_values` (`{field: baseline_value}` as the client read them) triggers a **field-scoped** check via `_check_concurrent_field_changes` — `UserError` only if one of *those* fields moved server-side since the client read it; concurrent writes to other fields are ignored; comparison is type-aware (`SAFE_TYPES`: integer/boolean/char/text/selection/float/monetary/many2one, jsonb columns excluded) and **fails open**. `last_write_date` survives as the legacy coarser row-level `write_date` fallback, only consulted when `known_values` is absent (the JS client always sends `known_values` now).
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
- `_web_read_group_get_groupby_formatter(groupby_spec, values)` — Returns formatter function for a groupby spec (handles m2o, m2m, date granularities, properties).

### models/web_onchange.py — Base (`_inherit = 'base'`)

Client-side form processing.

**Key Methods:**
- `onchange(values, field_names, fields_spec)` — Main RPC for form changes. `values` = current form state dict, `field_names` = list of changed fields, `fields_spec` = specification tree. Simulates change, applies onchange methods, returns value diffs + warnings. Handles x2many prefetch, dependent field recomputation, snapshot-based diffing.
- `web_override_translations(values)` — Bulk override translatable field values in current language + en_US. `values` is a dict mapping field names to new values.

### models/record_snapshot.py — RecordSnapshot (utility class)

Dict subclass for snapshot-based form state tracking. Not an ORM model.

**Key Methods:**
- `__init__(record, fields_spec, update_all=True)` — Capture record state per form specification tree. `update_all=False` skips the initial `read()` (used when constructing snapshots from values already in hand).
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
- `_search_panel_get_field_image(field_name, ...)` — Returns `{value: {count, display_name}}` dict for filter options.
- `_search_panel_rollup_counters_global(values_range, parent_name)` — Aggregate child counts to parent for hierarchical filters.
- `_search_panel_filter_parent_hierarchy(records, parent_name, ids)` — Filter to maximal ancestor-closed subset.

## Session and UI Bootstrap

### models/ir_http.py — IrHttp (`_inherit = 'ir.http'`)

Webclient context setup, session info, and request handling.

**Constants:**
- `ALLOWED_DEBUG_MODES`: `''`, `'1'`, `'assets'`, `'tests'`
- `CRAWLER_USER_AGENTS`: tuple of bot/crawler identifiers

**Key Methods:**
- `session_info()` — Main bootstrap RPC. Returns dict built by `_get_session_info_base` + `session_info` additions. Full key list:
  - From `_get_session_info_base`: `uid`, `is_system`, `is_admin`, `is_public`, `is_internal_user`, `registry_hash`, `menus_cache_version`, `show_effect`, `currencies`, `quick_login`, `bundle_params`, `test_mode`, `cwv_sample_rate`, `feature_flags`, `has_unaccent`, optionally `server_version`, `server_version_info`
  - `has_unaccent` (`self.env.registry.has_unaccent`) reports whether `ilike` folds accents on this database. Load-bearing: the client evaluates the same domains in memory (`@web/core/domain`) and must make the same choice — `--unaccent` defaults to off, so on a database without the extension `café` and `cafe` are different text and the client must not fold either
  - Added by `session_info`: `user_context`, `max_file_upload_size`, `active_ids_limit`, `db`, `support_url` (`https://www.odoo.com/help`), `name`, `username`, `partner_write_date`, `partner_display_name`, `partner_id`, `home_action_id`, `view_info`, `user_settings`, `homemenu_default_config` (the active company's `res.company.homemenu_default_config`, selected from allowed company IDs in the `cids` cookie, falling back to the user's default company, or `None`), `groups`, `web.base.url`, conditionally `user_companies` (company hierarchy, only for internal users)
  - From `_get_expiration_info`, internal users only: `warning` (`admin` for `base.group_system`, else `user`), `expiration_date`, `expiration_reason` and, when `sysadmin.message` holds JSON, `sysadmin_message` with its `message` run through `html_sanitize`. Read by the `enterprise_subscription` service for the home-menu banners and the expired-database block
  - `menus_cache_version` is `f"{registry_hash}:{session_uid}"`, composed server side **once** because two independent consumers compare against it: the boot-time menus preload inlined in `webclient_templates.xml` and `menu_storage.js`. Do not recompose it on either side — when each built its own they drifted apart silently, the only symptom being a lost 304 and a full menu payload on every load
  - `groups` is a single-flag dict `{"base.group_allow_export": bool}`, NOT a full list of the user's groups
  - `browser_cache_secret` is NOT part of `session_info()` — it is injected separately by `home.py` into the HTML template after `session_info()` returns
- `get_frontend_session_info()` — Lightweight variant for public/website pages (no company hierarchy).
- `lazy_session_info()` — Hook for expensive session data loaded after bootstrap. Currently returns `{profile_session, profile_collectors, profile_params}`. Note: `max_profile_allowed` is NOT part of this response.
- `webclient_rendering_context()` — Context dict for webclient HTML template.
- `color_scheme()` — Returns `"light"` (override point for dark mode).
- `content_density()` — Priority: cookie > user setting > `'default'`.
- `is_a_bot()` — Check if request matches known crawler user agents.

### models/ir_ui_menu.py — IrUiMenu (`_inherit = 'ir.ui.menu'`)

Webclient menu loader.

**Key Methods:**
- `load_web_menus(debug)` — Enriches `load_menus()` output with `appID`, `actionID`, `actionModel`, `actionPath`, `actionResModel` (the window action's `res_model`, `False` for any other action type), `webIcon`, `webIconData` for each menu item. Consumed by the sidebar and the app launcher (home menu).

### models/ir_ui_view.py — IrUiView (`_inherit = 'ir.ui.view'`)

View type metadata for webclient.

**Key Methods:**
- `get_view_info()` — Returns cached dict of view types with `display_name`, `icon`, `multi_record` flag.
- `_get_view_info()` — Hardcoded metadata for EXACTLY seven view types: `list`, `form`, `graph`, `pivot`, `kanban`, `calendar`, `search`. No other types are defined here (extend this method to add a new view type).

### models/ir_model.py — IrModel (`_inherit = 'ir.model'`)

Model metadata for webclient schema introspection.

**Key Methods:**
- `display_name_for(model_names: list[str])` — Display names for accessible models (hides access-denied vs nonexistent).
- `get_available_models()` — All accessible, non-transient, non-abstract models with display names.
- `_get_definitions(model_names)` — Field/relation/inverse metadata for a set of models. Used by `controllers/model.py:/web/model/get_definitions`. Note: `field_service.js` does NOT call this — it calls the standard ORM `fields_get` via `orm.cache({type:"disk"})`.

### models/ir_qweb_fields.py — IrQwebFieldImage (`_inherit = 'ir.qweb.field.image'`)

Enhanced image rendering for QWeb templates.

**Key Methods:**
- `record_to_html(record, field_name, options)` — Renders `<img>` tag with `/web/image/` URL, alt text, classes, responsive, zoom, itemprop.
- `_get_src_urls(record, field_name, options)` — Builds image URL with max_size, unique hash, optional zoom URL.

Also: **IrQwebFieldImage_Url** (`_inherit = 'ir.qweb.field.image_url'`) for URL-based image fields.

### models/ir_asset.py — IrAsset (`_inherit = 'ir.asset'`)

Narrows asset bundles to a HOOT suite's dependency closure (`&module_scope=`, see `TEST_TAGS.md`).

**Key Methods:**
- `_prepare_assets_params()` — Adds `unit_test_scope` to the asset params (and so to the ormcache key) when a scope is in effect.
- `_get_unit_test_scope()` — Returns the scoped addon, or `""`. Reads `module_scope` from the **request**, not the bundle, since the scope varies per run; only honoured on the runner routes (`UNIT_TEST_ROUTES` = `/web/tests` and `/web/bundle/`, the latter being where `loadBundle` lands) and only for an installed addon, so a stray param elsewhere cannot fragment the asset cache.
- `_get_addons_in_unit_test_scope(scope)` — `scope` plus its transitive **manifest** dependency closure (`ormcache`d on `scope`). Addons outside the closure are exactly the ones a correct suite must not depend on.
- `_get_addons_active(*, unit_test_scope=None, **params)` — Override that filters the active addons to that closure. Returns the unfiltered list when no scope is set. Feeds `Resolution.active` in base, which is what also gates `ir.asset` rows (they name a path, never an addon).
- `_get_asset_bundle_url_segments(assets_params)` — Contributes `scope/<addon>` to the published URL, so `Binary.content_assets_scoped` can rebuild the bundle the page linked. `unique` alone distinguishes a scoped bundle but cannot describe it.

## User Preferences

### models/res_users.py — ResUsers (`_inherit = 'res.users'`)

Web-specific user behavior.

**Key Methods:**
- `name_search(name, ...)` — Override: bubbles current user to top of search results.
- `_on_webclient_bootstrap()` — Hook for webclient-specific initialization (override point).
- `_is_captcha_login_required(credential)` — Check if CAPTCHA should block this credential (inspects `credential['type']`).
- `web_create_users(emails)` — Batch-create internal users from a list of email addresses (used by invite-user UI).

### models/res_users_settings.py — ResUsersSettings (`_inherit = 'res.users.settings'`)

Webclient user preferences.

**Fields:**
- `embedded_actions_config_ids` (One2many → `res.users.settings.embedded.action`)
- `density` (Selection, `default='default'`, `required=True`): UI density — `default` / `compact` / `condensed`
- `color_scheme` (Selection, `default='system'`, `required=True`): `system` / `light` / `dark`. `system` defers to the OS preference; `ir_http.color_scheme()` is the server-side override point
- `homemenu_config` (Json, `readonly=True`): the user's home menu layout. `update_homemenu_config(changes)` checks ownership/write access, locks the settings record and applies pin, hide, order, pinned-order or reset operations to the latest stored value. Version 2 is a JSON object `{version, order, pinned, hidden}` of menu xml ids; version 1 was the bare `order` array and still reads, as do legacy JSON strings. IDs are deduplicated; hidden excludes pinned; unknown versions fall back. An explicit empty layout remains personal; reset stores `None` to follow company defaults. `webclient/menus/menu_utils.js` supplies `readHomeMenuConfig` (nullable), `parseHomeMenuConfig` and `serializeHomeMenuConfig`, and is the only place either form is parsed or serialised. Browser storage notifications prompt other launchers to read the authoritative settings row. Failed saves retain pending operations and offer Retry. What the user *opens* is `homemenu_usage`, below
- `homemenu_usage` (Json, `readonly=True`): what this user opens and when, as `{xmlid: {n, t}}` — a count and a last-use timestamp, at most fifty entries, ranked by a frecency whose count halves weekly. It backs the launcher's Recents row and the command palette's empty query. Held here rather than in the browser so a second device does not start blank; `webclient/menus/menu_usage.js` keeps a `localStorage` copy as the other half, merges the two per read taking the higher count and later use, and writes back debounced. The merge never sums, because the merged table is written back to the place half of it was read from

**Key Methods:**
- `_format_settings(fields_to_format)` (`@api.model`) — `super()` + replaces `embedded_actions_config_ids` with its formatted payload when requested. This is what puts `user_settings` into `session_info`.
- `get_embedded_actions_settings()` — Current user's embedded action config.
- `set_embedded_actions_setting(action_id, res_id, ...)` — Create/update embedded action visibility and order.

### models/home_menu_badge.py — HomeMenuBadge (`_name = 'home.menu.badge'`)

An `AbstractModel` and a collection point, not a table: the counts the app
launcher puts on its tiles, gathered in one call for the whole grid. An addon
with something waiting for the user extends `_get_badges` and adds its own count
under its app's xml id; `sale`, `purchase`, `stock`, `project` and `project_todo`
do. The client reads it through one `home_menu_badges` registry provider
(`webclient/home_menu/server_badges.js`), which is why five contributing addons
cost one request rather than five.

Server-side rather than a provider per addon because a domain belongs where its
vocabulary lives — a confirmed order is `state = 'done'` on this fork — and the
web client has no business carrying that.

**Key Methods:**
- `get_badges()` (`@api.model`) — the public entry: `_get_badges()` with the zeroes dropped, since a tile shows nothing rather than a `0`.
- `_get_badges()` (`@api.model`) — `{xmlid: count}`, empty here; the seam addons extend.
- `_count_for(xmlid, model, domain)` (`@api.model`) — one contribution, or `{}` when the model is absent or the reader cannot read it. `search_count` runs as the user, so a count already respects record rules, but a user with no access raises rather than answering zero — and one raising provider costs the client every count it carries, not just the one.

### models/res_users_settings_embedded_action.py — ResUsersSettingsEmbeddedAction (`_name`)

Per-user embedded action configuration storage.

**Fields:**
- `user_setting_id` (Many2one → res.users.settings)
- `action_id` (Many2one → ir.actions.act_window, required)
- `res_model` (Char, required=True): Model of the parent record
- `res_id` (Integer): Parent record ID
- `embedded_actions_order` (Char): CSV action IDs for display order
- `embedded_actions_visibility` (Char): CSV action IDs for visibility
- `embedded_visibility` (Boolean): Whether top bar is visible

**Unique constraint:** `(user_setting_id, action_id, res_id)` — one config per user-action-record.

## Document Layout and Branding

### models/ir_actions_report.py — IrActionsReport (`_inherit = 'ir.actions.report'`)

The PDF half of the report action. `base` declares the action type, its bindings and the HTML and text renders; this inherit adds everything that needs `web`'s layouts or WeasyPrint: `_get_layout()` (`web.minimal_layout`), the paperformat `@page` CSS, `OdooURLFetcher` (serves `/web/assets`, `/static`, `/web/image` and `/report/barcode` URLs in-process, refuses the rest through `ir.egress`), `WeasyPrintEngine` (per-database font and parsed-CSS cache, incremental merge above `report.weasyprint_native_merge_max`, tolerant-font retry, PDF/A and XMP through `data["__pdf_options__"]`), the article split with saved-attachment reuse, `_render_qweb_pdf` / `_render_html_to_pdf` / `_render_html_to_image`, and the `report_action` override that sends an admin with no company layout to `web.action_base_document_layout_configurator`. Moved here from `base` at web 2.3; `base` alone renders no PDF and never could, since the shell it poured every body into is `web.minimal_layout`.

**Module-level:** `PDF_OPTIONS_DATA_KEY`, `OdooURLFetcher`, `WeasyPrintEngine`, `_weasy_state` (process-wide shared state; `clear_for_tests()`).

### models/report_layout.py — ReportLayout (`_name = 'report.layout'`)

The catalogue of external layouts the document-layout wizard offers: one row per `web.external_layout_*` view with its preview image and PDF. Records in `data/report_layout.xml`. Moved here from `base` at web 2.3.

**Fields:** `view_id` (Many2one `ir.ui.view`, required, cascade), `image` / `pdf` (Char — preview asset URLs), `sequence` (Integer, default 50), `name` (Char).

### models/base_document_layout.py — BaseDocumentLayout (`_name`, TransientModel)

Transient wizard for live-preview report customization (colors, fonts, logos).

**Fields** (not exhaustive — wizard includes many `related` fields from the company to enable live edit):
- `company_id`, `logo`, `report_header`, `report_footer`, `company_details`, `paperformat_id`, `external_report_layout_id`, `partner_id`, `phone`, `email`, `website`, `vat`, `name`, `country_id` (all `related="company_id.<field>"`, mostly `readonly=False` for edit-through)
- `preview_logo` (Binary): uploaded logo preview
- `layout_background`, `layout_background_image` (Selection / Binary): background choice + image
- `primary_color`, `secondary_color` (Char, `related="company_id.primary_color"` etc., `readonly=False`): Branding colors — edits propagate to the company
- `logo_primary_color`, `logo_secondary_color` (Char, `compute="_compute_logo_colors"`): Auto-extracted from logo
- `custom_colors` (Boolean, computed, `readonly=False`): True if user overrode auto-extracted colors
- `font` (Selection, `related="company_id.font"`, `readonly=False`)
- `report_layout_id` (Many2one → `report.layout`): Selected layout template
- `preview` (Html, computed, **`sanitize=False`**): Live QWeb-rendered report preview. `sanitize=False` is intentional — preview is rendered server-side from trusted QWeb templates and displayed inside a wizard iframe.

**Onchange methods:** `_onchange_company_id`, `_onchange_custom_colors`, `_onchange_report_layout_id`, `_onchange_logo` (propagate wizard changes back to company on save).

**Key Methods:**
- `extract_image_primary_secondary_colors(logo, white_threshold=225, mitigate=175)` — PIL-based color extraction from base64 image. `mitigate` caps maximum channel value to avoid overly-saturated results.
- `_compute_preview()` — Renders QWeb preview of selected layout.
- `action_save_layout()` — Returns `self.env.context.get("report_action")` if set, else a close action. Not abstract — subclasses can still override.

### models/res_company.py — ResCompany (`_inherit = 'res.company'`)

Auto-regenerate report stylesheet on style changes, and hold the company's default home menu layout.

**Fields:** `external_report_layout_id` (Many2one `ir.ui.view` — the `report.layout` view poured around every external report), `font` (Selection), `primary_color` / `secondary_color` (Char), `layout_background` (Selection) and `layout_background_image` (Binary) — the document-layout block, moved here from `base` at web 2.3 because nothing in `base` reads it; `report_theme_id` (Many2one `report.theme`, defaults to `web.report_theme_modern`); `homemenu_default_config` (Json): the home menu layout a user of the company sees until they save one of their own, the same `{version, order, pinned, hidden}` shape as `res.users.settings.homemenu_config`. Surfaced in `session_info` and written from the home menu's edit mode by an admin ("Set as company default"); a user's own layout replaces it whole, never merges with it.

**Key Methods:**
- `create(vals_list)` / `write(vals)` — Triggers `_update_asset_style()` if style fields change (font, colors, layout); `write` also clears the registry's `assets` cache, which used to be `base`'s job when it held the fields. `create` uses `@api.model_create_multi` (takes list of dicts).
- `_get_asset_style_b64()` — Renders `web.styles_company_report` QWeb template, returns base64 CSS.
- `_update_asset_style()` — Updates `web.asset_styles_company_report` attachment if content changed.

### models/report_theme.py — ReportTheme (`_name = 'report.theme'`)

A named bundle of report design tokens (a *skin*), orthogonal to `report.layout` (structure) and to the company brand colors. Token values are emitted verbatim as `--rp-*` CSS custom properties by `web.styles_company_report`, scoped to the per-company `.o_company_<id>_layout` selector, so a theme change re-skins every printed document without touching a report template. Fields hold raw CSS values so WeasyPrint resolves them during PDF rendering. `_order = 'sequence, id'`.

**Fields:** `name` (Char, required, translate), `sequence` (Integer, default 50), `font_body` / `font_display` (Char — CSS font-family; empty falls back to company font, then to body font), `row_padding` (default `0.5rem`), `border_radius` (default `0`), `rule_weight` (default `1px`).

**Key Methods:**
- `write(vals)` — Calls `res.company._update_asset_style()` when any of `_STYLE_FIELDS` changes. Without this the edit would not reach a rendered report until an unrelated company write, since the asset is only regenerated on `res.company` writes.
- `unlink()` — Same reflow when a theme still referenced by a company is deleted; referencing companies fall back to the built-in token defaults.
- `_get_css_vars(primary, secondary, base_font)` — Returns the `--rp-*` block as `Markup` (raw, unescaped). Raw is required because font stacks contain quotes/commas that `t-out` would escape into `&#39;`, which is invalid inside a stylesheet. Values are run through `_CSS_UNSAFE` (strips `{};\n\r<>`) to prevent breaking out of the declaration. Colors come from the company brand; the rest from this theme, or defaults when `self` is an empty recordset.

## Properties

### models/properties_base_definition.py — PropertiesBaseDefinition (`_inherit = 'properties.base.definition'`)

Model is **defined upstream in `base`**; web only extends it. The `ir.model.access.csv` in `security/` correctly does not grant access here.

**Key Methods:**
- `get_properties_base_definition(model_name, field_name)` — `@api.model`. ACL-checked retrieval of property field definitions. Returns the `web_search_read` result **dict** (`{"length", "records"}`) on `properties.base.definition` — annotated `-> dict[str, Any]`; a singular dict, not a list.

## Export Presets

### models/ir_exports.py — IrExports (`_name = 'ir.exports'`), IrExportsLine (`_name = 'ir.exports.line'`)

Saved export field lists, read and written by the export dialog through
`controllers/export.py`. Moved here from `base` at web 2.2: `base` never read
them, and the two access rows (`base.group_allow_export`) are the only security.

**Fields:**
- `ir.exports`: `name` (Char), `resource` (Char, indexed), `export_fields` (One2many → ir.exports.line, `copy=True`)
- `ir.exports.line`: `name` (Char), `export_id` (Many2one → ir.exports, cascade)

## Config

### models/res_config_settings.py — ResConfigSettings (`_inherit`, TransientModel)

The **General Settings** page. `web` owns the root settings form, so this holds
the company/branding block and the `module_*` install toggles for the optional
addons offered there — not just web's own preference.

**Fields** (30):
- `web_app_name` (Char, `config_parameter='web.web_app_name'`): Application name in browser title bar
- `show_effect` (Boolean, `config_parameter='base.show_effect'`) · `profiling_enabled_until` (Datetime, `config_parameter='base.profiling_enabled_until'`)
- `group_multi_currency` (Boolean, `implied_group='base.group_multi_currency'`) — the only group-implying field here
- Company block: `company_id` (Many2one, required, defaults to `env.company`), `company_name` / `company_country_code` / `company_country_group_codes` / `report_footer` / `external_report_layout_id` (all `related='company_id.*'`; `report_footer` is `readonly=False` for edit-through), `is_root_company` / `company_informations` / `company_count` / `active_user_count` / `language_count` (all computed)
- Module install toggles (Boolean, one per optional addon — setting one installs it): `module_base_import`, `module_google_calendar`, `module_microsoft_calendar`, `module_mail_plugin`, `module_auth_oauth`, `module_auth_ldap`, `module_account_inter_company_rules`, `module_voip`, `module_web_unsplash`, `module_sms`, `module_partner_autocomplete`, `module_geocoding`, `module_google_recaptcha`, `module_website_cf_turnstile`, `module_google_address_autocomplete`

**Key Methods:**
- `open_company()` / `open_new_user_default_groups()` — Jump to the company form / the default-groups template user.
- `edit_external_header()` / `_prepare_report_view_action()` — Open the report header layout in the editor.
- `_compute_is_root_company`, `_compute_company_informations`, `_compute_company_count`, `_compute_active_user_count`, `_compute_language_count`.

### models/res_partner.py — ResPartner (`_inherit = 'res.partner'`)

vCard export for contact data.

**Key Methods:**
- `_prepare_vcard()` — Constructs vobject vCard from partner. Sets: `n` (structured name), `fn` (formatted name), `adr` (with optional `region`/`country`), `email` (`type_param="INTERNET"`), `tel` (`type_param="work"`), `url` (website), `org`, `title`, `photo` (base64 with `encoding_param="B"`).
- `_get_vcard_file()` — Returns serialized vCard bytes.

> **`vobject` is imported lazily, not at module top.** `_get_vobject()` (`res_partner.py`, `functools.cache`d) performs the `import vobject.vcard` and builds the `Proxy` classes on first use, because the proxy class bodies reference `vobject.base` at *definition* time. A top-level import would make the whole `web` addon fail to import when the library is absent. `controllers/vcard.py` guards the route with `importlib.util.find_spec("vobject")` and raises a clean `UserError` when it is missing — so the failure mode is a user-facing error on the vcard request, **not** an import-time crash.
>
> `vobject` is **not** declared in `__manifest__.py` — the manifest has no `external_dependencies` key at all. The docstring on `_get_vobject()` claims it is declared; that docstring is wrong, and the guard in `vcard.py` is what actually makes the dependency optional. Declaring it would be the tidier fix, but it changes installability, so it is called out here rather than assumed.

## Observability

### models/web_cwv_metric.py — WebCwvMetric (`_name = 'web.cwv.metric'`)

Storage for Core Web Vitals beacons. Records are written by
`controllers/observability.py:cwv()` through `_record_beacon()` and pruned on a
daily cron (`_remove_old_metrics`).

**One row per pageview, not per beacon.** A page emits several beacons — INP and
CLS keep growing after the first tab-switch — so `_record_beacon()` upserts on
`pageview_id` rather than inserting each time. Rows are therefore *updated* in
place to the latest values; treat the table as pageview-keyed, not append-only.

`_log_access = False`: the four standard audit columns
(`create_uid`/`create_date`/`write_uid`/`write_date`) are skipped (high-volume,
and the upsert makes `write_date` misleading anyway; `recorded_at` captures
first-beacon arrival).

**Fields** (numeric vitals are server-clamped before persistence; see
`controllers/observability.py:_clamp_latency`/`_clamp_cls`):
- `recorded_at` (Datetime, required, indexed, readonly, default `now`) — beacon arrival timestamp; used as the retention partition key
- `url` (Char, required, indexed, readonly) — browser path + query at beacon time
- `user_id` (Many2one → res.users, indexed `btree_not_null`, ondelete=`set null`) — null for anonymous frontend traffic
- `user_agent` (Char, readonly) — truncated to 500 chars at the controller
- `lcp` (Float, ms, readonly) — Largest Contentful Paint
- `fcp` (Float, ms, readonly) — First Contentful Paint
- `ttfb` (Float, ms, readonly) — Time To First Byte
- `inp` (Float, ms, readonly) — Interaction to Next Paint, reported by `web_vitals_service.js` as the **worst-observed interaction duration over the page lifetime** (a P100 running max — a strict upper bound on the canonical Chromium P98 INP, actionable as a regression signal; swap the reducer for a proper P98 if the `web-vitals` library is ever vendored). Server-clamped like the other latencies (`_clamp_latency`, `controllers/observability.py`)
- `cls` (Float, unitless, readonly) — Cumulative Layout Shift (0 is best; not capped at 1)
- `pageview_id` (Char, `size=64`, readonly) — client-generated id, stable for one page load; the upsert key. Empty/NULL is allowed and never conflicts, so a beacon without one still lands as its own row

**Key Methods:**
- `_record_beacon(values)` (`@api.model`) — Atomic `INSERT ... ON CONFLICT` upserting on `pageview_id`, replacing an earlier search-then-write: race-free (the partial unique index is the arbiter) and one round-trip instead of two.
- `init()` — Creates the partial unique index `web_cwv_metric__pageview_id_uniq` on `(pageview_id) WHERE pageview_id IS NOT NULL`. Partial so rows without a pageview id do not collide with each other.
- `_remove_old_metrics()` (`@api.model`) — Daily cron retention sweep. Reads `web.cwv.retention_days` (default `"30"`). `0` disables (cron no-op). Issues a single raw `DELETE FROM web_cwv_metric WHERE recorded_at < now() - INTERVAL ...` (no ORM iteration — nothing here needs recomputation or cascade). Registered via `data/web_cwv_metric_data.xml`.

### models/web_js_error.py — WebJsError (`_name = 'web.js.error'`)

Storage for client-side JS error beacons. Records are written by
`controllers/observability.py:js_error()` via `sudo()` (beacons arrive from
anonymous frontend visitors too) and pruned on a daily cron (`_remove_old_errors`).

`_log_access = False`, same rationale as `web.cwv.metric`: append-only and
high-volume, with `recorded_at` capturing beacon arrival.

Producers of the beacons this stores:

- `static/src/module_loader.js` — the pre-ESM shim's `error` /
  `unhandledrejection` / asset-load listeners (`kind` `error`,
  `unhandledrejection`, `asset_load_error`, `module_rebind`).
- `static/src/core/errors/error_beacon.js` — the canonical ESM beacon.
- `static/src/env.js` — services that never started (`kind` `service_start`).

**Fields:** (13 — the beacon payload, one column per field the client sends,
plus arrival time and the reporting session)

- `recorded_at` (Datetime, required, indexed) — beacon arrival, standing in for
  `create_date` since `_log_access = False`.
- `user_id` (Many2one `res.users`, `ondelete="set null"`, `btree_not_null`) —
  session that emitted the beacon; null for anonymous frontend traffic.
- `phase` (Selection `pre_boot`/`post_boot`/`unknown`) — whether the module
  system had finished booting. A `pre_boot` failure means the loader itself
  never came up, so nothing else in the client is trustworthy at that point.
- `kind` (Selection, indexed) — `error`, `unhandledrejection`, `service_start`,
  `asset_load_error`, `module_rebind`. Kept in step with `_JS_ERROR_KINDS` in
  `controllers/observability.py` by `TestJsErrorTaxonomy`, which scans the
  emitters listed above so a newly-emitted kind cannot silently degrade to
  `error`.
- `message` (Char, required, `size=4096`) — the error message.
- `cause` (Text) — flattened `error.cause` chain, one `Caused by:` segment per
  level, depth-capped at 8 and cycle-guarded. This is the field an OWL lifecycle
  error points at: its own message says to read `cause`, and without it the
  report names a failure without saying why.
- `stack` (Text) — the reported stack.
- `filename` (Char, `size=500`), `line` (Integer), `col` (Integer) — the
  position the browser attributed the failure to; `0`/empty when it gave none.
- `url` (Char, `size=500`) — the failing page. Deliberately unindexed: the
  search view reaches it through `ilike` and `group_by`, neither of which a
  btree serves, so an index would only add a tuple write per INSERT on a
  write-only table.
- `user_agent` (Char, `size=500`) — reporting browser.
- `reloaded` (Selection `reloaded`/`suppressed`, nullable) — set only for
  `asset_load_error`: whether the loader's one-per-minute self-heal reload fired
  or the guard suppressed it. **Null means not applicable**, not "suppressed" — a
  Boolean here would claim a reload was withheld when none was attempted.

`message` is `Char(size=4096)`; `cause` and `stack` are `Text` with explicit
`CHECK(char_length(...) <= 4096)` constraints, since Text carries no length.

**Key Methods:**

- `_record_beacon(values)` (`@api.model`) — single raw parameterized INSERT. No
  upsert key, unlike `web.cwv.metric`: two identical errors from two sessions are
  two facts, not one row to update.
- `_remove_old_errors()` (`@api.model`) — daily cron retention sweep. Reads
  `web.js_error.retention_days` (default `"30"`); `0` disables. Matters more than
  the CWV sweep: the endpoint is `auth="public"`, so a caller bounded only by the
  120/60s rate limit could add ~172k rows a day. Registered via
  `data/web_js_error_data.xml`.

The ACL is `1,0,0,1` for `base.group_system` (`security/ir.model.access.csv`):
read and `unlink` granted, `write`/`create` denied — the controller writes
through `sudo()`.

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
| `ir_qweb_fields.py` | ir.qweb.field.image + ir.qweb.field.image_url | QWeb image rendering (2 classes: `IrQwebFieldImage`, `IrQwebFieldImage_Url`) |
| `ir_asset.py` | ir.asset | HOOT `&module_scope=` bundle narrowing |
| `ir_exports.py` | ir.exports + ir.exports.line | Export dialog presets (saved field lists) |
| `res_users.py` | res.users | User search priority, bootstrap hook |
| `home_menu_badge.py` | home.menu.badge | App launcher tile counts (abstract; addons extend `_get_badges`) |
| `res_users_settings.py` | res.users.settings | UI density, embedded actions |
| `res_users_settings_embedded_action.py` | res.users.settings.embedded.action | Per-user action config storage |
| `ir_actions_report.py` | ir.actions.report | PDF engine, layouts, attachments (the action type is base's) |
| `report_layout.py` | report.layout | External layout catalogue |
| `base_document_layout.py` | base.document.layout | Report layout wizard |
| `res_company.py` | res.company | Report style auto-regeneration |
| `report_theme.py` | report.theme | Report layout theme records |
| `properties_base_definition.py` | properties.base.definition | Property field definitions |
| `res_config_settings.py` | res.config.settings | web_app_name config |
| `res_partner.py` | res.partner | vCard export |
| `web_cwv_metric.py` | web.cwv.metric | Core Web Vitals beacon storage + retention |
| `web_js_error.py` | web.js.error | JS error beacon storage + retention |
