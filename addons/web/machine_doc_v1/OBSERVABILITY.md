# Observability — the campaign's logger and probe surface

Status: **Active. Removed at the end of the JS-improvement campaign.**
Scope: what a running `web` client can be made to report about itself, and how
to take a reading.

## Why this exists

Several attempts to improve this tree stalled because the reasoning was static:
read the code, form a belief, change it, hope. The readings that finally moved
`LIST_EDIT_RENDER_COST.md` (81 row renders to 4) and `VIEW_TEARDOWN_COST.md`
came from *instrumented runs*, not from reading. This page is the surface that
makes such a reading cheap, so the next improvement starts from a measurement.

Everything here is temporary by construction and comes out at the end of the
campaign. The per-component half was written by a stamper in the tooling tree,
deleted in `7b0f58cb517f`; no `// trace-stamp` line remains in any `static/src`, so that
half is already out. The namespaces below are deleted with the call sites that
use them.

## Two gates, deliberately independent

`core/utils/asset_log.js` carries both, and they are switched separately because
they answer different questions.

| Gate | Turns on | Effect | Use it for |
|---|---|---|---|
| `debug.<namespace>` | `localStorage.setItem("debug.rpc", "1")` | `console.debug("[rpc.request]", …)` per event | Watching one subsystem while reproducing a bug by hand |
| `__odooTrace` | `?odoo-trace=1` in the URL, or `localStorage["debug.trace"]` | Counts only, **silent** | Taking a figure a machine doc can cite |

**`?debug=<namespace>` does not work and never did — except for `assets`.** The server normalises the
debug parameter against an allowlist in `web/models/ir_http.py`:
`ALLOWED_DEBUG_MODES = ["", "1", "assets", "tests"]`
— and rewrites anything else to `"1"` before the page is built. Of the ten namespaces only `assets` survives
that filter, so `?debug=rpc` has never reached `rpcLog`. `localStorage` is the
route for the console gate. `ESM_BUNDLING.md`'s "Debug toggles" section is
correct and should not be "fixed" to match this one: it documents `?debug=assets`
only, which is the single namespace that survives the filter. The gap is that the
nine namespaces added since have no URL route, not that its instructions are
wrong. The sink reads `location.search` **directly**, which
nothing normalises, so it needs no change to a production allowlist for a
surface that is deleted at the end of the campaign.

Coupling them would make both useless: a measurement run producing 50 000
console lines is unreadable, and a hand-debugging session wants the text, not a
histogram. The recording call sits *before* the console gate inside
`_makeNamespacedLog`, so arming `__odooTrace` retro-fits countable data onto
every call site that already exists, with no edit to the files that log.

When both are off the cost is one property read on a `globalThis` slot — the
same shape `useRenderCounter` already uses for `__renderTrace`.

### Guarding a call site: `active()`, never `enabled()`

A call site that skips work when logging is off must ask `log.active()` —
console gate **or** sink armed. `log.enabled()` answers only "is the console
listening", so guarding on it makes the namespace invisible to `__odooTrace`
however the sink was armed.

This is not hypothetical. Both listeners in `core/network/rpc.js` guarded on
`enabled()`, and `rpc.*` recorded **nothing** on a fully armed page boot until
they moved to `active()` — the counters looked dead when the probe was fine.

### Taking a reading

```js
__odooTrace = true;
__odooTraceReset();
// …drive the interaction…
__odooTraceStats();   // { "rpc.request": 12, "view.load": 2, … }
```

`__odooTraceStats()` returns a **copy**, so a reading taken mid-interaction is
not mutated by what happens next.

### Where a reading is taken changes what it says

Two traps, both found by measuring rather than by reading, and both guarded by
`static/tests/core/utils/trace_choke_points.test.js`.

**One reading per test.** A second `mountView` in the same test does not re-parse
the arch, so the second reading under-reports. A three-field arch mounted after a
two-field arch records `field.resolve: 2`, not 3 — the same figure the first
mount produced, which is what makes it dangerous: it looks like a plausible
answer rather than a missing one. Mount once per test, or the count is of the
first arch.

