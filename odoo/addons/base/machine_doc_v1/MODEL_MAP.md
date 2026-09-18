# Base Module Model Map

Every Python model defined or extended by the `base` module, with fields, key methods, and purpose.

---

## Actions System

The action types — the core navigation primitives of the webclient — are one
file per type, each inheriting `ir.actions.actions`.

### models/ir_actions_actions.py

#### IrActions — `ir.actions.actions` (`_name`, `_table = ir_actions`, inherits `mixin.table.inheritance.root`)

Base action model. All action types inherit from this, each with its own
PostgreSQL table `INHERITS (ir_actions)`, created by the ORM from
`_table_inheritance_root`. The root table itself is sealed by a
`CHECK (false) NO INHERIT` constraint at init, after any row still sitting in
it is moved to the table its `type` names.

**Fields:**
- `name` (Char, required, translatable)
- `type` (Char, required) — Action type discriminator
- `xml_id` (Char, computed) — External identifier
- `path` (Char) — URL path; uniqueness lives in `ir.actions.path`
- `help` (Html, translatable) — Empty list help text
- `binding_model_id` (Many2one → ir.model) — Model to bind action to
- `binding_type` (Selection) — `action` or `report`
- `binding_view_types` (Char, default=`list,form`) — Views where binding appears

**Key Methods:**
- `get_bindings(model_name)` — Retrieve bound actions for a model
- `_get_action_dict_by_xml_id(full_xml_id)` — Read the action with this XML ID as a client-ready dict
- `_get_action_dict()` — Return action data dict for webclient; `type` is the concrete model, not the stored column
- `_get_fields_readable()` — Fields safe for web access
- `_get_field_target_model()` / `_get_field_groups()` — Per kind of action: the field naming the model it opens, the field holding the groups it is restricted to; empty on the root. The root asks these instead of probing its leaves' field names
- `_get_fields_binding_extra()` — Per kind: what a binding ships beyond `_BINDING_READ_FIELDS`; an addon extends it through `super()` on the leaf it adds a column to

### models/ir_actions_path.py

#### IrActionsPath — `ir.actions.path` (`_name`)

A side table holding one row per action that declares a URL path, so the
uniqueness of `ir.actions.actions.path` is a database constraint rather than a
search. Two `models.Constraint`s carry it: `_path_unique` on the path and
`_action_unique` on the action.

**Fields:** `path` (Char, required), `action_id` (Many2one → ir.actions.actions)

**Key Methods:**
- `init()` — Backfill from existing action paths, then WARN about any action
  whose path could not be backed because another already claims it. Those actions
  keep an unreachable path and are named in the log rather than dropped.

### models/ir_actions_act_window.py

#### IrActionsAct_Window — `ir.actions.act_window` (`_name`, inherits `ir.actions.actions`)

Window action — opens a view on a model.

**Fields:**
- `view_id` (Many2one → ir.ui.view) — Specific view
- `domain` (Char) — Python expression for filtering
- `context` (Char, required, default=`{}`) — Python dict
- `res_id` (Integer) — Record ID for form view
- `res_model` (Char, required) — Target model
- `target` (Selection) — `current`, `new`, `fullscreen`, `main`
- `view_mode` (Char, required) — Comma-separated: `list,form,kanban,...`
- `mobile_view_mode` (Char, default=`kanban`)
- `view_ids` (One2many → ir.actions.act_window.view)
- `views` (Binary, computed) — Ordered `(view_id, view_mode)` pairs
- `limit` (Integer, default=80) — Records per page
- `group_ids` (Many2many → res.groups) — Group restrictions
- `search_view_id` (Many2one → ir.ui.view) — Search view
- `embedded_action_ids` (One2many, computed) — Embedded actions
- `filter` (Boolean), `cache` (Boolean, default=True)

**Key Methods:**
- `_compute_views()` — Compute ordered view list
- `read(fields, load)` — Enriches help from model's `get_empty_list_help()`
- `_get_action_dict()` — Includes embedded actions data

### models/ir_actions_act_window_view.py

#### IrActionsAct_WindowView — `ir.actions.act_window.view` (`_name`)

View ordering within a window action.

**Fields:**
- `sequence` (Integer), `view_id` (Many2one → ir.ui.view)
- `view_mode` (Selection, required) — list, form, graph, pivot, calendar, kanban
- `act_window_id` (Many2one → ir.actions.act_window, cascade)
- `multi` (Boolean)

### models/ir_actions_act_window_close.py

#### IrActionsAct_Window_Close — `ir.actions.act_window_close` (`_name`, `_table = ir_act_window_close`, inherits actions)

Close window action. Minimal — just inherits type. Almost always returned as a
dict from Python rather than stored; its table exists so the root stays empty.

### models/ir_actions_act_url.py

#### IrActionsAct_Url — `ir.actions.act_url` (`_name`, inherits actions)

URL action — opens an external URL.

**Fields:**
- `url` (Text, required), `target` (Selection) — `new`, `self`, `download`

### models/ir_actions_todo.py

#### IrActionsTodo — `ir.actions.todo` (`_name`)

Configuration wizard queue.

**Fields:**
- `action_id` (Many2one → ir.actions.actions, required)
- `sequence` (Integer, default=10), `state` (Selection) — `open`, `done`

**Key Methods:**
- `ensure_one_open_todo()` — Keep only one open todo
- `action_launch()` — Launch wizard action

### models/ir_actions_client.py

#### IrActionsClient — `ir.actions.client` (`_name`, inherits actions)

Client-side action — triggers a JS component.

**Fields:**
- `tag` (Char, required) — Client action identifier
- `target` (Selection), `res_model` (Char), `context` (Char)
- `params` (Binary, computed/inverse), `params_store` (Binary)

---

### models/ir_actions_report.py

#### IrActionsReport — `ir.actions.report` (`_name`, inherits actions)

Report actions — the action type, its bindings, and the QWeb HTML and text
renders. The PDF path (WeasyPrint engine, layouts, attachments) is `web`'s
`_inherit` of this model; `base` alone renders no PDF.

**Fields:**
- `model` (Char, required) — Target model name
- `report_type` (Selection, required) — `qweb-html`, `qweb-pdf`, `qweb-text`
- `report_name` (Char, required) — QWeb template name
- `report_file` (Char) — Path to report file
- `group_ids` (Many2many → res.groups)
- `paperformat_id` (Many2one → report.paperformat)
- `print_report_name` (Char, translatable) — Filename expression
- `attachment_use` (Boolean) — Reload from cached attachment
- `attachment` (Char) — Save prefix expression

**Key Methods:**
- `_get_attachments(records, filenames)` — Cached report attachments per record
- `get_paperformat()` — Get paper format (self or company default)
- `_get_report(report_ref)` — Resolve id, name or record to the sudo report
- `_render_qweb_html(report_ref, docids, data)` — Render QWeb to HTML
- `_render_qweb_text(report_ref, docids, data)` — Render QWeb to text
- `_render(report_ref, res_ids, data)` — Dispatch on `report_type` (`_render_qweb_pdf` arrives with `web`)
- `prepare_barcode(barcode_type, value, **kwargs)` — Barcode PNG, also the QWeb barcode field's backend
- `_merge_pdfs(streams)` — pypdf merge with a per-stream error policy
- `report_action(docids, data, config)` — Return action dict for webclient

---

### models/ir_actions_server.py

#### IrActionsServer — `ir.actions.server` (`_name`, inherits actions)

Automated server actions — execute code, CRUD operations, or webhooks. The
webhook HTTP delivery, target scrubbing and log target live in
`odoo/libs/webhook.py` (Odoo-agnostic); the model schedules the delivery on
commit and logs the scheduling and the rollback.

**Fields:**
- `state` (Selection, required) — `object_write`, `object_create`, `object_copy`, `code`, `webhook`, `multi`
- `usage` (Selection) — `ir_actions_server` or `ir_cron`
- `model_id` (Many2one → ir.model, required)
- `model_name` (Char, related)
- `code` (Text) — Python code to execute
- `child_ids` (One2many → self) — Sub-actions for `multi` state
- `update_path` (Char) — Field path for write operations
- `update_m2m_operation` (Selection) — `add`, `remove`, `set`, `clear`
- `value` (Text) — Expression or literal value
- `evaluation_type` (Selection) — `value`, `sequence`, `equation`
- `webhook_url` (Char), `webhook_field_ids` (Many2many → ir.model.fields)

**Key Methods:**
- `run()` — Main entry point, dispatches to runner
- `_run_action_code_multi(eval_context)` — Execute Python code
- `_run_action_object_write(eval_context)` — Update records
- `_run_action_object_create(eval_context)` — Create record
- `_run_action_object_copy(eval_context)` — Duplicate record
- `_run_action_webhook(eval_context)` — Send POST request
- `_run_action_multi(eval_context)` — Run child actions sequentially
- `_prepare_eval_context(action)` — Prepare safe evaluation context
- `create_action()`, `unlink_action()` — Manage action bindings

#### IrActionsServerHistory — `ir.actions.server.history` (`_name`)

Code revision history for server actions.

**Fields:**
- `action_id` (Many2one → ir.actions.server, cascade), `code` (Text)

**Key Methods:**
- `_gc_histories()` — Autovacuum, keeps last 100 entries

#### ServerActionHistoryWizard — `server.action.history.wizard` (TransientModel)

Wizard to view diffs and restore previous code revisions.

---

## Model Registry

### models/ir_model.py

#### Unknown — `_unknown` (AbstractModel)

The placeholder model. Declares nothing but a name, and exists so code holding
an unresolvable model can still return a recordset: `odoo/tools/translate.py`
browses it when a translation's model is not in the registry, rather than raising
in the middle of an export.

#### IrModel — `ir.model` (`_name`)

Model metadata registry — one record per ORM model.

**Fields:**
- `name` (Char, translatable, required) — Human-readable description
- `model` (Char, required) — Technical model name (e.g., `res.partner`)
- `order` (Char, default=`id`, required) — Default SQL ordering
- `field_id` (One2many → ir.model.fields, required)
- `inherited_model_ids` (Many2many, computed)
- `state` (Selection) — `manual` (Studio) or `base` (code-defined)
- `access_ids` (One2many → ir.model.access), `rule_ids` (One2many → ir.rule)
- `abstract` (Boolean), `transient` (Boolean)
- `modules` (Char, computed) — Installed modules defining this model
- `count` (Integer, computed) — Total records
- `fold_name` (Char) — Field for kanban column folding

**Key Methods:**
- `_get(name)` — Get model record by technical name
- `_get_id(name)` — Get model ID by name (ormcache)
- `_reflect_models(model_names)` — Sync model metadata from registry to DB
- `create(vals_list)` — Create + reload registry
- `write(vals)` — Update + reload if order/fold_name changed
- `unlink()` — Delete + cleanup fields/crons/data + reload registry

#### IrModelInherit — `ir.model.inherit` (`_name`)

Tracks model inheritance relationships.

**Fields:**
- `model_id` (Many2one → ir.model, required)
- `parent_id` (Many2one → ir.model, required)
- `parent_field_id` (Many2one → ir.model.fields) — For `_inherits` only

**Key Methods:**
- `_reflect_inherits(model_names)` — Sync inheritance tree from registry

---

### models/ir_model_fields.py

#### IrModelFields — `ir.model.fields` (`_name`)

Field metadata registry — one record per field per model.

