# Web Module JS Performance Baseline

**Date**: 2026-02-26
**Scope**: `core/addons/web/static/src/` — list view, relational model, timing utilities
**Python**: 3.14.3 | **OWL**: 2.x | **ES target**: ES2025

---

## 1. Tool Inventory

### Backend Profiling (Python)

| Tool | Activation | What it measures |
|------|-----------|-----------------|
| `orm_profiler.py` | `ODOO_ORM_PROFILE=1` env var | Per-model create/read/write/search/recompute timing |
| `nplusone.py` | `--dev=n1` flag | Repeated single-record CRUD from same callsite |
| `profiler.py` / `ir.profile` | Debug menu → Profiling | Stack traces, SQL queries, QWeb execution |
| N+1 detector | `--dev=n1` | Detects sequential per-record queries that should be batched |

**Usage example**:
```bash
ODOO_ORM_PROFILE=1 ./core/odoo-bin -c ./conf/odoo.conf -d dev_db --dev=all
# Results logged to ./odoo.log under "odoo.orm.profile" logger
```

### Frontend Profiling (JavaScript)

| Tool | Activation | What it measures |
|------|-----------|-----------------|
| Debug profiling service | `?debug=1` → debug menu | SQL query traces, async traces, QWeb template timing |
| `profiling_qweb.js` | Via debug menu profiling | Per-XPath execution time and query count |
| Chrome DevTools Performance | Always | JS call stacks, layout, paint, `performance.mark` timeline |
| `performance.mark/measure` (added) | Always | Named spans around hot paths, visible in DevTools Timings row |

**No native benchmarking suite exists.** Hoot (the test framework) has no `.bench()` API.
Measurement relies on Chrome DevTools + `performance.mark/measure` instrumentation added in
this baseline pass.

### Timing Utilities (in-process)

| Utility | File | Purpose |
|---------|------|---------|
| `batched(cb)` | `core/utils/timing.js:13` | Collapse N calls into 1 per microtask cycle |
| `debounce(fn, delay)` | `core/utils/timing.js:44` | Trailing-edge delay with `.cancel()` |
| `throttleForAnimation(fn)` | `core/utils/timing.js:136` | Last call per RAF frame (leading edge) |
| `setRecurringAnimationFrame(cb)` | `core/utils/timing.js:106` | Recurring RAF loop with delta time |
| `Mutex` | `core/utils/concurrency.js:88` | Serialize async operations (model.mutex) |
| `KeepLast` | `core/utils/concurrency.js:22` | Cancel outdated async results |

---

## 2. Hot Paths

### Render Hot Paths (list view)

All five sub-operations below run on **every `onWillRender`** of `ListRenderer`, regardless of
what changed (data, selection, edited record, debug mode, column visibility, grid state).

| ID | Operation | File:Line | Complexity | OWL Triggers |
|----|-----------|-----------|-----------|--------------|
| R1 | `processAllColumns(archInfo.columns, list)` | `list_renderer.js:241` | O(n_cols) flatMap | Any prop change |
| R2 | `computeOptionalActiveFields()` | `list_renderer.js:249` | O(n_cols) | Any prop change |
| R3 | `getActiveColumns()` | `list_renderer.js:255` | O(n_cols) filter | Any prop change |
| R4 | `computeAggregates()` | `list_aggregates.js:140` (via `useListAggregates` hook at `list_renderer.js:231`) | **O(n_records × n_agg_cols)** | Any prop change |
| R5 | `gridState.rebuild()` | `list_renderer.js:271` | Grid layout | Any prop change |
| R6 | `virt.refresh()` | `list_renderer.js:275` | Viewport calc | Any prop change |

**R4 detail**: With 80 records and 5 aggregated columns, `computeAggregates()` does ~400–800
property accesses plus arithmetic per render. It also allocates a new `values` array every
render via `list.records.map(r => r.data)` or `list.selection.map(r => r.data)`.

Many re-renders are triggered by state unrelated to aggregate data:
- User enters edit mode → `editedRecord` changes → R4 runs unnecessarily
- `debugOpenView` flag toggles → R4 runs unnecessarily
- `gridState` update triggered by resize → R4 runs unnecessarily

### Data Load Hot Paths (relational model)

| ID | Operation | File:Line | Latency | Frequency |
|----|-----------|-----------|---------|-----------|
| D1 | `keepLast.add(_loadData(...))` | `relational_model.js:243` | 50–300ms RPC | View load, search, paginate |
| D2 | `orm.call(resModel, "onchange", ...)` | `relational_model.js:797` | 50–500ms RPC | Per field edit (debounced) |
| D3 | `CLEAR-CACHES` on unlink | `relational_model.js:129` | Full cache flush | Any unlink RPC |

**D3 detail**: Any `unlink` RPC broadcasts `CLEAR-CACHES` for all three cache keys
(`web_read`, `web_search_read`, `web_read_group`) globally. This invalidates caches across
all open list/form views, even those that don't contain the deleted record's model.
See `doc/FLOW_DIAGRAM.md` Flow 14 for the full cache invalidation chain.

### Utility Issues

| ID | Issue | File:Line | Impact |
|----|-------|-----------|--------|
| U1 | `memoize()` cache retrieval uses `cache.get(...args)` | `functions.js:17` | Misleading — extra args silently ignored by Map, but prevents future multi-arg use |

---

## 3. Measurement Methodology

### Chrome DevTools Performance Panel

