# ORM Architecture: Comparative Analysis & Implementation Path

> **Odoo 19.0 Fork** vs. SQLAlchemy, Django, Peewee, Tortoise, Pony
>
> Goal: Identify structural gaps and build an implementation path to make this
> fork the reference-quality Python ORM architecture.

---

## 1. Structural Overview

### 1.1 Scale at a Glance

| Project | ORM Files | ORM LOC | Largest File | Largest (lines) |
|---------|----------:|--------:|--------------|----------------:|
| **Odoo 19.0 Fork** | 52 | 23,071 | `fields/base.py` | 2,091 |
| SQLAlchemy 2.x | 121 | ~90,000 | `orm/mapper.py` | ~4,500 |
| Django 5.x | ~45 | ~27,000 | `sql/query.py` | ~3,100 |
| Peewee 3.x | 1 (+27 ext) | ~8,000 | `peewee.py` | ~7,500 |
| Tortoise 0.x | ~45 | ~14,000 | `queryset.py` | ~2,000 |
| Pony 0.x | ~17 | ~19,000 | `core.py` | ~8,500 |

### 1.2 Odoo Fork File Map (52 files, 23,071 lines)

```
orm/                              Layer
├── __init__.py            35     --
├── _typing.py             48     0  type aliases (runtime-light)
├── constants.py           81     0  READ_GROUP_* constants
├── primitives.py         315     0  IdType, NewId, Command, SUPERUSER_ID
├── protocols.py           33     0  structural typing contracts
├── parsing.py            146     0  field/domain/spec parsing
├── validation.py          82     0  name & identifier checks
├── decorators.py         369     X  @api.depends, @api.model, etc.
├── registration.py       688     X  MetaModel, model collection
├── helpers.py            224     X  OriginIds, company domain helpers
│
├── domain/             2,255     1  Domain AST, optimization, constants
│   ├── __init__.py       110
│   ├── ast.py          1,084
│   ├── constants.py      130
│   └── optimizations.py  931
│
├── fields/             7,690     1  11 field-type modules
│   ├── __init__.py       100
│   ├── base.py         2,091        Field base class
│   ├── relational.py   1,920        Many2one, One2many, Many2many
│   ├── properties.py   1,152        Properties, PropertiesDefinition
│   ├── textual.py        863        Char, Text, Html
│   ├── binary.py         395        Binary, Image
│   ├── temporal.py       325        Date, Datetime
│   ├── numeric.py        309        Integer, Float, Monetary
│   ├── selection.py      264        Selection
│   ├── misc.py           147        Id, Boolean, Json
│   └── reference.py      124        Reference, Many2oneReference
│
├── models/             6,899     2  metaclass + 14 mixins + read_group
│   ├── __init__.py        46
│   ├── base.py           550        BaseModel, Model, AbstractModel
│   ├── metaclass.py      124        MetaModel
│   ├── table_objects.py  231        Constraint, Index, UniqueIndex
│   ├── transient.py       89        TransientModel
│   └── mixins/         5,859
│       ├── __init__.py    74
│       ├── crud.py     1,132        create, write, unlink
│       ├── io.py         887        import/export
│       ├── search.py     602        _search, name_search
│       ├── access.py     459        ACL, record rules
│       ├── cache.py      421        invalidation, prefetch
│       ├── traversal.py  379        mapped, filtered, sorted
│       ├── read.py       378        _read, _fetch_field
│       ├── schema.py     366        _auto_init, column sync
│       ├── iteration.py  343        __iter__, ids, exists
│       ├── translation.py 285      _get_translation_*
│       ├── env.py        258        with_context, with_user
│       ├── lifecycle.py  196        _register_hook, _unregister_hook
│       ├── copy.py       169        copy, copy_data
│       └── read_group/ 1,715
│           ├── __init__.py 16
│           ├── mixin.py  613        _read_group entry point
│           ├── sql.py    471        SQL generation
│           ├── format.py 316        result formatting
│           └── fill.py   299        date/time filling
│
└── runtime/            2,401     3  Environment, Registry
    ├── __init__.py        58
    ├── environment.py    982
    └── registry.py     1,361
```

**Layer key:** 0 = zero ORM deps, 1 = fields/domain, 2 = models, 3 = runtime,
X = cross-cutting (used by multiple layers).

---

## 2. Dimension-by-Dimension Comparison

### 2.1 Layering Discipline