**HOOT cannot see one of the ten namespaces.**

| Namespace | In HOOT | Why |
|---|---|---|
| `component` | **never fires** | `mountWithCleanup` builds `new App(...)` directly instead of going through `env.js`'s `mountComponent` |

Any `component`-shaped figure has to come from a real page. The test asserts
that namespace's **absence**, so the day the harness shares that path it reports
the change rather than leaving the gap to be rediscovered.

`rpc` was on this list and **should not have been**. It read as absent under
HOOT and the obvious explanation — the mock server replacing the rpc layer — was
wrong. Both listeners in `core/network/rpc.js` guarded on `rpcLog.enabled()`, so
the namespace was invisible to the sink in *every* harness, real pages included;
the mock server dispatches `RpcEvent.REQUEST` exactly like the real one. Moving
those guards to `active()` made the traffic visible in both. A probe that reads
zero is a claim about the probe until the guard has been checked.




## The namespaces

9 namespaces, each with its own flag. There are 6 category factories
(`make<Name>Log(category)`) for callers that bind a category once; the other
loggers accept the category directly. The livechat logger is private and
exposed through its category factory.

| Namespace | Flag substring | Wired at | Answers |
|---|---|---|---|
| `asset` | `assets` | `env.js`, `boot/start.js`, `core/templates.js`, `core/assets.js`, `core/registry.js`, `session.js` | What loaded, in what order |
| `rpc` | `rpc` | `core/network/rpc.js` | Every request and its outcome |
| `model` | `model` | `model/relational_model/` — load, save, archive, delete, duplicate | Record lifecycle |
| `l10n` | `l10n` | `core/l10n/localization_service.js` | Translation fetch and cache |
| `component` | `component` | `env.js` (`mountComponent`) | Every `App` this fork mounts |
| `service` | `service` | `env.js` (`_startServices`) | Start order, dependencies, failures |
| `view` | `view` | `views/view.js` | Which view types load, and which hit the server |
| `field` | `field` | `fields/field.js` (`getFieldFromRegistry`) | Which field widget every arch node resolves to |
| `livechat` | `livechat` | `im_livechat/static/src/embed/cors/boot.js` (`cors`), `im_livechat/static/src/embed/common/livechat_service.js` (`service`) | The CORS URL rewrite, and the embed's init and persist paths |

The last four were added by this campaign. `component`, `service`, `view` and
`field` are **choke points**: every module in the tree flows through them, so
they observe files they do not edit.

### What the choke points cannot see

Which *component* re-rendered. That fact exists only inside each component's own
`setup()`, so it cannot be reached from a shared junction — which is what the
stamper below is for.

## The stamper (deleted)

Writes `useRenderCounter("<module>:<Class>")` into every component `setup()` in a
scope, and takes it back out.

It was deleted with the tooling tree in `7b0f58cb517f`. What follows records how it
behaved, for anyone rebuilding one.

Four properties make it safe to run against a shared tree:

1. **Reversible exactly.** Every inserted line carries a `// trace-stamp`
   trailing comment; `--revert` removes lines carrying it and nothing else. An
   apply/revert cycle over `addons/web/static/src` returns all 867 files
   byte-identical.
2. **Idempotent.** A second `--apply` stamps 0 lines.
3. **Lint-clean on arrival — and `--fix` must NOT be run.** A stamped tree
   passes `eslint` and `prettier` with zero findings, which is a hard
   requirement rather than a nicety: `eslint --fix` reflows a stamped line, and a
   wrapped call puts the sentinel on a line of its own, leaving `--revert`
   deleting one line of a three-line statement. Getting there took three fixes
   the first `--apply` exposed, 244 errors in total — the probe import must land
   in **sorted position within the right import group** (appending after the
   last import drops it into a trailing relative-import group), the scan must
   handle **multi-line imports** (a braced list spread over lines is invisible to
   a single-line pattern, so the probe sorts ahead of an import that precedes
   it), and every emitted line must fit prettier's 88 columns.
