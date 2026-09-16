# Website Module Model Map

Every Python model defined or extended by the `website` module, with the fields,
methods, and invariants that matter for the multi-website CMS. **63 model
classes** defined across `models/` (36 `.py` files) and `wizards/` (5 `.py`
files, 4 of which define models).

> **See also**: `ARCHITECTURE.md` (how these models compose into the frontend
> rendering pipeline), `ROUTE_MAP.md` (the controllers that call them),
> `CONVENTIONS.md` (COW/COU, `website_domain()`, published-mixin rules).

Kind legend: **NEW** = new model · **EXT** = extends a core model · **ABSTRACT**
= AbstractModel (mixin) · **TRANSIENT** = TransientModel · **SQL-VIEW** =
`_auto = False`.

## Cross-cutting invariants

These recur throughout and are the reason website models behave differently from
plain ORM models:

- **COW (Copy-On-Write)** — editing a *generic* (`website_id`-less)
  `ir.ui.view` / `ir.asset` under a `website_id` context copies it into a
  website-specific record instead of mutating the shared one. **COU
  (Copy-On-Unlink)** — deleting a generic view creates specific copies for the
  *other* websites so only the current one is affected. The engine lives in
  `ir_ui_view.py` `write`/`unlink`; never bypass with `no_cow` unless deliberate.
- **`website_domain()`** = `["website_id", "in", [False, *ids]]` — the canonical
  multi-website scoping filter ("generic OR mine"). Used everywhere records are
  read in a website context.
- **Cache invalidation** — writes affecting rendered output clear
  `self.env.registry.clear_cache("templates")` (or `"routing"` / `"assets"`).
- **`_inherits` delegation** — `website.page` and `website.controller.page` both
  delegate to `ir.ui.view` via `_inherits = {"ir.ui.view": "view_id"}`.

## The Signature Model

### models/website.py — Website (`_name = "website"`) — NEW

`_order = "sequence, id"`. The central multi-website configuration record and
the hub for frontend resolution, pages, and caching; the configurator lives in
`website_configurator.py` and the search stack in `website_search.py`, both
`_inherit = "website"` extensions in this module. ~44
fields.

**Notable fields:** `name`, `sequence`, `domain` (public URL, unique SQL
constraint `_domain_unique`), `domain_punycode` (compute, ASCII host),
`company_id`, `user_id` (the per-website **Public User**), `language_ids` /
`default_lang_id` / `auto_redirect_lang`, `menu_id` (compute, main menu),
`homepage_url`, `theme_id` (→ ir.module.module). Analytics/SEO:
`google_analytics_key`, `google_search_console`, `google_maps_api_key`,
`plausible_shared_key`/`plausible_site`, `robots_txt` (Html, `sanitize=False`).
Branding: `logo`, `favicon`, `social_default_image`, `social_*` handles.
Privacy: `cookies_bar`, `block_third_party_domains`,
`custom_blocked_third_party_domains`, `blocked_third_party_domains` (compute).
CDN: `cdn_activated`, `cdn_url`, `cdn_filters`. Custom code:
`custom_code_head`/`custom_code_footer` (Html, `sanitize=False`). Auth:
`specific_user_account`, `auth_signup_uninvited` (b2b/b2c), `configurator_done`.

