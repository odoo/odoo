# Web Module Test Tags

Quick reference for running targeted subsets of `core/addons/web/tests/`.

## By Speed/Type

| Tag | Type | Tests | Time |
|-----|------|-------|------|
| `web_unit` | TransactionCase (pure Python) | ~34 | ~30s |
| `web_http` | HttpCase (url_open, no browser) | ~50 | ~5 min |
| `web_tour` | HttpCase (start_tour/browser_js) | ~5 | ~2 min |
| `web_js` | Full JS suites (HOOT/QUnit) | ~34 | ~1-2 hr |
| `web_perf` | Query count regression (@warmup) | ~16 | ~2 min |
| `web_benchmark` | Statistical timing (run_benchmark) | ~8 | ~5 min |
| `click_all` | Click-everywhere (-standard) | ~4 | ~1+ hr |

## Granular JS Tests (web_js)

`WebSuite` (desktop) and `MobileWebSuite` (mobile) each have granular test methods
that target specific hoot suite groups via `&id=HASH` URL filters. Use `--test-tags`
to run individual groups instead of the full 1-2 hour suite.

| Method | Hoot suite(s) | Scope |
|--------|---------------|-------|
| `test_core` | `@web/core` | utils, registries, RPC, ORM, domain |
| `test_calendar` | `@web/views/calendar` | calendar view |
| `test_fields` | `@web/views/fields` | field widgets (suite path from `tests/views/fields/`, source at `@web/fields/`) |
| `test_form` | `@web/views/form` | form view |
| `test_kanban` | `@web/views/kanban` | kanban view |
| `test_list` | `@web/views/list` | list view |
| `test_graph_pivot` | `@web/views/graph`, `pivot_view`, `view_components`, `view_dialogs`, `widgets`, root view files | graph, pivot, misc view utilities |
| `test_search` | `@web/search` | search bar, filters, groupby |
| `test_webclient` | `@web/webclient` | action manager, navbar, settings |
| `test_public` | `@web/public` | public page components |
| `test_html_editor` | `@html_editor` | rich text editor |
| `test_misc` | `@web/env`, `@web/reactivity`, `@web/t_custom_click` | root-level test files |

```bash
# Single group — desktop only (~30s-2min)
--test-tags '/web:WebSuite.test_calendar' -u web

# Single group — mobile only
--test-tags '/web:MobileWebSuite.test_calendar' -u web

# Multiple groups — both platforms
--test-tags '/web:WebSuite.test_calendar,/web:WebSuite.test_form,/web:MobileWebSuite.test_calendar' -u web

# html_editor desktop
--test-tags '/web:WebSuite.test_html_editor' -u web

# Full suite (existing behavior)
--test-tags 'web_js/web' -u web
```

## By Topic

| Tag | Files | Scope |
|-----|-------|-------|
| `web_action` | test_action | Breadcrumb loading |
| `web_assets` | test_assets | Bundle generation, asset cursors |
| `web_db` | test_db_manager | Database manager UI |
| `web_domain` | test_domain | Domain validation endpoint |
| `web_favorite` | test_favorite | Favorite management tour |
| `web_health` | test_health | /web/health endpoint |
| `web_image` | test_image | Image serving, resize, access tokens |
| `web_layout` | test_base_document_layout | Document layout colors/logo |
| `web_login` | test_login | Login flow, user switching |
| `web_manifest` | test_webmanifest | PWA manifest routes |
| `web_menu` | test_load_menus, test_perf_load_menu | Menu loading + perf |
| `web_model` | test_ir_model | Model access, field creation |
| `web_partner` | test_partner | Partner access, vCard export |
| `web_pivot` | test_pivot_export | Pivot XLSX export |
| `web_profiler` | test_profiler | Profiling enable/disable |
| `web_properties` | test_res_partner_properties | Properties base definition |
| `web_qweb` | test_ir_qweb | QWeb image field rendering |
| `web_redirect` | test_web_redirect | URL redirect handling |
| `web_report` | test_reports | PDF report session/cookies |
| `web_router` | test_router | Action routing/resolution |
| `web_search` | test_web_search_read | web_search_read, web_name_search |
| `web_session` | test_session_info | Session info endpoint perf |
| `web_translate` | test_translate | Translation overrides |
| `web_users` | test_res_users, test_res_users_settings | User settings, name_search |

## Examples

```bash
# Fast feedback (~30s)
--test-tags='web_unit/web' -u web

# Single topic
--test-tags='web_image' -u web

# Multiple topics
--test-tags='web_image,web_login' -u web

# All HTTP tests (~5 min)
--test-tags='web_http/web' -u web

# Everything except slow JS/tours
--test-tags='/web,-web_js,-web_tour,-click_all'

# Only perf regression
--test-tags='web_perf' -u web

# Full suite (nightly)
--test-tags='*/web' -u web
```