4. **Hand-instrumented files are left alone.** 12 files place
   `useRenderCounter` by hand with labels that machine-doc pages cite
   (`LIST_EDIT_RENDER_COST.md` names `list.ListRenderer`) and that render-budget
   suites assert on. Stamping beside one would make a component publish two
   labels for one render and fork the reading. The guard is file-wide rather
   than per-`setup()` because `ListRenderer` calls its probe from
   `setupServices()`, a helper `setup()` delegates to — a guard scanning only
   the `setup()` block does not see it.

Labels are `basename:Class` — `list_renderer:ListRenderer` — not the full
addon-relative path, because a path-qualified label runs to 64 characters and
pushes the line past 88 columns. A site that still would not fit drops to the
class name alone; anything that then collides is promoted back to a
directory-qualified form even if that is over width, since two components
sharing one label would merge their counts into a single plausible-looking wrong
number. `--check` reports both the over-width lines and the qualified labels.

`--check` also reports which functions the stamp would push past `jsfunclen`'s
90-line budget, because that floor is exact in both directions. Two functions in
`web` sit at the edge; measured, the stamp moved the count **77 -> 78**, so one
of the two crossed and the other did not.

## A count is of EVENTS, not of domain objects

Each module binds ONE category for its whole file — `makeAssetLog("js")` at the
top of `core/assets.js`, `makeAssetLog("templates")` in `core/templates.js`.
Every `log(...)` in that file therefore increments the same key, whatever it is
reporting. **A count is interpretable only against how many call sites the
module has.**

| Key | Call sites | So a count of N means |
|---|---|---|
| `asset` js | 18 | N events across 19 kinds — cache hits, bundle fetches, import-map injections. **Not bundles.** |
| `asset` boot | 6 | N boot phases reached, of 6 possible |
| `asset` env | 5 | N env/service-wave milestones |
| `asset` templates | 2 | N compile-or-register events; roughly per template, but the two are summed |
| `asset` registry | 1 | N category opens — one site, so the count IS the thing |

This bit once already: `asset` js read 32 and was written up as "32 JS bundles".
It is 32 events from a 19-site module. A single-site category is a measurement;
a multi-site one is a signal that needs the source open beside it.

The campaign namespaces added later (`component`, `service`, `view`, `field`)
were given one category per *event kind* — `service.start` vs `service.started`,
`view.load` vs `view.loadViews` — precisely so their counts read directly.

## A real boot, measured

FROZEN at `6216a09c231`, on a 270-module database, `/odoo?odoo-trace=1` loaded as
`admin` in headless Chrome. Re-derivable only by running that page, so it is
pinned to a base commit rather than gated (§1.4) — **do not "correct"
these to current values**, the comparisons below rest on this base.

Split into namespace and category columns rather than written as
`namespace.category`: a dotted key whose category is `js` is indistinguishable
from a filename, and the docs' dangling-source-path sweep reads it as one.

| Namespace | Category | Count | Reads as |
|---|---|---|---|
| `asset` | templates | 1642 | template compile + register **events** (2 call sites) |
| `service` | start | 108 | services entering a start wave |
| `service` | started | 108 | …and resolving. Equality is the invariant worth watching |
| `asset` | registry | 72 | registry categories opened (1 call site, so this IS the count) |
| `asset` | env | 11 | env and service-wave milestones |
| `asset` | boot | 5 | boot phases |
| `asset` | js | 4 | asset-subsystem **events** (19 call sites) — not a bundle count |
| `l10n` | fetch / cache | 3 / 2 | translation fetch vs cache hits |
| `rpc` | request | 3 | network calls a bare webclient boot makes |
| `asset` | session | 2 | session reads |
| `component` | mount | 1 | one root `App` — the webclient itself |
| `action` | doAction / dispatch | 1 / 1 | the default action |

Two things worth carrying forward:

* **A bare boot costs only 3 RPCs**, so any interaction measured later is
  attributable to that interaction rather than to startup.
* **`service.start` is 108 here against 45 under HOOT.** The harness starts less
  than half the real service graph, so a service-ordering conclusion drawn from
  a HOOT reading covers under half of production.

Guarded by `web/tests/test_trace_probes.py`, which asserts the probes fire
rather than pinning the counts — the counts move with the module set, the firing
does not.