How cleanly are internal layers separated? Can lower layers be used independently?

| Project | Approach | Independence | Score |
|---------|----------|-------------|:-----:|
| **SQLAlchemy** | Core SQL + ORM as separate installable layers; ORM depends on Core but Core never imports ORM. `inspection.py` bridges layers via registry pattern. | Core usable without ORM. `engine/` usable without `sql/`. | **A+** |
| **Odoo Fork** | 4 documented layers (0→3) with cross-cutting modules. Layer 0 has zero ORM deps. Fields/domain at Layer 1. Models at Layer 2. Runtime at Layer 3. | Layers 0-1 are independently importable. Layer 2 requires runtime (circular via TYPE_CHECKING). | **A-** |
| **Django** | 4 implicit layers (fields → sql → queryset → model). `db/backends/` is a separate layer. No formal documentation of layer boundaries. | `sql/` can theoretically run without `models/`, but in practice tightly coupled. | **B+** |
| **Tortoise** | 3 layers (fields → queryset → model). Async-native. `TortoiseContext` provides isolation. | Moderate — queryset depends on model metaclass. | **B** |
| **Pony** | Pipeline DAG (entity → decompile → translate → build → provider). Clean unidirectional flow. | No — `core.py` is monolithic at 8,500 lines. | **B-** |
| **Peewee** | Single file — no layers. | N/A | **C** |

**Odoo Fork advantage:** Explicit 4-layer documentation with importability guarantees at each level. The `primitives.py` → `fields/` → `models/` → `runtime/` flow is cleaner than Django's implicit layering.

**Gap vs. SQLAlchemy:** SQLAlchemy's Core/ORM split is a genuine architectural boundary — Core is a standalone library. Odoo's layers are conventions within one package, not enforced boundaries.

---

### 2.2 File Granularity

How well are responsibilities distributed across files?

| Project | Avg lines/file | Max file | Max lines | Files >1,000 | Score |
|---------|---------------:|---------:|----------:|-------------:|:-----:|
| **Odoo Fork** | 444 | `fields/base.py` | 2,091 | 7 | **A** |
| **Tortoise** | ~340 | `queryset.py` | 2,000 | 3 | **A** |
| **SQLAlchemy** | ~740 | `orm/mapper.py` | 4,500 | ~15 | **B+** |
| **Django** | ~600 | `sql/query.py` | 3,100 | ~8 | **B** |
| **Pony** | ~1,120 | `core.py` | 8,500 | 3 | **D** |
| **Peewee** | 7,500 | `peewee.py` | 7,500 | 1 | **F** |

**Odoo Fork advantage:** Best average file size of any compared project. No file exceeds 2,100 lines. The 14-mixin decomposition (avg 460 lines) is genuinely best-in-class.

**No gap.** Odoo leads this dimension.

---

### 2.3 Circular Dependency Management

How does each project prevent or resolve import cycles?

| Project | Strategy | Mechanism | Score |
|---------|----------|-----------|:-----:|
| **SQLAlchemy** | Deferred loading | `preloaded.py` registry + `@preload_module` decorator + `TYPE_CHECKING` guards | **A+** |
| **Odoo Fork** | Guard + lazy import | `TYPE_CHECKING` guards, lazy imports in `helpers.py`, `from __future__ import annotations` | **A-** |
| **Django** | Registry + string refs | `apps.get_model()` registry, `lazy_related_operation()`, deferred imports in method bodies | **A-** |
| **Tortoise** | Two-phase init | String refs resolved during `init()`, `Apps` registry, `TortoiseContext` | **B+** |
| **Peewee** | Monolith | Single file eliminates the problem. `DeferredForeignKey` for user-level cycles. | **B** |
| **Pony** | Monolith + pipeline | `core.py` is self-contained. Pipeline modules form a DAG. | **B** |

**Odoo Fork advantage:** Clean TYPE_CHECKING separation in `_typing.py`. The `from __future__ import annotations` approach in helpers is elegant.

**Gap vs. SQLAlchemy:** `preloaded.py` is a formalized, reusable pattern with clear semantics. Odoo's approach works but is ad-hoc — each developer must independently discover the right technique for their specific circular import.

---

### 2.4 Mixin Decomposition

How is model behavior organized?