**Key methods:**
- `website_domain()` — the multi-website scoping domain.
- `get_current_website(fallback=True)` / `_get_current_website_id(domain, fallback)` — resolve the active website from request/domain. `_force()` / `_force_website(id)` pin it in session.
- `_get_cached(field)` / `_get_cached_values()` — ormcached scalar accessors (user_id, company_id, default_lang_id) avoiding per-request reads.
- **Configurator RPC surface:** `configurator_init`, `configurator_apply`, `configurator_skip`, `configurator_recommended_themes`, `configurator_set_menu_links`, `configurator_get_footer_links`, `get_theme_configurator_snippets`, `create_and_redirect_configurator`, + snippet preconfig helpers.
- **Page CRUD:** `new_page(...)`, `get_unique_path(url)`, `get_unique_key(...)`, `_bootstrap_homepage`, `copy_menu_hierarchy`, `is_page_existing`, `search_pages`, `search_url_dependencies`.
- **Frontend fuzzy-search engine:** `_search_get_details`, `_search_with_fuzzy`, `_search_exact`, `_search_render_results`, `_search_find_fuzzy_term`, `_trigram_enumerate_words` (pg_trgm), `_basic_enumerate_words`, `_search_text_from_html`.
- **Sitemap:** `_enumerate_pages`, `is_rule_enumerable`.
- **Rendering helpers:** `image_url`, `get_cdn_url`, `get_template`, `viewref`, `is_view_active`, `pager`, `_get_canonical_url`, `_is_canonical_url`.
- `_check_access_to_modify(record)` — the publish-rights gate used by mixins and editable QWeb.
- `create` (multi) bootstraps menu/homepage/pages/social defaults per new website; `unlink` guards the default website.

> `domain` must be unique. Public-user resolution is cached and
> security-sensitive. Homepage URL sync is scoped by real page resolution
> across websites.

## The Mixin Stack (models/mixins.py)

Other modules' models inherit these to become publishable / searchable /
SEO-aware. All ABSTRACT.

| Mixin (`_name`) | Adds | Notes |
|---|---|---|
| `mixin.website.seo.metadata` | `is_seo_optimized`, `website_meta_title/description/keywords/og_img`, `seo_name` | Override `_get_default_website_meta()` to change defaults; call `get_website_meta()` (do NOT override it). Inherited notably by `ir.ui.view`. |
| `mixin.website.cover_properties` | `cover_properties` (Text/JSON) | `_get_background(h,w)`; malformed JSON → `ValidationError`, not 500. |
| `mixin.website.page_visibility_options` | `header_visible`, `footer_visible` | |
| `mixin.website.page_options` | `header_overlay`, `header_color`, `header_text_color` | `_inherit`s the visibility mixin. |
| `mixin.website.multi` | `website_id` (M2O, ondelete restrict) | `can_access_from_current_website()` — checked by `ir_http._pre_dispatch` → 404/403. |
| `mixin.website.published` | `is_published`/`website_published`, `can_publish`, `website_url`, `website_absolute_url` | `website_publish_button()` (RPC toggle); `create`/`write` raise `AccessError` if publishing without `can_publish`. Override `website_url` per model. |
| `mixin.website.published.multi` | (composes published + multi) | Makes publish state context-`website_id` aware: a record bound to another website reads unpublished. `_search_website_published` supports only `in (True,)`. |
| `mixin.website.searchable` | frontend-search contract | Override `_search_get_detail()` (raises `NotImplementedError`): returns model/base_domain/search_fields/fetch_fields/mapping/icon. |

## Content: Pages, Menus, Routing

### models/website_page.py — WebsitePage (`_name = "website.page"`) — NEW

`_inherits = {"ir.ui.view": "view_id"}`, `_inherit = [published.multi.mixin,
searchable.mixin, page_options.mixin]`, `_order = "website_id"`. A CMS page that
delegates to `ir.ui.view`.

**Fields:** `url` (required), `view_id` (delegate, cascade), `website_id`
(related view, stored), `arch` (related), `website_indexed`, `date_publish`,
`menu_ids`, `is_in_menu`/`is_homepage`/`is_visible` (computes),
`is_new_page_template`. Constants: `_CACHE_DURATION = 3600`,
`_NON_RENDERING_FIELDS = {view_write_uid, view_write_date}` (writes touching
only these skip cache clear).