**Fields:**
- `name` (Char, required, indexed) — Field technical name
- `model` (Char, required, indexed), `model_id` (Many2one → ir.model, required)
- `field_description` (Char, required, translatable) — Human label
- `ttype` (Selection, required) — Field type (char, text, boolean, integer, float, monetary, date, datetime, one2many, many2one, many2many, selection, reference, html, binary, image, properties)
- `relation` (Char) — Comodel for relational fields
- `relation_field` (Char) — Inverse field for one2many
- `selection_ids` (One2many → ir.model.fields.selection)
- `related` (Char) — Dot-separated related field path
- `required`, `readonly`, `index` (Boolean)
- `translate` (Selection) — `standard`, `html_translate`, `xml_translate`
- `company_dependent` (Boolean)
- `state` (Selection) — `manual` or `base`
- `on_delete` (Selection) — `cascade`, `set null`, `restrict`
- `store` (Boolean, default=True), `compute` (Text), `depends` (Char)

**Key Methods:**
- `_get(model_name, field_name)` — Get field record
- `_get_ids_by_name(model_name)` — Get `{field_name: field_id}` dict
- `_reflect_fields(model_names)` — Sync field metadata from registry to DB

---

### models/ir_model_fields_selection.py

#### IrModelFieldsSelection — `ir.model.fields.selection` (`_name`)

Selection field options.

**Fields:**
- `field_id` (Many2one → ir.model.fields, required, indexed)
- `value` (Char, required), `name` (Char, required, translatable)
- `sequence` (Integer, default=1000)

**Key Methods:**
- `_get_selection(field_id)` — Get `[(value, name), ...]` for field
- `_reflect_selections(model_names)` — Sync selections from field definitions
- `_update_selection(model_name, field_name, selection)` — Insert/update/delete options
- `_process_ondelete()` — Handle ondelete policies when selection removed

---

### models/ir_model_access.py

Contains the access-control model. The constraint- and relation-reflection
models live in `models/ir_model_reflection.py` (re-exported from `ir_model.py`
for backward compatibility).

#### IrModelAccess — `ir.model.access` (`_name`)

Model-level access control lists.

**Fields:**
- `name` (Char, required, indexed), `active` (Boolean, default=True)
- `model_id` (Many2one → ir.model, required, indexed)
- `group_id` (Many2one → res.groups, indexed) — NULL = global access
- `perm_read`, `perm_write`, `perm_create`, `perm_unlink` (Boolean)

**Key Methods:**
- `check(model, mode, raise_exception)` — Check current user has access
- `_get_groups_with_access(model_name, access_mode)` — Get group expression (ormcache)
- `_get_models_allowed(mode)` — Models accessible to current user (ormcache)
- `group_names_with_access(model_name, access_mode)` — Visible group names with access
- `_prepare_access_error(model, mode)` — Build detailed AccessError message

#### IrModelConstraint — `ir.model.constraint` (`_name`)

Tracks database constraints created by models.

**Fields:**
- `name` (Char, required), `definition` (Char) — PostgreSQL constraint text
- `message` (Char, translatable) — Error message
- `model` (Many2one → ir.model), `module` (Many2one → ir.module.module)
- `type` (Char, size=1) — `f` (FK), `u` (unique/check), `i` (index)

**Key Methods:**
- `_reflect_constraints(model_names)` — Sync constraints from registry
- `unlink()` — Drop constraint from database

#### IrModelRelation — `ir.model.relation` (`_name`)

Tracks many2many relation tables.

**Fields:**
- `name` (Char, required) — M2M table name
- `model` (Many2one → ir.model), `module` (Many2one → ir.module.module)

**Key Methods:**
- `_uninstall_module_data()` — Drop M2M tables on module uninstall

---

### models/ir_model_data.py

#### IrModelData — `ir.model.data` (`_name`)

XML ID registry — maps external identifiers to database records.

**Fields:**
- `name` (Char, required) — ID suffix
- `complete_name` (Char, computed) — `module.name`
- `model` (Char, required) — Target model name
- `module` (Char, default=`""`, required) — Module prefix
- `res_id` (Many2oneReference) — Target record ID
- `noupdate` (Boolean) — Skip updates on module upgrade

**Key Methods:**
- `_get_xmlid_target(xmlid)` — Returns `(model, res_id)` (ormcache)
- `_xmlid_to_res_model_res_id(xmlid, raise_if_not_found)` — Safe wrapper
- `_xmlid_to_res_id(xmlid, raise_if_not_found)` — Extract just res_id
- `check_object_reference(module, xml_id, raise_on_access_error)` — Access check
- `_update_xmlids(data_list, update)` — Batch create/update XML IDs
- `_uninstall_module_data(modules_to_remove)` — Delete records by module on uninstall

### models/ir_model_common.py

#### Module-level helpers (non-ORM)

Shared by the `ir.model` family: `ACCESS_MODES` and the access-error message
table, the xmlid builders (`model_xmlid`, `field_xmlid`, `selection_xmlid`,
`inherit_xmlid`), the reflection upsert queries (`query_insert`,
`query_update`, `select_en`, `upsert_en`) and the registry helpers
(`prepare_compute`, `mark_modified`, `reload_schema`). Re-exports
`MODULE_UNINSTALL_FLAG` for downstream modules.

---

## Access Control

### models/ir_rule.py

#### IrRule — `ir.rule` (`_name`)

Record-level access rules — domain-based filtering per model/group/operation.

**Fields:**
- `name` (Char), `active` (Boolean, default=True)
- `model_id` (Many2one → ir.model, required, indexed)
- `groups` (Many2many → res.groups) — NULL = global rule
- `domain_force` (Text) — Rule domain expression
- `perm_read`, `perm_write`, `perm_create`, `perm_unlink` (Boolean, default=True)

**Key Methods:**
- `_get_domain_accessible_records(model_name, mode)` — Compute effective domain for current user (ormcache)
- `_get_rules(model_name, mode)` — Get applicable rules
- `_get_failing(for_records, mode)` — Get rules failing on specific records
- `_eval_context()` — Build safe_eval context (user, company_ids, company_id)

---

## UI Framework

### models/ir_ui_view.py

#### IrUiView — `ir.ui.view` (`_name`)

View definitions — the core UI building block.

**Fields:**
- `name` (Char, required), `model` (Char, indexed) — Target model
- `key` (Char, indexed) — Unique view key
- `priority` (Integer, default=16) — Lower = higher priority
- `type` (Selection) — list, form, graph, pivot, calendar, kanban, search, qweb
- `arch` (Text, computed/inverse) — View arch with translations
- `arch_base` (Text, computed/inverse) — Arch without translations
- `arch_db` (Text, translatable) — Stored arch
- `arch_fs` (Char) — File path if from XML
- `arch_prev` (Text) — Previous arch for rollback
- `inherit_id` (Many2one → self, indexed) — Parent view
- `inherit_children_ids` (One2many → self)
- `mode` (Selection) — `primary` or `extension`
- `active` (Boolean, default=True)
- `group_ids` (Many2many → res.groups) — NULL = all users

**Key Methods:**
- `apply_inheritance_specs(source, specs_tree, pre_locate)` — Apply XPath inheritance spec
- `_check_view(arch)` — Validate arch (groups, fields, actions)
- `_render_template(arch_tree, values, ...)` — Render arch through QWeb

### models/ir_ui_view_base.py

#### Base — `_inherit = 'base'` (extends all models)

Default view generators, view access, and access helpers.

**Key Methods:**
- `get_view(view_id, view_type, **options)` — Get view with inheritance applied
- `get_views(views, options)` — Load multiple views at once
- `get_empty_list_help(help_message)` — Hook for empty list message
- `_get_default_form_view()` — Auto-generate form view
- `_get_default_search_view()` — Auto-generate search view
- `_get_default_list_view()`, `_get_default_kanban_view()`, `_get_default_pivot_view()`, `_get_default_graph_view()`, `_get_default_calendar_view()`
- `_get_access_action(access_uid, force_website)` — Hook for record access action

### models/ir_ui_view_custom.py

#### IrUiViewCustom — `ir.ui.view.custom` (`_name`)

User-specific view customizations (Copy-on-Write).

**Fields:**
- `ref_id` (Many2one → ir.ui.view, required), `user_id` (Many2one → res.users, required)
- `arch` (Text, required) — Custom arch

### models/ir_ui_view_name_manager.py

#### NameManager (utility class, not ORM model)

Validates view XML structure: fields, actions, groups, names.

**Key Methods:**
- `add_available_field(node, name, node_info, info)` — Register available field
- `add_used_fields(node, names, node_info, use)` — Declare field dependency
- `check(view)` — Validate all dependencies exist + group consistency

---

### models/ir_ui_menu.py

#### IrUiMenu — `ir.ui.menu` (`_name`, `_parent_store = True`)

Menu tree — hierarchical navigation.

**Fields:**
- `name` (Char, required, translatable)
- `active` (Boolean, default=True), `sequence` (Integer, default=10)
- `child_id` (One2many → self), `parent_id` (Many2one → self, indexed)
- `parent_path` (Char, indexed)
- `group_ids` (Many2many → res.groups) — NULL = visible to all
- `web_icon` (Char), `web_icon_data` (Binary, attachment)
- `action` (Reference → ir.actions.*) — Linked action

**Key Methods:**
- `_get_visible_menu_ids(debug)` — Get visible menu IDs for current user (ormcache)
- `_filter_visible_menus()` — Filter to visible menus

---

### models/ir_asset.py

#### IrAsset — `ir.asset` (`_name`)

Asset bundle management — controls JS/CSS/SCSS file inclusion.

**Fields:**
- `name` (Char, required), `bundle` (Char, required) — Target bundle name
- `directive` (Selection, required) — `append`, `prepend`, `after`, `before`, `remove`, `replace`, `include`
- `path` (Char, required) — Glob pattern for files
- `target` (Char) — For after/before/replace directives
- `active` (Boolean, default=True), `sequence` (Integer, default=16)

**Key Methods:**
- `_get_asset_paths(bundle, assets_params)` — Resolved asset paths for a bundle
- `_fill_asset_paths(bundle, asset_paths, ...)` — Recursively resolve includes
- `_process_path(bundle, directive, target, ...)` — Apply directive
- `_get_asset_bundle_url(filename, unique, ...)` — Generate asset URL
- `_get_addons_sorted_topologically(addons_tuple)` — Dependency-based addon ordering

---

### models/ir_asset_paths.py

#### AssetPaths, BundleWalk (non-ORM)

The directive walk behind `ir.asset`: `BundleWalk` expands one bundle's
`append` / `prepend` / `after` / `before` / `remove` / `replace` / `include`
directives into an ordered `AssetPaths` list, keeping anchors so a later
directive can insert relative to an earlier one. `ResolvedPath` and
`AssetEntry` are the value types; `AssetDirectiveError` is what a directive
that points at nothing raises.

**Key Methods:**
- `AssetPaths.get_index(path, bundle)` / `get_index_of_first(paths, bundle)` — Position lookup for relative directives
- `AssetPaths.append_paths` / `insert_paths` / `remove_paths` — The three primitive edits
- `BundleWalk.walk(bundle)` — Recursive expansion, cycle-guarded by `seen`

---

### models/assetsbundle/bundle.py

#### AssetsBundle (non-ORM class)

Asset compilation engine — concatenates, minifies, and bundles JS/CSS/SCSS.

**Constructor:** `__init__(name, files, external_assets, env, css, js, debug_assets, rtl, assets_params, autoprefix)`

**Key Methods:**
- `get_links()` — List of (url, content) tuples for rendered assets
- `get_link(asset_type)` — Single compiled bundle link

**Asset Classes:** `JavascriptAsset`, `StylesheetAsset`, `ScssStylesheetAsset`, `LessStylesheetAsset`, `XMLAsset`

---

## Templating

### models/ir_qweb.py

#### IrQweb — `ir.qweb` (AbstractModel)

