# Website Module Route Map

Complete mapping of HTTP endpoints to Python handlers for `addons/odoo/addons/website/`.

> **See also**: `ARCHITECTURE.md` (frontend/editor/backend split), `MODEL_MAP.md`
> (models these routes read/write), `CONVENTIONS.md` (`website=True` /
> `multilang` / published-mixin rules that every public route obeys).

Legend: `JSONRPC` = `type="jsonrpc"` POST (this fork's JSON-RPC type string is
`"jsonrpc"`, not the legacy `"json"`) | `HTTP` = `type="http"` (default; all
methods unless `methods=[...]` restricts) | `auth` = authentication type |
`readonly` = routed to a read-only cursor/replica if configured.

## Website-specific route kwargs

These appear on almost every website route and are the reason a URL renders a
themed, translated, multi-website page instead of a bare backend response:

| Kwarg | Effect |
|-------|--------|
| `website=True` | Binds the request to the current `website` record (`ir.http._serve_page` / `env['website'].get_current_website()`), enabling the frontend layout, multi-website record filtering, and `request.website`. |
| `multilang=False` | Disables the `/<lang>/` URL prefix — used by machine endpoints (`/robots.txt`, `/sitemap.xml`, `/website/lang/...`, image back-compat) that must not be language-rewritten. |
| `sitemap=True` / `sitemap=<callable>` / `sitemap=False` | Controls inclusion in `/sitemap.xml`. A callable is a generator `f(env, rule, qs)` yielding `{"loc": ...}` entries. |
| `csrf=False` | Public POST endpoints that accept cross-origin form submissions (`/website/form/...`). |
| `captcha="website_form"` | Enables reCAPTCHA verification on the form-builder submission route. |

## Public Site — Page Serving & Navigation

### controllers/main.py — Website (extends portal `Home`)

| Method | Route | Auth | Kwargs | Handler | Purpose |
|--------|-------|------|--------|---------|---------|
| HTTP | `/` | public | `website=True`, `sitemap=True` | `index()` | Homepage. Multi-fallback so home is never a 404: `homepage_url` reroute → `_serve_page` → controller match → first reachable menu → 404. |
| HTTP | `/website/force/<int:website_id>` | user | `website=True`, `sitemap=False`, `multilang=False`, `readonly=True` | `website_force()` | Force a website in session (cross-domain redirect aware). Needs `group_multi_website` + `group_website_restricted_editor`. |
| HTTP | `/@/`, `/@/<path:path>` | public | `website=True`, `sitemap=False`, `multilang=False`, `readonly=True` | `client_action_redirect()` | Redirect internal users to the backend editor/preview of a path; others to the plain frontend. |
| HTTP | `/website/lang/<lang>` | public | `website=True`, `multilang=False` | `change_lang()` | Switch frontend language (`url_code`); sets `frontend_lang` cookie, redirects to `r`. |
| HTTP | `/robots.txt` | public | `website=True`, `multilang=False`, `sitemap=False` | `robots()` | Render `website.robots` (`text/plain`) with allowed routes + url_root. |
| HTTP | `/sitemap.xml` | public | `website=True`, `multilang=False`, `sitemap=False` | `sitemap_xml_index()` | Generate/serve cached sitemap (12h cache = `SITEMAP_CACHE_TIME`; split at `LOC_PER_SITEMAP=45000`; emits a sitemap **index** when >1 page). `url_root` is pinned to the server-canonical root, not the `Host` header. |
| HTTP | `/favicon.ico` | public | `website=True`, `multilang=False`, `sitemap=False`, `readonly=True` | `favicon()` | 301 redirect to the website favicon image URL (long cache). |
| HTTP | `/website/info` | public | `website=True`, `sitemap=sitemap_website_info`, `readonly=True` | `website_info()` | Render `website.website_info` (installed apps, l10n modules, version). |
| HTTP | `/website/configurator`, `/website/configurator/<int:step>` | user | `website=True`, `multilang=False` | `website_configurator()` | Redirect designers into the backend website-configurator action (or `/` if done); 404 for non-designers. |
| HTTP | `/website/social/<string:social>` | public | `website=True`, `sitemap=False` | `social()` | Redirect to the website's `social_<social>` external URL; 404 if unset. |
| HTTP | `/pages`, `/pages/page/<int:page>` | public | `website=True`, `sitemap=False`, `readonly=True` | `pages_list()` | Paginated public listing of website pages (fuzzy search); `page` clamped 1–100. |
| HTTP | `/website/search`, `/website/search/page/<int:page>`, `/website/search/<string:search_type>`, `/website/search/<string:search_type>/page/<int:page>` | public | `website=True`, `sitemap=False`, `readonly=True` | `hybrid_list()` | Full search-results page. Calls `self.autocomplete(...)` (so subclass overrides apply) and renders `website.list_hybrid`. |
| HTTP | `/google<string(length=16):key>.html` | public | `website=True`, `sitemap=False`, `readonly=True` | `google_console_search()` | Google Search Console verification file; exact-match on stored token else 404. |
| HTTP | `/website/action/<path_or_xml_id_or_id>`, `/website/action/<...>/<path:path>` | public | `website=True` | `actions_server()` | Resolve + run a **published** `ir.actions.server` (by xml_id / website_path / id); return its Response or redirect to `/`. |