**The full-page response cache** (the notable subsystem): `_get_response`,
`_get_response_cached` (ormcache `"templates.cached_values"`), `_get_cache_key`
(website / lang / path / debug / **cookie-consent** state), `_get_page_info`
(ormcached url→page), `_is_cache_usable` (GET, no params, public user, no
group), `_post_process_response_from_cache` (rewrites csrf_token, stamps
`_cached_page`/`_cached_view_id` for visitor tracking). `PageCannotBeCached`
exception. Cache is keyed with cookie-consent so embeds don't leak across
visitors. Other methods: `clone_page` (RPC), `_get_most_specific_pages`
(dedup generic vs specific by url), `write` (slugify/uniquify url, homepage sync,
cache invalidation), `unlink` (deletes orphan `ir.ui.view`).

### models/website_controller_page.py — WebsiteControllerPage (`_name = "website.controller.page"`) — NEW

`_inherits = {"ir.ui.view": "view_id"}`, `_inherit = [published.multi.mixin,
searchable.mixin]`. Exposes a model's records at `/model/<name_slugified>`.
Fields: `view_id` (listing view, delegate), `record_view_id`, `name_slugified`
(URL slug, stored, `_unique_name_slugified` constraint), `record_domain` (public
record restriction), `default_layout` (grid/list). `_check_user_has_model_access`
requires a concrete model + read access.

### models/website_technical_page.py — WebsiteTechnicalPage (`_name = "website.technical.page"`) — SQL-VIEW

`_auto = False`. Lists controller routes flagged `list_as_website_content` in
their route decorator. `_table_query` builds a VALUES-based SQL view from
`get_static_routes()` (ormcached `"routing"`).

### models/website_menu.py — WebsiteMenu (`_name = "website.menu"`) — NEW

`_parent_store = True`, `_order = "sequence, id"`. Fields: `name` (translate),
`url` (compute/store, default `"#"`), `page_id` (cascade),
`controller_page_id`, `sequence` (per-website max default), `website_id`
(cascade), parent tree fields, `is_visible` (compute — page/controller
visibility + ACL), `group_ids` (visibility groups), `is_mega_menu`,
`mega_menu_content` (Html, `html_translate`, `sanitize=False`),
`mega_menu_classes`. `_SAVE_ALLOWED_FIELDS` frozenset whitelists the editor
`save` RPC. `create` fans a website-less menu out to every website; `unlink`
removes per-website copies matched by url with guards
(`_unlink_except_master_tags`). `get_tree(website_id, menu_id)` and
`save(website_id, data)` are the editor RPCs. Constraint `_check_parent_menu`
(max 2 levels; mega menu no parent/child).

### models/website_rewrite.py — WebsiteRoute + WebsiteRewrite — NEW

- **`website.route`** (`_rec_name = "path"`) — mirror of the live GET routing map; `_refresh()` syncs the table, `name_search` self-refreshes on empty result.
- **`website.rewrite`** — URL redirect/rewrite rules. `redirect_type` = 404/301/302/308; `route_id` (→ website.route), `url_from`/`url_to`, `website_id` (cascade). `_check_url_to` validates 308 param parity + existing-page collisions. CRUD calls `_invalidate_routing()` for 308/404.

## Framework Extensions — Frontend Dispatch & Rendering

### models/ir_http.py — IrHttp (`_inherit = "ir.http"`) — EXT