QWeb template engine — compiles XML templates to Python functions, renders to Markup.

**Key Methods:**
- `_render(template, values, **options)` — Main render entry point → Markup string; `_render_batch` shares one prepared environment across many value dicts
- `_compile(template)` — Compile a template to its Python functions (ormcache `templates`, keyed by `_get_template_cache_signature()`)
- `_compile_node(el, compile_context, level)` — Recursively compile an XML node
- `_compile_directive_if()`, `_compile_directive_foreach()`, `_compile_directive_set()`, `_compile_directive_call()`, `_compile_directive_out()`, `_compile_directive_field()` — Directive handlers
- `_compile_expr(expr, raise_on_missing)` — Rewrite a template expression into sandboxed Python (`_SAFE_QWEB_OPCODES`)
- `_get_field(record, field_name, expression, tag_name, field_options, values)` — Field value through its `ir.qweb.field.*` converter; merges the converter's attributes into the node

### models/ir_qweb_fields.py

#### IrQwebField — `ir.qweb.field` (AbstractModel, 20 subclasses)

QWeb field value formatters — one subclass per field type.

**Base Methods:**
- `value_to_html(value, options)` — Format value to HTML string
- `record_to_html(record, field_name, options)` — Get value + format
- `attributes(record, field_name, options, values)` — Generate data-oe-* attributes

**Subclasses** — one per field type, each an AbstractModel with its own `_name`
so a template can address the converter directly (`t-options-widget`):

| Class | Model |
|-------|-------|
| IrQwebFieldInteger | `ir.qweb.field.integer` |
| IrQwebFieldFloat | `ir.qweb.field.float` |
| IrQwebFieldDate | `ir.qweb.field.date` |
| IrQwebFieldDatetime | `ir.qweb.field.datetime` |
| IrQwebFieldText | `ir.qweb.field.text` |
| IrQwebFieldSelection | `ir.qweb.field.selection` |
| IrQwebFieldMany2one | `ir.qweb.field.many2one` |
| IrQwebFieldMany2many | `ir.qweb.field.many2many` |
| IrQwebFieldOne2many | `ir.qweb.field.one2many` |
| IrQwebFieldHtml | `ir.qweb.field.html` |
| IrQwebFieldImage | `ir.qweb.field.image` |
| IrQwebFieldImage_Url | `ir.qweb.field.image_url` |
| IrQwebFieldMonetary | `ir.qweb.field.monetary` |
| IrQwebFieldFloat_Time | `ir.qweb.field.float_time` |
| IrQwebFieldTime | `ir.qweb.field.time` |
| IrQwebFieldDuration | `ir.qweb.field.duration` |
| IrQwebFieldRelative | `ir.qweb.field.relative` |
| IrQwebFieldBarcode | `ir.qweb.field.barcode` |
| IrQwebFieldContact | `ir.qweb.field.contact` |
| IrQwebFieldQweb | `ir.qweb.field.qweb` |

---

### models/ir_qweb_assets.py

#### IrQweb — `ir.qweb` (`_inherit`)

The asset half of the template engine: `t-call-assets` resolution into
`<script>` / `<link>` nodes, ESM bundle payloads and standalone bundles,
the import-map and loader-shim nodes for HOOT, and the esbuild circuit
breaker (`_open_esbuild_circuit` / `_close_esbuild_circuit`, a per-bundle
cooldown key and a forced-fallback set) that keeps a failing build from
being retried on every request.

**Key Methods:**
- `_get_asset_nodes(bundle, ...)` / `_get_asset_links(...)` — Entry points from `t-call-assets`
- `_get_asset_bundle(bundle, ...)` — Builds the `AssetsBundle`
- `_get_esm_bundle_payload(...)` / `_get_standalone_bundle(bundle)` — ESM outputs
- `_is_esbuild_fail_closed()` / `_get_esbuild_circuit_state(bundle)` — Breaker policy

---

## Scheduling

### models/ir_cron.py

#### IrCron — `ir.cron` (`_name`, `_inherit = ['mixin.recurrence.interval']`, `_inherits = {'ir.actions.server': 'ir_actions_server_id'}`)

Scheduled jobs — executes server actions on a recurring schedule.

**Fields:**
- `ir_actions_server_id` (Many2one, delegate, required) — Linked server action
- `cron_name` (Char, computed/stored)
- `user_id` (Many2one → res.users, required)
- `active` (Boolean, default=True)
- `repeat_interval` (Integer, default=1, required), `repeat_unit` (Selection, default=month) — from `mixin.recurrence.interval`, widened with minute/hour; next run computed by `odoo.tools.date_utils.next_after`
- `nextcall` (Datetime, required), `lastcall` (Datetime)
- `priority` (Integer, default=5)
- `failure_count` (Integer), `first_failure_date` (Datetime)

**Key Methods:**
- `_process_jobs(db_name)` — Static: execute ready jobs
- `_run_jobs_until_deadline(cr, job_ids, deadline)` — Work through one pass's jobs, yielding on its time budget
- `_run_job(cr, job)` — One job: consume its triggers, run it, record the outcome, reschedule
- `_run_job_within_budget(job, deadline)` — Repeat the job's action while the budget allows; returns a `CompletionStatus`
- `_acquire_job(cr, job_id, include_not_ready)` — Lock job for execution (SELECT FOR UPDATE)
- `_run_server_action(cron_name, server_action_id)` — Run the server action
- `_trigger(at)`, `_add_triggers(at_list)` — Schedule immediate execution
- `_notify_after_commit(cr)` — Wake cron workers via pg_notify once the transaction commits
- `method_direct_trigger()` — Run cron immediately (UI button)
- `toggle(model, domain)` — Toggle active state conditionally

#### IrCronTrigger — `ir.cron.trigger` (`_name`)

One-shot triggers that wake a cron job early.

**Fields:**
- `cron_id` (Many2one → ir.cron, required, cascade), `call_at` (Datetime, required)

#### IrCronProgress — `ir.cron.progress` (`_name`)

Progress tracking for long-running cron jobs.

**Fields:**
- `cron_id` (Many2one → ir.cron, required, cascade)
- `remaining` (Integer), `done` (Integer), `deactivate` (Boolean)

### models/ir_job.py

#### Base (AbstractModel, `_inherit = 'base'`)

Adds `delayed(priority, eta, channel, max_retries, identity_key)` to every
model: returns a proxy whose next method call is enqueued as an `ir.job`
instead of executed (the method must be decorated with `@api.job`).

#### IrJob — `ir.job` (`_name`)

Background job queue — a persisted method call (model, method, records,
JSON args) executed asynchronously by the job workers (`WorkerJob` /
`run_job_thread`, LISTEN/NOTIFY on channel `job_queue`), each in its own
transaction. States: wait_deps → pending → started → done / failed /
cancelled. Dependency graphs via `delayed(after=jobs)`: chains and fan-in;
dependents are released atomically with the dependency's completion and
cascade-cancelled (transitively) when a dependency fails or is cancelled.

**Fields:**
- `uuid` (Char), `channel` (Char, default='root'), `state` (Selection), `priority` (Integer, default=10)
- `eta` (Datetime) — earliest execution; `identity_key` (Char) — dedup handle (partial unique index while wait_deps/pending/started)
- `model_name`/`method_name` (Char, required), `record_ids`/`args`/`kwargs`/`context` (Json)
- `user_id` (Many2one → res.users, required), `company_id` (Many2one → res.company)
- `retry`/`max_retries` (Integer), `exc_name`/`exc_message` (Char), `exc_info` (Text)
- `started_at`/`done_at` (Datetime), `worker_ident` (Char)
- `depends_on_ids`/`dependent_ids` (Many2many self via `ir_job_dependency`)

