# State Management Patterns

> Decision tree and reference for choosing the right state pattern in `web/static/src/`.

## Canonical primitives

Translation between industry vocabulary and the OWL primitives in this codebase:

| Concept | OWL-native spelling | Industry analog |
|---------|---------------------|-----------------|
| Component-local signal | `useState({ ... })` | React `useState` / Vue `ref` / Solid `createSignal` (component-scoped) |
| Shared signal | `reactive({ ... })` returned from a service's `start()` | Vue 3 `reactive` / Solid store / Svelte 5 `$state` in module scope |
| Shared signal class | `class extends SignalStore` | Mobx observable class / Vue `reactive` on `this` / Pinia store class |
| Component-scoped effect | `useEffect` (from `@odoo/owl`) — fires only while owning component is mounted | React `useEffect` / Solid `createEffect` inside a component |
| Process-scoped effect | `effect(cb, deps)` (from `@web/core/utils/reactive`) — fires until garbage-collected; used by services and record observers | Solid `createEffect` at module scope / Vue 3 `watchEffect` / Svelte 5 `$effect` |
| Computed / derived value (on a class) | Plain JS getter reading signals (OWL is Proxy-based — getters track automatically) | Solid `createMemo` accessed via class field / Vue `computed` ref on `this` |
| Computed / derived value (free-standing) | **No OWL equivalent — see below** | Solid `createMemo` / Vue `computed` / Svelte 5 `$derived` |

`useEffect` cleans up on unmount; `effect(cb, deps)` survives as long as the
captured `deps` proxy does. Not interchangeable.

### There is no free-standing computed, and one cannot be added

Vue, Solid and Svelte can offer a module-scope `computed`/`createMemo`/`$derived`
because they maintain a global *active effect* stack: whoever is currently
rendering is ambient, so a value computed anywhere can register the reader that
pulled on it.

**OWL has no such stack.** A subscription is keyed on the *proxy a read travels
through*, at the moment of the read (`observeTargetKey`, `static/lib/owl/owl.es.js`),
and a proxy built with no callback — which is what bare `reactive(obj)` and
`SignalStore`'s own `this` are — returns early and registers nothing. So a
helper of the shape

```js
// cannot work in OWL
const fullName = derived(() => `${store.first} ${store.last}`);
```

closes over the store's own callback-less proxy. Every reader gets a correct
*value* and no *subscription*: the component renders once with the right text
and never updates. That is the same defect documented under *A bare `reactive()`
handed down as a prop subscribes NOBODY* below, in a shape that looks like a
framework primitive.

Both halves are pinned by
`static/tests/core/utils/reactive.test.js` — "a subscription belongs to the
proxy the read went through" and its passing counterpart.

**What to use instead:**

| Situation | Form |
|---|---|
| Derivation belongs to an instance | Plain getter on the `SignalStore` (``record.dirty``, ``coordinator.isSaving``) |
| A component derives across several sources | `useState()` each source in `setup`, then a getter on the component — the reads then travel through that component's own proxy |
| A derivation must be shared between components | Put it on the shared `SignalStore` or the service's `reactive()` as a getter, and let each component `useState()` that object |

Getters are not memoized; OWL batches renders within a tick.

**SignalStore.**  ``SignalStore`` is the canonical class name and the only
export; there is no `Reactive` alias, so
`import { Reactive } from "@web/core/utils/reactive"` fails at module-load
with a native "no such export" error.  25 production class declarations fork-wide
use ``extends SignalStore``.

## Keyed asynchronous work

`KeepLastByKey` in `static/src/core/utils/concurrency.js` retains guards only
while their latest task is pending. Settlement releases the key; cancellation
releases it immediately, even when the default superseded promise stays pending.
Cleanup checks both guard identity and generation so an older task cannot remove
a replacement. Cancellation detaches guards before invoking abort handlers, which
may synchronously register new work. `forget(key)` is equivalent to `cancel(key)`.
These contracts are exercised by `static/tests/core/utils/concurrency_keyed.test.js`.

The kanban progress-bar hook owns its count, aggregate and per-group request
guards. Destruction cancels all three alongside its timers and subscriptions.
Pending filter and root-load continuations check destruction before changing
bar state, notifying the model or initiating follow-up work. Checks after request
settlement also cover results delivered just before teardown. Regression coverage
lives in `static/tests/views/kanban/progress_bar_hook.test.js`.

## Decision Tree

```
Where does this state live?
│
├─ Single component only?
│  └─ useState({ ... })
│     Examples: pager_indicator.js, signature_dialog.js, file_input.js
│
├─ Shared across features (via service)?
│  └─ reactive({}) in service start()
│     Examples: notification_service.js, file_upload_service.js,
│               frequent_emoji_service.js
│
├─ ORM entity (record, list, group)?
│  └─ class extends SignalStore
│     Examples: datapoint.js, record.js, static_list.js, group.js
│
├─ Stateful UI behavior with computed logic?
│  ├─ Derivation naturally belongs to an instance?
│  │  └─ Express it as a getter on a SignalStore / shared reactive({})
│  │     — the Proxy tracks dependencies automatically, no explicit
│  │     computed primitive needed.
│  │     Avoid ``reactive({ get x(){}, set x(v){…mutate other state…} })``
│  │     with side-effecting setters — that's an effect masquerading
│  │     as state.  Use useEffect / effect instead.
│  └─ Derivation spans multiple sources?
│     └─ useState() each source in setup(), then a getter on the
│        component. There is NO free-standing computed primitive —
│        a value derived outside a component subscribes nobody,
│        see "There is no free-standing computed" above.
│
└─ >3 named states with guards?
   └─ State machine (document first, implement only if bug motivates it)
      See: Form Save State Diagram below
```

