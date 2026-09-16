# Website Module Conventions

Module-specific patterns, rules, and gotchas for working in
`addons/odoo/addons/website/`.

> **See also**: `ARCHITECTURE.md` (two-runtime split, request flow),
> `INTERACTIONS.md` (public-site Interaction framework), `MODEL_MAP.md`,
> `ROUTE_MAP.md`, `TEST_TAGS.md`. Framework-wide rules live in the web module's
> `machine_doc_v1/` and `doc/coding_guidelines.rst`.

## Multi-Website is the Ambient Concern

Almost every model, route, and cache in this module is website-scoped. Three
primitives recur:

- **`website_domain()`** = `["website_id", "in", [False, *ids]]` — the "generic
  OR mine" filter. Read website records through it (or through helpers that apply
  it) — a bare search leaks other websites' records.
- **`website.get_current_website()`** — resolves the active website from the
  request/domain. `_force_website(id)` pins one in session (used by
  `/website/force/<id>`).
- **`_filtered_most_specific(website_id)`** — narrows a recordset to one record per
  key, preferring the specific one when both a generic and a specific version match.

## COW / COU — the Generic-vs-Specific Content Model

Content records (`ir.ui.view`, `ir.asset`, `website.page`, `website.menu`) exist
as **generic** (`website_id = False`, shared) or **specific**
(`website_id = <id>`, per-website override).

- **COW (Copy-On-Write)** — writing to a generic record under a `website_id`
  context copies it to a specific record first, then writes the copy. The generic
  is never mutated. Engine: `models/ir_ui_view.py` `write`.
- **COU (Copy-On-Unlink)** — deleting a generic record creates specific copies
  for the *other* websites, so only the current one loses it. Engine:
  `ir_ui_view.py` `unlink`.

**Gotcha:** bypassing COW (context key `no_cow`) mutates the shared generic
record for *every* website. Only do it deliberately (e.g. theme updates that
must touch the template). `test_views.py::TestCowViewSaving` guards this.

## Controller Route Conventions

Public website routes are declared with a distinct kwarg set (full detail in
`ROUTE_MAP.md`):

| Kwarg | Meaning |
|-------|---------|
| `website=True` | Bind the request to the current `website` record → frontend layout, `request.website`, multi-website filtering. Almost all public routes set it. |
| `multilang=False` | Suppress the `/<lang>/` URL prefix. For machine endpoints (`/robots.txt`, `/sitemap.xml`, `/website/lang/...`, image back-compat). |
| `sitemap=True` / `<callable>` / `False` | Sitemap inclusion. A callable is a generator `f(env, rule, qs)` yielding `{"loc": ...}`. |
| `csrf=False` | Cross-origin form POST (`/website/form/...`). |
| `captcha="website_form"` | reCAPTCHA on form-builder submission. |
| `readonly=True` | Route to a read replica (same meaning as web: NOT about permissions — a `readonly` route that writes corrupts replicated data). |

- **Auth:** public routes use `auth="public"` (works with or without session, via
  the per-website public user). Editor RPCs use `auth="user"` and additionally
  gate on `group_website_restricted_editor` / designer groups inside the handler.
- **`type="jsonrpc"`**, not the legacy `"json"` (this fork's JSON-RPC type
  string). HTTP routes without `methods=[...]` accept all methods.
- **URL-less overrides** (`bundle`, `web_login`, `logout`) inherit the parent
  route's URL — they only re-decorate to change one kwarg (e.g. `auth="public"`).

## Published / SEO / Searchable Mixins

Making a model publishable on the website is done by inheriting mixins
(`models/mixins.py`), not by hand-rolling fields:

- **`mixin.website.published`** → `is_published`, `can_publish`, `website_url`. Override `website_url` per model. `create`/`write` raise `AccessError` if publishing without `can_publish` (which routes through `website._check_access_to_modify`).
- **`mixin.website.published.multi`** → the above + `website_id`-context-aware publish state (a record bound to another website reads unpublished). Use this, not the plain published mixin, for multi-website-scoped content.
- **`mixin.website.seo.metadata`** → `website_meta_*` fields. Override `_get_default_website_meta()` to set defaults; call `get_website_meta()` (never override it).
- **`mixin.website.searchable`** → override `_search_get_detail()` (returns model/base_domain/search_fields/fetch_fields/mapping/icon) to appear in frontend fuzzy search.

## Interaction & Builder Registration

The public site and the editor use distinct registries (see `INTERACTIONS.md` and
`ARCHITECTURE.md`):