## One interaction, measured

Opening a `res.partner` list action on a client already booted, 3 active
partners, headless Chrome.
FROZEN at `d9ff46405c9`. Guarded by `test_what_opening_a_list_view_costs`
in `web/tests/test_trace_probes.py`.

| Namespace | Category | Count |
|---|---|---|
| `action` | doAction / dispatch | 1 / 1 |
| `view` | load / loadViews | 1 / 1 |
| `rpc` | request / ok | 3 / 3 |
| `model` | load | 1 |
| `field` | resolve | 25 |
| `asset` | templates | 30 |

Per-component renders, from the hand-placed `useRenderCounter` probes:

| Component | Renders |
|---|---|
| `list.ListRenderer` | 1 |
| `list.ListRecordRow` | 3 |

**Three row renders against three active partners — one per visible row, and no
second pass.** That is the state `LIST_EDIT_RENDER_COST.md` fixed the edit-move
path into, holding on first paint too.

### The window has to start after boot settles

This reading is only correct because the sink is reset **two seconds after**
`odoo.isReady`, not at it. Reset immediately and boot's in-flight work lands in
the interaction:

| Namespace / category | reset at ready | reset after settle |
|---|---|---|
| `rpc` request | 5 | **3** |
| `rpc` ok | **8** | **3** |
| `asset` js | **32** | absent |

Two things that reading gets wrong. `rpc.ok` exceeds `rpc.request`, which is
impossible for one window and is the tell: request and response straddle the
reset. And **those 32 `asset` events are boot's tail, not the interaction's** —
a doc written from that window would attribute boot's asset work to opening a
list view, which is false and would look entirely plausible.

**An asymmetric request/response count means the window is wrong, not the
subsystem.** Check it before reading anything else in the same sample.

## What the surface has already found

### `session.js` evaluated twice — a known failure mode, reached by accident

`asset.session` read **2** on a single `/odoo` load under `HttpCase`. That
category has exactly **1** call site, at module scope in `static/src/session.js`,
so the count is a count of module evaluations: the body ran twice.

**This is not a new finding.** `ESM_BUNDLING.md`'s Failure modes table already
carries the row — *"Parent + satellite each load their own copy of the same
`@web/*` module"* — and names the diagnostic in as many words: **"add fingerprint
logger to module body; two distinct `MODULE LOADED` events means two
evaluations."** A module-scope probe IS that fingerprint logger. This surface
re-derived a documented symptom without recognising it, which is worth recording
precisely because the campaign's recurring failure is acting on a premise the
owner doc had already settled.

The mechanism, for the record: esbuild walks the import graph **from disk**, so a
bundle inlines dependencies it does not declare. `web.assets_tests` declares four
test-helper globs, which import `@web/env`, which imports `@web/session`
(`env.js:17`). `_esbuild_entry_lines` (`odoo/tools/assets/esbuild.py`) then
registers only `self.native_modules` — the *declared members* — so the inlined
copy runs but is never registered, `registerNativeModules` never sees a specifier
bound to a different object, and no `module_rebind` fires.

**The manifest is not at fault.** `session.js` is a member of **2** of web's
bundles (`assets_frontend_minimal`, `_assets_core`); a third mention is a
`("remove", ...)` in `assets_frontend_lazy`, which `ESM_BUNDLING.md` documents as
deliberately preventing this class of split for the frontend. That removal cannot
help here, because the duplication is created by esbuild's graph walk rather than
by bundle membership.

**It does not reach production.** `web.conditional_assets_tests` renders the
bundle only under `'tests' in debug or test_mode_enabled`
(`views/webclient_templates.xml`), and `_has_esm_test_satellites` makes the
page's import map answer the same question — with its own comment on why a
production page must not advertise test specifiers. So the duplication is
test-mode-only by construction, which is what the earlier reading here could not
establish and wrongly left open.