> `Website` declares **46 route handlers** in total. The table above is the
> page-serving/navigation subset; the editor, theme, SEO, snippet, and
> autocomplete handlers follow.

### controllers/model_page.py — ModelPageController (extends `Controller`)

Class constant: `pager_step = 20`.

| Method | Route | Auth | Kwargs | Handler | Purpose |
|--------|-------|------|--------|---------|---------|
| HTTP | `/model/<string:page_name_slugified>`, `/model/<...>/page/<int:page_number>`, `/model/<...>/<string:record_slug>` | public | `website=True`, `readonly=True` | `generic_model()` | Render a `website.controller.page` — list view (search/pager/order) or single-record view (via slug). Enforces publish state, `read` access, published-mixin filtering, and whitelists sortable order fields against the public `order` query param. |

## Public Site — Search, Autocomplete & Snippets

### controllers/main.py — Website

| Method | Route | Auth | Kwargs | Handler | Purpose |
|--------|-------|------|--------|---------|---------|
| JSONRPC | `/website/snippet/autocomplete` | public | `website=True`, `readonly=True` | `autocomplete()` | Public fuzzy-search autocomplete; clamps `limit` to `MAX_PAGE_SEARCH_RESULTS=500`; formats fields (highlight, monetary, truncate) to HTML. |
| JSONRPC | `/website/snippet/filters` | public | `website=True`, `readonly=True` | `get_dynamic_filter()` | Render a `website.snippet.filter` dynamic snippet's records. |
| JSONRPC | `/website/snippet/options_filters` | user | `website=True`, `readonly=True` | `get_dynamic_snippet_filters()` | Search-read available snippet filters (editor options). Restricted-editor gated. |
| JSONRPC | `/website/snippet/filter_templates` | public | `website=True`, `readonly=True` | `get_dynamic_snippet_templates()` | Return dynamic-filter QWeb templates + parsed `data-*` layout attributes. |
| JSONRPC | `/website/get_current_currency` | public | `website=True`, `readonly=True` | `get_current_currency()` | Website company currency `{id, symbol, position}`. |
| JSONRPC | `/website/country_infos/<model("res.country"):country>` | public | `methods=["POST"]`, `website=True`, `readonly=True` | `country_infos()` | Address fields, states, phone_code for a country. |
| JSONRPC | `/website/save_session_layout_mode` | public | `website=True`, `readonly=True` | `save_session_layout_mode()` | Store grid/list layout mode for a view in session. |
| JSONRPC | `/website/google_maps_api_key` | public | `website=True`, `readonly=True` | `google_maps_api_key()` | Website's Google Maps API key. |

## Editor, Theme & SEO (restricted-editor / designer gated)

### controllers/main.py — Website