| Project | Pattern | Count | Avg Size | Score |
|---------|---------|------:|----------|:-----:|
| **Odoo Fork** | Explicit mixin classes in `mixins/` | 14 | 460 lines | **A+** |
| **SQLAlchemy** | Multiple base classes (`Session`, `Query`, `Mapper`) with `_MapperEntity`, `_ColumnEntity`, etc. | ~8 | ~800 lines | **B+** |
| **Django** | Manager/QuerySet delegation + monolithic `Model` base | 2 (Manager + QuerySet) | ~2,700 lines | **B** |
| **Tortoise** | Single `Model` class + `MetaInfo` | 1 | ~1,860 lines | **C+** |
| **Pony** | Single `Entity` class in monolithic `core.py` | 1 | ~8,500 lines | **D** |
| **Peewee** | Single `Model` class in monolithic file | 1 | ~7,500 lines | **D** |

**Odoo Fork advantage:** This is the project's strongest dimension. 14 focused mixins with clear single-responsibility boundaries:

```
CrudMixin      → create/write/unlink          (1,132 lines)
IoMixin        → import/export                 (887 lines)
SearchMixin    → _search, name_search          (602 lines)
AccessMixin    → ACL, record rules             (459 lines)
CacheMixin     → invalidation, prefetch        (421 lines)
TraversalMixin → mapped, filtered, sorted      (379 lines)
ReadMixin      → _read, _fetch_field           (378 lines)
SchemaMixin    → _auto_init, column sync       (366 lines)
IterationMixin → __iter__, ids, exists          (343 lines)
TranslationMixin → _get_translation_*          (285 lines)
EnvMixin       → with_context, with_user       (258 lines)
LifecycleMixin → _register_hook                (196 lines)
CopyMixin      → copy, copy_data              (169 lines)
ReadGroupMixin → _read_group (sub-package)   (1,715 lines)
```

No other Python ORM achieves this level of behavioral decomposition while keeping all mixins under 1,200 lines.

**No gap.** Odoo leads this dimension by a wide margin.

---

### 2.5 Public API Design

How clean is the surface that external code imports from?

| Project | Pattern | Surface | Score |
|---------|---------|---------|:-----:|
| **Django** | Flat re-export `__init__.py` with `__all__` (~100 symbols) | `from django.db.models import Model, CharField` | **A** |
| **Odoo Fork** | 3 facade modules (`odoo/api/`, `odoo/fields/`, `odoo/models/`) re-exporting from canonical locations | `from odoo import api, fields, models` | **A** |
| **SQLAlchemy** | `orm/__init__.py` re-exports + `sqlalchemy` top-level convenience imports | `from sqlalchemy.orm import Session, relationship` | **A-** |
| **Peewee** | Direct module import (`from peewee import *`) | Flat, simple | **B+** |
| **Tortoise** | `Tortoise` class facade + re-exports | `from tortoise.models import Model` | **B** |
| **Pony** | `from pony.orm.core import *` (3-line `__init__`) | Flat but leaks internals | **B-** |

**Odoo Fork advantage:** The 3-facade pattern (`api`, `fields`, `models`) provides a natural organizational taxonomy that Django's flat list doesn't. Importing `from odoo import fields` immediately scopes the namespace.

**Minor gap:** `__all__` is not defined on the facade modules. Adding it would improve IDE autocompletion and prevent accidental internal symbol leakage.

---

### 2.6 Event/Hook System

How can external code observe or intercept ORM operations?

| Project | Mechanism | Hooks | Async | Weak Refs | Score |
|---------|-----------|------:|:-----:|:---------:|:-----:|
| **SQLAlchemy** | Full event framework (6 files, ~1,500 lines). Class-based dispatch, auto-generated `_Dispatch` companions, propagation through MRO. | ~60 | No | Yes | **A+** |
| **Django** | Standalone signal dispatcher (560 lines). `Signal` class with `connect/disconnect/send`. `ModelSignal` for lazy model refs. | 12 | Yes | Yes | **A** |
| **Tortoise** | Decorator-based registration (69 lines). Handlers stored on model class. | 4 | Yes (native) | No | **B-** |
| **Peewee** | Optional extension (`playhouse/signals.py`, 79 lines). Requires separate base class. | 5 | No | No | **C** |
| **Pony** | Entity method overrides only. No observer pattern. | 6 | No | No | **C-** |
| **Odoo Fork** | `LifecycleMixin._register_hook()` + direct method overrides. No observer/signal pattern. `@api.onchange` is UI-only. | ~3 | No | No | **C-** |

