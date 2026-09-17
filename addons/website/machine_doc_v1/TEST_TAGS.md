# Website Module Test Tags

Quick reference for running targeted subsets of `website`'s tests. Two surfaces:
**Python** (`tests/`, 51 `.py` files = 50 test modules incl. `common.py`, + `__init__.py`)
run through `odoo-bin`; **JS/HOOT + tours** (`static/tests/`, 225 `.js`) run in
the browser test runner.

> Unlike the `web` module, website does **not** define a rich `web_*`-style tag
> taxonomy. The whole tree carries only the standard `post_install` /
> `-at_install` phase pair plus **three** custom tags. Select suites by the
> module filter (`/website`) or by class/method, not by topic tag.

## Custom Tags (the only three)

| Tag | File(s) | Scope |
|-----|---------|-------|
| `website_snippets` | `test_snippets.py` (`TestSnippets`) | Large snippet drag/drop + editing tour suite |
| `website_visitor` | `test_website_visitor.py` (`WebsiteVisitorTestsCommon`) | Visitor tracking / dedup / analytics |
| `is_query_count` | `test_website_visitor.py` (`WebsiteVisitorTestsCommon`) | Query-count regression assertions (expensive) |

Everything else is selected via the implicit module tag `website` (from the
module path) + the standard phase tags.

## Test Base Classes

| Base class | Used for |
|------------|----------|
| `TransactionCase` / `BaseCase` | Pure-Python model/unit tests (rolled-back transaction). |
| `HttpCase` | HTTP server tests (`url_open`) **and** browser tours (`start_tour`). |
| `HttpCaseWithUserDemo` / `HttpCaseWithUserPortal` | HttpCase pre-seeded with the demo / portal user. |
| `HttpCaseWithWebsiteUser` (`tests/common.py`) | HttpCase with a **restricted-editor** website user ("Rafe Restricted") — the shared base for editor-permission tours. |

Tours run inside `HttpCase` suites via `start_tour(...)`; they drive a headless
browser executing a tour defined under `static/tests/tours/`. **`browser_js` is
used nowhere** — all browser interaction goes through `start_tour`.

## Test File → Scope

| File | Base class(es) | Scope |
|------|----------------|-------|
| `test_assets.py` | HttpCase | Website/web asset bundle generation + serving |
| `test_attachment.py` | HttpCase | ir.attachment handling (tour `drop_404_ir_attachment_url`) |
| `test_audit_regressions.py` | TransactionCase ×7 | Regression audit: host header, template-cache invalidation, menu unlink fan-out, multi-website page scoping, form IntegrityError, visitor page search, custom-asset isolation |
| `test_auth_signup_uninvited.py` | TransactionCase | Uninvited-signup auth behaviour |
| `test_base_url.py` | HttpCase / TransactionCase | `get_base_url` resolution per website |
| `test_client_action.py` | HttpCaseWithWebsiteUser | Backend→frontend editor client action (tours) |
| `test_configurator.py` | HttpCase | Configurator wizard + translation (tours) |
| `test_controllers.py` | HttpCase | Controller routing / responses |
| `test_converter.py` | BaseCase | slug/unslug + title→slug pure-python helpers |
| `test_crawl.py` | HttpCaseWithUserDemo | Crawls the CMS; asserts internal links return 200 |
| `test_custom_snippets.py` | TransactionCase / HttpCase | User-saved custom snippets (tours) |
| `test_disable_unused_snippets_assets.py` | TransactionCase | Unused snippet assets pruned |
| `test_fuzzy.py` | TransactionCase | Fuzzy search + autocomplete backend |
| `test_get_current_website.py` | HttpCaseWithUserDemo | `_get_current_website` resolution |
| `test_grid_layout.py` | HttpCase | Grid layout snippet (tour `grid_layout`) |
| `test_http_endpoint.py` | HttpCase | HTTP endpoint registration/serving |
| `test_iap.py` | HttpCase | IAP integration endpoints |
| `test_import_files.py` | TransactionCase | Import of website files/assets |
| `test_ir_asset.py` | HttpCase | ir.asset records for website bundles |
| `test_lang_url.py` | HttpCase | Language-prefixed URLs + controller redirects |
| `test_menu.py` | TransactionCase / HttpCase | Menu CRUD (tours `edit_menus`, `edit_megamenu`) |
| `test_multi_website.py` | HttpCase | Multi-website switching / isolation |
| `test_page.py` | TransactionCase / HttpCase | Page model CRUD / new-page creation |
| `test_page_manager.py` | HttpCase | Page manager UI (tour `page_manager`) |
| `test_performance.py` | HttpCaseWithUserPortal/Demo | Query-count / render performance benchmarks |
| `test_qweb.py` | TransactionCase(WithUserDemo) | QWeb rendering, attribute processing, data-snippet |
| `test_redirect.py` | TransactionCase / HttpCase | `website.rewrite` / 301–308 redirects + serving |
| `test_res_users.py` | TransactionCase | res.users website-specific behaviour |
| `test_sitemap.py` | TransactionCase / HttpCase | sitemap.xml generation + host handling |
| `test_res_lang.py` | TransactionCase | Language deactivation guard: refused for a user, open to the superuser |
| `test_skip_website_configurator.py` | HttpCase (TestConfiguratorCommon) | Skip configurator → automatic editor (tour) |
| `test_snippet_filter.py` | TransactionCase | Dynamic-snippet filter **security** (ACL) |
| `test_snippets.py` | HttpCase | Snippet drag/drop + editing (tag `website_snippets`, many tours) |
| `test_theme.py` | TransactionCase | Theme install/switch model logic |
| `test_ui.py` | HttpCase(WithUserDemo/WebsiteUser) | End-to-end UI: theme customize, HTML editor, translate, restricted editor (many tours) |
| `test_unsplash_beacon.py` | HttpCase | Unsplash beacon tracking (tour) |
| `test_views.py` | TransactionCase / HttpCase | View saving / **COW** per website, customization, theme views, crawler |
| `test_views_inherit_module_update.py` | (module-update helper) | View inheritance survives module update |
| `test_website_favicon.py` | TransactionCase | Favicon handling |
| `test_website_form_editor.py` | HttpCaseWithUserPortal / TransactionCase | Form builder editor + form model (tours) |
| `test_website_reset_password.py` | HttpCase | Frontend password reset (tour) |
| `test_website_technical_page.py` | TransactionCase | Technical (non-published) page behaviour |
| `test_website_visitor.py` | BaseCase / HttpCaseWithUserDemo / HttpCase | Visitor tracking, dedup, query counts (tags `website_visitor`, `is_query_count`) |
| `test_website_website_builder_assets_bundle.py` | HttpCase | website_builder assets bundle loads |