| Concern | Registry | File pattern |
|---------|----------|--------------|
| Public-site behavior | `public.interactions` | `interactions/*.js`, `snippets/*/*.js` |
| Edit-mode variant of an interaction | `public.interactions.edit` | `*.edit.js` (mixin `{Interaction, mixin}`) |
| Edit support for a public OWL component | `public_components.edit` | `core/component_interaction_edit.js` |
| Editor snippet-option UI | `builder_options` / `builder_actions` resources | `builder/plugins/options/**` |
| Editor page-level plugin | (html_builder `Plugin` resources) | `builder/plugins/*.js` |
| Frontend tour | `web_tour.tours` | `static/tests/tours/*.js` |

- **Interaction hygiene:** `selector` MUST be a static class property;
  `dynamicContent` MUST be an instance property — otherwise the service rejects
  that interaction's startup (logged, non-fatal; it does not throw or abort the
  rest of the scan).
- **Snippet options** pair a `BaseOptionComponent` (`static template`, `static
  selector`, `static applyTo`) with a `*_option_plugin.js` that registers it into
  `builder_options` at a `withSequence(...)` priority.

## Debug Loggers (quality campaign, medium-term)

Website's JS carries `makeLogger` sites from `@web/core/debug/debug_logger` on the four
campaign channels (logic, perf, pipeline, lifecycle). They are off by default: turn them on
with `odooLog.enable("website.*")` in the console, or with `?log=website.builder.*:perf` in the URL.
Frozen at odoo `a7145e8f8265`: 1,883 sites in 270 files. Re-measure before quoting a count.

| Namespace | Code |
|-----------|------|
| `website.builder.plugin.<static id>` | builder plugins |
| `website.builder.option.<name>` | option components |
| `website.builder.translation.<name>` | translation plugins and components |
| `website.interaction.<name>[.edit\|.preview]` | public interactions |
| `website.snippet.<s_name>[.edit]` | snippet JS; `website.form` and `website.dynamic_snippet` keep their older names |
| `website.dialog.*`, `.component.*`, `.field.*`, `.view.*`, `.client_action.*`, `.systray.*` | backend UI |
| `website.service.*`, `website.edit`, `website.content.*`, `website.utils.*` | services, edit service, `js/` helpers |

- **Sites are removed mechanically when the campaign ends, so the shape is fixed.** Allowed
  forms: the imports; a module-level `const log = makeLogger(...)`; `useLifecycleLog(log);`;
  `log.logic|pipeline|lifecycle(...);`; `const endX = log.perf(...)` plus `endX(...)`. No
  `log.measure`, and no site that is the only statement of its block.
- **Never add a method just to host a log.** `BuilderAction.has()` compares prototypes, so an
  added `load`, `prepare` or `clean` changes what the builder runs.
- **Payloads are lazy arrows, so a broken payload only fails with logging on.** A
  logging-off run cannot catch one. The campaign caught a payload reading a `const` above its
  declaration only by running the website HOOT suites with `&log=website.*`.
- The minimal frontend bundle inlines its own copy of the logger. The logger keeps its state
  on `window` so every copy shares one spec and one `odooLog`; keep it that way.

## Snippet File Convention

A snippet is an asset folder `snippets/s_<name>/` mixing:
- QWeb templates (`s_<name>.xml`, registered as `ir.ui.view` templates and declared in `__manifest__.py` `data`),
- SCSS (`s_<name>/000.scss`, `*.preview.scss` for the add-dialog preview),
- optional public JS: `s_<name>.js` (an Interaction / public widget) + `s_<name>.edit.js` (edit variant).

Most of the 66 `s_*` directories are template/SCSS-only. When a snippet needs
runtime behavior, add the `.js` (register in `public.interactions`) and, if it
behaves differently in the editor, a `.edit.js` mixin. See
`doc/website.snippet.rst` for snippet authoring.

## The Full-Page Response Cache

`website.page._get_response` caches rendered public pages
(ormcache `"templates.cached_values"`). The cache key
(`_get_cache_key`) includes website / lang / path / debug / **cookie-consent
state**. Two consequences:

- A page is only cacheable when `_is_cache_usable` holds: **GET, no query
  params, public user, no group restriction**. Anything else renders live.
- The cookie-consent component of the key is load-bearing: it prevents a
  consenter's third-party embeds from leaking into a refuser's cached page.
- `_post_process_response_from_cache` rewrites the CSRF token and stamps
  `_cached_page`/`_cached_view_id` so visitor tracking still fires on cache hits.
- Writes to `website.page` that touch only `_NON_RENDERING_FIELDS`
  (`view_write_uid`, `view_write_date`) skip cache invalidation. Menu changes
  clear `"templates"`; routing/rewrite changes clear `"routing"`.

## The Cookie Barrier (GDPR)

`ir_qweb.py::_post_processing_att` rewrites third-party iframe/script `src` to
`about:blank` + `data-nocookie-src` until the visitor grants consent
(`ir_http._is_allowed_cookie`, driven by the `website_cookies_bar` cookie).