## Pattern 1: `useState()` — Component-Local State

Wraps a plain object in OWL reactivity. Mutations trigger re-renders of the
owning component only. This is the default choice.

```javascript
setup() {
    this.state = useState({ count: 0, loading: false });
}
// Mutate directly:
this.state.count++;
this.state.loading = true;
```

**When to use**: State that belongs to one component and doesn't need to be
shared. Form field values, toggle flags, pagination state, loading indicators.

**Files**: ~74 occurrences across components/, views/, webclient/.

## Pattern 2: `reactive()` — Service-Level Shared State

Creates a reactive object in a service's `start()` method. Returned as part of
the service API so any component can `useService()` and read/write it.

```javascript
// In service:
const uploads = reactive({});
return { uploads, add(file) { uploads[id] = file; } };

// In component:
const fileUpload = useService("file_upload");
// fileUpload.uploads is reactive — reads trigger subscriptions
```

**When to use**: State shared across multiple unrelated components. Notifications,
file uploads, emoji frequency, currency rates, user preferences.

**Key files**:
- `core/file_upload/file_upload_service.js` — reactive upload tracking with progress
- `ui/notification/notification_service.js` — reactive notification dict
- `components/emoji_picker/frequent_emoji_service.js` — reactive usage counters with localStorage sync

### Browser-storage schemas have a single owner

Two groups of keys survive a reload, and each is owned by exactly one module —
never read or written by raw string literal from anywhere else:

| Module | Keys | Notes |
|---|---|---|
| `webclient/actions/action_storage.js` | `current_action`, `current_state`, `current_lang` | The action-restore cache. Reads are **total**: missing, empty, or corrupt all resolve to `{}`, because the URL is the source of truth. `withTemporaryEntry()` performs the synchronous swap that seeds a new tab (sessionStorage is copied into an auxiliary browsing context at open time). |
| `webclient/menus/menu_usage.js` | `webclient_menu_usage:<uid>` (localStorage) | What the user opens: `{xmlid: {n, t}}`, recorded by `menu_service.selectMenu` once the action is ready, ranked with a seven-day half-life, bounded at fifty entries. Read by the palette's `/` provider on an empty query and by `HomeMenu.recentApps`. Per user by key, never sent to the server. |
| `webclient/menus/menu_storage.js` | `webclient_menus`, `webclient_menus_version`, `webclient_menus_hash` (localStorage), `menu_id` (sessionStorage) | The menu tree cache. Written as a unit with the **version last** (it gates reuse on the next boot); a corrupt read discards the whole trio. `menu_id` is the current app, written by `menu_service` and read by `webclient.js` — the one key that was still open-coded at both ends. |

Both are centralised here rather than open-coded per consumer, so the parse
policy (what a corrupt or missing value resolves to) is uniform across readers.

### A bare `reactive()` handed down as a prop subscribes NOBODY

`reactive(target)` with no second argument uses OWL's `NO_CALLBACK`, and
`observeTargetKey` **returns early** for it (`static/lib/owl/owl.es.js`). A
component that receives such a proxy as a prop and reads it during render is
therefore not subscribed at all: the value changes and nothing re-renders.

Subscriptions are keyed on the **raw target**, not on the proxy. So the fix is to
re-target — `useState(obj)` returns `reactive(rawTarget, thisComponentsRender)`,
and a write through *any* proxy of that raw target then notifies you.

Two instances were live in this addon until 2026-08-09, both invisible while the
blanket forced render was papering over them:

| Where | Shape | Fix |
|---|---|---|
| `views/kanban/progress_bar_hook.js` | `groupInfo.activeBar` was a **getter closed over `self`**, the proxy that seeded the group — no reader could ever subscribe | plain reactive property synced by `_syncActiveBar`; `KanbanRenderer` / `KanbanHeader` re-target with `useState` |
| `views/kanban/kanban_renderer.js` | `this.props.quickCreateState \|\| useState({...})` — the controller always supplies the prop, so `useState` was never reached | `useState` called unconditionally on whichever object is used |

**Spotting it.** `props.X || useState(...)` is the mechanical tell; a fork-wide
sweep found no third instance. The harder shape is a getter inside a reactive
closing over an outer `this`/`self` — grep `const self = this` near `reactive(`.
Not every such closure is a fault: `kanban_controller.js`'s `quickCreateState`
getter reads `this._groupId`, which resolves through whichever proxy is reading,
and its `self` is used only by the setter for a side effect.