| Method | Route | Auth | Kwargs | Handler | Purpose |
|--------|-------|------|--------|---------|---------|
| HTTP | `/website/add`, `/website/add/<path:path>` | user | `website=True`, `methods=["POST"]` | `pagenew()` | Create a new website page (optionally menu/template); returns JSON `{url}`/`{view_id}` or redirects to editor/backend. |
| JSONRPC | `/website/get_new_page_templates` | user | `website=True`, `readonly=True` | `get_new_page_templates()` | Build the grouped new-page template gallery (custom + configurator/section templates). |
| JSONRPC | `/website/save_xml` | user | `website=True` | `save_xml()` | Write arbitrary view `arch`. Restricted-editor gated (else Forbidden). |
| JSONRPC | `/website/get_switchable_related_views` | user | `website=True`, `readonly=True` | `get_switchable_related_views()` | `customize_show` related views for a key (theme toggles). |
| JSONRPC | `/website/reset_template` | user | `methods=["POST"]` | `reset_template()` | Reset a broken view (soft = previous arch / hard = XML-file arch). |
| JSONRPC | `/website/seo_suggest` | user | `website=True`, `readonly=True` | `seo_suggest()` | Keyword suggestions from Google autocomplete API (parsed via defusedxml). |
| JSONRPC | `/website/get_alt_images` | user | `website=True` | `get_alt_images()` | Introspect `<img>` alt/decorative state across records. Restricted-editor gated. |
| JSONRPC | `/website/update_alt_images` | user | `website=True` | `update_alt_images()` | Write img alt/role into stored html/text fields only. Restricted-editor gated. |
| JSONRPC | `/website/update_broken_links` | user | `website=True` | `update_broken_links()` | Rewrite/remove `<a href>` in stored html/text fields. Restricted-editor gated. |
| JSONRPC | `/website/get_seo_data` | user | `website=True`, `readonly=True` | `get_seo_data()` | SEO meta fields + edit permissions for a record. |
| JSONRPC | `/website/check_can_modify_any` | user | `website=True`, `readonly=True` | `check_can_modify_any()` | Whether the user may modify any of the given records. Restricted-editor gated. |
| JSONRPC | `/website/get_suggested_links` | user | `website=True`, `readonly=True` | `get_suggested_link()` | Link-editor autocomplete: matching pages, last-modified pages, app/controller URLs. |
| JSONRPC | `/website/check_existing_link` | user | `website=True`, `readonly=True` | `check_existing_link()` | Whether a page already exists for a link. |
| JSONRPC | `/website/get_languages` | user | `website=True`, `readonly=True` | `website_languages()` | `[(js_locale, url_code, name)]` for the website's languages. |
| JSONRPC | `/website/get_translated_elements` | user | `readonly=True` | `translated_elements()` | List of `TRANSLATED_ELEMENTS`. |
| JSONRPC | `/website/field/translation/update` | user | `website=True` | `update_field_translation()` | Update per-language field translations for a record/field. |
| JSONRPC | `/website/theme_customize_data_get` | user | `website=True`, `readonly=True` | `theme_customize_data_get()` | Active view/asset keys among the given keys. |
| JSONRPC | `/website/theme_customize_data` | user | `website=True` | `theme_customize_data()` | Enable/disable views or assets by key (optional hard arch reset). |
| JSONRPC | `/website/theme_customize_bundle_reload` | user | `website=True`, `readonly=True` | `theme_customize_bundle_reload()` | Fresh `web.assets_frontend` bundle URLs. |
| JSONRPC | `/website/update_footer_template` | user | `website=True` | `update_footer_template()` | Enable a footer template + matching copyright-width template. |
| JSONRPC | `/website/theme_upload_font` | user | `website=True` | `theme_upload_font()` | Validate + store an uploaded font (zip or single file). Enforces `MAX_FONT_FILE_SIZE=10MB` / `SUPPORTED_FONT_EXTENSIONS` + magic-byte checks. |
| JSONRPC | `/website/google_font_metadata` | user | `website=True` | `google_font_metadata()` | Cache + return Google Fonts metadata (daily refresh) to avoid CORS. |
| JSONRPC | `/website/get_assets_editor_resources` | user | `website=True` | `get_assets_editor_resources()` | Views + scss + js resources for the assets editor. |

## Form Builder (public submission)

### controllers/form.py — WebsiteForm

| Method | Route | Auth | Kwargs | Handler | Purpose |
|--------|-------|------|--------|---------|---------|
| HTTP POST | `/website/form` | public | `methods=["POST"]`, `multilang=False`, `readonly=True` | `website_form_empty()` | Returns `""`. Workaround so `<form action="/website/form/">` gets no language prefix. |
| HTTP POST | `/website/form/<string:model_name>` | public | `methods=["POST"]`, `website=True`, `csrf=False`, `captcha="website_form"` | `website_form()` | Validate + insert a submitted form record into `<model_name>`. Partial CSRF (only when session authenticated). Savepoint-wrapped; returns JSON `{id}` / `{error}` / `{error_fields}` / `False`. |

> **Form pipeline helpers** (non-route, `form.py`): `_handle_website_form` →
> `extract_data` → `create_record` / `create_attachments`, with per-type
> `_input_filters` (`identity`, `integer`, `floating`, `html`, `boolean`,
> `binary`, `one2many`, `many2many`, `tags`). For `mail.mail` submissions it
> enforces an HMAC `website_form_signature` (anti open-relay) before `.send()`.

## Backend Dashboard & New Content

### controllers/backend.py — WebsiteBackend