**Gap:** This is Odoo's weakest dimension. The current hook system is:

1. **`_register_hook()`** — called once at registry build time, not per-operation
2. **Method overrides** — `create()`, `write()`, `unlink()` can be overridden, but there's no way to observe operations without inheriting
3. **`@api.onchange`** — UI-layer only, not triggered by ORM operations
4. **No decoupled observation** — addons that want to react to another model's changes must use `_inherit` or override + `super()`, creating tight coupling

SQLAlchemy's event system and Django's signals both allow **decoupled observation** where module A can listen to module B's events without modifying B's code. This is the single largest architectural gap in the Odoo ORM.

---

### 2.7 Layer Boundary Enforcement

How are architectural rules enforced beyond documentation?

| Project | Enforcement | Tooling | Score |
|---------|-------------|---------|:-----:|
| **SQLAlchemy** | Convention + `preloaded.py` makes violations visible + `interfaces.py` contracts + `base.py` foundations | No automated lint, but patterns make violations obvious | **B+** |
| **Django** | Convention + `isort:skip` comments + apps registry | `django.setup()` catches registration errors at startup | **B** |
| **Odoo Fork** | Convention + layer documentation in `__init__.py` | None — violations are silent | **C+** |
| **Tortoise** | Convention + `TortoiseContext` isolation | `init()` validates configuration at startup | **C+** |
| **Peewee** | N/A (single file) | N/A | **N/A** |
| **Pony** | N/A (monolithic core) | `generate_mapping()` validates at startup | **N/A** |

**Gap:** Odoo's layers are well-documented but unenforced. A developer can accidentally import from `runtime/` inside `fields/` and nothing will complain until (maybe) a circular import manifests at runtime. SQLAlchemy's `preloaded.py` doesn't prevent violations either, but it makes them architecturally visible — if you need `@preload_module`, you know you're crossing a boundary.

---

### 2.8 Constructor/Implementation Separation

Are public factory functions separated from heavy implementation classes?

| Project | Pattern | Score |
|---------|---------|:-----:|
| **SQLAlchemy** | Dedicated `_*_constructors.py` files in both `orm/` and `sql/`. Public functions like `relationship()`, `mapped_column()`, `and_()`, `or_()` wrap internal classes. | **A** |
| **Django** | Field constructors are the classes themselves. `Q()` and `F()` are lightweight wrappers. No separation. | **C+** |
| **Odoo Fork** | Field constructors are the classes themselves. No separation. | **C** |
| **Tortoise** | Field constructors are the classes themselves. | **C** |
| **Peewee** | Field constructors are the classes themselves. | **C** |
| **Pony** | `Required()`, `Optional()`, `Set()` are constructor functions that wrap internal types. Partial separation. | **B-** |

**Gap:** Not critical for Odoo's use case. In SQLAlchemy, constructor separation exists because Core SQL expressions have complex internal class hierarchies that users shouldn't see. Odoo's field classes (`Char`, `Many2one`, etc.) are the public API — they're simple enough to instantiate directly. This separation adds value primarily when the implementation class hierarchy is complex and unstable.

**Verdict:** Low priority. Document as a known pattern but don't implement unless field internals become significantly more complex.

---

## 3. Scorecard Summary

| Dimension | Odoo Fork | SQLAlchemy | Django | Tortoise | Pony | Peewee |
|-----------|:---------:|:----------:|:------:|:--------:|:----:|:------:|
| Layering discipline | A- | **A+** | B+ | B | B- | C |
| File granularity | **A** | B+ | B | A | D | F |
| Circular dep mgmt | A- | **A+** | A- | B+ | B | B |
| Mixin decomposition | **A+** | B+ | B | C+ | D | D |
| Public API design | **A** | A- | A | B | B- | B+ |
| Event/hook system | C- | **A+** | A | B- | C- | C |
| Layer enforcement | C+ | **B+** | B | C+ | N/A | N/A |
| Constructor separation | C | **A** | C+ | C | B- | C |
| **Overall** | **B+/A-** | **A** | **B+** | **B** | **C+** | **C+** |

### Where Odoo Fork Leads