**Key Methods:**
- `_enqueue(records, method_name, ..., after=)` — transactional INSERT (ON CONFLICT dedup) + postcommit NOTIFY; with `after`, starts in wait_deps
- `_process_jobs(db_name)` — Static: worker entry point (guards, reap, dependency repair sweep, claim loop)
- `_claim_next(cr, worker_ident)` — claim under advisory xact-lock + SKIP LOCKED, per-channel capacity
- `_run_claimed(cr, job)` — execute, mark done and release ready dependents in the same transaction (atomic completion)
- `_record_failure(cr, job, exc)` — retry with backoff (`RetryableJobError.seconds` honored) or fail + cascade-cancel dependents
- `_release_dependents(cr, job_id)` / `_cancel_dependents(cr, job_ids)` / `_release_ready_dependents(cr)` — graph resolution (inline fast path + repair sweep for unlocked enqueue races)
- `_reap_dead_jobs(cr)` — requeue started jobs whose session advisory lock is gone
- `_notify_after_commit(cr)` / `_notify_workers(db_name)` — wake job workers via pg_notify; `_job_ping(message)` — smoke-test job
- `_notify_failed(cr, job, exc)` — hook on permanent failure (no-op in base; override per DB, cf. `IrCron._notify_admin`)
- `action_run_now()` — execute a pending job inline in the current transaction (ignores eta/capacity, like cron's direct trigger)
- `action_requeue()` (recomputes wait_deps vs pending), `action_cancel()` (wait_deps/pending; cascades) — UI/state actions

Views: `views/ir_job_views.xml` (list/form/search + channel list), menus under
Settings > Technical > Automation (`menu_ir_job_act`, `menu_ir_job_channel_act`).

#### IrJobChannel — `ir.job.channel` (`_name`)

Per-channel concurrency capacity (cluster-wide, enforced by the claim query).

**Fields:**
- `name` (Char, required, unique), `capacity` (Integer, default=1, > 0), `active` (Boolean)

---

## Storage and Streaming

### models/ir_attachment.py

#### IrAttachment — `ir.attachment` (`_name`)

File storage with pluggable backends (see `ir_attachment_storage.py`:
`AttachmentStorage` / `DbStorage` / `FileStorage`, `@register_storage`).
Two dispatch axes: `ir_attachment.location` selects where NEW content is
written (`_get_storage_backend()`); existing content follows its store key,
resolved by URI scheme via `_get_storage_backend_for_key()` (plain sharded keys →
local filestore). The `_file_*` methods are local-filestore primitives.

Filestore keys are **algorithm-tagged**: `b3/<shard>/<digest>` for the
BLAKE3 content digest (`odoo/libs/hashing.py`), and the historical
untagged `<shard>/<sha1>` when the extension is absent. Both layouts
coexist — reads follow the stored `store_fname`, so a digest change needs
no filestore rewrite. `_gc_rehash_legacy_keys` converges old keys only if
`ir_attachment.rehash_legacy_keys_limit` is set (default: off).

**Fields:**
- `name` (Char, required), `description` (Text)
- `res_model` (Char), `res_field` (Char), `res_id` (Many2oneReference)
- `company_id` (Many2one → res.company)
- `type` (Selection, required) — `url` or `binary`
- `url` (Char, indexed), `public` (Boolean), `access_token` (Char)
- `raw` (Binary, computed/inverse) — Raw bytes
- `datas` (Binary, computed/inverse) — Base64 encoded
- `db_datas` (Binary) — Database storage field
- `store_fname` (Char, indexed) — Filestore path
- `file_size` (Integer), `checksum` (Char, size=64 — BLAKE3 hex; legacy
  rows keep their 40-char sha1 until re-keyed), `mimetype` (Char)
- `index_content` (Text) — Extracted text for full-text search

**Key Methods:**
- `_get_storage_location()` — Configured location name (`file`, `db`, or custom)
- `_get_storage_backend()` — Write-side backend for the configured location
- `_get_storage_backend_for_key(fname)` — Read-side backend owning a store key
- `_storage_delete(fname)` — Key-dispatched content deletion
- `_get_filestore()` — Filestore directory path
- `_file_read(fname, size)`, `_file_write(bin_value, checksum)`, `_file_delete(fname)`
- `_gc_file_store()` — Autovacuum: runs every backend's `autovacuum()`
- `_gc_rehash_legacy_keys(limit)` — Autovacuum: opt-in re-keying of rows
  still on a legacy digest; no-op unless `rehash_legacy_keys_limit` is set
- `_content_checksum(bin_data)` / `_file_store_path(checksum)` — content
  digest and the tagged store key derived from it
- `_is_content_collision_check_enabled()` — whether a dedup hit re-reads the stored
  file; defaults on for sha1, off for BLAKE3, overridable by parameter
- `_mimetype_from_values(values)` — Detect MIME type
- `_postprocess_contents(values)` — Image auto-resizing
- `create_unique(values_list)` — Create only if checksum+size unique
- `generate_access_token()` — Generate scoped access tokens
- `_get_serve_attachment(url, extra_domain, order)` — Find attachment by URL
- `_from_request_file(file, mimetype, ...)` — Create from HTTP upload
- `_to_http_stream()` — Convert to Stream for download

### models/ir_attachment_assets.py

#### IrAttachment — `ir.attachment` (`_inherit`)

Generated-asset bookkeeping split out of `ir_attachment.py`: the domains
that identify compiled bundles and ESM outputs, their garbage collection with
a grace period, and `regenerate_assets_bundles()`.

**Key Methods:**
- `_get_domain_generated_assets(...)` / `_get_domain_esm_generated_assets()` — What counts as a generated asset
- `_gc_esm_assets()` — Sweep, returns `(removed, remaining)`
- `regenerate_assets_bundles()` — Drop and rebuild

### models/ir_attachment_storage.py

#### AttachmentStorage, DbStorage, FileStorage (non-ORM)

The storage backends `ir.attachment` writes through. `register_storage`
adds a backend under its `location` name (`db`, `file`; other modules add
schemes such as `s3://`), and `backend_for_key(env, key)` picks one for a
stored key, falling back to `UnknownSchemeStorage` with a once-per-scheme
warning when nothing claims the scheme.

**Key Methods:**
- `write(data, checksum)` / `write_stream(fileobj)` — Store and return the column values
- `read(key, size)` / `delete(key)` / `to_stream(attachment, stream)` — Retrieval
- `migration_domain()` — Rows to move when `ir_attachment.location` changes
- `autovacuum()` — Backend-specific GC hook

---

### models/ir_binary.py

#### IrBinary — `ir.binary` (AbstractModel)

File streaming helpers for download/image endpoints.

**Key Methods:**
- `_find_record(xmlid, res_model, res_id, access_token, field)` — Find record for streaming
- `_record_to_stream(record, field_name)` — Convert field to Stream
- `_get_stream_from(record, field_name, filename, ...)` — Create download stream
- `_get_image_stream_from(record, field_name, ...)` — Image stream with resizing
- `_get_placeholder_stream(path)` — Placeholder image stream

---

### models/ir_egress.py

#### IrEgress — `ir.egress` (AbstractModel)

The one outbound HTTP pipeline. Every address a request reaches is classified by
`odoo/libs/netguard.py` and checked against a policy (`public` or `private`,
widened by the `base.egress_allowed_networks` system parameter); the connection is
pinned to the checked address, every redirect hop is checked again, and responses
are capped in bytes and seconds by `odoo/libs/guarded_http.py`.

**Key Methods:**
- `check_url(url, policy)` — Resolve and check a URL, raising `DestinationRefused`
- `session(purpose, policy, timeout, max_bytes, max_seconds, max_redirects)` — A guarded `requests.Session`
- `request(method, url, purpose, policy, ...)` — One request through a guarded session
- `_prepare_session(session, purpose, policy)` — Extension hook for addons that add logging, credentials or rate limits
- `_get_policy(policy)` — The policy with the configured extra networks

---

## Sequences

### models/ir_sequence.py

#### IrSequence — `ir.sequence` (`_name`)

Auto-incrementing sequences — manages PostgreSQL sequences.

**Fields:**
- `name` (Char, required), `code` (Char) — Sequence code
- `implementation` (Selection) — `standard` (gapless reads) or `no_gap` (serialized)
- `prefix`, `suffix` (Char) — Pattern with date interpolation
- `number_next` (Integer, default=1), `number_increment` (Integer, default=1)
- `padding` (Integer, default=0)
- `company_id` (Many2one → res.company)
- `use_date_range` (Boolean), `date_range_ids` (One2many → ir.sequence.date_range)

**Key Methods:**
- `next_by_id(sequence_id)` — Get next value by ID
- `next_by_code(sequence_code)` — Get next value by code
- `_get_current_sequence(sequence_date)` — Get sequence or date-range subsequence
- `create(vals_list)` — Create PostgreSQL sequence if standard implementation
- `write(vals)` — Alter PostgreSQL sequence

---

## Configuration and Defaults

### models/ir_config_parameter.py

#### IrConfigParameter — `ir.config_parameter` (`_name`, `_rec_name = key`)

System parameters — key-value configuration store.

**Fields:**
- `key` (Char, required, unique), `value` (Text, required)

**Key Methods:**
- `init(force)` — Initialize default parameters (database.secret, database.uuid, web.base.url, etc.)
- `get_param(key, default)` — Retrieve parameter value
- `set_param(key, value)` — Set or create parameter
- `_get_param(key)` — Cached parameter fetch (ormcache)

### models/ir_default.py

#### IrDefault — `ir.default` (`_name`)

Default field values — per-user, per-company, per-condition.

**Fields:**
- `field_id` (Many2one → ir.model.fields, required, cascade)
- `user_id` (Many2one → res.users, cascade) — NULL = all users
- `company_id` (Many2one → res.company, cascade) — NULL = all companies
- `condition` (Char), `json_value` (Char, required)

**Key Methods:**
- `set(model_name, field_name, value, user_id, company_id, condition)` — Set default
- `_get(model_name, field_name, user_id, company_id, condition)` — Retrieve default
- `_get_model_defaults(model_name, condition)` — Cached defaults per model
- `discard_records(records)`, `discard_values(model_name, field_name, values)` — Clear defaults

### models/ir_filters.py

#### IrFilters — `ir.filters` (`_name`)

Saved search filters.

**Fields:**
- `name` (Char, required), `user_ids` (Many2many → res.users) — Empty = shared
- `domain` (Text, required), `context` (Text, required), `sort` (Char, required)
- `model_id` (Selection) — Target model
- `is_default` (Boolean), `active` (Boolean, default=True)
- `action_id` (Many2one → ir.actions.actions)
- `embedded_action_id` (Many2one → ir.embedded.actions)

**Key Methods:**
- `get_filters(model, action_id, embedded_action_id, ...)` — Retrieve user's filters
- `create_filter(vals)` — Create filter with validation

## HTTP and Routing

### models/ir_http.py

#### IrHttp — `ir.http` (AbstractModel)

HTTP routing, authentication, and request dispatch.

**Key Methods:**
- `routing_map(key)` — Generate and cache routing map for installed modules (ormcache)
- `_match(path_info)` — Match HTTP path to routing rule
- `_authenticate(endpoint)` — Authenticate request based on endpoint auth type
- `_auth_method_none()`, `_auth_method_user()`, `_auth_method_public()`, `_auth_method_bearer()` — Auth handlers
- `_pre_dispatch(rule, args)` — Pre-dispatch hook (upload limits, language)
- `_dispatch(endpoint)` — Execute endpoint with reCAPTCHA verification
- `_post_dispatch(response)` — Post-dispatch hook
- `_handle_error(exception)` — Error handler
- `_serve_fallback()` — Serve files from attachments
- `_get_translations_for_webclient(modules, lang)` — Translations for JS
- `_slugify(value, max_length, path)` — URL slug generation
- `_slug(value)` — Record to slug, `_unslug(value)` — Slug to (prefix, id)

---

## Module System

### models/mixin_table_inheritance_root.py

#### MixinTableInheritanceRoot — `mixin.table.inheritance.root` (AbstractModel)

The machinery a PostgreSQL table-inheritance tree needs (`ir.actions.actions`,
`resource.asset`): the concrete model of a row from its `tableoid`, root-level
`write`/`unlink` dispatched to the concrete models, `ondelete` enforced in Python
because no foreign key can target an inherited row, and a check at `init` that
every subtype table really inherits the root.

The leaves' own many2ones *are* real foreign keys, and a cascading one deletes a
leaf row inside PostgreSQL, behind that Python `ondelete`. The registry indexes
those cascades (`cascades_into_inheritance_trees`, direct or through plain
models, as dotted paths) and `BaseModel.unlink` unlinks the rows they would
reach through the ORM first; `ir.model.unlink` does so before it drops tables.

**Key Methods:**
- `_get_concrete()` — The record re-browsed on its concrete model
- `_get_model_names_concrete()` — Concrete model per id, from `tableoid` cross-checked with the type column
- `_check_table_inheritance()` — Raise at init when the table does not inherit the declared root
- `_constrain_type_to_table()` — `CHECK (type = '<model>')` on each leaf table one model owns; skipped, with an error, while rows naming another model remain
- `_apply_ondelete_unenforced()` — Cascade / set null / restrict for every relation the database cannot enforce

### models/mixin_module_link.py

#### MixinModuleLink — `mixin.module.link` (`_name`, AbstractModel)

One row per module named by another module's manifest. `name` is the *string*
the manifest wrote, so a link may point at a module this database has never
seen; `linked_id` resolves it to a record when one exists and `state` reports
`unknown` when it does not. Both concrete links below inherit it, which is why
neither declares those two fields itself.

**Fields:** `name` (Char, indexed), `module_id` (Many2one → ir.module.module, cascade), `linked_id` (Many2one → ir.module.module, computed + searchable), `state` (Selection, computed)

**Key Methods:**
- `_search_linked_id(operator, value)` — Search on the resolved module by
  translating to a search on `name`, so an unresolvable link still matches
  `not in`

### models/ir_module_module_dependency.py

#### IrModuleModuleDependency — `ir.module.module.dependency` (`_name`, inherits `mixin.module.link`)

One row per `depends` entry in a manifest. `_module_dependency_uniq` forbids
declaring the same dependency twice.

**Fields:** `linked_id` (relabelled *Dependency*), `auto_install_required` (Boolean, default=True) — whether this dependency blocks automatic installation of the dependent

**Key Methods:**
- `all_dependencies(module_names)` — Transitive closure of the dependency graph,
  read breadth-first with one `_read_group` per level rather than per module

### models/ir_module_module_exclusion.py

#### IrModuleModuleExclusion — `ir.module.module.exclusion` (`_name`, inherits `mixin.module.link`)

One row per `excludes` entry in a manifest — the modules that may not be
installed alongside this one. Read by the installer before it resolves the
dependency graph. `_module_exclusion_uniq` forbids declaring the same exclusion
twice.

**Fields:** `linked_id` (relabelled *Excluded Module*)

### models/ir_module.py

#### IrModuleCategory — `ir.module.category` (`_name`)

Module categories (application groups).

**Fields:**
- `name` (Char, required, translatable), `parent_id` (Many2one → self)
- `child_ids` (One2many), `module_ids` (One2many → ir.module.module)
- `privilege_ids` (One2many → res.groups.privilege)
- `sequence` (Integer), `visible` (Boolean, default=True), `exclusive` (Boolean)

#### IrModuleModule — `ir.module.module` (`_name`)

Module lifecycle management.

**Fields:**
- `name` (Char), `shortdesc` (Char, translatable), `summary` (Char, translatable)
- `author` (Char), `website` (Char)
- `state` (Selection) — installed, uninstalled, to upgrade, to remove, to install
- `category_id` (Many2one → ir.module.category)
- `dependencies_id` (One2many → ir.module.module.dependency)
- `application` (Boolean), `installable` (Boolean), `auto_install` (Boolean)
- `db_version` (Char) — version persisted at last install/upgrade
- `manifest_version` (Char, computed) — version in manifest on disk
- `license` (Selection)

**Key Methods:**
- `button_install()`, `button_uninstall()`, `button_upgrade()`, `button_immediate_upgrade()`
- `get_module_info(name)` — Read manifest metadata
- `update_list()` — Scan filesystem for new/updated modules

---

## Logging and Profiling

### models/ir_logging.py

#### IrLogging — `ir.logging` (`_name`)

Server/client log storage (bypasses ORM for performance).

**Fields:**
- `name` (Char), `type` (Selection: `client`/`server`), `dbname` (Char)
- `level` (Char), `message` (Text), `path` (Char), `func` (Char), `line` (Char)

### models/ir_profile.py

#### BaseEnableProfilingWizard — `base.enable.profiling.wizard` (TransientModel)

Turns profiling on for a bounded window. Profiling is off by default and this is
the only supported way to enable it, so it cannot be left on by accident: the
wizard writes an expiry into `ir.config_parameter`.

**Fields:** `duration` (Selection), `expiration` (Datetime, computed from `duration`)

**Key Methods:** `submit()` — Write the expiry into `ir.config_parameter` and close

#### IrProfile — `ir.profile` (`_name`)

Code profiling with Speedscope output.

**Fields:**
- `session` (Char), `name` (Char), `duration`, `cpu_duration` (Float)
- `sql` (Text), `traces_async`, `traces_sync` (Text)
- `sql_count`, `entry_count` (Integer)
- `speedscope` (Binary, computed), `speedscope_url` (Text, computed)

**Key Methods:**
- `set_profiling(profile, collectors, params)` — Enable/disable profiling
- `_gc_profile()` — Autovacuum profiles older than 30 days

---

## Import

### models/ir_fields.py

#### IrFieldsConverter — `ir.fields.converter` (AbstractModel)

Data import type conversion — converts external data formats to ORM field values.

**Key Methods:**
- `_get_converter_record(model, fromtype)` — converter callable for a whole record
- `_resolve_converter_field(field, fromtype)` — converter callable for one field, or `None` when its type has none
- `_get_db_id(field, subfield, value)` — database id a reference resolves to, plus warnings
- `_str_to_boolean()`, `_str_to_integer()`, `_str_to_float()`, `_str_to_date()`, `_str_to_datetime()`, `_str_to_selection()`, `_str_to_many2one()`, `_str_to_many2many()`, `_str_to_one2many()`, `_str_to_json()`, `_str_to_properties()`

---

## Embedded Actions

### models/ir_actions_server_history.py

#### IrActionsServerHistory — `ir.actions.server.history` (`_name`)

One row per saved version of a server action's `code`, written by
`ir.actions.server.write`; `_gc_histories` trims each action to its most
recent versions.

**Fields:**
- `action_id` (Many2one → ir.actions.server, required, cascade)
- `code` (Text)

### models/ir_actions_embedded.py

#### IrEmbeddedActions — `ir.embedded.actions` (`_name`)

Actions embedded within views (tabs, sub-views).

**Fields:**
- `name` (Char, translatable), `sequence` (Integer)
- `parent_action_id` (Many2one → ir.actions.act_window, required, cascade)
- `parent_res_id` (Integer), `parent_res_model` (Char, required)
- `action_id` (Many2one → ir.actions.actions, cascade)
- `python_method` (Char) — Alternative: method returning action
- `user_id` (Many2one → res.users) — NULL = shared
- `is_deletable` (Boolean, computed), `is_visible` (Boolean, computed)
- `domain` (Char), `context` (Char), `group_ids` (Many2many → res.groups)

---

## Autovacuum

### models/ir_autovacuum.py

#### IrAutovacuum — `ir.autovacuum` (AbstractModel)

Garbage collection framework.

**Key Methods:**
- `_run_vacuum_cleaner()` — Execute all `@api.autovacuum` methods across all models
- `_gc_orm_signaling()` — Garbage collection on ORM signaling tables

---

## Demo Data

### models/ir_demo.py / ir_demo_failure.py

#### IrDemo — `ir.demo` (TransientModel)

**Key Methods:** `install_demo()` — Force demo data installation

#### IrDemoFailure — `ir.demo_failure` (TransientModel)

**Fields:** `module_id` (Many2one → ir.module.module), `error` (Char)

#### IrDemoFailureWizard — `ir.demo_failure.wizard` (TransientModel)

**Fields:** `failure_ids` (One2many), `failures_count` (Integer, computed)

---

## Partners

### models/res_partner.py

#### ResPartner — `res.partner` (`_name`, `_parent_store = True`)

Core business entity — contacts, companies, addresses.
Inherits: `mixin.format.address`, `mixin.format.vat.label`, `mixin.avatar`, `mixin.properties.base.definition`

**Fields (key selection):**
- `name` (Char, indexed), `complete_name` (Char, computed, indexed)
- `parent_id` (Many2one → self), `child_ids` (One2many → self)
- `ref` (Char, indexed) — Internal reference
- `lang` (Selection, computed, stored, readonly=False) — Language
- `tz` (Selection) — Timezone
- `user_id` (Many2one → res.users, computed, precompute, readonly=False, stored) — Salesperson
- `vat` (Char, indexed), `company_registry` (Char)
- `bank_ids` (One2many → res.partner.bank)
- `tag_ids` (Many2many → res.partner.tag) — Tags
- `active` (Boolean, default=True)
- `type` (Selection) — `contact`, `invoice`, `delivery`, `other`
- Address fields: `street`, `street2`, `zip`, `city`, `state_id`, `country_id`
- `partner_latitude`, `partner_longitude` (Float)
- `email`, `email_formatted` (Char), `phone_ids` (Many2many → phone.number)
- `preferred_phone_id` (Many2one → phone.number, editable, stored) — contact-owned priority; unlinking the number clears it. `_phone_get_number()` selects active numbers using this preference, then the shared number order.
- `main_phone_id`, `main_mobile_id` (Many2one → phone.number, computed, stored) — typed selections from that same contact order.
- `main_bank_id` (Many2one → res.partner.bank, computed, stored)
- `is_company` (Boolean)
- `company_id` (Many2one → res.company)
- `commercial_partner_id` (Many2one, computed, stored, recursive, indexed)
- `commercial_company_name` (Char, computed, stored)
- `barcode` (Char, company_dependent)

**Key Methods:**
- `_compute_display_name()` — Format with company, type, address
- `name_search(name, domain, operator, limit)` — Search by name, ref, email, VAT
- `_get_complete_name()` — Build display name with company/type
- `_compute_avatar_*()` — Avatar computation (SVG or image)
- `_fields_sync(values)` — Sync fields between parent/child
- `_update_parent_address(partner)` — Auto-link children when parent created
- `create(vals_list)`, `write(vals)` — With partner_share computation, commercial field sync

### models/res_partner_tag.py

#### ResPartnerTag — `res.partner.tag` (`_name`, `_parent_store = True`)

Partner tags — hierarchical.

**Fields:**
- `name` (Char, required, translatable), `color` (Integer)
- `active` (Boolean, default=True)
- `parent_id` (Many2one → self, cascade), `child_ids` (One2many)
- `parent_path` (Char, indexed) — Materialized path for `_parent_store`
- `partner_ids` (Many2many → res.partner)

### models/res_partner_identifier_type.py

#### ResPartnerIdentifierType — `res.partner.identifier.type` (`_name`, `_inherit = ["mixin.catalog"]`, `_order = "sequence, name"`)

A *kind* of identifier a contact can carry — RFC, CURP, SIREN, GLN. The
dimension only; what a given contact's identifier is lives in
`res.partner.identifier`. This is where the family departs from
`mixin.attribute`, whose value model is a catalog several subjects select from:
an identifier's value is free text unique to its holder.

**Fields:**
- `code` (Char, required) — the stable key localizations and integrations
  resolve by; the label is translated and editable, so it is never the key
- `sequence` (Integer, default=10)
- `country_ids` (Many2many → res.country) — offer the type only in these
  countries; empty means everywhere
- `pattern` (Char, "Format") — optional regex the normalized value must match,
  anchored both ends, checked before any code-specific rule
- `unique_across_contacts` (Boolean, default=True)
- `multiple_per_contact` (Boolean, default=False)
- `synced_with_commercial` (Boolean, default=False) — copy down from the
  commercial entity; on for what identifies a *company*, off for a person

**Constraints:** `_code_uniq` UNIQUE(code); `_name_src_uniq` via
`mixin_catalog.name_uniq_index`; `_check_pattern_compiles`.

**Methods:**
- `_normalize(value)` — strip punctuation and case, so `RIFE001128IT2` and
  `RIFE-001128-IT2` compare equal. The stored `value` keeps what was typed
- `validate(value)` — three stages cheapest first: `pattern`, then a rule
  looked up as `_validate_code_<code>` on this model, then `_check_hook`. Returns the
  normalized value; raises `ValidationError`. **`_validate_code_<code>` is a dispatch
  key, not an `@api.constrains` hook** (coding_guidelines §2.4.14): the
  variable half is the `code` column, so the prefix is frozen and a
  localization adds a method rather than editing `validate`
- `_check_hook(normalized)` — extension point for a rule needing more than a
  boolean
- `_get_type_by_code(code)` — resolve a type by its stable code, or an empty recordset

### models/res_partner_identifier.py

#### ResPartnerIdentifier — `res.partner.identifier` (`_name`, `_order = "type_id, id"`, `_rec_name = "value"`)

One identifier a contact carries: this type, this value. Deliberately not a
`mixin.attribute.value` — that model is a vocabulary several subjects point at,
and two contacts sharing one identifier row is exactly what duplicate detection
exists to find, so it must not be expressible.

**Fields:**
- `partner_id` (Many2one → res.partner, required, cascade, indexed)
- `type_id` (Many2one → res.partner.identifier.type, required, **restrict**,
  indexed)
- `value` (Char, required) — as written on the document
- `normalized_value` (Char, compute stored, indexed) — punctuation and case
  removed, so two spellings deduplicate as one
- `company_id` (Many2one, related `partner_id.company_id`, stored,
  `index="btree_not_null"`)

**Index:** `_type_value_index` on `(type_id, normalized_value)`.

**Constraints:**
- `_check_value_is_valid` — delegates to `type_id.validate(value)`
- `_check_one_per_contact` — one value per type per contact unless
  `multiple_per_contact`
- `_check_not_taken_by_another_contact` — scoped to the **commercial entity**,
  because a company and its own addresses share one tax ID by design and that
  is not a collision

Both multi-record constraints issue **one query for the whole recordset**, not
one per row: they fire on every create, and an import of ten thousand contacts
would otherwise issue ten thousand searches apiece.

### models/res_partner_industry.py

#### ResPartnerIndustry — `res.partner.industry` (`_name`)

**Fields:** `name` (Char, translatable), `full_name` (Char, translatable), `active` (Boolean)

### models/mixin_format_address.py

#### FormatAddressMixin — `mixin.format.address` (AbstractModel)

Customizes address form layout based on country `address_view_id` or `address_format`.

**Key Methods:**
- `_view_get_address(arch)` — Customize address form view
- `_get_view()` — Override to apply address customization

### models/mixin_format_vat_label.py

#### FormatVatLabelMixin — `mixin.format.vat.label` (AbstractModel)

Relabels VAT field based on company country's `vat_label`.

---

## Users

### models/res_users.py

#### ResUsers — `res.users` (`_name`, `_inherits = {'res.partner': 'partner_id'}`)

User accounts — inherits all partner fields.

**Fields (beyond partner):**
- `partner_id` (Many2one → res.partner, required)
- `login` (Char, required, unique)
- `password` (Char) — Hashed
- `new_password` (Char, computed/inverse) — For password changes
- `signature` (Html)
- `active` (Boolean, default=True)
- `groups_id` (Many2many → res.groups)
- `share` (Boolean, computed) — Non-internal user
- `companies_count` (Integer, computed)
- `company_id` (Many2one → res.company, required) — Current company
- `company_ids` (Many2many → res.company) — Allowed companies
- `action_id` (Many2one → ir.actions.actions) — Home action
- `notification_type` (Selection) — `email` or `inbox`

**Properties:**
- `SELF_READABLE_FIELDS` — Fields readable by user on own record
- `SELF_WRITEABLE_FIELDS` — Fields writable by user on own record

**Key Methods:**
- `_login(db, credential, user_agent_env)` — Authenticate user
- `_check_credentials(credential, env)` — Verify credentials
- `authenticate(db, credential, user_agent_env)` — Full auth flow
- `check_identity(fn)` — Decorator requiring password re-verification
- `_is_admin()`, `_is_system()`, `_is_superuser()` — Access level checks
- `has_group(group_ext_id)` — Check if user belongs to group
- `_change_password(new_passwd)` — Change password
- `action_reset_password()` — Send password reset email
- `_default_group_ids()` — Default groups (base.group_user + implied)

### models/res_users_apikeys.py

#### ResUsersApikeys — `res.users.apikeys` (`_name`, `_auto = False`)

API key management with custom SQL table (encrypted key storage).

**Fields:**
- `name` (Char), `user_id` (Many2one → res.users, cascade)
- `scope` (Char), `expiration_date` (Datetime)

**Key Methods:**
- `_check_credentials(*, scope, key)` — Verify API key
- `_generate(scope, name, expiration_date)` — Generate and store key
- `_gc_user_apikeys()` — Autovacuum expired keys

#### ResUsersApikeysShow — `res.users.apikeys.show` (AbstractModel)

The one-shot display of a freshly generated key. Abstract on purpose — the key
is never stored in a table, only rendered once into this form, because the
database keeps a hash and cannot show the secret again.

**Fields:** `id` (Id), `key` (Char)

#### ResUsersApikeysDescription — `res.users.apikeys.description` (TransientModel)

API key creation wizard.

### models/res_users_identitycheck.py

#### ResUsersIdentitycheck — `res.users.identitycheck` (TransientModel)

Password verification wizard — used by `@check_identity` decorator.

**Key Methods:**
- `_check_identity()` — Verify password credential
- `run_check()` — Validate identity, execute deferred action

### models/res_users_log.py

#### ResUsersLog — `res.users.log` (`_name`)

Login tracking.
**Key Methods:** `_gc_user_logs()` — Keep only latest log per user

### models/res_users_deletion.py

#### ResUsersDeletion — `res.users.deletion` (`_name`)

User deletion queue.
**Key Methods:** `_gc_portal_users(batch_size=50)` — Cron: batch-delete queued users

### models/res_users_login_cooldown.py

#### ResUsersLoginCooldown — `res.users.login.cooldown` (`_name`)

Durable, cross-process counter behind the login-failure cooldown: one row per
source, carrying the failure tally and the moment of the last one.
**Key Fields:** `source` (indexed), `failures`, `last_failure` (indexed)

### models/res_users_settings.py

#### ResUsersSettings — `res.users.settings` (`_name`, unique `user_id`)

Per-user settings storage.

**Key Methods:**
- `_find_or_create_for_user(user)` — Find or create settings record
- `set_res_users_settings(new_settings)` — Update and return formatted settings

---

## Companies

### models/res_company.py

#### ResCompany — `res.company` (`_name`, `_parent_store = True`)

Company hierarchy with branch support.

**Fields:**
- `name` (Char, related → partner.name, required, stored, readonly=False)
- `active` (Boolean, default=True), `sequence` (Integer)
- `parent_id` (Many2one → self), `child_ids`, `all_child_ids` (One2many)
- `root_id` (Many2one, computed) — Root company
- `partner_id` (Many2one → res.partner, required)
- `currency_id` (Many2one → res.currency, required)
- `user_ids` (Many2many → res.users)
- Address fields (computed from partner with inverses)
- `paperformat_id` (Many2one → report.paperformat)

**Key Methods:**
- `_get_field_names_delegated_to_root()` — Fields synced from root (currency_id)
- `_get_accessible_branches()` — Browse accessible branches for current user
- `_get_public_user()` — Get/create public user for company
- `create(vals_list)` — Auto-create partner, sync delegated fields, install l10n
- `write(vals)` — Enforce hierarchy, copy delegated fields to branches

---

## Security Groups

### models/res_groups.py

#### ResGroups — `res.groups` (`_name`)

Security groups with implication chains and disjoint constraints.

**Fields:**
- `name` (Char, required, translatable)
- `user_ids`, `all_user_ids` (Many2many → res.users)
- `comment` (Text, translatable)
- `full_name` (Char, computed) — `privilege / group`
- `share` (Boolean) — Non-internal group
- `api_key_duration` (Float) — Max API key duration (days)
- `sequence` (Integer)
- `privilege_id` (Many2one → res.groups.privilege)
- `implied_ids` (Many2many → res.groups) — Direct implications
- `all_implied_ids` (Many2many, computed) — Transitive closure
- `disjoint_ids` (Many2many) — Mutually exclusive groups

**Key Methods:**
- `_check_disjoint_groups()` — Prevent users having exclusive groups
- `_add_implied_group(implied_group)` — Add group to implications
- `_remove_group(implied_group)` — Remove group from implications
- `_get_user_type_groups()` — Return employee/portal/public disjoint groups
- `_get_group_definitions()` — Return SetDefinitions for closure computation
- `_is_feature_enabled(group_reference)` — Check superuser feature flag

### models/res_groups_privilege.py

#### ResGroupsPrivilege — `res.groups.privilege` (`_name`)

Group privilege categories (User Types, Features, etc.).

**Fields:**
- `name` (Char, required, translatable), `description` (Text)
- `placeholder` (Char, default=`No`) — Selection placeholder text
- `sequence` (Integer, default=100)
- `category_id` (Many2one → ir.module.category)
- `group_ids` (One2many → res.groups)

---

## Localization

### models/res_country.py

#### ResCountry — `res.country` (`_name`)

**Fields:**
- `name` (Char, required, translatable), `code` (Char, size=2, required)
- `address_format` (Text), `address_view_id` (Many2one → ir.ui.view)
- `currency_id` (Many2one → res.currency)
- `phone_code` (Integer)
- `country_group_ids` (Many2many → res.country.group)
- `state_ids` (One2many → res.country.state)
- `name_position` (Selection: before/after)
- `vat_label` (Char, translatable), `state_required`, `zip_required` (Boolean)

**Key Methods:**
- `name_search(name, ...)` — Search by 2-char code first, then name
- `get_address_fields()` — Extract field names from address_format

#### ResCountryGroup — `res.country.group` (`_name`)

**Fields:** `name` (Char, required, translatable), `code` (Char, unique), `country_ids` (Many2many)

#### ResCountryState — `res.country.state` (`_name`)

**Fields:** `country_id` (Many2one, required), `name` (Char, required), `code` (Char, required)

### models/res_currency.py

#### ResCurrency — `res.currency` (`_name`)

**Fields:**
- `name` (Char, size=3, required) — ISO 4217 code
- `symbol` (Char, required), `rounding` (Float, default=0.01)
- `rate`, `inverse_rate` (Float, computed from rate_ids)
- `decimal_places` (Integer, computed from rounding)
- `rate_ids` (One2many → res.currency.rate)
- `position` (Selection: after/before), `active` (Boolean, default=True)

**Key Methods:**
- `_get_rates(company, date)` — SQL subquery for exchange rates
- `round(amount)`, `compare_amounts(amount1, amount2)`, `is_zero(amount)`
- `_get_conversion_rate(from_currency, to_currency, company, date)` — Conversion rate
- `_convert(from_amount, to_currency, company, date, round)` — Convert amount
- `amount_to_text(amount)` — Textual representation (num2words)

#### ResCurrencyRate — `res.currency.rate` (`_name`)

**Fields:**
- `name` (Date, required), `rate` (Float) — Technical rate
- `company_rate`, `inverse_company_rate` (Float, computed/inverse)
- `currency_id` (Many2one, required, cascade), `company_id` (Many2one)

### models/res_lang.py

#### ResLang — `res.lang` (`_name`)

Language management and formatting.

**Fields:**
- `name` (Char, required), `code` (Char, required) — Locale code
- `iso_code` (Char), `url_code` (Char, required)
- `active` (Boolean), `direction` (Selection: ltr/rtl)
- `date_format`, `time_format` (Selection)
- `week_start` (Selection 1-7), `grouping` (Selection: international/indian)
- `decimal_point` (Char, default=`.`), `thousands_sep` (Char, default=`,`)

**Key Methods:**
- `_activate_lang(code)`, `_create_lang(lang, lang_name)` — Activate/create language
- `_get_data(**kwargs)` — Get LangData by field (ormcache)
- `get_installed()` — List of `(code, name)` tuples
- `format(percent, value, grouping)` — Language-specific number formatting

### models/res_bank.py

#### ResBank — `res.bank` (`_name`)

**Fields:** `name` (Char, required), `bic` (Char, indexed), address fields, `active` (Boolean)

#### ResPartnerBank — `res.partner.bank` (`_name`, `_rec_name = acc_number`)

Partner bank accounts.

**Fields:**
- `acc_number` (Char, required), `sanitized_acc_number` (Char, computed, stored)
- `partner_id` (Many2one → res.partner, required)
- `allow_out_payment` (Boolean), `bank_id` (Many2one → res.bank)
- `currency_id` (Many2one → res.currency)

**Key Methods:**
- `_compute_sanitized_acc_number()` — Remove non-word chars, uppercase
- `unlink()` — Archive instead of delete

---

## Devices

### models/res_device.py

#### ResDeviceLog — `res.device.log` (`_name`)

Device/session tracking.

**Fields:**
- `session_identifier` (Char, required), `platform`, `browser` (Char)
- `ip_address`, `country`, `city` (Char)
- `device_type` (Selection: computer/mobile)
- `user_id` (Many2one → res.users), `first_activity`, `last_activity` (Datetime)
- `revoked` (Boolean), `is_current` (Boolean, computed)

**Key Methods:**
- `_update_device(request)` — Log device info from HTTP request
- `_gc_device_log()` — Autovacuum old device logs

#### ResDevice — `res.device` (`_name`, `_auto = False`, SQL view)

Latest device per session/platform/browser (aggregated view).

**Key Methods:**
- `revoke()` — Revoke device session (`@check_identity` decorated)
- `_revoke()` — Delete from session store, mark revoked

---

## Mixins

### models/mixin_image.py

#### ImageMixin — `mixin.image` (AbstractModel)

Multi-resolution image fields.

**Fields:** `image_1920` (Image, max 1920), `image_1024`, `image_512`, `image_256`, `image_128` (computed, stored, auto-resized)

### models/mixin_avatar.py

#### AvatarMixin — `mixin.avatar` (AbstractModel, inherits `mixin.image`)

SVG avatar generation from name initials.

**Fields:** `avatar_1920`, `avatar_1024`, `avatar_512`, `avatar_256`, `avatar_128` (Image, computed)

**Key Methods:**
- `_compute_avatar(avatar_field, image_field)` — Use image or generate SVG
- `_prepare_avatar_svg()` — Generate SVG with initials and HSL color

### models/properties_base_definition.py / mixin_properties_base_definition.py

#### PropertiesBaseDefinition — `properties.base.definition` (`_name`)

Properties field definition storage.

**Fields:**
- `properties_field_id` (Many2one → ir.model.fields, required, unique, cascade)
- `properties_definition` (PropertiesDefinition)

#### PropertiesBaseDefinitionMixin — `mixin.properties.base.definition` (AbstractModel)

Adds properties support to any model.

### models/decimal_precision.py

#### DecimalPrecision — `decimal.precision` (`_name`)

**Fields:** `name` (Char, required, unique), `digits` (Integer, required, default=2)
**Key Methods:** `precision_get(application)` — Cached lookup of digits (ormcache)

### models/phone_number.py

#### PhoneNumber — `phone.number` (`_name`)

A phone number as a record several contacts can share, which is what replaced
the `phone` and `mobile` columns on partners, users and companies.
`_rec_name` is `number`; `_rec_names_search` also covers `sanitized` and `label`.
**Key Fields:** `number`, `sanitized` (computed), `type`, `country_id`,
`primary`, `label`, `partner_ids`
**Key Methods:** `_normalize_number(number, country)`, `_get_phone_country()`

### models/report_paperformat.py

#### ReportPaperformat — `report.paperformat` (`_name`)

**Fields:** `name` (Char, required), `format` (Selection, default=A4), `orientation` (Selection), margins (top/bottom/left/right Float), `header_spacing` (Integer, mm — used by DIN5008 templates), `css_margins` (Boolean — WeasyPrint body-padding mode), `dpi` (Integer — Web Studio preview zoom), `disable_shrinking` (Boolean — Web Studio preview)

### models/mixin_catalog.py

#### MixinCatalog — `mixin.catalog` (AbstractModel)

Catalog entry — a uniquely-named, archivable reference row. The base every small
reference table in the fork inherits instead of redeclaring the pair.

**Fields:** `name` (Char, required, translatable), `active` (Boolean, default=True)

The uniqueness is on the SOURCE-LANGUAGE value, not the translated one:
`_name_src_uniq` is a `models.UniqueIndex` over `(name->>'en_US')` with NULLS NOT
DISTINCT, because `name` is a translated jsonb column and indexing the whole
value would let two rows collide in `en_US` while differing in one translation.

**Module-level helpers:**
- `name_uniq_index(*scope, message=, nulls_distinct=, where=)` — Rebuild the index scoped to more columns (per company, per parent) or filtered
- `no_name_uniq_index()` — Opt out entirely, for an inheritor whose names are not unique

### models/mixin_lifecycle.py

#### MixinLifecycle — `mixin.lifecycle` (AbstractModel)

A document that moves through declared states: the part of an order's lifecycle
that has nothing to do with lines, partners or invoices. The adopter declares its
own `state` selection and `_STATE_TRANSITIONS`, and implements
`_prepare_confirmation_values`.

**Fields:** `locked` (Boolean, tracked)

**Guards:** every `write` runs `_get_check_write_guards` — a locked record keeps
all but `_LOCKED_WRITABLE_FIELDS`, `_get_fields_state_frozen` freezes fields per
state, and a `state` outside `_STATE_TRANSITIONS` is refused. A record past draft
and not cancelled is not deleted. `action_confirm` and `action_cancel` run their
check registries (`_get_confirm_validation_methods`, `_get_cancel_validation_methods`)
before writing; `action_draft`, `action_lock` and `action_unlock` write directly.

Adopters: `mixin.order` (base_order), `maintenance.order` through
`mixin.approval.lifecycle` (approval).

### models/mixin_color.py

#### MixinColor — `mixin.color` (AbstractModel)

Shared color behavior without stored fields: overridable palette defaults,
hex-field validation through `odoo.libs.colors.hex_to_rgb`, palette-index
validation, index-to-hex conversion with an explicit palette and fallback,
and RGB hex lightening through `odoo.libs.colors.lighten_hex`.
Consumers retain their field types, defaults, and constraint triggers.

### models/mixin_tag.py

#### MixinTag — `mixin.tag` (AbstractModel, inherits `mixin.catalog`, `mixin.color`)

Coloured label with a stable code. The code survives a rename, so data files and
integrations can point at a tag without depending on its display name.

**Fields:** `name`, `active` (from `mixin.catalog`), `color` (Integer), `code` (Char)

**Key Methods:**
- `_default_color()` — Deterministic colour from the name
- `_name_to_code(name)` — Slugified stable code

### models/mixin_hierarchy.py

#### MixinHierarchy — `mixin.hierarchy` (AbstractModel)

Owns `_parent_store` and the `parent_path` column for every tree model in the
module, plus the one recursion constraint they used to each spell
themselves; a model overrides `_hierarchy_cycle_message` when a
domain-specific sentence reads better.

**Fields:** `parent_path` (Char, index)

**Key Methods:**
- `_check_parent_id()` — Raises `ValidationError` on a cycle

### models/mixin_tag_nested.py

#### MixinTagNested — `mixin.tag.nested` (AbstractModel, inherits `mixin.tag`, `mixin.hierarchy`)

A tag with a parent/child hierarchy; `parent_path` and `_parent_store` come
from `mixin.hierarchy`, this mixin adds the path-aware display name.

**Fields:** `parent_id` / `child_ids`, `parent_path` (via `mixin.hierarchy`)

**Key Methods:**
- `_check_parent_id()` — Reject recursion
- `_search_display_name(operator, value)` — Match on the full path

### models/tag_tag.py

#### TagTag — `tag.tag` (`_name`, inherits `mixin.tag.nested`)

The concrete generic tag model. Modules that need tags without their own table
point a Many2many here rather than declaring a fourth `x.tag`.

**Fields:** `parent_id` (Many2one → tag.tag), `child_ids` (One2many)

### models/mixin_band.py

#### MixinBand — `mixin.band` (AbstractModel)

Numeric band — a `[min, max)` interval with the overlap rules enforced. `max_value`
of zero means open-ended.

**Fields:** `min_value` (Float), `max_value` (Float)

**Key Methods:**
- `_is_band(record)` — Whether the record participates in banding
- `_get_domain_band_scope()` — Domain selecting the bands this one must not overlap
- `_is_range_overlapping(a, b)`, `_is_covering(value)` — Interval arithmetic
- `_check_band()` — Constraint: non-negative lower bound, ordered bounds, no overlap

### models/mixin_favorite.py

#### MixinFavorite — `mixin.favorite` (AbstractModel)

A single per-record favourite flag, not per user. See `mixin.user.favorite` for
the per-user form.

**Fields:** `is_favorite` (Boolean)

### models/mixin_user_favorite.py

#### MixinUserFavorite — `mixin.user.favorite` (AbstractModel)

Per-user favourites. Replaces the hand-written `_compute_is_favorite` /
`_search_is_favorite` / `_inverse` triple that models kept redeclaring, and
declares `@api.depends_context("uid")` once so the compute cannot serve one
user's answer to another.

**Fields:** `favorite_user_ids` (Many2many → res.users), `is_user_favorite` (Boolean, computed, searchable, inversed)

**Key Methods:**
- `_update_user_favorite(users, add)` — The write path both the inverse and the action use
- `_check_user_favorite_access()` — A user may only favourite for themselves
- `_search_is_user_favorite(operator, value)`, `action_toggle_user_favorite()`
- `_order_field_to_sql(...)` — Ordering by the flag without a subquery per row

### models/mixin_merge.py

#### MixinMerge — `mixin.merge` (AbstractModel)

Record merge engine. The generic half of what the partner merge wizard used to
carry inline: re-point every foreign key and every `reference` field from the
source records onto the destination, then absorb the source values.

**Key Methods:**
- `_get_relations_to_repoint(model)` — FK (table, column) pairs, minus the excluded tables
- `_get_foreign_keys_on_table(table)`, `_has_check_or_unique_constraint(table, column)` — Schema introspection
- `_update_foreign_keys_generic(model, src_records, dst_record)` — Re-point every FK
- `_repoint_table`, `_repoint_join_rows`, `_repoint_rows`, `_repoint_rows_one_by_one` — The per-table strategies
- `_update_reference_fields_generic(...)` — Sidecar rows, `reference` fields, company-dependent many2ones and `ir_default`
- `_update_values_generic(...)` — Merge field values onto the destination
- `_is_source_absorbed_on_merge()` — Hook: whether the destination takes the sources' values

### models/kpi_provider.py

#### KpiProvider — `kpi.provider` (AbstractModel)

Contract for anything that publishes a KPI summary.

**Key Methods:** `get_kpi_summary()` — Override to return this provider's KPIs

---

### models/mixin_recurrence_interval.py

#### MixinRecurrenceInterval — `mixin.recurrence.interval` (AbstractModel)

Every N units. `repeat_interval` (Integer, default 1, positive), `repeat_unit` (Selection day/week/month/year; consumers widen it with `selection_add`). `_get_recurrence_delta()`, `_get_next_recurrence_after(start, after, tz)` over `odoo.tools.date_utils.next_after`. Taken by `ir.cron`, `account.move`, `account.transfer.model`, `fleet.vehicle.log.contract`, `sale.subscription.plan` and the rule mixin.

### models/mixin_recurrence_anchored.py

#### MixinRecurrenceAnchored — `mixin.recurrence.anchored` (AbstractModel)

Fixed points inside a period rather than every N units: `repeat_unit` (day/week/month/year), `repeat_weekday` (MON..SUN), `repeat_day` and `repeat_month` (string Selections, the day clamped to the month), and with `repeat_twice` a second `repeat_second_day`/`repeat_second_month`. `_get_next_anchor(after)` is strictly after, `_get_previous_anchor(on)` on or before, over `odoo.tools.date_utils.next_anchor`/`previous_anchor`, which clamp a day past a short month's end instead of skipping the month. An occurrence is a boundary: the period it closes ends as that day starts. A day of `last` is the one exception to how a day is named. Its boundary is the first of the next month, so its period is the calendar month, and `_get_anchor_day(boundary)` returns the last day it names. Taken by `hr.leave.accrual.level`, which credits an end-of-period accrual on that named day. Owns `WEEKDAY_SELECTION`, which the rrule mixin imports.

### models/mixin_recurrence_rule.py

#### MixinRecurrenceRule — `mixin.recurrence.rule` (AbstractModel, `_inherit = ['mixin.recurrence.interval']`)

Adds the end policy `repeat_type` (forever/until); `REPEAT_TYPE_COUNT` is `selection_add`-ed only by consumers that can stop on a count.

### models/mixin_recurrence_rrule.py

#### MixinRecurrenceRrule — `mixin.recurrence.rrule` (AbstractModel, `_inherit = ['mixin.recurrence.rule']`)

The iCalendar half: weekday set, `month_by`, `day`, `weekday`, `byday`, timezone, `repeat_number`, `repeat_until` and the serialised `rrule`, with parse/serialise and occurrence enumeration capped at `MAX_RECURRENT_OCCURRENCES`.

### models/mixin_recurrence_occurrence.py

#### MixinRecurrenceOccurrence — `mixin.recurrence.occurrence` (AbstractModel)

`recurrence_update` (this/subsequent/all, not stored): which occurrences an edit or deletion applies to.

## Config

### models/res_config.py

#### ResConfig — `res.config` (TransientModel)

Base configuration wizard. Override `execute()` to save settings.

#### ResConfigSettings — `res.config.settings` (TransientModel)

Settings wizard framework with automatic field handling. Fields with naming conventions:
- `default_*` — Set default values for model fields
- `group_*` — Toggle group membership
- `module_*` — Install/uninstall modules
- `config_parameter` attribute — Read/write ir.config_parameter

**Key Methods:**
- `_get_classified_fields(fnames)` — Classify fields by type
- `default_get(fields)` — Load current values
- `set_values()` — Save defaults, apply groups, set config parameters
- `execute()` — Save settings and handle module installation

---

## Wizards

### wizards/base_partner_merge.py

#### BasePartnerMergeAutomaticWizard — `base.partner.merge.automatic.wizard` (TransientModel)

Partner deduplication — manual or automatic merge.

**Key Methods:**
- `_update_foreign_keys(src_partners, dst_partner)` — Update all FK references
- `_update_reference_fields(src_partners, dst_partner)` — Update reference fields
- `_merge(partner_ids, dst_partner, extra_checks)` — Core merge orchestration
- `action_start_manual_process()`, `action_start_automatic_process()` — Launch modes

#### BasePartnerMergeLine — `base.partner.merge.line` (TransientModel)

One candidate group the wizard found. Holds `min_id` and `aggr_ids`, the
partners the automatic pass would merge together.

### wizards/change_password.py

Password change wizards — admin batch change and self-service.

- `change.password.wizard` (ChangePasswordWizard) — Admin form, one line per user
- `change.password.user` (ChangePasswordUser) — A line: the user and the new password
- `change.password.own` (ChangePasswordOwn) — Self-service, requires the current password

### wizards/base_language_install.py / base_import_language.py / base_export_language.py

Language management wizards — install, import PO files, export translations.

- `base.language.install` (BaseLanguageInstall) — Activate languages, optionally overwrite existing terms
- `base.language.import` (BaseLanguageImport) — Load a `.po`/`.csv` for one language
- `base.language.export` (BaseLanguageExport) — Emit `.pot`/`.po`/`.tgz`/`.csv` for chosen modules

### wizards/base_module_update.py / base_module_upgrade.py / base_module_uninstall.py

Module lifecycle wizards — scan, upgrade, uninstall with dependency analysis.

- `base.module.update` (BaseModuleUpdate) — Rescan the addons path into `ir.module.module`
- `base.module.upgrade` (BaseModuleUpgrade) — Confirm and run the pending upgrade set
- `base.module.uninstall` (BaseModuleUninstall) — Show the dependency cascade before uninstalling

### wizards/reset_view_arch.py

#### ResetViewArchWizard — `reset.view.arch.wizard` (TransientModel)

Reset view to original arch — soft (arch_prev) or hard (arch_fs).

### wizards/wizard_ir_model_menu_create.py

#### WizardIrModelMenuCreate — `wizard.ir.model.menu.create` (TransientModel)

Create menu item for custom model.

---

## Model Index

Quick lookup — file → model → primary role:

| File | Model(s) | Role |
|------|----------|------|
| `ir_actions_actions.py` | ir.actions.actions | Base action model, bindings, path |
| `ir_actions_path.py` | ir.actions.path | Side table making an action path unique |
| `ir_actions_act_window.py` | ir.actions.act_window | Window action (opens views on a model) |
| `ir_actions_act_window_view.py` | ir.actions.act_window.view | View ordering within a window action |
| `ir_actions_act_window_close.py` | ir.actions.act_window_close | Close-window action |
| `ir_actions_act_url.py` | ir.actions.act_url | URL action |
| `ir_actions_client.py` | ir.actions.client | Client-side action (JS component) |
| `ir_actions_todo.py` | ir.actions.todo | Configuration wizard queue |
| `ir_actions_report.py` | ir.actions.report | PDF/HTML report rendering (WeasyPrint) |
| `ir_actions_server.py` | ir.actions.server | Automated actions (code/CRUD/webhook); delivery in `odoo/libs/webhook.py` |
| `ir_actions_server_history.py` | ir.actions.server.history | Code versions of a server action |
| `ir_asset.py` | ir.asset | Asset bundle management |
| `ir_asset_paths.py` | AssetPaths, BundleWalk (non-ORM) | Asset directive walk |
| `ir_attachment.py` | ir.attachment | File storage (DB/filestore) |
| `ir_attachment_assets.py` | ir.attachment (extension) | Generated-asset GC and regeneration |
| `ir_attachment_storage.py` | AttachmentStorage, DbStorage, FileStorage (non-ORM) | Storage backends |
| `ir_autovacuum.py` | ir.autovacuum | GC framework (@api.autovacuum) |
| `ir_binary.py` | ir.binary | File/image streaming helpers |
| `ir_egress.py` | ir.egress | Outbound HTTP pipeline (address policy, pinning, caps) |
| `ir_config_parameter.py` | ir.config_parameter | System key-value parameters |
| `ir_cron.py` | ir.cron, .cron.trigger, .cron.progress | Scheduled jobs + triggers |
| `ir_default.py` | ir.default | Field default values |
| `ir_demo.py` | ir.demo | Demo data installation |
| `ir_demo_failure.py` | ir.demo_failure, .demo_failure.wizard | Demo failure tracking |
| `ir_actions_embedded.py` | ir.embedded.actions | Embedded view actions |
| `ir_fields.py` | ir.fields.converter | Import type converters |
| `ir_filters.py` | ir.filters | Saved search filters |
| `ir_job.py` | ir.job, ir.job.channel | Background job queue + channels |
| `ir_http.py` | ir.http | HTTP routing/auth/dispatch |
| `ir_logging.py` | ir.logging | Server/client logs |
| `ir_model.py` | ir.model, ir.model.inherit | Model registry + inheritance |
| `ir_model_access.py` | ir.model.access | Model-level ACL |
| `ir_model_reflection.py` | ir.model.constraint, ir.model.relation | DB constraint/relation tracking for uninstall |
| `ir_model_data.py` | ir.model.data | XML ID registry |
| `ir_model_common.py` | helpers (non-ORM) | xmlid builders, reflection upserts, access errors |
| `ir_model_fields.py` | ir.model.fields | Field metadata registry |
| `ir_model_fields_selection.py` | ir.model.fields.selection | Selection options |
| `ir_module.py` | ir.module.module, .category | Module lifecycle |
| `mixin_module_link.py` | mixin.module.link | Manifest-named module link (abstract) |
| `ir_module_module_dependency.py` | ir.module.module.dependency | Manifest `depends` entries |
| `ir_module_module_exclusion.py` | ir.module.module.exclusion | Manifest `excludes` entries |
| `kpi_provider.py` | kpi.provider | KPI aggregation hook (abstract) |
| `ir_profile.py` | ir.profile | Code profiling |
| `ir_qweb.py` | ir.qweb | Template engine |
| `ir_qweb_fields.py` | ir.qweb.field (+ 21 subclasses) | Template field formatters |
| `ir_qweb_assets.py` | ir.qweb (extension) | Asset nodes, ESM bundles, esbuild circuit |
| `ir_rule.py` | ir.rule | Record-level access rules |
| `ir_sequence.py` | ir.sequence, .date_range | Auto-incrementing sequences |
| `ir_ui_menu.py` | ir.ui.menu | Menu hierarchy |
| `ir_ui_view.py` | ir.ui.view | View definitions + inheritance |
| `ir_ui_view_base.py` | base (mixin) | Default view generators |
| `ir_ui_view_custom.py` | ir.ui.view.custom | User view customizations |
| `ir_ui_view_name_manager.py` | NameManager (utility) | View XML validator |
| `assetsbundle/bundle.py` | AssetsBundle (non-ORM) | Asset compilation |
| `mixin_avatar.py` | mixin.avatar | SVG avatar generation |
| `mixin_band.py` | mixin.band | Numeric band / range mixin |
| `mixin_catalog.py` | mixin.catalog | Unique translated name, archivable |
| `mixin_lifecycle.py` | mixin.lifecycle | Declared state transitions, locking, confirm/cancel checks |
| `mixin_color.py` | mixin.color | Shared color defaults, validation, and palette conversion |
| `mixin_favorite.py` | mixin.favorite | Per-record favourite flag |
| `mixin_user_favorite.py` | mixin.user.favorite | Per-user favourite flag |
| `mixin_merge.py` | mixin.merge | Record merge engine |
| `mixin_tag.py` | mixin.tag | Coloured label with a stable code |
| `mixin_tag_nested.py` | mixin.tag.nested | Tag with a parent/child hierarchy |
| `mixin_hierarchy.py` | mixin.hierarchy | `_parent_store` tree on a materialized path |
| `tag_tag.py` | tag.tag | Generic tag records |
| `decimal_precision.py` | decimal.precision | Decimal precision config |
| `mixin_image.py` | mixin.image | Multi-resolution images |
| `properties_base_definition.py` | properties.base.definition | Properties definitions |
| `mixin_properties_base_definition.py` | mixin.properties.base.definition | Properties mixin |
| `phone_number.py` | phone.number | Shared phone numbers |
| `report_paperformat.py` | report.paperformat | Paper format config |
| `res_bank.py` | res.bank, res.partner.bank | Banks + accounts |
| `res_company.py` | res.company | Company hierarchy |
| `res_config.py` | res.config, res.config.settings | Settings framework |
| `res_country.py` | res.country, .group, .state | Geography |
| `res_currency.py` | res.currency, .rate | Currencies + rates |
| `res_device.py` | res.device.log, res.device | Session tracking |
| `res_groups.py` | res.groups | Security groups |
| `res_groups_privilege.py` | res.groups.privilege | Group categories |
| `res_lang.py` | res.lang | Languages |
| `res_partner.py` | res.partner | Contacts/companies |
| `res_partner_tag.py` | res.partner.tag | Partner tags |
| `res_partner_identifier_type.py` | res.partner.identifier.type | Identifier kinds (RFC, CURP, SIREN…) |
| `res_partner_identifier.py` | res.partner.identifier | One contact's identifier value |
| `mixin_format_address.py` | mixin.format.address | Address formatting |
| `mixin_format_vat_label.py` | mixin.format.vat.label | VAT label formatting |
| `res_partner_industry.py` | res.partner.industry | Industries |
| `res_users.py` | res.users | User accounts |
| `res_users_apikeys.py` | res.users.apikeys, .description, .show | API keys |
| `res_users_deletion.py` | res.users.deletion | User deletion queue |
| `res_users_identitycheck.py` | res.users.identitycheck | Password verification |
| `res_users_log.py` | res.users.log | Login tracking |
| `res_users_login_cooldown.py` | res.users.login.cooldown | Login-failure cooldown |
| `res_users_settings.py` | res.users.settings | User preferences |

Wizards (`wizards/`):

| File | Model(s) | Role |
|------|----------|------|
| `base_export_language.py` | base.language.export | Translation export wizard |
| `base_import_language.py` | base.language.import | Translation import wizard |
| `base_language_install.py` | base.language.install | Language installation wizard |
| `base_module_update.py` | base.module.update | Module list update wizard |
| `base_module_upgrade.py` | base.module.upgrade | Module upgrade wizard |
| `base_module_uninstall.py` | base.module.uninstall | Module uninstall wizard |
| `base_partner_merge.py` | base.partner.merge.automatic.wizard, base.partner.merge.line | Partner deduplication wizard |
| `change_password.py` | change.password.wizard, change.password.user, change.password.own | Password change wizards |
| `reset_view_arch.py` | reset.view.arch.wizard | View arch reset wizard |
| `server_action_history.py` | server.action.history.wizard | Server-action run history wizard |
| `wizard_ir_model_menu_create.py` | wizard.ir.model.menu.create | Menu creation wizard |