All JSONRPC, all `auth="user"`.

| Method | Route | Kwargs | Handler | Purpose |
|--------|-------|--------|---------|---------|
| JSONRPC | `/website/fetch_dashboard_data` | `readonly=True` | `get_dashboard_data()` | Website dashboard data (group flags, website list, Plausible analytics share URL). |
| HTTP | `/website/iframefallback` | `website=True`, `readonly=True` | `get_iframe_fallback()` | Render `website.iframefallback` (editor iframe fallback). |
| JSONRPC | `/website/check_new_content_access_rights` | `readonly=True` | `check_create_access_rights()` | Per-model `create` access for the "New Content" modal. Requires `group_website_restricted_editor` else Forbidden. |
| JSONRPC | `/website/track_installing_modules` | `readonly=True` | `website_track_installing_modules()` | Track install progress of selected configurator features/dependencies. |

## Assets & Bundles (per-website)

### controllers/binary.py — WebsiteBinary (extends web `Binary`)

| Method | Route | Auth | Kwargs | Handler | Purpose |
|--------|-------|------|--------|---------|---------|
| HTTP | `/web/assets/<int:website_id>/<unique>/<string:filename>` | public | `readonly=True` | `content_assets_website()` | Serve website-scoped asset bundles; 404 if `website_id` doesn't exist, else `super().content_assets(..., assets_params={"website_id": website_id})`. |

### controllers/webclient.py — WebsiteWebClient (extends web `WebClient`)

| Method | Route | Handler | Purpose |
|--------|-------|---------|---------|
| — (inherited) | `bundle` override (bare `@http.route()`) | `bundle()` | Inject `website_id` into request context (from `bundle_params`) before delegating to `super().bundle()`, so asset bundles resolve per-website. |

## Back-Compat Image Routes

### controllers/main.py — WebsiteBinary (extends web `Binary`)

| Method | Route | Auth | Kwargs | Handler | Purpose |
|--------|-------|------|--------|---------|---------|
| HTTP | `/website/image`, `/website/image/<xmlid>`, `/website/image/<xmlid>/<int:width>x<int:height>`, `/website/image/<xmlid>/<field>`, `/website/image/<xmlid>/<field>/<int:width>x<int:height>`, `/website/image/<model>/<id>/<field>`, `/website/image/<model>/<id>/<field>/<int:width>x<int:height>` (7 URLs) | public | `website=False`, `multilang=False`, `readonly=True` | `website_content_image()` | Backward-compat wrapper mapping legacy `/website/image/...` params to `content_image(...)`. |

> Two distinct classes are named `WebsiteBinary`: one in `binary.py`
> (per-website bundle serving) and one in `main.py` (legacy image routes).

## Session

### controllers/main.py — WebsiteSession (extends web `Session`)

| Method | Route | Handler | Purpose |
|--------|-------|---------|---------|
| — (inherited) | `logout` override (`@http.route(auth="public")`) | `logout()` | Force `auth="public"` so logout works without a live session. |

## Route Count Summary

Counts are **(handler functions) / (declared URL-pattern variants)**. A single
`@http.route(routes=[...])` counts as one handler but several URL variants.
URL-less overrides inherit their pattern from the superclass and declare 0.

| Category | Controller class (file) | Handlers / URLs |
|----------|-------------------------|-----------------|
| Public site: pages, sitemap/robots, lang, search, editor, theme, SEO, snippets, server actions, translation | `Website` (main.py) | 46 / 53 |
| Backend dashboard + new content | `WebsiteBackend` (backend.py) | 4 / 4 |
| Form-builder submission | `WebsiteForm` (form.py) | 2 / 2 |
| Generic model-page rendering | `ModelPageController` (model_page.py) | 1 / 3 |
| Website-scoped asset serving | `WebsiteBinary` (binary.py) | 1 / 1 |
| Asset bundle (website_id context) | `WebsiteWebClient` (webclient.py) | 1 / 0 (inherited) |
| Logout (public auth) | `WebsiteSession` (main.py) | 1 / 0 (inherited) |
| Back-compat image routes | `WebsiteBinary` (main.py) | 1 / 7 |
| **Total** | **8 controller classes across 8 files** | **57 handlers / 70 URL variants** |

Of the 57 handlers, **3 are URL-less overrides** (`WebsiteWebClient.bundle`,
`Website.web_login`, `WebsiteSession.logout`) inheriting their URL from the
superclass route. Type split: **24 HTTP / 33 JSONRPC** (`type="jsonrpc"`) = 57.