1. **Mixin decomposition** — 14 focused mixins, no file >1,200 lines. No competitor comes close.
2. **File granularity** — Best avg lines/file (444) of any multi-file ORM.
3. **Public API ergonomics** — The `from odoo import api, fields, models` triple-facade is more natural than Django's flat 100-symbol namespace or SQLAlchemy's scattered imports.
4. **Domain optimization** — Dedicated `domain/optimizations.py` (931 lines) with AST-level boolean simplification. No other ORM has a comparable domain optimizer.

### Where Odoo Fork Trails

1. **Event/hook system** — No decoupled observation mechanism. Worst of the multi-file ORMs.
2. **Layer enforcement** — Documented but not enforced. Violations are silent.
3. **Circular dep formalization** — Works but ad-hoc. No equivalent to `preloaded.py`.
4. **Constructor separation** — Not needed today, but limits future API evolution.

---

## 4. Implementation Path

The following phases are ordered by **impact/effort ratio** — highest-value, lowest-risk
changes first. Each phase is independently deployable and testable.

### Phase 1: Layer Enforcement (1-2 weeks)

**Goal:** Make layer violations detectable at CI time, not just by convention.

**Why first:** Zero runtime cost, zero API change, pure developer-experience improvement.
Prevents regressions as the codebase grows.

#### 1a. Import layer metadata

Add a `_layer` attribute to each `__init__.py`:

```python
# orm/primitives.py (already exists — no change needed)
# Layer 0: zero ORM dependencies

# orm/fields/__init__.py
_layer = 1  # Fields layer — may import from Layer 0

# orm/models/__init__.py
_layer = 2  # Models layer — may import from Layers 0-1

# orm/runtime/__init__.py
_layer = 3  # Runtime layer — may import from Layers 0-2
```

#### 1b. Import lint rule

Create a lightweight lint script (or `ruff` custom rule) that:

1. Parses each `.py` file's imports using `ast.parse()`
2. Resolves `from ..fields import X` to the target module's layer
3. Flags violations: "Layer N module importing from Layer M where M > N"

Example violations that should be caught:
```python
# In orm/fields/base.py (Layer 1):
from ..runtime import Environment  # ERROR: Layer 1 → Layer 3

# In orm/domain/ast.py (Layer 1):
from ..models import BaseModel     # ERROR: Layer 1 → Layer 2
```