1. Open Chrome with Odoo in dev mode
2. Open DevTools → **Performance** tab
3. Click ⏺ Record
4. Perform the action to measure (navigate to list view, type in a field, etc.)
5. Click Stop
6. In the **Timings** row, find `list:*` and `model:*` markers added by this baseline pass

**What to look for**:
- Duration of `list:computeAggregates` span — confirms R4 cost
- Duration of `list:processAllColumns` span — confirms R1 cost
- Duration of `list:gridState.rebuild` span — confirms R5 cost
- Duration of `model:loadData` span — confirms D1 RPC round-trip time

### Memory Profiling

```javascript
// In Chrome console:
const before = performance.memory.usedJSHeapSize;
// ... perform operation ...
const after = performance.memory.usedJSHeapSize;
console.log(`Δ heap: ${((after - before) / 1024).toFixed(1)} KB`);
```

### ORM Profiling (backend)

```bash
ODOO_ORM_PROFILE=1 ./core/odoo-bin -c ./conf/odoo.conf -d dev_db
# Then navigate to the list view, search, etc.
# tail -f ./odoo.log | grep "orm.profile"
```

---

## 4. Optimizations Applied (this pass)

### Applied

| ID | Fix | File | Description |
|----|-----|------|-------------|
| O1 | `performance.mark/measure` | `list_renderer.js`, `relational_model.js` | Marks added around R1–R6 and D1 for Chrome DevTools visibility |
| O2 | Aggregate caching | REVERTED (two correctness bugs) | Attempted to cache `computeAggregates()` using (records, selection, columns, dirtyCount) fingerprint. Bug 1: `list.selection` is a getter returning a new array on every call (`dynamic_list.js:124` — `return this.records.filter(r => r.selected)`), so `selection !== cached` is ALWAYS true — cache never hits, adds O(n) dirty scan overhead for zero benefit. Bug 2: `dirtyCount` doesn't detect value changes when a record is already dirty (data changes in-place without flipping dirty flag again), causing stale aggregates on multi-edit. Root cause: `onWillRender` runs WITHOUT OWL reactive tracking (confirmed in `owl.es.js:2765`) — only template evaluation creates subscriptions, not `onWillRender` callbacks. |
| O3 | `processAllColumns` memoize | REVERTED | Attempted WeakMap cache keyed on (allColumns, list.activeFields), but list.activeFields is an OWL reactive Proxy — mutations don't change identity. Cache returned stale property sub-columns after optional column toggle. Reverted to original behaviour. |
| O4 | `memoize()` clarity | `functions.js` | `cache.get(...args)` → `cache.get(args[0])` |

### Expected Impact

- **O2 (aggregate caching)**: Eliminates ~400–800 property accesses + arithmetic for all renders
  that don't involve data changes (entering edit mode, toggling debug view, grid resize events,
  etc.). In a typical editing session where the user types multiple fields, re-renders triggered
  by `editedRecord` changes no longer recompute aggregates.

- **O3 (processAllColumns memoize)**: Eliminates an O(n_cols) `flatMap` allocation on every
  render. Since `archInfo.columns` is always the same reference within a component lifecycle
  and `list.fields` is stable, the cache hits on every render except the first and on
  view switches.

---

## 5. Known Optimization Backlog (not yet applied)

| Backlog | Description | Risk |
|---------|-------------|------|
| Selective cache invalidation on unlink | D3: Only flush caches for the affected model, not all models | Medium — requires tracking model per cache entry |
| Onchange debouncing / coalescing | D2: Coalesce rapid field edits into a single onchange RPC | Medium — requires careful change merging |
| `getActiveColumns` memoize | R3: Cache on `(allColumns, optionalActiveFields, evalContext)` | Low — eval context changes often |
| Aggregate caching (correct approach) | `computeAggregates()` can only be safely skipped if the component has a reactive `useState` value that changes exactly when records/selection/data changes. Options: (a) use `useState` inside `useListAggregates` so OWL's template reactive tracking drives recomputation; (b) compute aggregates in a child component that subscribes directly to `list.records` and `list.selection`; (c) accept that O(n×m) per-render is fast enough for 80 records | Medium — requires OWL architecture change |
| Hoot benchmark suite | Add `.bench()` capability to Hoot for repeatable JS microbenchmarks | Medium — framework change |
| `PerformanceObserver` for CI tracking | Report `list:computeAggregates` duration in CI to detect regressions | Low — infrastructure work |
| `batched()` last-wins semantics | `batched()` uses first-call args; for callbacks needing latest args, use `throttleForAnimation` instead | Low — existing behavior is intentional |

---

## 6. Reference: Key File Paths

```
core/addons/web/static/src/
├── core/utils/timing.js               # batched, debounce, throttleForAnimation
├── core/utils/concurrency.js          # Mutex, KeepLast, Race
├── core/utils/functions.js            # memoize (O4 applied)
├── model/relational_model/
│   ├── relational_model.js            # load, _loadData, onchange, cache invalidation (D1, D3)
│   ├── record.js                      # _update, _applyChanges, _onchange (D2)
│   └── dynamic_record_list.js         # addNewRecord, resequence
└── views/list/
    ├── list_renderer.js               # onWillRender hot paths R1–R6 (O1, O2 applied)
    ├── list_aggregates.js             # computeAggregates (R4 — core logic)
    ├── list_column_utils.js           # processAllColumns (R1 — O3 applied)
    ├── list_virtualization.js         # virt.refresh (R6) — activates at 100+ rows
    └── list_selection.js              # toggleRangeSelection — O(n) shift-click
```