**A green suite does not clear this.** Both instances had passing tests —
something else re-rendered at the same moment, so the behaviour was right by
coincidence rather than by subscription. What changes when you fix it is that the
dependency becomes stated.

## Pattern 3: `SignalStore` Base Class — Model Entities

Classes extending `SignalStore` (`core/utils/reactive.js`) auto-wrap
`this` in `reactive()` during construction.  Used for ORM data
structures where any property mutation must propagate to the UI.

```javascript
class DataPoint extends SignalStore {
    constructor(model, config, data) {
        super();           // returns reactive(this)
        markRaw(config);   // exclude heavy config from reactivity
        this.setup(config, data);
    }
}
```

`SignalStore` is the only export; there is no `Reactive` alias.

**Inheritance chain** (actual class names in code):

```
SignalStore
    └── DataPoint
          ├── RelationalRecord        (record.js — exported as `RelationalRecord`, not `Record`)
          ├── StaticList
          ├── Group
          └── DynamicList
                ├── DynamicRecordList
                └── DynamicGroupList
```

`DataPoint` `extends SignalStore` directly.

**Critical detail**: Use `markRaw()` on large objects that don't need reactivity
(field definitions, active fields, configs). Without it, OWL deep-wraps every
nested property, causing massive overhead.

**Key files** — the 4 direct `SignalStore` subclasses in `web`, plus the
`DataPoint` chain above:
- `core/utils/reactive.js` — `SignalStore` base class (3 lines of behavior)
- `model/relational_model/datapoint.js` — `DataPoint`
- `model/model.js` — `Model`
- `model/sample_data_coordinator.js` — `SampleDataCoordinator`
- `model/relational_model/urgent_save_coordinator.js` — `UrgentSaveCoordinator`
- `views/form/form_save_coordinator.js` — `FormSaveCoordinator`
- `components/dropdown/dropdown_hook.js` — `DropdownState`
- `model/relational_model/record.js` — `RelationalRecord extends DataPoint` (exported as `RelationalRecord`, NOT `Record`)

## Pattern 4 (discouraged): `reactive()` with side-effecting setters

Some call sites use `reactive({})` with JS getters/setters where the setter
triggers side effects on other reactive state:

```javascript
this.quickCreateState = reactive({
    _groupId: null,
    get groupId() { return this._groupId; },
    set groupId(id) {
        if (self.model.useSampleModel) {
            self.model.removeSampleDataInGroups();  // side effect
        }
        this._groupId = id;
    },
});
```

The setter is an effect pretending to be state: the dependency graph goes
opaque (nothing shows that mutating `groupId` clears sample data), every setter
call carries hidden downstream mutations, and side effects do not compose like
data flows.

**Preferred alternative** — plain state, side effect in a `useEffect` watching a
signal dependency:

```javascript
this.quickCreateState = reactive({ groupId: null });
useEffect(
    () => {
        if (self.model.useSampleModel) {
            self.model.removeSampleDataInGroups();
        }
    },
    () => [this.quickCreateState.groupId],
);
```

The one legitimate surviving use case is *caching* inside the getter
(memoize an expensive derivation) — that's not a state mutation and
remains fine on a `SignalStore` getter.

> **Pattern 4 sites.** Every surviving setter has a documented constraint
> that defeats the `useEffect` rewrite; **zero are open refactor targets**:
>
> | Site | Verdict |
> |---|---|
> | `views/kanban/kanban_controller.js` (`set groupId`) | ⛔ Canonical exception to Pattern 4. The setter MUST clear sample data synchronously on the same microtask as the `groupId` mutation, or sample records still paint while the quick-create form mounts. A previous `useEffect` migration (commit `19fb5d01bb81`) was reverted because deferred cleanup broke 3 sample-data integration tests in `kanban_view.test.js` ("empty grouped kanban with sample data and click quick create" and siblings). **This page is the rationale of record** — the source carries only a self-contained `eslint-disable` pointing back here, per the no-explanatory-comments rule. **Keep as-is.** |
> | `core/transition.js` (`set shouldMount`) | ⚠ Pattern 4 by syntax, but the setter implements a deliberate state-machine timing contract (`clearTimeout`, `prevState` tracking, `onNextPatch` scheduling). A `useEffect` rewrite changes observable timing. **Leave**. |
> | `core/transition.js` (`set shouldMount`, disabled-config branch) | ✗ Not Pattern 4. Pure passthrough `state.shouldMount = val`. |
> | `components/emoji_picker/emoji_picker.js` (`set searchTerm`) | ✗ Not Pattern 4. Delegation between `props.state` and `this.state`. |
> | `components/dropdown/_behaviours/dropdown_nesting.js` (`set isOpen`) | ⚠ Edge case — fires `BUS.trigger("dropdown-opened", this)` (fire-once-on-edge signal, not state mutation). `useEffect` rewrite would either fire too often or require a `prev`-tracking dance uglier than the setter. **Leave**. |
>
> Pattern 4 is a review vocabulary, not a backlog. For a new cross-state setter,
> ask whether it is the synchronous-timing exception (kanban kind), the
> state-machine timing kind (transition kind), or an effect masquerading as
> state. Only the third is a refactor.

