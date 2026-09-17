# ESM Bundling — End-to-End Pipeline

Code path an asset travels from a `.js` file on disk to an executing module
in the browser, with observability hooks, failure modes, and tunable knobs.

## Pipeline diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│ File on disk                                                         │
│   /addons/<addon>/static/src/**/*.js                                 │
│   Pragma: /** @odoo-module native */                                 │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  is_native_module() / is_odoo_module()
                                │  odoo/tools/assets/esm_graph.py
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ AssetsBundle.__init__()   assetsbundle/bundle.py                     │
│   files partitioned into:                                            │
│     • self.javascripts         (classic JS; legacy bundle)           │
│     • self.native_modules      (@odoo-module [native]; esbuild fuel) │
│     • self.templates           (XML for QWeb)                        │
│     • self.stylesheets         (SCSS/CSS)                            │
│   Only when bundle name ∈ esm_registry().bundles                     │
│   (assetsbundle/bundle.py sets self._is_esm_bundle).                 │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ HTTP GET /odoo                                                       │
│   ir_qweb._get_asset_nodes(bundle, debug)  ir_qweb_assets.py         │
└──────────┬────────────────────────────────┬──────────────────────────┘
           │  debug mode                    │  production
           ▼                                ▼
┌───────────────────────────┐   ┌───────────────────────────────────────┐
│ Per-file serve            │   │ Admin override? (config param)        │
│   get_native_module_data  │   │ Circuit open? (_esbuild_cooldowns)    │
│   → import_map per spec   │   │ Wait for pg_advisory_xact_lock        │
│   → <link modulepreload>  │   └─────────────────┬─────────────────────┘
│   → <script type=module>  │                     │  all green
│       /<addon>/static/... │                     ▼
└────────────┬──────────────┘   ┌────────────────────────────────────────┐
             │                  │ esbuild_native_bundle()                │
             │                  │   assetsbundle/bundle.py               │
             │                  │                                        │
             │                  │ 1. Generate entry.js (piped on STDIN — │
             │                  │    nothing written to the code tree):  │
             │                  │      import * as __owl from "@odoo/owl";│
             │                  │      import * as __m0 from "./path0";   │
             │                  │      ...                               │
             │                  │      odoo.loader.registerNativeModules(│
             │                  │        {"@odoo/owl":__owl,"@spec/0":..})│
             │                  │      (+ hoot-family modules.set aliases)│
             │                  │                                        │
             │                  │ 2. subprocess(esbuild, cwd=odoo_root,  │
             │                  │      --bundle --format=esm --minify    │
             │                  │      --keep-names --target=<target>    │
             │                  │      --external:@odoo/*                │
             │                  │      --external:/web/static/lib/*      │
             │                  │      --external:<EXTERNAL_BARE_SPEC>...│
             │                  │      --alias:<lib/header/stub>         │
             │                  │      NODE_PATH=<@addon symlink root>   │
             │                  │      --resolve-extensions=.js,.mjs,... │
             │                  │      --outfile --metafile [--sourcemap]│
             │                  │      timeout=<timeout_s>)              │
             │                  │                                        │
             │                  │ 3. Read output.js + metafile.json      │
             │                  │ 4. Write attachment (+ .meta.json,     │
             │                  │    .esm.js.map siblings):              │
             │                  │  /web/assets/esm/<hash>/<bundle>.esm.js│
             │                  └─────────────────┬──────────────────────┘
             │                                    │
             └───────────────────┬────────────────┘
                                 ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ Rendered HTML                                                             │
│   pre_nodes:                                                              │
│     <script>/* module_loader.js shim */</script>    (inline)              │
│     <script type="importmap">{imports:{@odoo/*: ...,}}</script>           │
│     <link rel="modulepreload" href="/web/assets/lib/..."> (prod only:   │
│       each library the bundle imports statically, owl and luxon)         │
│   [legacy bundle, if any]                                                 │
│   post_nodes:                                                             │
│     <script type="module" src=".../esm/<hash>/<bundle>.esm.js"            │
│             data-bridge="<bundle>"></script>                              │
│     <script type="module">import { templates } from @web/core/...</script>│
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────┐
│ Browser                                                                   │
│   1. Shim executes (sync): globalThis.odoo.loader = new OdooModuleLoader()│
│   2. Import map resolves @odoo/owl etc. to vendored ESM                   │
│   3. Bundle <script type=module> fetches, parses, executes                │
│   4. Bundle entry calls odoo.loader.registerNativeModules({...})          │
│   5. Template module calls odoo.loader.modules.get("@web/core/templates") │
│   6. boot/main.js → boot/start.js → mountComponent(WebClient)             │
└───────────────────────────────────────────────────────────────────────────┘
```

### A page bundle registers only what something outside it names

The entry esbuild compiles for a page bundle imports every member as a
namespace and hands the whole map to `odoo.loader.registerNativeModules`, which
keeps every export of every member alive. Since 2026-09-06 a member is a
namespace import only when something outside the bundle names it
(`_get_exported_specs`, `ir_qweb_assets_esbuild.py`; `EsbuildCompiler`'s
`exported_specs`): a bare or relative import from a declared consumer — its
dynamic children, its secondary and import-map satellites, and the children of
any declared parent whose members include all of this bundle's (the
`web.assets_frontend_minimal` / `web.assets_frontend_lazy` family) — or a
string literal equal to a member specifier that is not the target of a static
import, anywhere in the bundle or a consumer (`odoo.loader.modules.get("…")`,
the `html_editor_upgrade` registry values `html_upgrade_manager` reads).
`@web/core/templates` and `@web/core/assets` (the lazy-loading entry point a
tour or an embedding script reads off the loader) are always in. Every other member is `import "./path"`:
evaluated for its side effects, its unused exports shaken. Satellites
(`secondary_import_map_includes`, `import_map_includes` children) register
everything, because their consumers are the runtime children of the pages
they ride on. Measured on `web.assets_web` with website and mass_mailing
installed: 203 of 1,667 members registered, 5.6 % fewer bytes raw and 6.1 %
gzipped. `TestPageBundleExportSurface` pins the rule: the surface is a strict
subset, every child import and every literal stays in, and the compiled code
registers exactly the surface.

## Declarative ESM registry (`odoo.tools.assets.esm_registry`)

ESM bundle membership is **declarative**, not hardcoded: each module declares
its own ESM bundle relationships in its `__manifest__.py` under an
`esm` key; the aggregate is built once per process from
`Manifest.get_all_addon_manifests()` by `esm_registry()`
(odoo/tools/assets/esm_registry.py, returning an `EsmRegistry`
NamedTuple) and invalidated by `invalidate_esm_registry()`,
wired into `AssetsBundle.invalidate_addon_scan_cache` (the canonical
"addons on disk changed" signal from `ir.module.module.update_list()`).

| `esm` manifest key | Purpose |
|-----|---------|
| `bundles` | This module's esbuild-compiled bundles |
| `exports` | Module specifiers (starting with `@`) to expose from a compiled bundle when they belong to that bundle; merged into its exported members by `ir_qweb_assets_esbuild.py` |
| `runtime_bundles` | Bundles fetched at runtime through `/web/bundle` (`loadBundle`). A property of the BUNDLE — no parent page is named. Aggregated into `EsmRegistry.runtime_bundle_names` (together with every `dynamic_children` child), which is the predicate `use_esm` reads in `web/controllers/webclient.py`; without it the route serves the legacy branch and every module-syntax file becomes a `console.error` stub while `loadBundle` still resolves. A runtime bundle with **no** declared parent is served **per file** (there is no page whose modules could be stubbed), so a bare `runtime_bundles` entry is the debug shape in production; declare the parent under `dynamic_children` to get the compiled child. Because such a bundle is fetched into whatever page asks for it, `_get_export_consumers` counts it as a consumer of every page bundle, so a compiled page registers the specifiers it imports; before, `project_gantt.project_sharing_unit_tests` read `undefined` for `@web/views/kanban` and failed at `class … extends` |
| `dynamic_children` | Parent → lazy children. Declaring a parent does three things: the parent's page does not bridge the child's specifiers; the child is a runtime bundle without restating it; and, since 2026-09-06, the child is **compiled** against that parent (`_get_compiled_runtime_payload`, below) instead of being served per file. With several parents the child is compiled against the modules **every** installed parent owns (intersection), so it loads on any of their pages |
| `dynamic_children_from` | Page → the page whose `dynamic_children` it takes, declared by the module that owns the page. For a second page built on the same code as a base page, such as `knowledge.webclient` and `document.webclient`, which include `web.assets_backend` as `web.assets_web` does: children are keyed on the page name, so without it every child another module declares on `web.assets_web` (`spreadsheet.o_spreadsheet`, the `web_tour` runtimes, `html_editor`'s) is missing from the variant, whose import map then cannot resolve `@odoo/o-spreadsheet`. Expanded once in `_prepare_esm_registry`, so every reader sees an ordinary parent. The base must be a registered bundle that takes its children from nobody, one page names one base, and restating an inherited child is refused |
| `import_map_includes` | Parent → satellites reusing the parent's import map, skipping esbuild; used for test-runner bundles |
| `external_libs` | Bare specifier → root-relative URL for a library this module ships (`@odoo/owl`, `chartjs-chart-geo`, …). One specifier resolves to one URL and the owning module declares it; a second module declaring it differently is an error |
| `exports` | Module specifiers (`@web/core/registry`, …) that must stay reachable **by name** from outside the bundle graph — a test's `browser_js`, a tour started from Python — which no scan of JavaScript sources can discover, so the module that owns them declares them. Aggregated into `EsmRegistry.exports`; `_get_exported_specs` (`ir_qweb_assets_esbuild.py`) adds them to a compiled page's exports beside the specifiers its consumers import. Anything not starting with `@` is rejected at registry build |
| `secondary_import_map_includes` | Parent → satellites loaded as a separate later `<script>`; only the satellite's NEW import-map specifiers merge into the parent's map. **Gated**: the merge runs only when the satellites are actually rendered (`'tests' in debug or test_mode_enabled`), the same condition `web.conditional_assets_tests` uses |

Choosing between the last two, since both silence the "module-syntax file in a
non-ESM bundle" stub and neither raises when it is the wrong one:

- `import_map_includes` — the child is **never compiled**: `EsbuildCompiler.compile`
  returns an empty result when `_import_map_included` is set
  (fed from `registry.import_map_included_bundles` in `AssetsBundle._prepare_esbuild_compiler`). Its specifiers
  ride the parent's map and resolve to individual source URLs, which is what a test
  runner loading files on demand wants.
- `secondary_import_map_includes` — the child **is** compiled, and this is the only
  key that populates `secondary_parents`, the mapping that makes esbuild `--alias`
  the child's shared specifiers onto `odoo.loader.modules` shims
  (`esbuild_stubs.stub_aliases`).
  Required whenever the satellite must drive the parent's *live* instances, e.g. a
  tour calling `patchWithCleanup(browser, …)` against an already-running app.

Example:

```python
# web/__manifest__.py — the only manifest using all four keys:
'esm': {
    'bundles': [...14 bundles...],
    'dynamic_children': {'web.assets_web': ['web.assets_clickbot',
                                            'web.assets_emoji']},
    'import_map_includes': {'web.assets_unit_tests_setup':
                            ['web.assets_unit_tests']},
    'secondary_import_map_includes': {'web.assets_web': ['web.assets_tests'],
                                      'web.assets_frontend': ['web.assets_tests'],
                                      'web.assets_frontend_lazy': ['web.assets_tests']},
}
# web_tour/__manifest__.py — the CHILD declares its lazy bundles under the parent:
'esm': {
    'bundles': ['web_tour.automatic', 'web_tour.interactive', 'web_tour.recorder'],
    'dynamic_children': {'web.assets_web': ['web_tour.automatic',
                                            'web_tour.interactive',
                                            'web_tour.recorder']},
}
# point_of_sale/__manifest__.py — bundles-only (no children/includes).
```

### A dynamic child is compiled against the page that loads it

`/web/bundle/<child>?page=<page bundle>` in production answers `{"is_esm": true,
"esm_url": "/web/assets/esm/<group hash>/<child>.esm.js", ...}` and the client
`import()`s that one URL (`assets.loadESMModule`, `core/assets.js`). The client
reads `page` off the `data-bundle` attribute of the import map the server
stamped on the document (`pageBundleOf`), so a cross-document load names the
target document's page, and the descriptor cache is keyed by bundle and page.

The server compiles every child declared under that page **together**
(`_get_runtime_group_urls_cached`, `ir_qweb_assets.py`;
`_compile_runtime_group`, `ir_qweb_assets_esbuild.py`; `EsbuildCompiler.compile_group`):

1. the page's member specifiers are the "parent-owned" set
   (`_get_runtime_parent_specs`). Every child member the page already owns is
   **dropped from the child's entry** — a child manifest may list parent files
   to feed the debug import map, and they must never be evaluated twice — and
   so is every member whose URL is a declared `esm.external_libs` file, which
   the browser resolves through the import map and dedups by URL;
2. each addon a child touches is mirrored into a temp tree (`esbuild_stubs.mirror_aliases`,
   one symlink per real file) where every parent-owned module any child reaches
   — by bare specifier or by relative import — is replaced by a **strict stub**
   (`_strict_stub_source`: `odoo.loader.modules.get(spec)` or throw; a child
   evaluates after its parent registered, so it reads once instead of
   listening); `@addon` is aliased to the mirror and esbuild runs with
   `--preserve-symlinks`, so relative imports stay inside the mirror;
3. esbuild runs once with one entry per child, `--splitting`, `--entry-names=[name].esm`
   and `--chunk-names=chunk-[hash].esm`: a module two siblings share (the three
   `web_tour` bundles share `tour_step`) becomes a chunk both entries import by
   relative URL, so the browser evaluates it once, as URL identity did on the
   per-file path;
4. each entry gets its templates appended exactly as a page bundle does, and
   the whole output set is persisted under one content-addressed directory
   `/web/assets/esm/<group hash>/` (`_save_esm_group`: immutable, one year, the
   404 self-heal applies) with the esbuild metafile as a sidecar named group.meta.json. The
   garbage collector keeps a directory alive while any entry in it is the
   newest of its name (`_get_esm_gc_collectable`), because a chunk's hashed name is
   reused by nothing.

A page stamps the bundle it rendered first, which may be one member of the
family a child declares (the website frontend stamps `web.assets_frontend_lazy`,
built by including `web.assets_frontend`); the declared parent that contributes
to that page is the one used (`_get_runtime_group_parents`). In test mode the
page also renders its secondary satellites (`web.assets_tests`), whose members
the child stubs as well, so a test-mode group is a separate cache entry
(`runtime:<parents>:tests`). With no `page` at all (a caller outside the web
client) the group is the children sharing the child's exact set of installed
declared parents, compiled against the modules **all** of them own.
Anything a child imports that neither it nor the page owns is bundled from
disk and logged as `event=runtime_child_inlines` — on a page that also owns it,
that is a singleton split, and the log line is the only warning. The circuit
breaker, advisory lock and admin override apply per group (`runtime:<parents>`);
a declined compile falls back to the per-file payload below; a read-only test
cursor propagates `ReadOnlySqlTransaction` so the route retries read-write, as a
page bundle does. The debug payload (`?debug=assets`) is per-file, unchanged.
Pregeneration warms one group per installed parent.

`TestDynamicBundleIntegrity.test_a_runtime_bundle_resolves_every_parent_module_through_a_stub`
reads a group directory back and checks every parent-owned module a child
reaches is a loader read and none is re-registered;
`TestRuntimeBundlesInTheBrowser` loads every compiled child of `web.assets_web`
in Chrome and fails on the first `rebind` event. Measured on the spreadsheet
bundle before/after: 244 requests and 4.8 MB (raw, uncompressed, 7-day cached
sources) with 7 rebinds per open, against 7 requests, one immutable file
(497 KB gzip) and none.

### A page bundle is one file, and a dynamic child is declared on every page that reaches it

A dynamic `import()` in page code resolves one of two ways: to a stub, when
the page declares a child that owns the module (`_get_esbuild_child_externals`
aliases every child member to a loader stub), or to the module inlined from
disk. `web.assets_emoji` declared under `web.assets_web` alone gave every
backend page the stub and every frontend page the 461 KB table; it is declared
under `web.assets_frontend` too, and
`TestDynamicBundleIntegrity.test_a_page_never_inlines_what_a_dynamic_child_owns`
reads each page's metafile and fails on the next such case.

Compiling page bundles with `--splitting` instead was measured and rejected
on 2026-09-06: with the stubs in place the backend page has nothing left to
split (its dynamic imports are a few hundred bytes each), it would fetch
fifteen shared chunks (213 KB) at boot beside the entry, and every module in
a shared chunk evaluates before every module left in the entry — the HOOT
page bound `window.fetch` in `browser.js` before hoot installed its mocks and
twelve tests failed. Member order is load-bearing; one file keeps it.

### `--keep-names` stays

Dropping `--keep-names` is worth 3.7 % raw and 4 % gzipped on `web.assets_web`
(measured 2026-09-06: 4,195,650 → 4,039,172 bytes, 1,124,001 → 1,079,983
gzipped) and is not taken: `mail/static/src/model/record.js` registers a model
under `this._name || this.name`, so a minified class name would rename every
mail model that does not declare `_name`. The flag goes when the models do.

### A bundle made of libraries only is served classic

Four declared bundles (`html_editor.assets_history_diff`,
`html_editor.assets_image_cropper`, `mail.assets_lamejs`,
`spreadsheet.assets_print`) carry no native module: their members are classic
library scripts. The route serves them in the classic list envelope — the
scripts load through `loadJS` — instead of an ESM envelope with an empty
specifier list and a 26-entry import map the client would inject for nothing.
`TestBundleDescriptorFormat.test_a_library_only_bundle_is_served_classic` pins it.

### Not every ESM bundle can be served per file

A runtime bundle with no declared parent, and every runtime bundle under
`?debug=assets`, is served **per file**, and a bundle built for esbuild is not
automatically servable that way. esbuild walks the import graph from disk, so a
member's relative `./sibling.js` resolves whether or not the sibling is in the
bundle's file list; served per-file there is no such walk, and the specifier
would fetch a second copy of a module some other bundle on the page already
owns. `_check_lazy_bundle_relative_imports` refuses that, and
`TestDynamicBundleIntegrity` sweeps every bundle in `runtime_bundle_names` so
the refusal lands in CI rather than as an HTTP 500.

Five declared bundles currently fail that check, and **all five are correct as
they are** — do not "fix" them by adding the escaping files to the bundle:

| Bundle | Why the escape is right |
|---|---|
| `web.assets_frontend_lazy` | It is `web.assets_frontend` **minus** the five files `web.assets_frontend_minimal` owns (`session`, `cookie`, `dom/ui`, `minimal_dom`, `lazyloader`). Removing them from the member list is what stops this bundle re-registering specifiers the minimal bundle already registered. Adding them back would create the singleton split the removal exists to prevent |
| `web.assets_inside_builder_iframe` | Rendered into the builder iframe — a separate document with its own module graph |
| `api_doc.assets` | Its own page, which does not render `web.assets_frontend` |
| `im_livechat.embed_assets_unit_tests_setup` | A test-setup bundle that removes `im_livechat/static/**` and re-adds a chosen few |
| `im_livechat.assets_embed_core` | Include-only. Its first entry removes `web/static/src/core/browser/title_service.js`, which only exists in the parents that include it (`web.assets_frontend`, `im_livechat.assets_embed_external`) — an exact-path `remove` is strict, so standalone it raises. Note the side effect: installing `im_livechat` drops `title_service.js` from `web.assets_frontend`. Verified harmless — nothing on the frontend calls `useService("title")`, and `mail.assets_public`, whose `discuss_patch.js` does, keeps both |

The rule is not "close every bundle under its relative imports". It is: a bundle
is servable per-file only if it is closed, and `esm.runtime_bundles` is the
declaration that says it must be.

Invariants are enforced by `check_esm_config` (`esm_registry.py`) when the
registry is built —
loud by design, so a bad manifest fails the first render/bundle that touches
the registry.  For ALL THREE mappings (`dynamic_children`,
`import_map_includes`, AND `secondary_import_map_includes`):
- Every parent is a registered ESM bundle (in `bundles`)
- Every child is a registered ESM bundle (in `bundles`)
- No duplicate name within a parent's merged children list
Plus: every `runtime_bundles` and `standalone_bundles` entry is a registered
bundle, and, cross-mapping: no bundle is both a dynamic child AND an
import-map-include of the same parent.  Unknown keys under `esm` are rejected
(`_ESM_MANIFEST_KEYS`); a non-Mapping `esm`, a bare-string `bundles`, or a
non-dict mapping value raise `TypeError` earlier in the build.

External libs are **declared per manifest** under `esm.external_libs` (bare
specifier → root-relative URL) and aggregated by `esm_registry.external_libs()`;
a specifier is owned by exactly one module, and two modules declaring it
differently is an error. That table is the only source of specifier
resolution: esbuild leaves every `@odoo/*` specifier and every declared bare
specifier external (`external_bare_specifiers()`) and the page's import map
resolves them, a standalone bundle aliases each of them to its declared file
(`_standalone_alias_flags`), and a bundle whose member is a declared library
file (`web.assets_unit_tests_setup` carries hoot) also registers the library
under its declared specifier — `external_lib_aliases()` reads each URL as a
specifier, so `@odoo/hoot` is `@web/../lib/hoot/hoot` without a second table
saying so. The former `_LIB_CANDIDATES` alias table (bundled copies of
`@popperjs/core`, `@odoo/hoot-dom`, `@odoo/o-spreadsheet`) is gone: nothing
bundled imported the first, the second was external anyway, and the third is
the `@odoo-module alias=` header of `o_spreadsheet.js`, which `_esbuild_flags`
already turns into an alias.
Cross-file invariants are checked once per process by
`AssetsBundle._check_external_libs(external_libs())`, reached through
`_check_external_libs_once()` in `AssetsBundle.__init__`:
- Every `esm.external_libs` specifier resolves for esbuild —
  `external_bare_specifiers()` membership or `--external:@odoo/*` coverage
- Every `esm.external_libs` URL exists on disk (URLs under addons absent from
  `addons_path` are skipped)

In production the import map does not name the vendored file: every
`esm.external_libs` URL is rewritten by `esm_libs.served_external_libs()` to
`/web/assets/lib/<unique>/<declared path>`, where `<unique>` hashes the
library's relative-import closure (`lib_closure`: the declared file plus every
`./` and `../` import it reaches inside the addon's `static/`), and the render
that builds the map persists a minified copy (`minify_js` with `--keep-names`)
of each file of that closure at those URLs (`IrQweb._ensure_served_libs`).
The route serves them immutable for a year, and a sibling imported by relative
URL resolves under the same `<unique>` prefix to the same instance. A page
under `debug=assets` keeps the declared URLs, readable and uncached; the two
tables never mix on one page, since a library reached by two URLs would be two
instances. A `<link rel="modulepreload">` precedes the page bundle for
each library the bundle imports statically (owl, luxon, dompurify), read off
the esbuild metafile's external `import-statement` entries, so the browser
fetches them beside the bundle instead of after parsing it; a library behind
`import()` gets none. Measured 2026-09-06, gzip: owl 50 → 27 KB, luxon 60 → 22 KB,
fullcalendar 162 → 88 KB, three.js 406 → 186 KB.

A heavy library is reached through **one facade**: a module under
`static/src/core/lib/` or `static/src/lib/` that owns the `import("<spec>")`
(`makeLazyLib` in `core/lib/lazy_lib.js`; `chartjs.js`, `fullcalendar.js`,
`geoengine/static/src/lib/geo_libs.js`, `web_threed/static/src/lib/three.js`).
The view code stays eager and small; the library is fetched on first use
through the import map, once. `TestLibraryFacades` (`test_esm_pipeline.py`)
reads every facade of every installed addon, refuses a facade importing its
library statically, and fails when a member of `web.assets_web` or
`web.assets_frontend` outside those directories imports a facaded library
statically. Bundles a single page or a lazy child owns may still take a
library eagerly (survey's live session page, the spreadsheet child).

Bridge export surfaces and import discovery are primarily computed by a
persistent `es-module-lexer` node worker (`odoo/tools/assets/esm_lexer.py` +
`odoo/tools/assets/js/esm_lexer_worker.mjs`, installed by the same
`npm install` that provides esbuild); a regex extractor in `esm_graph.py` is the
automatic fallback when the worker is unavailable or a source doesn't lex.

Worker robustness contract (`esm_lexer.py`):
- **POSIX-only.** The worker uses `select` on pipes; on non-POSIX the regex
  path is always used.
- **Hard per-request deadline** (`_REQUEST_TIMEOUT_S`, 10s). The pipes are
  binary + non-blocking and BOTH the request write and the response read are
  gated by a wall-clock deadline (`_write_all` / `_read_line`), so a worker
  that stopped reading (full ~64 KB pipe) or emitted a partial line can never
  block a caller past the budget — a plain `stdin.write` / `readline` could.
- **Respawn-once, then disable.** A worker that dies mid-request is respawned
  and the request retried once; a *spawn* failure (no `node`) disables the
  worker for the process immediately; and `_MAX_CONSECUTIVE_FAILURES` (2)
  consecutive request failures also disable it — so a present-but-broken
  worker degrades the whole process to the regex path fast instead of paying
  the 10s budget on every module (which would be minutes across a big bundle).
- **Discovery parity.** The regex fallback (`_IMPORT_ANY_RE`) covers named /
  default / namespace / mixed (`import D, { y } from …`) / bindingless
  side-effect imports, matching the worker's specifier discovery. `has_default`
  can differ cosmetically for `export { x as default }`, harmless because the
  shim emits the default block unconditionally.

## Logger taxonomy (Python ↔ JS)

Both sides use the same category names so `grep event=bundled` works across
the whole stack when logs are merged.

| Category | Python logger | JS logger | Emitted at |
|----------|---------------|-----------|-----------|
| `bundle` | `odoo.assets.bundle` | — | AssetsBundle lifecycle (init, asset partitioning) |
| `bridge` | `odoo.assets.bridge` | — | Native-to-legacy data-URI bridge construction |
| `esbuild` | `odoo.assets.esbuild` | — | subprocess invoke / success / timeout / fail |
| `loader` | `odoo.assets.loader` | inline `[asset.loader]` | `module_loader.js` shim — idempotent install check and `registerNativeModules` entry counts |
| `attach` | `odoo.assets.attach` | — | ir.attachment writes/reuse for bundle output |
| `fallback` | `odoo.assets.fallback` | — | Prod→debug degradation, circuit open, admin override |
| `lock` | `odoo.assets.lock` | — | PG advisory-lock acquire/release |
| `esm` | `odoo.assets.esm` | `makeAssetLog("esm")` | Import-map + bundle-node generation |
| `env` | — | `makeAssetLog("env")` | Service launcher, wave resolution |
| `js` | — | `makeAssetLog("js")` | Lazy bundle fetch (core/assets.js) |
| `templates` | — | `makeAssetLog("templates")` | registerTemplate / getTemplate |
| `registry` | — | `makeAssetLog("registry")` | Sub-registry creation |

> No `boot` category exists on either side — boot events surface through
> `loader` (Python shim + JS inline) and `env` (JS service launcher).

Event format (Python `log_event`): `event=<name> k1=v1 k2=v2`.
Event format (JS `assetLog`): `[asset.<category>] <...parts>` via `console.debug`.

## Debug toggles

### Python side
```bash
odoo-bin --log-handler=odoo.assets:DEBUG              # full trace
odoo-bin --log-handler=odoo.assets.esbuild:INFO       # esbuild only
odoo-bin --log-handler=odoo.assets.fallback:WARNING   # alerting
```

### JS side (any of)
- URL: `?debug=assets` (or any debug mode containing "assets")
- DevTools: `localStorage.setItem("debug.assets", "1")`
- DevTools: `window.__ODOO_ASSET_TRACE__ = true`

Then enable the DevTools "Verbose" log level so `console.debug` lines
become visible.

## Tunable parameters (ir.config_parameter)

All names are `web.esbuild.<key>`.  Defaults come from the hardcoded
class constants listed in the table and apply when the parameter is
unset or unparseable.

| Key | Default | Class constant (file:line) | Effect |
|-----|---------|---------------------------|--------|
| `timeout_s` | `30` | `EsbuildCompiler._ESBUILD_TIMEOUT_S` (odoo/tools/assets/esbuild.py) | subprocess timeout (seconds) |
| `target` | `"es2023"` | `EsbuildCompiler._ESBUILD_TARGET` (esbuild.py) | esbuild `--target=`. es2023 so esbuild stops downlevel-polyfilling `Promise.withResolvers`; all es2023 features have >18mo support on Chrome 110+/Safari 16+/FF 115+. |
| `source_maps` | `""` | `EsbuildCompiler._ESBUILD_SOURCE_MAPS` (esbuild.py) | esbuild `--sourcemap=<mode>`. `""` (off), `"linked"` (sidecar `.js.map` + `sourceMappingURL` comment — DevTools fetches only when opened), `"external"` (sidecar without comment), `"inline"` (base64 data URL appended — ~2x bundle size). Unknown modes silently fall back to `""`. |
| `cooldown_s` | `60.0` | `IrQweb._ESBUILD_COOLDOWN_S` (ir_qweb_assets.py) | Circuit-breaker cooldown after 1st failure |
| `extended_cooldown_s` | `600.0` | `IrQweb._ESBUILD_EXTENDED_COOLDOWN_S` (ir_qweb_assets.py) | Cooldown after 2nd consecutive failure |
| `force_fallback_bundles` | `""` | — | Comma-separated bundle names to force into debug path |

Compilation waits for the transaction-scoped advisory lock. Contention must not
switch an individual bundle to the debug layout: that can instantiate dependencies
twice alongside already bundled code. The former `lock_retries` and
`lock_retry_sleep_s` parameters are no longer read. Database lock/statement timeouts
propagate as errors; they do not select a different module layout. The lock covers
compilation, not subsequent attachment publication, so a waiting request can still
compile again if the preceding result has not been published yet.

Dedicated attachment-writing transactions serialize the URL existence check and
insertion under a separate publication lock. They use READ COMMITTED so a waiter
sees the preceding writer's commit. The request transaction keeps its original
isolation level. This prevents concurrent cold requests from persisting duplicate
library and compiled-asset URLs through that path.

A secondary bundle that explicitly lists a parent-owned module uses the parent's
module just like a transitive dependency. It does not import and register that
module again as an entry. External libraries retain their separate serving path.
Parent stubs also replace relative imports through a source mirror with symlink
preservation. Each addon retains separate static sibling directories (`tests`,
`lib`, etc.). The source index includes a compiler-semantics version; increment it
when changed compilation semantics could otherwise reuse an old artifact.

Operators set these via the UI (Settings → Technical → System Parameters)
or programmatically:

```python
env["ir.config_parameter"].sudo().set_param("web.esbuild.timeout_s", "60")
```

## Failure modes

| Symptom | Cause | Signal |
|---------|-------|--------|
| `Failed to resolve module specifier` in browser | import map missing a spec | `odoo.assets.esm DEBUG event=no_native_modules` or validator error at startup |
| esbuild subprocess non-zero exit | Syntax error in an ESM source | `odoo.assets.esbuild WARNING event=failed bundle=<name> exit=<code>` + stderr on next line |
| Requests serve un-minified bundles | Circuit open after failure | `odoo.assets.fallback WARNING event=circuit_open` (at trip) then `DEBUG event=circuit_blocked` (per request) |
| Cold request waits before compilation | Another worker holds the bundle lock | `odoo.assets.lock DEBUG event=waiting`, then `event=acquired wait_s=…` |
| A dynamic child is served per file in production and stays so | The runtime group compiled but persisting it failed after both the read-write escalation and the request cursor (a database-level fault); `_get_runtime_group_urls_uncached` caches the empty result on purpose, so the group is not re-compiled on every request while the database faults | `odoo.assets.attach WARNING event=runtime_group_save_failed` once, then `odoo.assets.fallback INFO event=runtime_child_per_file` per request; any `assets` cache clear (attachment unlink, *Clear cache*, restart) retries the compile |
| A read-only test cursor keeps declining a bundle after the cause is gone | `_get_esm_variant_nodes_cached` remembers a readonly decline per (bundle, params, satellites, page scope) in the `assets` LRU so the same test run does not retry a compile it cannot persist | `odoo.debug` `readonly_decline_remembered`; `clear_cache("assets")` drops the memo with everything else, which is the intended retry |
| `[registry] Duplicate add for key "…" … (first registration wins)` console.warn in debug | Module loaded twice (separate instances) — `registry.add` is first-wins and warns rather than throwing | Missing bridge shim (happy path is an attachment URL; `data:` URI only as the read-only-cursor fallback); check `_prepare_native_to_legacy_bridge` |
| Test `patchWithCleanup(Klass.prototype, …)` has no effect; production code keeps using unpatched method | Parent + satellite each load their own copy of the same `@web/*` module → `Klass` in test bundle is a different class than the one the production controller instantiates | Add fingerprint logger to module body — two distinct `MODULE LOADED` events means two evaluations. Root cause is usually a sibling manifest (e.g. `spreadsheet/__manifest__.py` pulls `web/static/src/views/graph/graph_model.js` into `spreadsheet.o_spreadsheet`, which is then `('include',)`'d by the satellite test bundle). Fix wires the satellite import through the parent's self-bridge via the `prod_import_map[alias] = shim` override in `_get_esm_nodes_prod` (`ir_qweb_assets.py`). |

## Cache invalidation on source change — no manual flush needed

**Dev mode rebuilds a bundle on a source-file mtime change; you do NOT need
to `DELETE FROM ir_attachment WHERE name LIKE '%assets_unit%'` before a run.**

The bundle's served URL carries a 7-hex *version* segment
(`/web/assets/<version>/web.assets_unit_tests.min.js`), which is
`AssetsBundle.get_checksum()[0:7]` — a SHA256 over each member's
`unique_descriptor`. That descriptor is `"{url},{last_modified}"`
(`assetsbundle/assets.py`), and `last_modified` is the file's `st_mtime`,
freshly `stat()`'d by `ir_asset._glob_static_file`. So editing any JS source
changes its mtime → changes the checksum → changes the version → the render
path looks up a version with no attachment → **rebuilds** (esbuild for the
ESM bundle, concatenation for the legacy `.min.js`) and writes the new row.
Stale content is impossible once the version differs; the old attachment is
just GC'd later.

The one caveat is the `cache="assets"` **ormcache** on
`ir_qweb._get_asset_links_cached` / `ir_asset._get_asset_paths`: its key
does NOT include mtime (it's `bundle`/`assets_params`/`rtl`/…), and it's only
bypassed when `dev_mode` contains `"xml"` (`@tools.conditional`,
`ir_qweb_assets.py`). But that ormcache is **in-memory, per-process**, so:

- **`--stop-after-init` test loop** (a fresh process per run, the workflow
  used here): the ormcache starts cold every run, recomputes from fresh
  mtimes, and always reflects edits. No flush, ever.
- **A long-lived server** (`config/p314o19marin.conf`, no `--dev`): the
  ormcache persists in-process, so an edit made while the server is up is
  invisible until the `"assets"` cache clears (server restart,
  Settings → Technical → *Clear cache*, or any asset-attachment unlink). If
  you want live reload against a running server, start it with
  `--dev=xml,reload` — `xml` disables the conditional ormcache and `reload`
  restarts on `.py` change; JS is then picked up on the next request. This is
  a server-lifecycle choice, not a bug, and still needs no manual SQL flush.

## Serving & caching

ESM artifacts are served by a dedicated route
(`web/controllers/binary.py::content_esm_assets`,
`/web/assets/esm/<unique>/<filename>`) with `Cache-Control: immutable` +
one-year `max-age` — safe because every URL is content-addressed (the
`<unique>` segment is a hash of the bytes, or `bridges` with the hash in
the filename). There is deliberately no on-the-fly rebuild on this route:
a missing row is a hard 404, and regeneration happens through the render
path after `ir.attachment.unlink`'s assets-cache clear.

Persistence is decoupled from the request transaction:
`IrQweb._save_esm_attachment_rows` (bundle/templates/sourcemap) and
`BridgeShimManager._persist_bridges_via_rw_cursor` (loader bridges) create
attachment rows through a dedicated read-write registry cursor that commits
independently, so a request rollback can never orphan an ormcached bundle
URL, and read-only replica renders persist + reference by URL instead of
inlining the bundle. Inlining survives only as the degradation path when no
writable cursor exists at all (read-only test cursors, primary down). Content
reverts (A → B → A) reuse the old row and bump its `write_date`, which
`_gc_esm_assets` uses for newest-per-name liveness.

**Current-cursor guard (deadlock avoidance).** The out-of-band cursor exists
ONLY to survive an HTTP-request rollback. When there is no request — registry
preload / asset pregeneration (`lifecycle._run_post_install_tests` →
`_pregenerate_assets_bundles`), cron, CLI — the current cursor is already the
durable one, and opening a SECOND real `registry.cursor()` on the same thread
self-deadlocks: this thread holds `ir_attachment` locks on the current cursor,
so the second cursor's INSERT waits on a lock only the now-suspended thread can
release (a one-thread/two-cursor cycle Postgres cannot break). Both savers
therefore persist on the current cursor when there is no request. **The two
guards are intentionally NOT identical:**

- `_save_esm_attachment_rows`: `if _module.current_test or not request:`
  → current cursor. The `current_test` term is required because a plain
  `TransactionCase`'s `registry.cursor()` is a REAL cursor whose out-of-band
  commit would leak rows past the test rollback.
- `_persist_bridge_shims`: `if not request:` → current cursor, else the rw
  cursor **even under a test**. A bare `current_test` branch here would break
  HttpCase tours: the browser fetches loader-bridge URLs on SEPARATE
  TestCursors, and only the `registry.cursor()` path publishes rows visible to
  them; persisting on the render's own cursor left dynamic-child bridges
  unfetchable (`Failed to fetch dynamically imported module`). Do not "unify"
  these guards.

## Service worker

`/web/static/src/service_worker.js` is NOT an `@odoo-module native` file —
it uses `@odoo-module ignore` so the bundler treats it as a classic script,
served via the `/service-worker.js` controller as a plain script (service
workers have limited ESM support — no import maps in some browsers). Do not
convert it without first verifying import-map + module-worker support across the
browser-support matrix.

## Loader contract (`module_loader.js`)

The shim installs `globalThis.odoo.loader` as an instance of
`OdooModuleLoader`, a real ES class so Hoot's test helpers can subclass
it via `Object.getPrototypeOf(odoo.loader.constructor)`. The esbuild-generated
entry exercises exactly one method (`registerNativeModules`). Current surface:

### Public API

| Member | Kind | Purpose |
|--------|------|---------|
| `modules: Map<string, any>` | field | Shared map of specifier → module namespace.  Populated by `registerNativeModules`; consulted by bridge shims so sibling bundles see the SAME object for `@web/core/registry` etc. |
| `bus: EventTarget` | field | Loader lifecycle events.  One event today: `rebind` (CustomEvent, `detail.specifiers`), fired when `registerNativeModules` re-binds a known specifier to a DIFFERENT namespace object — a singleton-split signal in production, the expected signal under dev hot-reload.  Subscribe via `odoo.loader.bus.addEventListener("rebind", …)`. |
| `registerNativeModules(map)` | method | Bulk-assign `specifier → namespace` into `modules`.  Last-write-wins on duplicate keys; same-object re-binds stay silent, different-object re-binds dispatch `rebind` + a debug-gated `[asset.loader]` log (never a throw — it runs at bundle top level).  Called by the esbuild-generated entry and by `@web/core/assets.loadESMBundle`. |
| `handleAssetLoadError(target)` | method | One-shot, rate-limited (60 s via `sessionStorage`) `location.reload()` that self-heals a 404'd content-addressed bundle/bridge URL — e.g. a client holding an old page after a GC sweep or `clear_cache("assets")`. Invoked by the capture-phase resource-load `error` listener in the inline reporter. |

### Error reporting

Build-time errors (missing specifier, cycle, syntax) surface from
**esbuild**: the bundle step fails, the circuit breaker trips (see
`ir_qweb._esbuild_cooldowns`), and the request falls back to the
debug per-file serve path — where the browser's native module
resolver surfaces the error directly in DevTools.

The shim additionally inlines a **pre-bundle error reporter**: it
installs `error` / `unhandledrejection` listeners before any module
evaluates and `sendBeacon`s to `/web/observability/js_error`
(throttled to one beacon per (message, line, col, hash(stack+cause))
per page — the stack and cause discriminate, since OWL reports every
lifecycle failure with one generic message at 0:0).  This
covers the window where the bundle itself fails to parse/evaluate and
`@web/core/errors/error_service` is unreachable; it is the pre-ESM
mirror of `@web/core/errors/error_beacon` — keep payload fields and
endpoint in sync with that module and
`observability.py::js_error`.

The reporter installs three listeners: bubble-phase `error` (runtime
errors, `kind:"error"`), capture-phase `error` (resource-load failures —
a 404'd module/link — which beacon `kind:"asset_load_error"` AND call
`odoo.loader.handleAssetLoadError(target)` for the one-shot self-heal
reload above), and `unhandledrejection`. Each payload carries a
`phase` of `pre_boot` / `post_boot` (from `odoo.isReady`), so a beacon
tells you whether the failure happened before or after the web client
mounted.

## See also

- `FLOW_DIAGRAM.md` — 14 end-to-end sequence diagrams
- `ARCHITECTURE.md` — module-wide architecture (boot flow, services, views)
- `CONVENTIONS.md` — coding patterns and gotchas
