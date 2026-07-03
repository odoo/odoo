# Scope-protection prototype

Exploring an Owl 3 replacement for `hooks.js` `_protectMethod`: stopping a
destroyed component's async continuation from running, keyed on an Owl `Scope`
(works for components *and* plugins), without threading a scope at every call
site.

## Files

- `scope_protection.js` — the module. Two mechanisms:
  - **(A) recommended** — `protect(promise, scope)` / `protectMethod(scope, fn)`:
    returns a *thenable* bound to the consuming scope. `await` intercepts a
    thenable's `.then`, so awaited calls are guarded at any depth. Scope is
    captured once at the injection boundary (`useScope()` in setup).
  - **(B) experimental** — `installThenPatch()` + `installEntrySeeding()`: the
    "monkeypatch global `Promise` + seed the ambient scope at Owl entry points"
    idea. Kept only to observe its limitation.
- `../../tests/core/utils/scope_protection_probe.mjs` — self-contained node
  harness (mock Scope) proving the design points.

## The load-bearing finding

Native `await` on a native promise does **not** call a monkeypatched
`Promise.prototype.then` — only explicit `.then()` chains do. `await` on a
*thenable* **does** call its `.then`. Hence (B) is blind to the async/await that
dominates Odoo code, and (A) (a thenable at the boundary) is the mechanism that
actually works.

## Run

```bash
# fast, no server: the design experiments (D1..D4)
node addons/web/static/tests/core/utils/scope_protection_probe.mjs
```

In-browser cases to try next:

- **(a) dead-component RPC** — wire `protectMethod(useScope(), rawFn)` into a
  `useService`-style hook, mount a component, fire an RPC, destroy before it
  resolves; assert the continuation throws `AbortError` (swallowed by
  `error_service.js`).
- **(b) interference check** — only relevant to (B): call `installThenPatch()`
  at boot and run the web test suite; watch for breakage in framework/vendored
  promise chains. (A) needs no such check — it is opt-in per call.
- **(c) foreign-promise edge** — only relevant to (B): run a chart.js/luxon flow
  under a seeded scope, destroy mid-op, see whether the library's own `.then`
  continuations get aborted. (A) never wraps unrelated promises (see probe D4).