The frontend dispatch layer.
- **Routing:** `routing_map`/`_routing_map_key` (per-website), `_generate_routing_rules` (applies website.rewrite 308/404), `_get_rewrites` (ormcached `"routing"`), `_get_converters` (adds `model`), `_match` (stamps `request.website_routing`), `_pre_dispatch` (enforces `can_access_from_current_website` → 404/403).
- **Slugging:** `_slug` (uses `seo_name`), `_slug_matching`, `_url_for` (applies rewrites).
- **Public user:** `_get_public_users` / `_auth_method_public` (per-website public user).
- **Frontend lifecycle:** `_frontend_pre_dispatch` (sets website_id/company/tz/editor ctx), `_post_dispatch` → `_register_website_track` (fires visitor tracking on 200 GETs, non-bot).
- **Serving fallback:** `_serve_fallback` → `_serve_page` (website.page + trailing-slash redirects) / `_serve_redirect` (website.rewrite 301/302, specific-over-generic).
- **Session/cookies:** `get_frontend_session_info` (adds website_id, geoip country/phone, lang_url_code), `_is_allowed_cookie` (GDPR optional-cookie consent from `website_cookies_bar` cookie).
- Module-level helpers: `sitemap_qs2dom(qs, route, field)`, `get_request_website()` (the mockable "are we in frontend?" check — import the module, not the function). `ModelConverter` injects `current_website_id` into route domains.

### models/ir_qweb.py — IrQweb (`_inherit = "ir.qweb"`) — EXT

Website rendering layer. `URL_ATTRS` maps rewritable attributes
(form.action, a.href, link.href, script.src, img.src). `_prepare_frontend_environment`
sets website/editable/translatable/company/cookie-consent context.
**`_post_processing_att`** is the big one: lazy-load `<img>`, `url_for`
rewriting, CDN rewriting, background-image adaptation, and the **third-party
cookie barrier** — rewriting iframe/script `src` to `about:blank` +
`data-nocookie-src` when consent isn't granted (`data-no-post-process` skips it;
static nodes never honor the per-request debug bypass — GDPR safety).

### models/ir_ui_view.py — IrUiView (`_inherit = ["ir.ui.view", "mixin.website.seo.metadata"]`) — EXT

**The COW/COU engine** + view visibility. Fields: `website_id` (cascade),
`page_ids`/`controller_page_ids`, `track` (per-page visitor tracking),
`visibility` (`''` public / connected / restricted_group / password),
`visibility_password` (hashed) + SEO metadata via the mixin. `write` = **COW**
(copies generic view to website-specific, relocates inherit children, creates
specific pages); `unlink` = **COU**. `_get_views_inheriting` prefers inactive
specific over active generic. `_handle_visibility(do_raise)` enforces
public/connected/group/password → 403. `get_view_hierarchy` / `get_related_views`
are the editor RPCs. `save(value, xpath)` diverts writes to the specific view.

### Other `ir.*` / `base` extensions

| File | Model | Role |
|------|-------|------|
| `ir_actions_server.py` | `ir.actions.server` | Publish code actions at `/website/action/<path>` (`website_path`, `website_published`, `website_url`); action may return a `response`. |
| `ir_asset.py` | `ir.asset` | Multi-website assets with COW (`key`, `website_id`); `_get_asset_bundle_url` namespaces the URL by website id; cross-website byte-reuse deliberately disabled. |
| `ir_attachment.py` | `ir.attachment` | `key`, `website_id`; `create` stamps current website unless `not_force_website_id` ctx; website-scoped `_get_serve_attachment`. |
| `ir_binary.py` | `ir.binary` | `_find_record` resolves theme attachments by `key` + website_id before super. |
| `ir_model.py` | `base` | `get_base_url()` (own website domain → company website domain → ICP), `get_website_meta()`, `_get_base_lang()`. |
| `models.py` | `base` | `_can_return_content()` allows serving a field's content when the record is `website_published`. |
| `ir_model_data.py` | `ir.model.data` | `_process_end_unlink_record` cascade-unlinks theme `copy_ids` on theme uninstall. |
| `ir_qweb_fields.py` | `ir.qweb.field.contact` + `ir.qweb.field.html` | Extra contact render options; injects the form signature into `<form>` in rendered HTML. |
| `ir_rule.py` | `ir.rule` | Injects `website` into eval context (frontend only) + `website_id` into the domain cache key. |
| `ir_ui_menu.py` | `ir.ui.menu` | `load_menus_root` — with `force_action` ctx, forces backend actions from web_menus. |
| `ir_module_module.py` | `ir.module.module` | **The theme install/upgrade/remove engine** (see below). |