`TYPE_CHECKING` imports are exempt (they don't execute at runtime).

#### 1c. Integration

- Add lint script to pre-commit hooks
- Add to CI pipeline (fail on violations)
- Document in `CONTRIBUTING.md`

**Files to create:**
- `core/tools/lint_orm_layers.py` (~120 lines)
- Update `.pre-commit-config.yaml`

**Estimated effort:** 2-3 days for the lint script, 1 day for CI integration.

---

### Phase 2: ORM Event System (2-3 weeks)

**Goal:** Allow decoupled observation of ORM operations without `_inherit` coupling.

**Why second:** Highest architectural impact. Unblocks addon-to-addon communication
patterns that currently require tight inheritance coupling.

#### 2a. Design Principles

1. **Minimal** — Start with CRUD events only (the 80% case)
2. **Typed** — Event payloads are dataclasses, not `**kwargs`
3. **Sync-first** — Odoo is sync; no async dispatch needed
4. **No weak refs** — Odoo models are long-lived (registry lifetime); weak refs add complexity without benefit
5. **Compatible with `_inherit`** — Events fire alongside, not instead of, the existing override pattern

#### 2b. Event Types (Phase 2 scope)

```python
# orm/events.py

from dataclasses import dataclass
from enum import Enum, auto

class EventType(Enum):
    BEFORE_CREATE = auto()
    AFTER_CREATE = auto()
    BEFORE_WRITE = auto()
    AFTER_WRITE = auto()
    BEFORE_UNLINK = auto()
    AFTER_UNLINK = auto()
    AFTER_SEARCH = auto()          # observation only (no mutation)
    REGISTRY_READY = auto()        # replaces _register_hook use cases

@dataclass(frozen=True, slots=True)
class CreateEvent:
    model: str                     # e.g., "sale.order"
    vals_list: list[dict]          # values being created
    records: object | None = None  # populated in AFTER_CREATE

@dataclass(frozen=True, slots=True)
class WriteEvent:
    model: str
    records: object                # recordset being written
    vals: dict                     # values being written

@dataclass(frozen=True, slots=True)
class UnlinkEvent:
    model: str
    records: object                # recordset being deleted

@dataclass(frozen=True, slots=True)
class SearchEvent:
    model: str
    domain: list
    result: object                 # recordset result
```

#### 2c. Dispatcher

```python
# orm/events.py (continued)

class EventDispatcher:
    """Registry-scoped event dispatcher.

    Listeners are registered per-model or globally ('*').
    Dispatch is synchronous and in registration order.
    """

    __slots__ = ('_listeners',)

    def __init__(self):
        # {EventType: {model_name: [callable]}}
        self._listeners: dict[EventType, dict[str, list]] = {}

    def listen(self, event_type: EventType, model: str, fn: callable) -> None:
        """Register a listener for an event type on a specific model."""
        by_model = self._listeners.setdefault(event_type, {})
        by_model.setdefault(model, []).append(fn)

    def dispatch(self, event_type: EventType, event) -> None:
        """Fire all listeners for an event type."""
        by_model = self._listeners.get(event_type, {})
        for fn in by_model.get(event.model, ()):
            fn(event)
        for fn in by_model.get('*', ()):  # global listeners
            fn(event)
```

#### 2d. Integration Points

Wire dispatch calls into the existing mixin methods:

```python
# orm/models/mixins/crud.py — CrudMixin.create()
def create(self, vals_list):
    dispatcher = self.env.registry.event_dispatcher
    event = CreateEvent(model=self._name, vals_list=vals_list)
    dispatcher.dispatch(EventType.BEFORE_CREATE, event)

    records = ... # existing create logic

    event = CreateEvent(model=self._name, vals_list=vals_list, records=records)
    dispatcher.dispatch(EventType.AFTER_CREATE, event)
    return records
```

#### 2e. Registration API

Addons register listeners in `_register_hook()` (leveraging existing lifecycle):

```python
# In any addon model:
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _register_hook(self):
        super()._register_hook()
        dispatcher = self.env.registry.event_dispatcher
        dispatcher.listen(EventType.AFTER_CREATE, 'stock.picking', self._on_picking_created)

    def _on_picking_created(self, event):
        # React to stock.picking creation without inheriting stock.picking
        ...
```

**Files to create/modify:**
- `core/odoo/orm/events.py` (~200 lines) — new
- `core/odoo/orm/models/mixins/crud.py` — add dispatch calls (~20 lines)
- `core/odoo/orm/runtime/registry.py` — instantiate `EventDispatcher` (~5 lines)
- `core/odoo/orm/models/mixins/lifecycle.py` — update docstring

**Estimated effort:** 1 week for core, 1 week for tests, 0.5 weeks for documentation.

---

### Phase 3: Module Boundary Contracts (1-2 weeks)

**Goal:** Each sub-package explicitly declares its public API via `__all__` and
`interfaces.py` / `protocols.py`.

**Why third:** Builds on Phase 1 (layer enforcement) by adding intra-layer boundaries.
Makes refactoring safe — if it's not in `__all__`, it's not public.

#### 3a. Add `__all__` to every `__init__.py`

Currently, none of the 52 files define `__all__`. Add it to every package init:

```python
# orm/fields/__init__.py
__all__ = [
    'Field', 'Id', 'Boolean', 'Json',
    'Integer', 'Float', 'Monetary',
    'Char', 'Text', 'Html',
    'Selection',
    'Date', 'Datetime',
    'Binary', 'Image',
    'Many2one', 'One2many', 'Many2many',
    'Reference', 'Many2oneReference',
    'Properties', 'PropertiesDefinition',
]
```

#### 3b. Add `protocols.py` to sub-packages that lack them

Currently only `orm/protocols.py` exists at the top level. Add lightweight protocol
files to `fields/` and `models/` that define the contracts their consumers depend on:

```python
# orm/fields/protocols.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class FieldLike(Protocol):
    """Minimal contract that any field must satisfy."""
    name: str
    type: str
    model_name: str
    store: bool
    def convert_to_column(self, value, record, values=None, validate=True): ...
    def convert_to_cache(self, value, record, validate=True): ...
    def convert_to_read(self, value, record): ...
```

This allows the models layer to depend on `FieldLike` (the protocol) rather than
`Field` (the concrete class), reducing coupling.

**Files to modify:** All 8 `__init__.py` files in `orm/` and sub-packages.
**Files to create:** `orm/fields/protocols.py`, `orm/models/protocols.py` (~50 lines each).

**Estimated effort:** 3-4 days.

---

### Phase 4: Formalized Circular Dependency Resolution (1 week)

**Goal:** Replace ad-hoc lazy imports with a consistent, documented pattern inspired by
SQLAlchemy's `preloaded.py`.

**Why fourth:** The current approach works, but each new cross-layer reference requires
the developer to independently discover the right technique. A formal pattern reduces
cognitive load and prevents mistakes.

#### 4a. Create `orm/_registry.py`

A simplified version of SQLAlchemy's `preloaded.py` tailored to Odoo's needs:

```python
# orm/_registry.py
"""
Module registry for deferred cross-layer imports.

Usage:
    # In a lower-layer module that needs a higher-layer type at method time:
    from . import _registry

    def some_method(self):
        BaseModel = _registry.models.BaseModel
        ...

    # In orm/__init__.py (after all sub-packages are imported):
    _registry.populate()
"""

class _ModuleRegistry:
    """Lazily populated module attribute store."""

    __slots__ = ('_modules',)

    def __init__(self):
        object.__setattr__(self, '_modules', {})

    def __getattr__(self, name):
        try:
            return self._modules[name]
        except KeyError:
            raise AttributeError(f"Module {name!r} not yet populated") from None

    def populate(self):
        """Called once after all orm sub-packages are imported."""
        from . import fields, models, runtime, domain
        self._modules.update(
            fields=fields,
            models=models,
            runtime=runtime,
            domain=domain,
        )

registry = _ModuleRegistry()
```

#### 4b. Migrate existing lazy imports

Replace patterns like:

```python
# Current (ad-hoc):
def to_record_ids(args):
    from odoo.orm.models import BaseModel  # lazy to avoid circular
    ...
```

With:

```python
# New (consistent):
from odoo.orm import _registry

def to_record_ids(args):
    BaseModel = _registry.models.BaseModel
    ...
```

This doesn't change behavior but makes every cross-layer reference go through
one discoverable mechanism.

**Files to create:** `orm/_registry.py` (~40 lines)
**Files to modify:** `orm/__init__.py` (add `_registry.populate()` call),
`orm/helpers.py`, `orm/decorators.py` (migrate lazy imports)

**Estimated effort:** 3-4 days.

---

### Phase 5: Read-Group Pipeline Refactor (2-3 weeks)

**Goal:** Reorganize `read_group/` from responsibility-based files to pipeline-stage files,
matching the actual data flow.

**Why fifth:** The current `read_group/` works well but has grown to 1,715 lines across
4 files organized by *what they do* (sql, format, fill) rather than *when they execute*.
Pipeline-oriented organization (parse → plan → execute → format → fill) would make
the read_group flow easier to follow and extend.

#### 5a. Current vs. Proposed

```
Current:                          Proposed:
read_group/                       read_group/
├── mixin.py    (613 lines)       ├── __init__.py   (mixin entry point)
├── sql.py      (471 lines)       ├── parse.py      (spec parsing, validation)
├── format.py   (316 lines)       ├── plan.py       (query planning, field resolution)
├── fill.py     (299 lines)       ├── execute.py    (SQL gen + DB execution)
└── __init__.py (16 lines)        ├── format.py     (result transformation)
                                  └── fill.py       (date/time filling)
```

The `mixin.py` entry point becomes `__init__.py`. The large `sql.py` is split into
`plan.py` (field resolution, groupby processing) and `execute.py` (SQL generation,
query execution).

#### 5b. Benefits

- **Debuggability:** Each pipeline stage can be tested independently
- **Extensibility:** New stages (e.g., caching) slot in naturally
- **Readability:** Reading top-to-bottom follows the execution flow

**Estimated effort:** 2 weeks (mostly moving code + updating tests).

---

### Phase 6: Registry Decomposition (3-4 weeks)

**Goal:** Split `registry.py` (1,361 lines — second largest file) into focused modules.

**Why sixth:** Lower priority because `registry.py` is internal infrastructure that
rarely changes. But at 1,361 lines, it's harder to navigate than necessary.

#### 6a. Proposed Split

```
runtime/
├── __init__.py
├── environment.py     (982 lines — keep as-is)
├── registry/
│   ├── __init__.py    (Registry class — orchestration only, ~400 lines)
│   ├── loading.py     (module loading, model assembly, ~400 lines)
│   ├── caches.py      (LRU caches, invalidation, ~200 lines)
│   ├── signals.py     (inter-registry signaling, ~200 lines)
│   └── init.py        (database init, populate, ~200 lines)
```

**Estimated effort:** 3-4 weeks (high-risk refactor, needs extensive testing).

---

## 5. Implementation Timeline

```
Month 1                    Month 2                    Month 3
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ Phase 1: Layer Lint  │  │ Phase 2: Events      │  │ Phase 5: Read-Group  │
│ (1-2 weeks)          │  │ (2-3 weeks, cont.)   │  │ Pipeline (2-3 weeks) │
│                      │  │                      │  │                      │
│ Phase 2: Events      │  │ Phase 3: Contracts   │  │ Phase 6: Registry    │
│ (start, 2-3 weeks)   │  │ (1-2 weeks)          │  │ (3-4 weeks, start)   │
│                      │  │                      │  │                      │
│                      │  │ Phase 4: _registry.py │  │                      │
│                      │  │ (1 week)             │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

**Phase dependencies:**
- Phase 1 (layer lint) → independent, start immediately
- Phase 2 (events) → independent, start immediately (parallel with Phase 1)
- Phase 3 (contracts) → builds on Phase 1
- Phase 4 (_registry.py) → independent but benefits from Phase 3
- Phase 5 (read-group) → independent
- Phase 6 (registry decomp) → depends on Phase 2 (events affect registry)

---

## 6. Success Metrics

After all phases, the Odoo ORM should score:

| Dimension | Current | Target | Path |
|-----------|:-------:|:------:|------|
| Layering discipline | A- | **A+** | Phase 1 + Phase 4 |
| File granularity | A | **A** | Already leading |
| Circular dep mgmt | A- | **A** | Phase 4 |
| Mixin decomposition | A+ | **A+** | Already leading |
| Public API design | A | **A+** | Phase 3 |
| Event/hook system | C- | **A-** | Phase 2 |
| Layer enforcement | C+ | **A** | Phase 1 + Phase 3 |
| **Overall** | **B+/A-** | **A/A+** | All phases |

The target is an ORM that matches SQLAlchemy's architectural rigor while maintaining
Odoo's superior mixin decomposition and file granularity — combining the best
structural properties of every surveyed project.

---

## Appendix A: Per-Project Architectural Patterns Worth Studying

### From SQLAlchemy
- **`preloaded.py`** — Formalized deferred module loading (→ Phase 4)
- **`interfaces.py` per package** — Abstract contracts at package boundary (→ Phase 3)
- **`_Dispatch` auto-generation** — Metaclass creates dispatch objects from event method stubs (→ Phase 2 inspiration)
- **`inspection.py`** — Registry-based cross-layer bridge without coupling

### From Django
- **`Signal` with `dispatch_uid`** — Deduplication prevents double-registration (→ Phase 2)
- **`lazy_related_operation()`** — Callback-when-model-ready pattern
- **`ModelSignal` with string sender** — `"app_label.ModelName"` resolved lazily
- **Manager/QuerySet** as extension mechanism — composable query behavior

### From Tortoise
- **`TortoiseContext`** — Context-variable scoped state for async isolation
- **Two-phase initialization** — Collect models, then wire relationships
- **Async-native signals** — Coroutine handlers dispatched with `await`

### From Pony
- **Pipeline DAG** — Unidirectional module dependencies by design (→ Phase 5 inspiration)
- **Generator-expression queries** — Python AST as query DSL (architectural novelty, not applicable to Odoo)

### From Peewee
- **`Context` state machine for SQL generation** — Clean separation of SQL rendering state
- **Radical simplicity** — Proof that a full ORM can be <8,000 lines

---

## Appendix B: What NOT to Adopt

| Pattern | Source | Why Skip |
|---------|--------|----------|
| Monolithic core file | Peewee, Pony | Contradicts the fork's granularity advantage |
| Bytecode decompilation | Pony | Fragile, CPython-specific, maintenance nightmare |
| Async-native rewrite | Tortoise | Odoo is fundamentally sync; async wrappers are sufficient |
| Constructor separation | SQLAlchemy | Odoo fields are simple enough to instantiate directly |
| `__all__` on every module | All | Only on `__init__.py` files — individual modules are internal |
| Weak-ref listeners | SQLAlchemy, Django | Odoo models are registry-lifetime; weak refs add complexity without benefit |

---

*Document generated 2026-02-07. Reflects the Odoo 19.0 fork ORM after the
shim-elimination restructure (52 files, 23,071 lines).*
