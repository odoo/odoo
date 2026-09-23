# View Teardown Cost — Investigation & Decision Record

Status: **Investigated. Not pursued — no code changed.** Date: 2026-08-09.
Scope: the DOM teardown half of a backend view navigation.

## Why this was opened

Profiling a cold view navigation (navigate away, then back) put `remove` at
**8.9% of self time** — the single largest application-attributable entry, ahead
of every OWL function and of all application code. Nothing in
`machine_doc_v1` explained it, so it looked like the most promising unexplored
lead in the render path.

Measured with the render bench's attribute mode (tooling/bench/render_bench,
deleted with `tooling/` on 2026-09-11) and with a CPU profile
taken over six repeated navigations to an 80-row `res.partner` list.

## What `remove` actually is

Not application code. The caller chain resolves entirely inside the vendored
OWL bundle, bottoming out in the native `Element.remove()`:

```
remove [native]
  └─ remove [owl.es.js:1101]     ← blockdom, recursive over the block tree
    └─ remove [owl.es.js:1057]
      └─ remove [owl.es.js:2708]
        └─ remove [owl.es.js:69]
          … recursion …
            └─ patch  [owl.es.js:47]
```

Line numbers are 1-based, as an editor shows them. They were first recorded
one lower across the board — CDP reports `CallFrame.lineNumber` **0-based**,
and the profile was transcribed without converting. Every frame still resolved
to a real `remove`/`patch`, one line further down, which is exactly why the
error survived a reading: the chain was right and only the coordinates were
off. Add 1 when copying a frame out of a profile.

It is blockdom tearing the outgoing view's block tree down node by node when the
action manager patches the new controller in. `_destroy` / `beforeRemove`
(component lifecycle) are separate and cheap by comparison — the hottest
`_destroy` node measured **1.2 ms** self.

## Measured scaling

Same navigation, two list sizes, six navigations each, 60µs sampling:

| List | Elements in action manager | `remove` per navigation | Share of busy CPU | Navigation median |
|---|---|---|---|---|
| 80 rows (640 cells, 16 elements/row) | 1444 | **13.95 ms** | 10.1% | 211.7 ms |
| 10 rows (80 cells, 16 elements/row) | 259 | **7.81 ms** | 12.3% | 75.4 ms |

**Teardown is not linear in node count.** 5.6× the elements costs 1.8× the
teardown, so roughly **half of it is fixed** — the control panel, navbar and
action-manager chrome, not the rows. The row-dependent part of an 80-row list is
only ~6 ms.

## Decision

**Do not pursue.** Three independent reasons:

1. **The hot code is vendored.** blockdom's recursive removal lives in
   `owl.es.js`. `static/lib/` is DO-NOT-MODIFY, and patching a vendored
   library to save single-digit milliseconds is not a trade this fork should
   make.
2. **The addressable share is small.** The only lever we own is emitting fewer
   DOM elements per row (currently 16 elements for 8 cells). Halving that — a
   broad, regression-prone change across the list templates and every renderer
   subclass — would recover at most ~3 ms of a 212 ms navigation.
3. **The fixed half is not the list at all.** Even an empty view pays ~7 ms, so
   list-side work cannot remove most of it.

## If revisited

- The real prize in a navigation is the other 90%, not this. Re-profile the whole
  `doAction` path before returning here.
- Keeping the outgoing controller alive (view caching / reuse instead of destroy)
  would skip teardown *and* the rebuild on back-navigation. That is an
  action-manager architecture change, far larger than this document's scope, and
  it should be justified against the full navigation cost rather than against
  `remove` alone.
- Re-derive the numbers before quoting them; they are a point-in-time reading of
  one machine, headless Chromium, and one 80×8 list.

Key files: `webclient/actions/action_service.js` (controller swap) ·
`static/lib/owl/owl.es.js` (blockdom `remove`, vendored) · the render bench
(gone with `tooling/`).