## Model → renderer subscription: `useReactiveModel`

Reactive subscription is the **default**; the deep render on every
`ModelEvent.UPDATE` is the exception, and each model that still needs it says so.

- `Model` extends `SignalStore` and owns `_updateEpoch`, a counter bumped by
  every `notify()` (`model.js` — `this._updateEpoch++` right before the bus
  trigger).
- `useReactiveModel(model)` (exported from `model/model.js`) wraps the model
  in `useState()` and reads `_updateEpoch` in `onWillRender`, so the calling
  component subscribes to the epoch: every `model.notify()` re-renders it
  directly. Use it in renderers that snapshot derived state from the model
  (e.g. PivotRenderer's `getTable()`). Pivot and graph are on this pattern and
  carry no flag.
- `useModelWithSampleData` installs **no** listener of its own. A controller
  already wraps its model in `useState`, so its own reads subscribe it.

### There is no forced-render escape hatch

`useModelWithSampleData` briefly carried a `static forceRenderOnUpdate` opt-in
for the five views that still needed the blanket deep render. All five have since
been migrated and the branch is gone: **no model can ask for a forced render**.

Migrating a view meant some combination of three fixes, and the third is the one
worth remembering:

1. The controller wraps its model in `useState` — several did not, so their
   template reads of `model.hasData()` / `model.useSampleModel` subscribed
   nothing (`web_cohort`, `web_map`, `web_grid`, `web_gantt`).
2. The renderer takes `useReactiveModel(this.props.model)` instead of reading
   the raw prop, which tracks nothing for the reading component.
3. **Derived state rebuilt from `onWillUpdateProps` needs an epoch check.** A
   forced render fires `onWillUpdateProps` on children *even when their props
   are identical*, and that — not any subscription — is what re-ran
   `GanttRenderer.computeDerivedParams()` on every `notify()`. Without it the
   renderer rendered fresh output from stale mappings and 50 tests failed with
   no exception raised. The fix is `Model.updateEpoch`, which exists precisely
   for this: `computeDerivedParams` stamps the epoch it built from and
   `onWillRender` rebuilds when the model has moved on.

**Why the polarity was inverted.** As a global default the deep render silently
covered for state nothing subscribed to. Removing it surfaced a real defect in
the kanban progress bars: `activeBar` was a getter closed over the proxy that
happened to seed the group, so a component reading `groupInfo.activeBar` during
render could never subscribe to it — the value changed and nothing re-rendered.
It is now a plain reactive property kept in step by `_syncActiveBar`, and
`KanbanRenderer` / `KanbanHeader` re-target the prop with `useState` so their
reads are tracked. Measured on an 80×8 list, sort, pager, search facet,
select-all and a single-record edit render identically with and without the
blanket, so this was a correctness and clarity change, not a performance one.

## Record State Architecture

Records maintain a three-layer state model:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  _values    │    │  changes    │    │  data       │
│  (server)   │ +  │  (user)     │ =  │  (merged)   │
│             │    │  markRaw()  │    │  read by UI │
└─────────────┘    └─────────────┘    └─────────────┘
```

| Property | Source | Reactive? | Purpose |
|----------|--------|-----------|---------|
| `_values` | Server (read/write RPC) | No (markRaw) | Last-known server state |
| `changes` | User edits | No (markRaw) | Accumulated unsaved changes |
| `data` | `{..._values, ...changes}` | Yes | Merged view consumed by UI |
| `dirty` | Imperative plain field (set in `applyChanges`, `discard`, `loadLocked`) | Yes (reactive) | Whether record has unsaved edits. NOT computed from `changes` — `dirty=true` can coexist with an empty `changes` briefly during flow transitions. |
| `invalidFields` | Validation | Yes (Set) | Fields that failed validation |

**Save flow**: `changes` → RPC write → server returns new `_values` → `changes` cleared → `data` rebuilt.
**Discard flow**: `changes` cleared → `data` rebuilt from `_values` only → `dirty = false`.

**Edit-state owner (`RecordEditState`, `model/relational_model/record_edit_state.js`)**:
the editable-state layer — the pending-edit `ChangeSet`, the reactive `dirty`
signal, `invalidFields`/`unsetRequiredFields`, the char/text/html `textValues`
tracking, and the `savePoint` — is owned by a single `RecordEditState` instance
held at `record._editState`. The record exposes getters/setters
(`dirty`, `changes`, `invalidFields`, `unsetRequiredFields`,
`_textValues`, `_initialTextValues`, `_savePoint`,
`closeInvalidFieldsNotification`) that delegate to the owner, so every consumer
(sibling helpers, fields/views, subclasses, test mocks) is unchanged. `_values`
(server layer) and `_saveInFlight` stay on the record. The `(dirty, changes)`
invariant now has one home: `RecordEditState.clearChanges()` is the only
sanctioned reset and pairs bag-clear with `dirty=false` atomically (I3);
`markDirty()` raises `dirty` alone (I1/I2). **Reactivity**: `_editState` is NOT
`markRaw`, so reached through the record's reactive proxy `dirty`/`invalidFields`
stay reactive, while `toRaw(record)._editState` yields the raw owner for the raw
reads in `updateLocked`; the bags (`changeSet`, `textValues`, `unsetRequiredFields`)
are `markRaw` inside the owner exactly as before.

**Scoped re-validation on commit**: committing changes re-checks
unset-required status only for fields whose status could actually have
changed. `computeRevalidationScope(changedFieldNames, activeFields)`
(`model/relational_model/record_utils.js`) returns the changed fields
plus every field whose `invisible` / `required` / `readonly` modifier
expression references one of them (a per-`activeFields` memoized dependency
map), plus fields with an unparseable modifier (always re-validated as a
fallback — fails safe). The scope is passed as `scopedFields` to
`checkValidityLocked({ removeInvalidOnly: true, scopedFields })`
(`record.js`; orchestration lives in
`model/relational_model/record_validator.js`), so a keystroke does not
re-evaluate the modifier expressions of every field in a large form.

## Form Save State Diagram

The form controller manages save/discard transitions through the model's mutex
for serialization. This is not implemented as a formal state machine but
follows this implicit state graph:

```
                    ┌──────────┐
                    │  CLEAN   │ ◄───────────────────────┐
                    │ dirty=F  │                         │
                    └────┬─────┘                         │
                         │ user edit                     │
                         ▼                               │
                    ┌──────────┐     discard()      ┌────┴─────┐
                    │  DIRTY   │ ──────────────────►│ DISCARD  │
                    │ dirty=T  │                    │ revert   │
                    └────┬─────┘                    └──────────┘
                         │ save()
                         ▼
                    ┌──────────┐
                    │ VALIDATING│
                    │ checkValidity
                    └────┬──┬──┘
                  valid  │  │ invalid
                         ▼  ▼
                    ┌─────────┐  ┌──────────┐
                    │ SAVING  │  │  ERROR   │
                    │ RPC     │  │ invalid  │
                    │ write() │  │ fields   │
                    └────┬────┘  └────┬─────┘
                         │            │ user fixes
                         │            └──► DIRTY
                         ▼
                    ┌──────────┐
                    │ RELOADING│
                    │ read()   │
                    └────┬─────┘
                         │
                         ▼
                       CLEAN
```

**Serialization**: All transitions go through `model.mutex.exec()`, ensuring
only one save/discard/load runs at a time.

**Group identity**: `model/relational_model/group_key.js` supplies the keys for
group configuration and datapoint reuse. Parsed values retain their types, so an
unset selection and the literal string `"false"` have separate groups. Encoded
keys stay client-side; opening information sent to the server uses group values.

**Local list ordering**: `static_list_utils.js` gives unset selection values the
same empty-string sort convention as local char values. Multi-column ties are
resolved iteratively. This local ordering convention does not claim PostgreSQL
NULL-placement or locale-collation parity.

**Created-row reconciliation**: proposed virtual/server ID pairs must occur at
matching positions when membership arrays are supplied. Validation scans client
membership until every pair is witnessed and checks only the corresponding server
positions. Empty batches skip the scan; absent rows are not identity evidence. Rank-order pairing without positional inputs is
unchanged.

**Field context identity**: `model/relational_model/field_context.js` evaluates
context on every call and retains only the latest result per field, record, and
consumer. Field widgets supply themselves as weak cache owners, so two widgets
with different contexts remain independent and destroyed widgets are not retained.
Equivalent results reuse that object even when their expression strings differ;
changed evaluated values replace it. This bounds expression history, not evaluation
time.

**Urgent save**: On page unload (`beforeunload`), `urgentSave()` uses
`navigator.sendBeacon()` to fire-and-forget unsaved changes. This bypasses
the mutex and normal flow.

`UrgentSaveCoordinator` restores its idle state if the bus's `trigger()` throws.
Work registered before that throw is still observed. Owl's EventBus uses
`EventTarget`: listener exceptions are reported globally and do not propagate
through `trigger()`. The coordinator cleanup does not convert those exceptions
into rejected saves, impose a deadline, or guarantee beacon delivery.

**Preprocessing failure**: a normal record update waits for every started
preprocessor promise to settle before restoring touched relation-list snapshots.
This includes a synchronous preprocessor exception after asynchronous work has
started. If parent notification rejects after values were applied, rollback also
restores the earlier, pre-preprocessing list snapshots; the apply/undo snapshot
alone already contains the edited membership. Urgent saves retain synchronous
preprocessing and their existing skipped waits. Client rollback does not undo
separately completed server-side calls.

> **Optimistic-locking parity — field-scoped baseline values**: both paths
> send `kwargs.known_values`, a `{field: originally-loaded value}` map built
> once per save (`concurrencyBaseline`, `record_save.js`) from
> `record._values` for the fields being written — skipping uncomparable types
> (x2many, binary, html, date/datetime, json, properties, reference) and
> jsonb-backed `translate` / `company_dependent` fields. The urgent
> (sendBeacon) path attaches it via `urgentKwargs`
> (`record_save.js`); the normal path via `kwargs.known_values`
> (`record_save.js`); both only for existing records (`resId`
> truthy). Server side, `models/web_read.py:_check_concurrent_field_changes`
> rejects only genuine per-field conflicts, ignores concurrent writes to
> other fields, and **fails open** for fields with no baseline (an empty
> baseline means no check — correct on tab close, where the user's work must
> never be dropped). The client does not send the whole-record
> `last_write_date`; the server accepts that kwarg only as a fallback,
> consulted when `known_values` is absent.

**Key files**:
- `views/form/form_controller.js` — `save()` entry point
- `views/form/form_controller.js` — `discard()` entry point
- `views/form/form_controller.js` — `beforeLeave()` auto-save
- `model/relational_model/record_edit_state.js` — `RecordEditState` owner (change set, `dirty`, validity, text-values, savepoint; `clearChanges()`/`markDirty()`)
- `model/relational_model/record.js` — `applyChanges()` (dirty tracking)
- `model/relational_model/record.js` — `discard()` (mutex-wrapped)
- `core/network/result_set_cache_invalidator_service.js` — `CLEAR-CACHES` emission (unlink + action_archive + action_unarchive; method set defined by `RESULT_SET_REMOVING_METHODS`; model-scoped on BOTH layers: RAM via reverse index, IndexedDB via cursor filter on the stored `model` — see Flow 14).

**All 6 CLEAR-CACHES emission sites in the web module:**

| File:Line | Trigger | Scope |
|---|---|---|
| `core/network/result_set_cache_invalidator_service.js` | `unlink` / `action_archive` / `action_unarchive` RPC response (set defined by `RESULT_SET_REMOVING_METHODS`) | tables: web_read, web_search_read, web_read_group; model-scoped in RAM only |
| `core/network/result_set_cache_invalidator_service.js` | `base.language.install` `action_install_lang` RPC response (a new language invalidates virtually everything cached) | all |
| `search/search_favorites_mixin.js` | `ir.filters` write/unlink (saved-favorite mutations) | `"get_views"` table |
| `webclient/actions/action_cache_invalidation.js` | `ir.actions.act_window` write/unlink | `"/web/action/load"` table |
| `views/view_service.js` | `ir.ui.view` / `ir.filters` write/unlink | `"get_views"` table |
| `webclient/service_worker_service.js` | Post-service-worker-registration on hard refresh | all |

Plus **one listener** at `core/network/rpc.js` that routes the event to `rpc_cache.js` for cache invalidation.

## Model Load Lifecycle

> There is no load-coordinator object. `model/relational_model/load_coordinator.js`
> does not exist — do not cite it.

The load lifecycle is carried by three primitives on `RelationalModel` plus one
observable flag:

| Primitive | Lives | Role |
|---|---|---|
| `model.keepLast` | `relational_model.js` (`markRaw(new KeepLast())`) | Cancellation: `load()` wraps `_loadData` in `keepLast.add(...)` (`relational_model.js`) so an in-flight load is dropped when a newer one starts. |
| `model.mutex` | RelationalModel | Per-record save/discard serialization. Used across `RelationalRecord.save` / `.discard` / `.delete` / `.update`. |
| `model.urgentSave` (`UrgentSaveCoordinator`) | `model/relational_model/urgent_save_coordinator.js` | Cross-cutting urgent-save mode, orthogonal to loading. |
| `model.isReady` | `model.js` / `relational_model.js` | Reactive "first load done" flag. Before the first load resolves, `load()` installs an **empty root** (`_createEmptyRoot`) so the control panel renders immediately; `isReady = true` is promoted in the same synchronous block as the real-root + config writes so OWL batches them into a single render. |

## Typed Events

Global events are defined in `core/events.js` and exported from `@web/core`.

| Constant | String Value | Bus | Purpose |
|----------|-------------|-----|---------|
| `AppEvent.SERVICES_LOADED` | `SERVICES-LOADED` | env.bus | All services ready |
| `AppEvent.WEB_CLIENT_READY` | `WEB_CLIENT_READY` | env.bus | WebClient mounted |
| `AppEvent.ACTION_MANAGER_UPDATE` | `ACTION_MANAGER:UPDATE` | env.bus | Controller changed |
| `AppEvent.ACTION_MANAGER_UI_UPDATED` | `ACTION_MANAGER:UI-UPDATED` | env.bus | UI render done |
| `AppEvent.WEBCLIENT_LOAD_DEFAULT_APP` | `WEBCLIENT:LOAD_DEFAULT_APP` | env.bus | Load home |
| `AppEvent.CLEAR_UNCOMMITTED_CHANGES` | `CLEAR-UNCOMMITTED-CHANGES` | env.bus | Save/discard all |
| `AppEvent.ACTION_MANAGER_SETTLED` | `ACTION_MANAGER:SETTLED` | env.bus | Action dispatch fully unwound — fired once per user gesture, on the outermost unwind only (`_dispatchDepth === 0` in `webclient/actions/action_service.js`), so re-entrant dispatches (server action, function client action, `act_url` close, report close) do not announce a premature settle. Consumed by `webclient/clickbot/clickbot.js` |
| `AppEvent.MENUS_APP_CHANGED` | `MENUS:APP-CHANGED` | env.bus | App switched |
| `AppEvent.BLOCK` / `UNBLOCK` | `BLOCK` / `UNBLOCK` | env.bus | UI blocking |
| `AppEvent.ACTIVE_ELEMENT_CHANGED` | `active-element-changed` | env.bus | Dialog focus |
| `AppEvent.RESIZE` | `resize` | env.bus | Window resize |
| `AppEvent.HOME_MENU_TOGGLED` | `HOME-MENU:TOGGLED` | env.bus | Home menu opened/closed (consumed by `webclient/burger_menu/burger_menu.js`) |
| `RpcEvent.REQUEST` / `RESPONSE` | `RPC:REQUEST` / `RPC:RESPONSE` | rpcBus | RPC lifecycle. Both carry `{data, url, settings}`; RESPONSE adds `result` (success) or `error` (failure). `url` is on **both** events, which is what lets an observer identify the endpoint of a call whose `params` carry no `model`/`method` (session_info, `/web/action/load`, `get_views`). |
| `RpcEvent.CLEAR_CACHES` | `CLEAR-CACHES` | rpcBus | Invalidate caches |
| `RpcEvent.BACKGROUND_REFRESH_FAILED` | `RPC:BACKGROUND-REFRESH-FAILED` | rpcBus | A stale-while-revalidate background refresh failed (`core/network/rpc_cache.js`) |
| `RouterEvent.ROUTE_CHANGE` | `ROUTE_CHANGE` | routerBus | URL changed |
| `RouterEvent.EPHEMERAL_POPPED` | `EPHEMERAL_POPPED` | routerBus | Ephemeral history markers popped (`core/browser/router.js`) |
| `SearchModelEvent.UPDATE` | `update` | env.searchModel | Search state changed |
| `SearchModelEvent.FOCUS_VIEW` | `focus-view` | env.searchModel | Focus the view |
| `SearchModelEvent.FOCUS_SEARCH` | `focus-search` | env.searchModel | Focus the search bar |
| `SearchModelEvent.DIRECT_EXPORT_DATA` | `direct-export-data` | env.searchModel | Export all records |
| `ModelEvent.UPDATE` | `update` | `model.bus` | Model data changed |
| `ModelEvent.WILL_SAVE_URGENTLY` | `WILL_SAVE_URGENTLY` | `model.bus` | Urgent-save (tab close) about to run — `model/relational_model/urgent_save_coordinator.js` |
| `ModelEvent.NEED_LOCAL_CHANGES` | `NEED_LOCAL_CHANGES` | `model.bus` | Ask open editors to commit pending input (`fields/relational/x2many/x2many_field.js`) |
| `ModelEvent.FIELD_IS_DIRTY` | `FIELD_IS_DIRTY` | `getBus()` | Per-field dirty signal (`fields/field_dirty_signal.js`) |
| `ModelEvent.RECORD_DISCARDED` | `RECORD_DISCARDED` | `model.bus` | After a record restores its saved values or savepoint; `{ recordId }` lets buffered editors reset only their own draft (`model/relational_model/record.js`) |
| `ModelEvent.PROPERTY_FIELD_EDIT` | `PROPERTY_FIELD:EDIT` | `model.bus` | Enter property-definition edit mode (`fields/specialized/properties/properties_field.js`) |
| `ModelEvent.SCROLL_TO_CURRENT_HOUR` | `SCROLL_TO_CURRENT_HOUR` | `model.bus` | Calendar scroll request (`views/calendar/calendar_controller.js`) |
| `UserEvent.ACTIVE_COMPANIES_CHANGED` | `ACTIVE_COMPANIES_CHANGED` | `userBus` | Allowed-company selection changed (`core/user.js`). Load-bearing for `name_service` cache clearing — see ARCHITECTURE.md |
| `FileUploadEvent.ADDED` / `LOADED` / `ERROR` | `FILE_UPLOAD_ADDED` / `FILE_UPLOAD_LOADED` / `FILE_UPLOAD_ERROR` | `file_upload` service bus | Upload lifecycle (`core/file_upload/file_upload_service.js`) |
| `CommandPaletteEvent.SET_CONFIG` | `SET-CONFIG` | command palette bus | Reconfigure the open palette (`ui/commands/command_service.js`) |
| `PagerEvent.UPDATED` | `PAGER:UPDATED` | `env.bus` | Pager value/total changed — fired by `components/pager/pager.js` **only when `env.isSmall`**, and never on first mount, so the small-screen `components/pager/pager_indicator.js` is the sole consumer |
| `DropdownEvent.OPENED` | `DROPDOWN:OPENED` | `env.bus` | A dropdown opened (`components/dropdown/_behaviours/dropdown_nesting.js`). Every other nesting instance listens and closes itself through `handleChange(other)`, which is how sibling dropdowns stay mutually exclusive |

## Server-side `__version` stamp for cached endpoints

`useSpecialData` exposes `{ data, isReady }`. It retains the previous data while
loading replacement choices, but only the latest request may mark them ready.
Choice widgets disable interaction while `isReady` is false, including their
event handlers so an already-open menu cannot select an obsolete choice.
Prop updates and reactive record dependencies trigger loads; rendering the
result does not trigger another load. Identical ORM requests share the model's
cache. Disk-cache refreshes notify only current subscribers, and changing inputs
or destroying a widget removes its subscriptions. Debug namespace:
`web.field.special_data` (`load`, `superseded`, `ready`, `failed`).

Superseding a load releases its waiter without aborting shared RPC work. Initial
mounting waits for current data, not an obsolete request; errors from current
initial loads remain owned by Owl's error boundary. Replacing a load or destroying
the widget disposes its record observations, including dependencies read after
an obsolete asynchronous loader resumes.

`update: "always"` consumers ask the cache to revalidate against the server on
every read; the cache calls back with `(value, hasChanged)`.

Opted-in endpoints inject a `__version` field (content digest of
canonical JSON — `odoo.tools.hashing.cache_hash`: BLAKE3, sha256 without the
extension) into their dict return value.  The cache compares versions
when both sides carry one (O(1), ~2,000× faster on the bench than the
`JSON.stringify` comparison), falls back to
`jsonEqual` otherwise.  Backward-compatible in both directions: old server +
new client → fallback path; new server + old client → unknown field ignored.

| Surface | File | Role |
|---|---|---|
| Decorator | `odoo/tools/cache_version.py` `versioned` / `versioned_envelope` | Stamps `__version = cache_hash(canonical_json(result))` (sorted keys, compact separators, `default=str`; see `odoo/libs/hashing.py` for the algorithm) on dict returns (`versioned`); or stashes hash on `http.request._response_version` for non-dict returns (`versioned_envelope`). Located under `odoo.tools` so any addon can import without manifest dependency gymnastics. |
| Consumer | `addons/web/static/src/core/network/rpc_cache.js` `payloadChanged` | Replaces direct `jsonEqual(prev, curr)` in the `hasChanged` computation. Prefers `__version === __version` when both sides have it. |

**Currently opted-in endpoints** (Phases 1 + 2 + 3 + 4a):
- `search_panel_select_range` / `search_panel_select_multi_range` — Phase 1, `@versioned`
- `web_search_read` (`models/web_read.py`) — Phase 2, `@versioned`, hot path
- `web_read_group` (`models/web_read_group.py`) — Phase 2, `@versioned`, hot path
- `web_read` (`models/web_read.py`) — Phase 3, `@versioned_envelope`, hot path (list return)
- `project.project.get_template_tasks` (`addons/project/models/project_project.py`) — Phase 4a, `@versioned_envelope`, consumed by `project_task_template_dropdown.js` and `fsm_task_template_dropdown.js`

**Pending follow-up endpoints** (also `update: "always"` consumers):
- m2o special data (`fields/relational/special_data.js`) — generic ORM proxy; per-`loadFn` identification needed before decorating the backing methods
- `project.project` template list (`project_template_dropdown.js` uses raw `searchRead`) — switch the JS to a custom `@versioned_envelope` server method, e.g. `get_project_templates`, when the perf win is profiled to matter

### Two decorator forms

| Form | When | Mechanism | Survives JSON round-trip? |
|---|---|---|---|
| `@versioned` | Method returns a `dict` | Mutates the dict in-place: `result["__version"] = cache_hash(...)` | Yes — `__version` is a JSON key |
| `@versioned_envelope` | Method returns a `list`, scalar, or anything non-dict | Stashes hash on `http.request._response_version`; dispatcher (`odoo/http/dispatcher.py` `_response`) lifts it as `version` sibling-of-`result` in the JSON-RPC envelope; `rpc.js` re-attaches as `result.__version` for objects/arrays | RAM: yes (`structuredClone` preserves array own-props). IndexedDB: no (`JSON.stringify` drops array own-props on encrypt); self-heals on next refresh |

The client-side `payloadChanged` reads `result[VERSION_FIELD]` uniformly — agnostic
to which decorator the server used.

The hash uses `sort_keys=True` so the digest is invariant under Python dict
insertion order — two interpreter runs over the same query can yield
different insertion orders and the version must stay stable across them.

### Comparison cascade (cheap → expensive)

When `update: "always"` fires, `payloadChanged(prev, curr)` walks four layers,
returning at the first that produces an answer:

| # | Layer | Cost | Wins when |
|---|---|---|---|
| 1 | `prev === curr` | O(1) | The same reference is passed twice (rare) |
| 2 | `prev.__version !== curr.__version` | O(1) | Both sides have a version stamp |
| 3 | `shapeDiffers(prev, curr)` — array/object length, type mismatch | O(1) | Row appended/removed; type changed |
| 4 | `!jsonEqual(prev, curr)` — full deep compare | O(n) | Same shape, possibly same content |

Layer 3 makes the version-less fallback path (still used by `web_read`,
template dropdowns, m2o special data) much cheaper for the common
append/remove case — benchmarked at ~400× speedup over the layer-4 fallback
for a 200-record list when length differs by one, with ~1 ns/call overhead
when shapes match and the call falls through.