**Gotcha:** static nodes never honor the per-request debug bypass — this is
deliberate GDPR safety. `data-no-post-process` opts a node out. Don't "simplify"
this away; it's tested (`test_qweb.py::TestQwebProcessAtt`).

## Form Builder Security

The form builder (`/website/form/<model>`, `controllers/form.py` +
`website_form.py`) is a public write endpoint — its guards are load-bearing:

- A model is form-writable only if `ir.model.website_form_access = True`.
- Fields are **blacklisted by default** (`ir.model.fields.website_form_blacklisted`,
  SQL default true); `formbuilder_whitelist()` (designer-gated) opts fields in.
- `mail.mail` submissions require a valid HMAC `website_form_signature` before
  `.send()` — the anti-open-relay guard. Don't route mail through the form path
  without it.
- `get_authorized_fields()` leaks field metadata and is **designer-gated** for
  that reason.

## Dynamic Snippet Filter Security

`website.snippet.filter._prepare_values`: a client-supplied `search_domain`'s
leaves must reference **direct fields only** (no dotted paths) — otherwise a
crafted domain could leak unpublished related records. The single-record path
(`limit == 1` + `res_id`) applies the same publication/record-rule scoping as the
multi path, so a supplied id can't bypass publication.

## Visitor Tracking — UTC-Explicit SQL

`website_visitor.py` uses raw SQL (`INSERT ... ON CONFLICT` upsert,
`FOR NO KEY UPDATE SKIP LOCKED`) with **UTC-explicit** timestamps
(`now() at time zone 'UTC'`). This matches the fork's process-wide `TZ=UTC`
pinning — comparing against a naive local `now()` would drift. Keep new
visitor-datetime SQL UTC-explicit.

## Themes are Staging Data

Theme modules ship `theme.*` records that are **copied** into real
website-specific records on install (`ir_module_module.py` engine, tracked via
`copy_ids` / `theme_template_id`). Don't expect a theme's `theme.ir.ui.view` to
be the live view — the live view is its base-model copy. Toggle theme
views/assets through `theme.utils.enable/disable_view` / `_asset` (COW-aware),
not by writing `active` directly.

## Model Extension Pattern

Grouped by concern, matching the web module's convention:
- `ir_*.py` extend framework models (`ir.http` = dispatch, `ir.qweb` = rendering, `ir.ui.view` = COW, `ir.asset`/`ir.attachment`/`ir.binary` = assets).
- `res_*.py` extend user/company/partner/lang for website scoping.
- `website_*.py` are the module's own models (page, menu, rewrite, visitor, snippet_filter, form).
- `mixins.py` holds the abstract mixins other modules inherit.
- `theme_models.py` holds the `theme.*` staging models.

## Py 3.14 Note (PEP 758)

`mixins.py`, `website_form.py`, and others use the **bracketless** multi-exception
form (`except ValueError, TypeError:` with no `as`). This is valid on Python 3.14
and enforced by `ruff` — do **not** "fix" it back to `except (A, B):` (it causes a
lint loop). See the workspace CLAUDE.md.

## Gotchas

1. **Two runtimes, one codebase.** A file under `interactions/`, `core/`,
   `snippets/*.js`, or `js/content/` ships to visitors (`web.assets_frontend`);
   a file under `builder/`, `client_actions/`, `components/`, `services/` ships
   to the backend editor. `*.edit.js` ships to *neither* the frontend nor the
   plain backend — only inside the builder iframe. Check the manifest before
   assuming your file loads where you think.

2. **`systray_items/` is SCSS-only.** The Edit/Publish/Mobile/New-content systray
   *button JS* lives in `client_actions/website_preview/`, not `systray_items/`.

3. **`website_id = False` is meaningful, not "unset".** It marks a *generic*
   (all-websites) record. Filtering `website_id = <id>` alone hides generic
   content; always use `website_domain()`.

4. **The editor edits the real site.** Edit mode loads the live frontend in an
   iframe and layers `public.interactions.edit` mixins over the running
   interactions via `core/website_edit_service.js`. There is no separate "editor
   DOM" — which is why interactions must `destroy()` cleanly (they *are* torn
   down when entering edit mode).

5. **Prefer Interactions over `publicWidget`.** The legacy `PublicRoot` /
   `publicWidget.Widget` layer (`js/content/`) still runs, but new public
   behavior should be an Interaction. Reserve legacy for `PublicRoot`
   page-level events (lang switch, publish, gmap requests).

6. **Publishing needs `can_publish`.** Writing `is_published=True` on a
   published-mixin model without publish rights raises `AccessError`, not a
   silent no-op. Gate UI on `can_publish`.

7. **Homepage is never a 404.** `Website.index` has a multi-step fallback
   (homepage_url → `_serve_page` → controller match → first reachable menu → 404)
   so `/` always resolves to something reachable. Preserve the chain.