**Tour-driven files (12):** `test_attachment`, `test_client_action`,
`test_configurator`, `test_custom_snippets`, `test_grid_layout`,
`test_page_manager`, `test_skip_website_configurator`, `test_snippets`,
`test_ui`, `test_unsplash_beacon`, `test_website_form_editor`,
`test_website_reset_password`.

## JS / HOOT & Tours (`static/tests/`)

225 `.js` files. Tour *definitions* live under `static/tests/tours/` (86 files)
and are registered into `registry.category("web_tour.tours")`, then launched by
the Python `start_tour` calls above. HOOT suites (`*.test.js`) run in the JS test
runner (`/web/tests`), not via `--test-tags`.

| Area | Files | Tests |
|------|------:|-------|
| `tours/` | 86 | Interactive tour definitions (snippets, editor, configurator, form builder, navigation, …) |
| `builder/` (+ `options/`, `theme_tab/`, `website_builder/`, `custom_tab/`) | 72 | Website builder/editor OWL: actions, overlay, drag-drop, snippet options, per-snippet option panels |
| `interactions/` (+ carousel/cookies/dropdown/header/popup/snippets) | 50 | Public-site Interactions (frontend behaviors + `.edit.` variants) |
| `mock_server/` (+ `mock_models/`) | 3 | HOOT mock models for `website` / `website.visitor` + livechat data patch |
| `core/` | 3 | `interaction_util`, `public_component_edit`, `website_map_service` |
| root (`helpers.js`, field/systray tests) | 4 | Shared helpers + new-content systray, page_url field, redirect field |

## Running Tests

```bash
VENV=venv/p314o19marin/bin/python
CONF=config/p314o19marin.conf

# All website tests during (re)install — coexist with a running server via --no-http:
$VENV addons/odoo/odoo-bin -c $CONF -d <db> -u website --test-enable --no-http --stop-after-init

# By module tag (slash-prefixed = module name):
$VENV addons/odoo/odoo-bin -c $CONF -d <db> --test-tags /website --no-http --stop-after-init

# A single custom-tagged suite:
$VENV addons/odoo/odoo-bin -c $CONF -d <db> --test-tags website_snippets --no-http --stop-after-init
$VENV addons/odoo/odoo-bin -c $CONF -d <db> --test-tags website_visitor  --no-http --stop-after-init

# Exclude the expensive query-count checks:
$VENV addons/odoo/odoo-bin -c $CONF -d <db> --test-tags /website,-is_query_count --no-http --stop-after-init

# One class / method:
$VENV addons/odoo/odoo-bin -c $CONF -d <db> --test-tags /website:TestUi.test_replace_media --no-http --stop-after-init
```

> Give each concurrent run its own `-d <db>` (tours + COW writes fight over
> shared state). Keep `--no-http` unless you need to watch the browser.
