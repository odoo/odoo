# Vendored libraries

Third-party libraries shipped inside the `web` module. Replace a directory wholesale
when updating rather than editing it incrementally.

Where the fork genuinely needs a change, **make it in the file and mark it with an
`AgroMarin:` comment** saying what diverged and why:

```js
// AgroMarin: don't support scripting (#115302)
value: false,
```

That marker is the record. It cannot drift from the code, because it *is* the code, and
`grep -rn "AgroMarin:" <lib>/` is the complete inventory of the **in-file**
divergences a bump must re-apply. A whole fork-local file — `ace/mode-qweb.js` —
carries no marker to find, so the inventory table below records those instead.
Counting it in CI is a follow-up (t24489); today the gates below check versions and
advisories only, so the marker is a convention kept by hand — a divergence left
unmarked is one the next bump silently discards.

Do not keep a parallel `.patch` file alongside a library: a copy of a diff can disagree
with the file it describes, and nothing reads it at build time. Keep reshaping tooling
in `tooling/vendored/`, not inside the vendored tree.

`versions.json` in this directory is the **single source of truth** for what is vendored
and at which version. It is machine-checked — see [Verification](#verification) — so the
inventory below is a reading aid, not the authority. Update `versions.json` in the same
commit as the files it describes.

## Inventory

| Directory | Version | Upstream | Notes |
|-----------|---------|----------|-------|
| `Chart/` | 4.5.1 | `chart.js` | Minified, no banner. Bundles `@kurkle/color` 0.3.2. Lazy (`@web/core/lib/chartjs`). |
| `ace/` | 1.44.0 | `ace-builds` | `src-noconflict` variant. `mode-qweb.js` is **fork-local**. Lazy (`web.ace_lib` bundle). |
| `bootstrap/` | 5.3.8 | `bootstrap` | JS bundle + the whole `scss/` tree the design system compiles against. 2 `AgroMarin:` markers (`bootstrap.esm.js:2038`, `scss/_functions.scss:191`). **Fork-modified**. |
| `chartjs-adapter-luxon/` | 1.3.1 | `chartjs-adapter-luxon` | Side-effect import that registers luxon on Chart's date adapter. |
| `diff_match_patch/` | forked | — | Trimmed fork of google/diff-match-patch (diff functions only); see its header. |
| `dompurify/` | 3.4.12 | `dompurify` | Upstream `dist/purify.es.mjs` verbatim. **Security-critical** — see below. |
| `fullcalendar/` | 7.0.2 | `fullcalendar` | Upstream `all/global.js` + ESM footer, 8 `AgroMarin:` markers (7 in `fullcalendar.esm.js`, 1 in `locales-all.esm.js`). **Fork-modified** — see below. |
| `hoot/` | internal | — | Odoo HOOT test framework, developed in-tree. |
| `hoot-dom/` | internal | — | Odoo HOOT DOM helpers, developed in-tree. |
| `luxon/` | 3.7.2 | `luxon` | Reached only through the `@web/core/l10n/luxon` facade. 1 `AgroMarin:` marker (`luxon.js:8135`). **Fork-modified**. |
| `odoo_ui_icons/` | 1.2 | — | IcoMoon build over Carbon + Material; see `Read Me.txt`. |
| `owl/` | 2.8.4 | `@odoo/owl` | `dist/owl.es.js` built from [`Agro-Marin/owl` `2.8-marin`](https://github.com/Agro-Marin/owl/tree/2.8-marin): upstream v2.8.4 + four owl-3-form commits: `t-out` renders non-block objects as text, a `t-call-context` template reads its context as `this`, `<t t-call="x" a="expr"/>` passes `a` to the callee, and `a.translate="Text"` passes the translated text. |
| `pdfjs/` | 6.1.200 | `pdfjs-dist` | Largest vendored library. 13 `AgroMarin:` markers, 12 in `web/viewer.js` and 1 in `web/viewer.html`. **Fork-modified** — see below. Lazy (`@web/core/utils/pdfjs`). |
| `popper_compat/` | generated | — | **Not a third-party library.** Self-contained build of `@web/libs/popper_compat`, which replaced Popper. See below. |
| `prismjs/` | 1.30.0 | `prismjs` | Custom download with a fixed language set; keep the set when bumping. |
| `signature_pad/` | 5.1.3 | `signature_pad` | |
| `zxing-library/` | 0.23.0 | `@zxing/library` | Locally built single-file ESM bundle — **not** a pristine upstream file. |

### Libraries needing extra care

**`dompurify/`** backs `html_editor`'s sanitize plugin, which calls it with `IN_PLACE`,
a cross-realm window (`DOMPurify(this.window)`, for editables in iframes), and custom
`ADD_TAGS` / `ADD_ATTR`. Historically that is the exact configuration surface DOMPurify
advisories target, several of them specific to `IN_PLACE` and to cross-realm use. Treat
any advisory reported against this library as release-blocking, and re-run the
`@html_editor` suite after every bump.

**`fullcalendar/`** is not a pristine upstream file. `fullcalendar.esm.js` is upstream's
`all/global.js` carrying 6 marked divergences, followed by a hand-written ESM export
footer (itself the 7th). To bump it:

1. `npm pack fullcalendar@<version>` and unpack it.
2. Re-apply each `AgroMarin:` divergence — `grep -n "AgroMarin:" fullcalendar.esm.js`
   on the outgoing file lists them, and each comment states what it re-injects and why.
3. Append the existing ESM footer (everything from the `// ─────` rule onward).
4. Regenerate `locales-all.esm.js` from the release's `locales-all/global.js`, replacing
   the trailing `})(FullCalendar.Shared);` with `})(Shared);` and prepending the import
   header.
5. Copy `skeleton.css` and `LICENSE.md` from the **same** release.

Step 5 is not optional: v7 regenerates its `fc-*` class hashes on every build, and a
bump both reshuffles nearly all of them and recycles a few onto unrelated roles — so a
stale stylesheet or a hard-coded hash matches the *wrong* element instead of simply
missing. Never write an `fc-<hash>` literal; resolve names through
`fcInternalClassName()` in `@web/views/calendar/hooks/full_calendar_hook`.

**`pdfjs/`** ships the full viewer, which the npm package does not carry, so a bump
starts from a release archive on the GitHub releases page — specifically the
**legacy** one, `pdfjs-<v>-legacy-dist.zip`, never the plain `-dist.zip`. The modern
build calls `Map.prototype.getOrInsertComputed` with no feature detection and never
defines it, and that method only reached Baseline in February 2026 (Firefox 144,
Safari 26.2, Chrome 145) — so taking that build breaks PDF preview on every older
browser, which is not hypothetical: t24581 was reported from Chrome 141. Only the
legacy build bundles the core-js polyfill, in both `build/pdf.js` and
`build/pdf.worker.js`. `addons/web/tests/test_pdfjs_dist.py` gates the flavour
against the bundle files, which is the only place it can be gated — a browser that
ships the method natively satisfies any runtime check whatever build is vendored.
`pdfjs-<v>-legacy-dist.zip` does not match the vendored layout:
`tooling/vendored/mechanise_pdfjs.sh <unzipped-dir>`
reshapes it (`.mjs` to `.js`, source-map references stripped, scripting sandbox and
sample assets dropped), and its header explains each choice. Run it first, then
re-apply the 12 `AgroMarin:` markers in `web/viewer.js` and the one in `web/viewer.html`.

The reshape is deliberately blind to webpack's build-provenance comments
(`;// ./node_modules/...`), which name the source module rather than a shipped file.
Rewriting those would misreport where the code came from.

**`popper_compat/`** is generated, not vendored. Popper was removed: Bootstrap was
its only importer and used a single entry point, `createPopper`, which
`web/static/src/libs/popper_compat.js` reimplements over the in-house position
engine (`@web/core/position/utils`) — one positioning engine instead of two, and
60 kB less to ship.

Bundled code gets that **source** inlined by esbuild. This directory holds a
self-contained build for pages outside the asset pipeline — the IoT box homepage,
the database manager, the error page — which load `bootstrap.esm.js` straight into
the browser and resolve `@popperjs/core` through an import map; having no bundler,
they cannot follow the source module's `@web/...` imports.

Because that build derives from in-tree code that changes (unlike a pinned upstream
release), the drift gate runs `build.sh --check` and fails if it is stale. After
editing `popper_compat.js`, run `build.sh`.

Behaviour is verified against real Popper rather than assumed: 60 placement
scenarios in each text direction — every placement, at the viewport centre and each
edge so that 20 of them genuinely flip — matched Popper's geometry to the pixel and
agreed on every resolved placement. Two bugs that only that comparison would have
caught are now regression-tested in `tests/libs/popper_compat.test.js`: the
standalone build threw on pages with no localization service, and RTL placements
were mirrored twice (Bootstrap already resolves RTL itself, so placements arrive
physical, while the engine speaks logical).

**`zxing-library/`** is built locally because upstream ships no single-file ESM bundle.
The build command — including a **pinned** esbuild version, since esbuild's IIFE
parenthesisation changes between releases and an unpinned rebuild yields a large
cosmetic diff — is in the file's banner comment. Only browsers without a native
`BarcodeDetector` ever fetch it.

## Verification

```bash
# offline: every pinned version re-derived from the shipped bytes
tooling/vendored/check_vendored_libs.py --drift

# network: OSV advisories against the pinned versions
tooling/vendored/check_vendored_libs.py --audit
```

Both exit non-zero on failure and belong in CI. `--audit` reports (and does not
silently pass) libraries it could not reach OSV for, so an offline run never looks like
a clean bill of health.

## Update procedure

1. **Confirm the upgrade is needed.** Pin it to a real reason — a security advisory, a
   required feature, a license change. Do not chase versions for their own sake; every
   update churns the diff and risks a bundle-size regression.
2. **Replace the directory wholesale.** Before deleting anything, run
   `grep -rn "AgroMarin:" <lib>/` and keep the output: that is the complete list of
   in-file fork divergences you must re-apply to the new release, each with its own
   rationale. Fork-local whole files are listed in the inventory table instead.
   Re-apply them in the file and keep the marker.
3. **Update `versions.json`** in the same commit, and this table with it.
4. **Run both gates** (`--drift`, `--audit`).
5. **Re-run `--test-tags=web_assets -u web`** to confirm bundle generation still works.
6. **Run the consuming suites** — e.g. `@html_editor` for dompurify, `@web/views/calendar`
   for fullcalendar, `@web/views/fields/ace_field` for ace, the full `@web` suite for owl.
7. **Check the LICENSE.** If it changed upstream, surface that in the PR description.