## Themes (models/theme_models.py + ir_module_module.py)

Theme modules ship data as `theme.*` staging records; on install `ir.module.module`
copies them into real website-specific records (`copy_ids` back-reference,
`_convert_to_base_model(website)` returns the base vals).
`ir_module_module.py`'s `_theme_model_names` OrderedDict maps each base model to
its theme staging model:

| Staging model (`theme.*`, NEW) | Copies to |
|---|---|
| `theme.ir.ui.view` | `ir.ui.view` |
| `theme.ir.asset` | `ir.asset` |
| `theme.ir.attachment` | `ir.attachment` |
| `theme.website.menu` | `website.menu` |
| `theme.website.page` | `website.page` |
| `theme.utils` (ABSTRACT, `_auto=False`) | header/footer template lists + `enable/disable_asset`/`_view` COW-aware toggles |

`ir.module.module` methods: `write` (loads/upgrades themes on install/upgrade),
`_theme_load`/`_theme_unload`/`_theme_cleanup`, `_update_records`/`_post_copy`,
the `_stream_themes`/`_theme_get_upstream`/`_downstream` dependency walk,
`button_choose_theme`/`button_remove_theme`/`button_refresh_theme`. `theme_models.py`
also re-opens `ir.ui.view`/`ir.asset`/`ir.attachment`/`website.menu`/`website.page`
to add the `theme_template_id` back-link.

## Dynamic Snippets, Forms, Visitors

### models/website_snippet_filter.py — WebsiteSnippetFilter (`_name = "website.snippet.filter"`) — NEW

`_inherit = [published.multi.mixin]`. Powers dynamic snippets (carousels/lists).
Fields: `action_server_id` XOR `filter_id` (`_check_data_source_is_provided`),
`field_names` (comma list), `limit` (1–16), `website_id`, `model_name` (compute).
`_render(template_key, limit, search_domain, ...)` is the RPC entrypoint (template
must be prefixed `dynamic_filter_template_`). **Security:** in `_prepare_values`
the client `search_domain` leaves must reference direct fields only — no dotted
paths — to avoid leaking unpublished related records; the single-record path
(limit==1 + res_id) applies the same publication/record-rule scoping.

### models/website_form.py — form builder (3 classes)

- **`website` (EXT)** — `_get_website_form_last_record()` (session-tracked).
- **`ir.model` (EXT)** — `website_form_access` (opt-in), `website_form_default_field_id`, `website_form_label`, `website_form_key`; `_get_fields_form_writable`, `get_fields_authorized()` (RPC, **designer-gated** — leaks field metadata), `get_compatible_form_models()`.
- **`ir.model.fields` (EXT)** — `website_form_blacklisted` (default True; whitelist-by-negation). `init()` sets the SQL default; `formbuilder_whitelist(model, fields)` (RPC, designer-gated, raw SQL to avoid registry reload); `_unlink_except_used_in_website_form` (ondelete guard parsing HTML fields).

### models/website_visitor.py — WebsiteTrack + WebsiteVisitor — NEW

- **`website.track`** (`_log_access = False`, `_order = "visit_datetime DESC"`) — one row per page view: `visitor_id` (cascade), `page_id`, `url` (indexed), `visit_datetime`.
- **`website.visitor`** — visitor identity + analytics. `access_token` (required, partner.id for logged-in, sha1 for anonymous; `_access_token_unique`), `partner_id` (compute/store), geo/lang fields, `visit_count`, `is_connected` (within 5 min). `_upsert_visitor(...)` does a **raw SQL `INSERT ... ON CONFLICT` upsert** (+ optional track insert) so concurrent hits funnel to `DO UPDATE`; `_merge_visitor(target)` aggregates an anonymous visitor into the partner's on login. `_cron_unlink_old_visitors` (60-day default). **All datetime SQL is UTC-explicit** (`now() at time zone 'UTC'`) — matches the fork's TZ=UTC pinning.

