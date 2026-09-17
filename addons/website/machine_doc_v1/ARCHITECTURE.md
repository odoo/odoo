# Website Module Architecture

High-level structure, data flow, and runtime organization for
`addons/odoo/addons/website/`.

> **See also**: `INTERACTIONS.md` — the public-site Interaction framework
> lifecycle (the website analog of web's STATE_MANAGEMENT). `DIRECTORY_MAP.md` —
> all 142 `static/src` directories mapped to subsystem + responsibility.
> `MODEL_MAP.md`, `ROUTE_MAP.md`, `CONVENTIONS.md`, `TEST_TAGS.md`.

## Module Identity

- **Name:** Website ("Enterprise website builder")
- **Technical name:** `website`
- **Category:** Website/Website
- **Depends:** `digest`, `social_media`, `google_recaptcha`, `utm`, `html_builder`
- **External deps:** `geoip2` (python) — for visitor geolocation
- **Role:** The multi-website CMS: public-facing rendered pages + the in-browser page builder/editor

Unlike `web` (the backend webclient), `website` is fundamentally a **public
HTTP-rendered site** (server-side QWeb) with a **layered in-browser editor**. Two
concerns dominate the whole module: **multi-website scoping** and the
**generic-vs-specific (COW) content model**.

## Two Runtimes

The single most important structural fact: website ships **two independent JS
runtimes**, kept in separate asset bundles.

```
┌──────────────────────────────────────────────────────────────────────┐
│  PUBLIC-SITE RUNTIME  (web.assets_frontend)                           │
│  Server renders QWeb HTML → browser runs Interactions over the DOM    │
│                                                                       │
│  interactions/**  core/**  js/content/**  snippets/**/*.js  utils/**  │
│  · Interaction base class (@web/public/interaction)                   │
│  · Colibri engine + "public.interactions" service scan the DOM        │
│  · legacy PublicRoot / publicWidget layer still active                │
│  ( *.edit.js REMOVED from this bundle )                               │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│  BACKEND / EDITOR RUNTIME  (web.assets_backend + editor bundles)      │
│  OWL client action hosts the site in an <iframe> and edits it         │
│                                                                       │
│  client_actions/website_preview/**   builder/**   components/**       │
│  services/**   systray_items (SCSS)                                   │
│  · WebsiteBuilderClientAction = the "website_preview" client action   │
│  · builder/ extends the html_builder editor with website plugins      │
│  · edit-mode interaction variants (*.edit.js) re-injected into the    │
│    iframe via website.assets_inside_builder_iframe                    │
└──────────────────────────────────────────────────────────────────────┘
```

The editor **reuses the public runtime**: it loads the real frontend inside an
iframe, then layers edit behavior on top. `*.edit.js` files register mixins into
`public.interactions.edit`; `core/website_edit_service.js` walks each
interaction's prototype chain and applies the mixins to produce an *editable*
version. The manifest strips `*.edit.*` from `web.assets_frontend` and re-adds
them (plus `website_edit_service.js`) only inside
`website.assets_inside_builder_iframe`.

## Request Flow — Serving a Public Page

```
Browser GET /some/page
   │
   v
ir.http._dispatch  (models/ir_http.py — website=True routes)
   │  _frontend_pre_dispatch: resolve website, company, lang, tz, editor ctx
   │  _pre_dispatch: can_access_from_current_website → 404/403
   v
Route match / _serve_fallback
   ├─ website.rewrite hit? → _serve_redirect (301/302/308/404)
   └─ website.page hit?    → _serve_page
                              │
                              v
                     website.page._get_response
                       │  full-page response cache (ormcache),
                       │  keyed by website/lang/path/debug/cookie-consent
                       v
                     ir.qweb render (models/ir_qweb.py)
                       │  _prepare_frontend_environment
                       │  _post_processing_att:
                       │    · url_for / CDN rewriting
                       │    · <img> lazy-load
                       │    · third-party COOKIE BARRIER (src→about:blank
                       │      until consent) — GDPR
                       v
                     HTML response
   │
   v
_post_dispatch → _register_website_track  (visitor analytics, 200 GET, non-bot)
   │
   v
Browser: public.interactions service scans DOM, starts matching Interactions
```

## Content Model — Generic vs Specific (COW)

Website content (`ir.ui.view`, `ir.asset`, `website.page`, `website.menu`) exists
in two forms:

- **Generic** — `website_id = False`. Shipped by modules/themes, shared by all websites.
- **Specific** — `website_id = <id>`. A per-website override.

Editing a generic record under a `website_id` context does **not** mutate it —
**COW (Copy-On-Write)** copies it into a specific record first. Deleting a generic
record triggers **COU (Copy-On-Unlink)**: specific copies are created for the
*other* websites so only the current one loses it. The engine is in
`models/ir_ui_view.py` (`write`/`unlink`). `website_domain()` =
`["website_id", "in", [False, *ids]]` is the "generic OR mine" filter used
everywhere records are read, and `_filtered_most_specific()` narrows a recordset
to one record per key, preferring the specific one. This is the website analog of the web module's
state-architecture complexity — get it wrong and one website's edits leak into
another.

## Themes

Themes are ordinary modules that ship data as `theme.*` **staging** records
(`theme.ir.ui.view`, `theme.ir.asset`, `theme.ir.attachment`,
`theme.website.page`, `theme.website.menu`). On install/upgrade,
`ir.module.module` (`models/ir_module_module.py` — the theme engine) copies each
staging record into real, website-specific base records (tracked by `copy_ids` /
`theme_template_id`). `theme.utils` provides COW-aware `enable/disable_view` /
`enable/disable_asset` toggles used by theme customization.

## Directory Structure

Top-level layout (detailed maps are separate docs):

| Path | Contents | Map |
|------|----------|-----|
| `controllers/` | 9 `.py` — 8 Controller classes, with the SEO and theme routes as mixins of `Website` in `seo.py` and `theme.py` (public pages, sitemap, form builder, model pages, dashboard) | `ROUTE_MAP.md` |
| `models/` | 45 `.py` — 63 model classes (website, mixins, pages/menus, framework extensions, themes, visitors) | `MODEL_MAP.md` |
| `wizards/` | 4 `.py` + XML — transient wizards (robots, blocked domains, language install, portal) | `MODEL_MAP.md` |
| `static/src/` | 348 JS across 142 directories (two runtimes) | `DIRECTORY_MAP.md` |
| `static/tests/` | 225 `.js` (HOOT suites + 86 tours) | `TEST_TAGS.md` |
| `tests/` | 51 Python test files | `TEST_TAGS.md` |
| `views/` · `data/` · `security/` · `i18n/` | QWeb templates, ~66 `s_*` snippet templates, fixtures, ACLs, translations | — |
| `doc/` | `website.snippet.rst` (snippet authoring guide) | — |

## JavaScript Architecture

Layered organization under `static/src/`. See `DIRECTORY_MAP.md` for the full
per-directory table.

| Layer | Directory | Runtime | Purpose |
|-------|-----------|---------|---------|
| **Interactions** | `interactions/` | public | DOM-bound public-site controllers (headers, popups, carousels, cookies, scroll, anchors, lazy-load). Registered in `public.interactions`. |
| **Frontend core** | `core/` | public | Frontend services (`website_menus`, `website_page`, `website_cookies`, `website_map`) + the edit-mode bridge (`website_edit_service.js`). |
| **Legacy content** | `js/content/` | public | `WebsiteRoot` (extends legacy `PublicRoot`), `snippets.animation.js` (edit-mode over `publicWidget.Widget`), early-boot DOM helpers. |
| **Snippets** | `snippets/` | public | Per-snippet public JS (Interaction or public widget) + `.edit.js` variants; ~66 `s_*` dirs, most SCSS/XML-only. |
| **Builder** | `builder/` | editor | Extends the `html_builder` editor: `WebsiteBuilder` + website `Plugin`s + snippet-option `BaseOptionComponent`s. |
| **Client actions** | `client_actions/` | backend | `website_preview` (the iframe-hosting editor client action), dashboard, configurator. |
| **Components** | `components/` | backend | Editor dialogs (add-page, edit-menu, SEO, page-properties), backend fields, page/theme views, media/resource editors, loaders. |
| **Services** | `services/` | backend | `website_service.js` (reactive backend state), `website_custom_menus.js`. |
| **Common** | `common/` | both | Mail `Record` models (`Website`, `WebsiteVisitor`) shared public + backend. |
| **Utils** | `utils/`, `js/` | both | `google_maps.js` (shared public/editor API loader), `images.js`, `videos.js`, `misc.js` (EventBus, UTM); `text_processing.js`, `highlight_utils.js`, `http_cookie.js`. |

## Asset Bundles

Defined in `__manifest__.py`. The split is **frontend (public) vs editor
(wysiwyg/builder) vs backend (webclient)**.

### Public Frontend
| Bundle | Contents |
|--------|----------|
| `web.assets_frontend` | The visitor site. Globs `interactions/**`, `core/**`, `utils/**`, `snippets/**/*.js`, then **removes** `interactions/**/*.edit.js` and `snippets/**/*.edit.js` (the only two `.edit.js`-bearing dirs); also removes `multirange_input.js`, `ripple_effect.js` (on-demand) and `core/website_edit_service.js`. **Replaces** the framework's `public_root_instance.js` with website's `website_root_instance.js`. |
| `web.assets_frontend_minimal` | Early-boot subset: `misc.js`, `inject_dom.js`, `auto_hide_menu.js`, `redirect.js`, `adapt_content.js`, `generate_video_iframe.js`. |
| `web.assets_frontend_lazy` | Removes the minimal subset (loaded later instead). |
| `mail.assets_public` | `**/common/**/*` (shared record models). |

### Editor / Builder
| Bundle | Contents |
|--------|----------|
| `website.assets_inside_builder_iframe` | Includes `html_builder.assets_inside_builder_iframe`; adds all `**/*.edit.*` + `core/website_edit_service.js`. Re-injects edit-mode interactions into the preview iframe. |
| `website.website_builder_assets` | Includes `html_builder.assets`; adds `builder/**/*` (minus `*.edit.*`) — the builder UI. |
| `website.assets_wysiwyg` / `website.assets_all_wysiwyg` | Legacy wysiwyg helpers, edit-mode SCSS, form/cookies-bar XML. |
| `website.assets_editor` | Editor chrome loaded into the backend (folded into `web.assets_backend`): resource editor, dialogs, navbar, burger menu, systray SCSS, client-action XML, `js/backend/**`. |

### Backend
| Bundle | Contents |
|--------|----------|
| `web.assets_backend` | **Includes** `website.assets_editor` + `html_editor.assets_link_popover`; adds backend SCSS, `client_actions/*/*` (minus test-mode), backend fields/views, `services/website_service.js`, `common/**`. |
| `web.assets_web_dark` | Dark-mode SCSS overrides. |

### Tests
| Bundle | Contents |
|--------|----------|
| `web.assets_tests` | Tour tests + `website_builder_action_test_mode.js`. |
| `web.assets_unit_tests[_setup]` | HOOT harness pulling `core/**`, `utils/**`, `interactions/**`, `snippets/**`, builder tests, mock server. |

> `dynamic_children` wires `website.assets_inside_builder_iframe` +
> `website.website_builder_assets` into `web.assets_web` on demand (loaded only
> when the editor opens, not on every backend page).

## SCSS Variable Injection

Website injects into the framework's shared SCSS variable bundles so themes can
recolor the whole UI:
- `web._assets_primary_variables` ← `primary_variables.scss`, `options/user_values.scss`, and the user color palettes (`user_color_palette`, `user_gray_color_palette`, `user_theme_color_palette`).
- `web._assets_secondary_variables` ← (prepend) `secondary_variables.scss`.
- `web._assets_frontend_helpers` ← (prepend) `bootstrap_overridden.scss`.

## File Counts

| Category | Count |
|----------|-------|
| Python (controllers) | 9 files (8 Controller classes; `__init__.py` has no routes) |
| Python (models) | 45 files (63 model classes) |
| Python (wizard) | 4 `.py` + XML |
| Python (tests) | 51 |
| JavaScript (src) | 348 across 142 directories |
| JavaScript (`.edit.js` variants) | 32 |
| JavaScript (tests) | 225 (incl. 86 tours) |
| SCSS | 153 |
| Snippet template dirs (`s_*`) | 66 |
| Route handlers / URL variants | 57 / 70 |
