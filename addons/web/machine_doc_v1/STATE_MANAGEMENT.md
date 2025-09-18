# State Management Patterns

> Decision tree and reference for choosing the right state pattern in `web/static/src/`.

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
│  └─ class extends Reactive (auto-wraps in reactive())
│     Examples: datapoint.js, record.js, static_list.js, group.js
│
├─ Stateful UI behavior with computed logic?
│  └─ reactive({}) with getters/setters
│     Examples: kanban_controller.js (quickCreateState)
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

**Files**: ~38 occurrences across components/, views/, webclient/.

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
- `services/file_upload_service.js` — reactive upload tracking with progress
- `ui/notification/notification_service.js` — reactive notification dict
- `services/frequent_emoji_service.js` — reactive usage counters with localStorage sync

## Pattern 3: `Reactive` Base Class — Model Entities

Classes extending `Reactive` (`core/utils/reactive.js`) auto-wrap `this` in
`reactive()` during construction. Used for ORM data structures where any
property mutation must propagate to the UI.

```javascript
class DataPoint extends Reactive {
    constructor(model, config, data) {
        super();           // returns reactive(this)
        markRaw(config);   // exclude heavy config from reactivity
        this.setup(config, data);
    }
}
```

**Inheritance chain**: `Reactive` → `DataPoint` → `Record` / `StaticList` / `DynamicList` / `Group`

**Critical detail**: Use `markRaw()` on large objects that don't need reactivity
(field definitions, active fields, configs). Without it, OWL deep-wraps every
nested property, causing massive overhead.

**Key files**:
- `core/utils/reactive.js:26` — `Reactive` base class (4 lines)
- `model/relational_model/datapoint.js:12` — `DataPoint extends Reactive`
- `model/relational_model/record.js:42` — `Record extends DataPoint`
- `components/dropdown/dropdown_hooks.js:15` — `DropdownState extends Reactive`

## Pattern 4: `reactive()` with Getters/Setters — Computed State

For UI state that needs side effects on mutation, use `reactive({})` with
JS getters/setters instead of plain properties.

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

**When to use**: Rarely. Only when a state change must trigger side effects
beyond re-rendering (clearing caches, removing sample data, triggering RPCs).

## Record State Architecture

Records maintain a three-layer state model:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  _values     │    │  _changes    │    │  data        │
│  (server)    │ +  │  (user)      │ =  │  (merged)    │
│              │    │  markRaw()   │    │  read by UI  │
└─────────────┘    └─────────────┘    └─────────────┘
```

| Property | Source | Reactive? | Purpose |
|----------|--------|-----------|---------|
| `_values` | Server (read/write RPC) | No (markRaw) | Last-known server state |
| `_changes` | User edits | No (markRaw) | Accumulated unsaved changes |
| `data` | `{..._values, ..._changes}` | Yes | Merged view consumed by UI |
| `dirty` | Computed from `_changes` | Yes | Whether record has unsaved edits |
| `_invalidFields` | Validation | Yes (Set) | Fields that failed validation |

**Save flow**: `_changes` → RPC write → server returns new `_values` → `_changes` cleared → `data` rebuilt.
**Discard flow**: `_changes` cleared → `data` rebuilt from `_values` only → `dirty = false`.

## Form Save State Diagram

The form controller manages save/discard transitions through the model's mutex
for serialization. This is not implemented as a formal state machine but
follows this implicit state graph:

```
                    ┌──────────┐
                    │  CLEAN   │ ◄──────────────────────┐
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
                    ┌────────┐  ┌──────────┐
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

**Urgent save**: On page unload (`beforeunload`), `urgentSave()` uses
`navigator.sendBeacon()` to fire-and-forget unsaved changes. This bypasses
the mutex and normal flow.

**Key files**:
- `views/form/form_controller.js:644` — `save()` entry point
- `views/form/form_controller.js:665` — `discard()` entry point
- `views/form/form_controller.js:475` — `beforeLeave()` auto-save
- `model/relational_model/record.js:359` — `_applyChanges()` (dirty tracking)
- `model/relational_model/record.js:224` — `discard()` (mutex-wrapped)

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
| `AppEvent.MENUS_APP_CHANGED` | `MENUS:APP-CHANGED` | env.bus | App switched |
| `AppEvent.BLOCK` / `UNBLOCK` | `BLOCK` / `UNBLOCK` | env.bus | UI blocking |
| `AppEvent.ACTIVE_ELEMENT_CHANGED` | `active-element-changed` | env.bus | Dialog focus |
| `AppEvent.RESIZE` | `resize` | env.bus | Window resize |
| `RpcEvent.REQUEST` / `RESPONSE` | `RPC:REQUEST` / `RPC:RESPONSE` | rpcBus | RPC lifecycle |
| `RpcEvent.CLEAR_CACHES` | `CLEAR-CACHES` | rpcBus | Invalidate caches |
| `RouterEvent.ROUTE_CHANGE` | `ROUTE_CHANGE` | routerBus | URL changed |