**Why it still matters in test mode** is the consequence the Failure modes row
names: `patchWithCleanup(Klass.prototype, …)` silently does nothing when the test
bundle holds a different `Klass` than the code under test. That is a wrong test
that passes, not a visible break. The documented fix is to wire the satellite
import through the parent's self-bridge (`prod_import_map[alias] = shim` in
`_get_esm_nodes_prod`, `ir_qweb_assets.py`) — owner: `ESM_BUNDLING.md`.

## Every component that renders when a list view opens

The stamper's payoff: the same interaction as above, with all 207 component
`setup()`s stamped, so the render profile covers the whole tree rather than the
14 hand-instrumented components. FROZEN at `92a83f0b495`, 3 active partners.

| Component | Renders | | Component | Renders |
|---|---|---|---|---|
| `ErrorHandler` | 11 | | `Dropdown` | 6 |
| `Field` | 9 | | `CheckBox` | 4 |
| `LoadingIndicator` | 3 | | `Transition` | 3 |
| `ImageField` | 3 | | `ListRecordRow` | 3 |
| `MultiRecordController` | 2 | | `Layout` | 2 |
| `ControlPanel` | 2 | | `SearchBar` | 2 |
| `SearchBarMenu` | 2 | | `ActionContainer` | 1 |
| `View` | 1 | | `WithSearch` | 1 |
| `CogMenu` | 1 | | `ActionMenus` | 1 |
| `NavBar` | 1 | | `Pager` | 1 |
| `ListRenderer` | 1 | | `ListAggregatesRow` | 1 |

### A count is per LABEL, not per instance

`useRenderCounter` increments one key per label, so a component mounted N times
contributes N even if each instance rendered once. `Field` at 9 is 3 rows x 3
arch fields, `CheckBox` at 4 is 3 rows plus the header select-all, and
`ImageField` at 3 is one avatar per row — all one render each. Reading any of
those as "rendered 9 times" would be wrong.

**So the signal to look for is a count above 1 on a component the view mounts
ONCE.** Five qualify here: `MultiRecordController`, `Layout`, `ControlPanel`,
`SearchBar` and `SearchBarMenu` all render **twice** opening a single list view.
`ListRenderer` renders once beside them, so the second pass stops at the
renderer — prop diffing is doing its job — and what repeats is the control-panel
chain.

### Diagnosed: it is the designed cost of `lazy: true`, and the benefit is conditional

The count alone could not settle it — two renders on first mount can be
legitimate. The ordered SEQUENCE could. Instrumenting the chain with
`onWillRender` + `onMounted` and the model's row count
(`static/tests/views/control_panel_render_budget.test.js`):

```
pass 1   MultiRecordController [rows=0]  Layout  ControlPanel  SearchBar
pass 2   MultiRecordController [rows=3]  Layout  ControlPanel  SearchBar  SearchBarMenu
then     MOUNTED:SearchBarMenu … MOUNTED:MultiRecordController
```

**Root cause, in the source.** `useModelWithSampleData` (`model/model.js`) does
not await the load when the model is lazy:

```js
onWillStart(() => {
    const prom = load(component.props);
    if (options.lazy) {
        prom.catch(…);   // NOT returned — onWillStart does not await
    } else {
        return prom;     // returned — onWillStart awaits
    }
});
```

and `computeModelOptions` (`views/view_utils.js`) turns that on precisely for a
view that has a control panel:

```js
lazy: !env.config.isReloadingController && !env.inDialog && !!display.controlPanel
```

So the second render is **intended**: render the chrome immediately, re-render
when records arrive. The chain that renders twice is exactly the chrome the flag
names. This is a designed trade, not waste — the earlier reading of it here as
discarded work was wrong.

**What makes the controller re-render at all is documented already**, in
`STATE_MANAGEMENT.md`:
*"`useModelWithSampleData` installs no listener of its own. A controller already
wraps its model in `useState`, so its own reads subscribe it."* `list_controller.js` does exactly that —
`this.model = useState(useModelWithSampleData(...))` — so when the lazy load
populates the root, the controller's own subscription re-renders it. The
mechanism is not new here; what is new is the *shape* it produces on initial
mount, and the latency bet below.

**The benefit is real, and it is conditional on load latency.** Both cases are
measured, by holding `web_search_read` on a `Deferred`:

| | fast load | slow load |
|---|---|---|
| passes | 2 | 2 |
| first pass reaches `SearchBarMenu` | **no** — aborts partway | **yes** — completes |
| anything mounts between the passes | **no** | **yes — the whole chain** |
| what the first pass bought | nothing | the control panel on screen |

On a slow load the design does exactly what it is for: the chain renders once
with an empty model, **mounts**, and the user sees the control panel while the
records are still in flight; one further pass follows when they arrive, mounting
nothing.

On a fast load the records land *during* the first pass. OWL discards the
in-progress fiber — which is why `SearchBarMenu`, unconditional in
`search_bar.xml`, never appears in it — and re-renders. Nothing paints in
between, so that pass is pure cost.

**So "twice" is not a defect and not free: it is a bet on latency that a
developer machine always loses.** A mock server and a local page both resolve
the load before the initial mount fiber can patch, so local profiling sees only
the cost and never the payoff. Any figure taken here understates the design's
value and overstates its waste.

**Ruled out by measurement, not by reading.** The search model's `UPDATE` bus
never fires on this path (instrumented; absent from the sequence). No component
calls `this.render()` (patched; never hit). And the transient write in
`useSearchBarToggler` — `showSearchBar: false` immediately corrected to
`!ui.isSmall` in `setup()`, which looks exactly like the transient
`LIST_EDIT_RENDER_COST.md` found — is **not** the cause: seeding the state with
its final value changed the sequence not at all. That fix was tried and reverted.

## Gate posture

`addons/web` is on `COMMUNITY_NO_CONSOLE_MODULES`, so `console.log` is an eslint
**error** here and the `eslint` floor is exact. `asset_log.js` is the one
sanctioned exception, carrying a file-level
`eslint-disable no-console -- dedicated asset logging utility`. Probes go
through it; a bare `console.log` added anywhere else in `web` moves the floor.

## Removal

The whole surface comes out at the end of the campaign. Order matters: the gates
reference the code, so deleting code first turns a tidy removal into a red lane.

**Goes:**

1. Done: the stamper and its directory went with the tooling tree in `7b0f58cb517f`,
   and no `// trace-stamp` line is left in any `static/src`.
2. The structured sink in `core/utils/asset_log.js`: `_record`,
   `_traceArmedAtInit`, `log.active`, and the `__odooTrace` / `__odooTraceStats`
   / `__odooTraceReset` globals.
3. The two RPC guards in `core/network/rpc.js` go back to `rpcLog.enabled()`.
   `active()` exists only because the sink does; with the sink gone the console
   gate is again the whole question. **This is a behaviour change to re-verify,
   not a mechanical revert** — those guards were on `enabled()` before, and that
   is precisely what made `rpc.*` invisible.
4. The four campaign namespaces and their call sites: `component` (`env.js`),
   `service` (`env.js`), `view` (`views/view.js`), `field` (`fields/field.js`).
5. `static/tests/core/utils/trace_choke_points.test.js` and
   `tests/test_trace_probes.py` (plus its line in `tests/__init__.py`) — both
   test the probes, so neither outlives them.
6. Every assertion in `factcheck.sh` that names the surface, and this page.
   Removing the page while leaving its assertions is the failure mode to avoid:
   they read files that no longer exist and fail as a missing-file error rather
   than as an obviously deleted check.

**Stays:**

* `static/tests/views/control_panel_render_budget.test.js`. It uses no probe —
  it patches component prototypes directly — and what it pins is *production*
  behaviour: the `lazy: true` render shape and the latency bet behind it. Its
  value survives the campaign that found it.
* Nothing needs migrating for the `session.js` double evaluation: it is an
  instance of a row `ESM_BUNDLING.md` already carries, not a new fact. Deleting
  this page loses no knowledge there.
* `useRenderCounter` and the 14 hand-placed probes, which predate the campaign.

**Then:** decide per page whether a figure it cites should be re-derived from a
surviving mechanism or frozen to the commit that measured it — §1.4. A figure whose probe is gone and that is not frozen is a figure
nothing holds. The two readings on this page are already frozen; anything that
quoted them elsewhere is not.