## Supporting Models

| File | Model | Kind | Role |
|------|-------|------|------|
| `assets.py` | `website.assets` | ABSTRACT | SCSS/JS customization: `save_asset`/`reset_asset` (RPC), `update_scss_customization` (palettes, local Google fonts). |
| `html_text_processor.py` | `website.html.text.processor` | ABSTRACT | HTML/snippet text processing for configurator / ai_website (context-cache based, no stored fields). |
| `website_configurator_feature.py` | `website.configurator.feature` | NEW | Configurator feature catalog (`_check_module_xor_page_view`). |
| `res_company.py` | `res.company` | EXT | `website_id` (compute/store, first website); can't archive a company with a website. |
| `res_lang.py` | `res.lang` | EXT | Blocks deactivating a website language; `_get_frontend` (ormcached, hreflang, es_419 special-case). |
| `res_partner.py` | `res.partner` (+ published.multi) | EXT | `visitor_ids`, publishing, map helpers, `[website]` suffix in multi-website display name. |
| `res_users.py` | `res.users` | EXT | Website-scoped login (`_login_key` unique(login, website_id)), signup scoping, visitor link/merge on `authenticate`. |
| `base_partner_merge.py` | `base.partner.merge.automatic.wizard` | TRANSIENT/EXT | Merge visitors before FK reassign (avoids partner_id unique violation). |

## Wizards / Transient Models

| File | Model | Role |
|------|-------|------|
| `website_page_properties.py` | `website.page.properties.base` + `website.page.properties` | Page-properties editor (menu/homepage/publish inverse); URL change creates a `website.rewrite`. |
| `res_config_settings.py` | `res.config.settings` | Website settings panel (`group_multi_website` implied group; dozens of related-to-website fields; Plausible URL parse). |
| `wizards/base_language_install.py` | `base.language.install` | Adds `website_ids`; assigns installed langs to selected websites. |
| `wizards/blocked_third_party_domains.py` | `website.custom_blocked_third_party_domains` | Edit/normalize blocked 3rd-party domains. |
| `wizards/portal_wizard.py` | `portal.wizard.user` | Website-aware duplicate-user detection. |
| `wizards/website_robots.py` | `website.robots` | robots.txt editor. |

## Model Index

Quick lookup — file → model → role.

| File | Model (`_name` / `_inherit`) | Kind | Role |
|------|------|------|------|
| website.py | `website` | NEW | Central multi-website config; frontend resolution, pages, caching hub |
| website_configurator.py | `website` | INHERIT | Configurator: IAP calls, snippet preconfiguration, `configurator_apply` |
| website_search.py | `website` | INHERIT | Frontend search: exact, trigram/basic fuzzy term enumeration, result rendering |
| mixins.py | `mixin.website.seo.metadata` | ABSTRACT | SEO/OpenGraph/Twitter metadata |
| mixins.py | `mixin.website.cover_properties` | ABSTRACT | Cover image JSON properties |
| mixins.py | `mixin.website.page_visibility_options` | ABSTRACT | header/footer visible flags |
| mixins.py | `mixin.website.page_options` | ABSTRACT | header overlay/color options |
| mixins.py | `mixin.website.multi` | ABSTRACT | `website_id` + current-website access check |
| mixins.py | `mixin.website.published` | ABSTRACT | publish state + can_publish + website_url |
| mixins.py | `mixin.website.published.multi` | ABSTRACT | published + multi-website aware |
| mixins.py | `mixin.website.searchable` | ABSTRACT | frontend fuzzy-search contract |
| website_menu.py | `website.menu` | NEW | Site navigation tree (mega menus, per-website fan-out) |
| website_page.py | `website.page` | NEW | CMS page (delegates ir.ui.view) + full-page response cache |
| website_controller_page.py | `website.controller.page` | NEW | Model-listing page at `/model/<slug>` |
| website_technical_page.py | `website.technical.page` | SQL-VIEW | Read-only list of listable controller routes |
| website_rewrite.py | `website.route` | NEW | Mirror of live GET routing map |
| website_rewrite.py | `website.rewrite` | NEW | URL redirect/rewrite rules (301/302/308/404) |
| website_snippet_filter.py | `website.snippet.filter` | NEW | Dynamic-snippet data source |
| website_visitor.py | `website.track` | NEW | One row per page view |
| website_visitor.py | `website.visitor` | NEW | Visitor identity + analytics (SQL upsert) |
| website_configurator_feature.py | `website.configurator.feature` | NEW | Configurator feature catalog |
| html_text_processor.py | `website.html.text.processor` | ABSTRACT | HTML/snippet text processing |
| assets.py | `website.assets` | ABSTRACT | SCSS/JS customization service |
| website_form.py | `website` / `ir.model` / `ir.model.fields` | EXT×3 | Form builder opt-in + field whitelist |
| ir_http.py | `ir.http` | EXT | Frontend dispatch, routing, rewrites, visitor track, cookie consent |
| ir_qweb.py | `ir.qweb` | EXT | Website rendering: url_for/CDN/lazy-load/cookie barrier |
| ir_ui_view.py | `ir.ui.view` (+seo.metadata) | EXT | COW/COU engine + view visibility |
| ir_actions_server.py | `ir.actions.server` | EXT | Publish code actions on website |
| ir_asset.py | `ir.asset` | EXT | Multi-website assets + COW |
| ir_attachment.py | `ir.attachment` | EXT | website_id/key on attachments |
| ir_binary.py | `ir.binary` | EXT | Resolve theme attachments by key |
| ir_model.py | `base` | EXT | `get_base_url`/`get_website_meta`/`_get_base_lang` |
| models.py | `base` | EXT | `_can_return_content` for published records |
| ir_model_data.py | `ir.model.data` | EXT | Cascade-unlink theme copies on uninstall |
| ir_qweb_fields.py | `ir.qweb.field.contact` + `.html` | EXT×2 | Contact options; form signature in HTML |
| ir_rule.py | `ir.rule` | EXT | website in eval context + cache key |
| ir_ui_menu.py | `ir.ui.menu` | EXT | force_action backend menu loading |
| ir_module_module.py | `ir.module.module` | EXT | Theme install/upgrade/remove engine |
| theme_models.py | `theme.ir.asset` / `theme.ir.ui.view` / `theme.ir.attachment` / `theme.website.menu` / `theme.website.page` / `theme.utils` | NEW×5 + ABSTRACT | Theme staging + copy-to-base |
| res_company.py | `res.company` | EXT | company↔website link, map helpers |
| res_lang.py | `res.lang` | EXT | website-scoped frontend languages/hreflang |
| res_partner.py | `res.partner` (+published.multi) | EXT | visitor_ids + publishing + map |
| res_users.py | `res.users` | EXT | website-scoped login/signup + visitor linking |
| base_partner_merge.py | `base.partner.merge.automatic.wizard` | TRANSIENT/EXT | Merge visitors on partner merge |
| website_page_properties.py | `website.page.properties[.base]` | TRANSIENT | Page-properties editor + redirect creation |
| res_config_settings.py | `res.config.settings` | TRANSIENT/EXT | Website settings panel |
| wizards/base_language_install.py | `base.language.install` | TRANSIENT/EXT | Assign installed langs to websites |
| wizards/blocked_third_party_domains.py | `website.custom_blocked_third_party_domains` | TRANSIENT | Edit blocked 3rd-party domains |
| wizards/portal_wizard.py | `portal.wizard.user` | TRANSIENT/EXT | Website-aware duplicate detection |
| wizards/website_robots.py | `website.robots` | TRANSIENT | robots.txt editor |
