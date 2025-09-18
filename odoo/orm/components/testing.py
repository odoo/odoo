"""Database-free ORM test environment.

Provides :class:`InMemoryEnvironment`, a lightweight ORM substitute that
uses :class:`DictBackend` instead of PostgreSQL and plain Python callables
instead of ``@api.depends`` compute methods.

This enables testing ORM algorithms (compute chains, cache behavior,
PENDING handling, flush convergence, relational traversal) at component
speed (~3ms) instead of integration speed (~30s).

Scalar fields::

    env = InMemoryEnvironment({
        "sale.order": ModelDef("sale.order", {
            "name": FieldDef("name", "char"),
            "amount": FieldDef("amount", "float"),
            "tax": FieldDef("tax", "float", compute=compute_tax, depends=("amount",)),
        }),
    })
    id_ = env.create("sale.order", {"name": "SO001", "amount": 100.0})
    env.flush()
    assert env.read("sale.order", id_, "tax") == 10.0

Relational fields::

    env = InMemoryEnvironment({
        "res.partner": ModelDef("res.partner", {
            "name": FieldDef("name", "char"),
            "order_ids": FieldDef("order_ids", "one2many",
                                  comodel="sale.order", inverse_field="partner_id"),
        }),
        "sale.order": ModelDef("sale.order", {
            "name": FieldDef("name", "char"),
            "partner_id": FieldDef("partner_id", "many2one", comodel="res.partner"),
        }),
    })
    pid = env.create("res.partner", {"name": "Alice"})
    oid = env.create("sale.order", {"name": "SO001", "partner_id": pid})
    assert env.read("sale.order", oid, "partner_id") == pid
    assert env.read("res.partner", pid, "order_ids") == (oid,)

    # Dot-notation traversal
    assert env.read("sale.order", oid, "partner_id.name") == "Alice"

Pure compute functions (Phase 2)::

    def compute_tax(amount: float) -> float:
        return amount * 0.1

    env = InMemoryEnvironment({
        "order": ModelDef("order", {
            "amount": FieldDef("amount", "float"),
            "tax": FieldDef("tax", "float",
                            compute=compute_tax, depends=("amount",), pure=True),
        }),
    })
"""

import enum as _enum
import typing
from collections import deque
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from .cache import FieldCache


class _Sentinel(_enum.Enum):
    """Compute-state sentinels (local copy for standalone testing)."""

    PENDING = -2


PENDING = _Sentinel.PENDING
from .compute import ComputeEngine
from .storage import DictBackend
from .unit_of_work import UnitOfWork

if typing.TYPE_CHECKING:
    from collections.abc import Callable

# Relational field type names
_RELATIONAL_TYPES = frozenset({"many2one", "one2many", "many2many"})


@dataclass
class FieldDef:
    """Lightweight field definition for InMemoryEnvironment.

    :param name: field name
    :param type: field type string ("char", "integer", "float", "boolean",
        "many2one", "one2many", "many2many", etc.)
    :param store: whether the field is stored (default True)
    :param compute: optional callable — either:
        - traditional: ``fn(env, model, record_id) -> value``
        - pure (when ``pure=True``): ``fn(**field_values) -> value``
    :param depends: field names this compute depends on (triggers recomputation).
        Supports dot-notation for cross-model dependencies (e.g. ``"partner_id.name"``).
    :param required: whether the field is required
    :param default: default value (static or callable ``fn() -> value``)
    :param comodel: target model name for relational fields
    :param inverse_field: for One2many — the Many2one field name on comodel
    :param pure: if True, compute is a pure function ``fn(**deps) -> value``
    """

    name: str
    type: str
    store: bool = True
    compute: Callable | None = None
    depends: tuple[str, ...] = ()
    required: bool = False
    default: typing.Any = None
    # Relational fields
    comodel: str | None = None
    inverse_field: str | None = None
    # Pure compute (Phase 2)
    pure: bool = False

    @property
    def model_name(self) -> str:
        """Set by ModelDef during registration."""
        return self._model_name

    @model_name.setter
    def model_name(self, value: str) -> None:
        self._model_name = value

    @property
    def is_stored_computed(self) -> bool:
        return self.store and self.compute is not None

    @property
    def is_relational(self) -> bool:
        return self.type in _RELATIONAL_TYPES

    def __hash__(self):
        return hash((self._model_name, self.name))

    def __eq__(self, other):
        if not isinstance(other, FieldDef):
            return NotImplemented
        return self._model_name == other._model_name and self.name == other.name

    def __repr__(self):
        return f"FieldDef({self._model_name}.{self.name})"


@dataclass(slots=True)
class ModelDef:
    """Lightweight model definition for InMemoryEnvironment.

    :param name: model name (e.g. "sale.order")
    :param fields: dict mapping field names to FieldDef instances
    """

    name: str
    fields: dict[str, FieldDef] = dataclass_field(default_factory=dict)

    def __post_init__(self):
        for fdef in self.fields.values():
            fdef.model_name = self.name


class InMemoryEnvironment:
    """Database-free ORM test environment.

    Supports:
    - Field access with compute-before-read guarantee
    - Computed fields (via plain Python callables or pure functions)
    - Many2one, One2many, Many2many relational fields
    - Dot-notation field traversal (e.g. ``"partner_id.name"``)
    - Cross-model dependency triggers via dotted depends
    - Cache-miss fetch from DictBackend storage
    - Dirty tracking and flush (to DictBackend)
    - Convergence loop with stall detection

    Does NOT support:
    - SQL domains, ACL, translations, IR models
    - Multi-user / multi-company contexts
    """

    def __init__(self, models: dict[str, ModelDef]) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.storage = DictBackend()
        self.uow = UnitOfWork(self.cache, self.engine)
        self._models = models
        self._next_id: dict[str, int] = dict.fromkeys(models, 1)

        # Build dependency graph: field → set of dependent fields
        # This handles both same-model and cross-model (dotted) dependencies.
        self._dependents: dict[FieldDef, set[FieldDef]] = {}
        self._cross_model_triggers: dict[FieldDef, set[FieldDef]] = {}
        self._build_dependency_graph()

    def _build_dependency_graph(self) -> None:
        """Build the dependency and trigger graphs from field definitions.

        For same-model deps like ``depends=("amount",)``, creates a direct
        edge: ``amount → computed_field``.

        For cross-model deps like ``depends=("partner_id.name",)``, creates:
        1. A trigger from the local relational field (``partner_id``)
        2. A cross-model trigger from the remote field (``partner.name``)
           that resolves through the relational field back to local records.
        """
        for model in self._models.values():
            for fdef in model.fields.values():
                if not fdef.compute or not fdef.depends:
                    continue
                for dep_path in fdef.depends:
                    if "." in dep_path:
                        # Cross-model: "partner_id.name"
                        parts = dep_path.split(".", 1)
                        local_fname, remote_fname = parts[0], parts[1]
                        # Trigger when the local relational field changes
                        local_field = model.fields.get(local_fname)
                        if local_field is not None:
                            self._dependents.setdefault(local_field, set()).add(fdef)
                        # Cross-model trigger: when the remote field changes,
                        # find local records pointing to that remote record
                        if local_field is not None and local_field.comodel:
                            remote_model = self._models.get(local_field.comodel)
                            if remote_model is not None:
                                remote_field = remote_model.fields.get(remote_fname)
                                if remote_field is not None:
                                    self._cross_model_triggers.setdefault(
                                        remote_field, set()
                                    ).add(fdef)
                    else:
                        # Same-model dependency
                        dep_field = model.fields.get(dep_path)
                        if dep_field is not None:
                            self._dependents.setdefault(dep_field, set()).add(fdef)

    def _get_field(self, model: str, field_name: str) -> FieldDef:
        """Look up a field definition."""
        model_def = self._models.get(model)
        if model_def is None:
            raise KeyError(f"Unknown model: {model!r}")
        fdef = model_def.fields.get(field_name)
        if fdef is None:
            raise KeyError(f"Unknown field: {model!r}.{field_name!r}")
        return fdef

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def create(self, model: str, values: dict) -> int:
        """Create a record, returning its auto-incremented ID.

        Stored computed fields get PENDING in cache and are scheduled
        for recomputation.  Many2many fields accept tuples of IDs.
        """
        model_def = self._models.get(model)
        if model_def is None:
            raise KeyError(f"Unknown model: {model!r}")

        record_id = self._next_id[model]
        self._next_id[model] += 1

        # Set provided values in cache
        for fname, value in values.items():
            fdef = model_def.fields[fname]
            # Normalize Many2many to tuple
            if fdef.type == "many2many" and isinstance(value, (list, set)):
                value = tuple(value)
            self.cache.set_value(fdef, record_id, value)
            self.cache.mark_dirty(fdef, [record_id])

        # Set defaults and PENDING for missing fields
        for fname, fdef in model_def.fields.items():
            if fname in values:
                continue
            # One2many fields are virtual — never stored directly
            if fdef.type == "one2many":
                continue
            if fdef.is_stored_computed:
                self.cache.set_value(fdef, record_id, PENDING)
                self.engine.schedule(fdef, [record_id])
            elif fdef.default is not None:
                default = fdef.default() if callable(fdef.default) else fdef.default
                self.cache.set_value(fdef, record_id, default)
                self.cache.mark_dirty(fdef, [record_id])
            # Default for Many2many is empty tuple, not None
            elif fdef.type == "many2many":
                self.cache.set_value(fdef, record_id, ())
                self.cache.mark_dirty(fdef, [record_id])
            else:
                self.cache.set_value(fdef, record_id, None)
                self.cache.mark_dirty(fdef, [record_id])

        return record_id

    def read(self, model: str, record_id: int, field_name: str) -> typing.Any:
        """Read a field value, triggering compute if needed.

        Supports:
        - Scalar fields: returns the cached/computed value
        - Many2one: returns the related record's ID (int or None)
        - One2many: returns a tuple of IDs from the inverse Many2one
        - Many2many: returns a tuple of IDs
        - Dot-notation: ``"partner_id.name"`` resolves through Many2one

        Non-stored computed fields are always computed on read (never cached),
        matching the real ORM's ``Field.__get__`` behavior for ``store=False``.
        """
        # Dot-notation: resolve through relational chain
        if "." in field_name:
            return self._read_dotted(model, record_id, field_name)

        fdef = self._get_field(model, field_name)

        # One2many: virtual field, resolved from inverse Many2one
        if fdef.type == "one2many":
            return self._resolve_one2many(fdef, record_id)

        # Non-stored computed: always compute on read (no caching)
        if fdef.compute and not fdef.store:
            return self._call_compute(fdef, record_id)

        # Inline resolve: check pending → read cache → fetch on miss
        if self.engine.has_pending_field(fdef):
            self._recompute_field(fdef)

        value = self.cache.get_value(fdef, record_id, default=PENDING)
        if value is not PENDING:
            return value

        self._fetch_from_storage(fdef, record_id)
        return self.cache.get_value(fdef, record_id, default=None)

    def _read_dotted(self, model: str, record_id: int, dotted_name: str) -> typing.Any:
        """Resolve a dot-separated field path like ``"partner_id.name"``.

        Traverses Many2one relationships: reads the Many2one to get the
        related ID, then reads the field on the related model.
        """
        parts = dotted_name.split(".", 1)
        local_fname, rest = parts[0], parts[1]

        # Read the local relational field
        fdef = self._get_field(model, local_fname)
        if fdef.type != "many2one":
            raise ValueError(
                f"Dot-notation requires Many2one traversal, "
                f"but {model}.{local_fname} is {fdef.type!r}"
            )

        related_id = self.read(model, record_id, local_fname)
        if related_id is None:
            return None
        if fdef.comodel is None:
            raise ValueError(f"Field {model}.{local_fname} has no comodel defined")

        # Recurse: read the rest of the path on the comodel
        return self.read(fdef.comodel, related_id, rest)

    def _resolve_one2many(self, fdef: FieldDef, record_id: int) -> tuple[int, ...]:
        """Resolve a One2many field by searching the inverse Many2one.

        Looks in both cache and storage for comodel records where the
        inverse Many2one field equals ``record_id``.
        """
        if fdef.comodel is None or fdef.inverse_field is None:
            return ()

        comodel = self._models.get(fdef.comodel)
        if comodel is None:
            return ()
        inverse_fdef = comodel.fields.get(fdef.inverse_field)
        if inverse_fdef is None:
            return ()

        # Search cache first
        result_ids: list[int] = []
        field_cache = self.cache.get_field_data(inverse_fdef)
        if field_cache:
            for rid, val in field_cache.items():
                if val is not PENDING and val == record_id:
                    result_ids.append(rid)

        # Also check storage for flushed records not in cache
        storage_ids = self.storage.search_rows(
            fdef.comodel, fdef.inverse_field, record_id
        )
        cache_id_set = set(result_ids)
        for sid in storage_ids:
            if sid not in cache_id_set:
                # Check if cache has a different value (cache wins)
                if field_cache and sid in field_cache:
                    continue  # already checked above
                result_ids.append(sid)

        return tuple(sorted(result_ids))

    def _fetch_from_storage(self, fdef: FieldDef, record_id: int) -> None:
        """On cache miss, try to fetch from DictBackend storage.

        This simulates the real ORM's ``_fetch_field`` behavior: when a
        cache miss occurs for a stored field, read from the database
        (here: DictBackend) and populate the cache.
        """
        row = self.storage.get_row(fdef.model_name, record_id)
        if row is not None and fdef.name in row:
            self.cache.set_value(fdef, record_id, row[fdef.name])

    def write(self, model: str, record_id: int, values: dict) -> None:
        """Write values to a record, marking dirty and scheduling recomputation.

        Schedules ALL transitive dependents, not just direct ones — matching
        the real ORM's ``modified()`` trigger tree traversal.  Also handles
        cross-model triggers for dotted dependencies.
        """
        model_def = self._models[model]
        for fname, value in values.items():
            fdef = model_def.fields[fname]
            # Normalize Many2many to tuple
            if fdef.type == "many2many" and isinstance(value, (list, set)):
                value = tuple(value)
            self.cache.set_value(fdef, record_id, value)
            self.cache.mark_dirty(fdef, [record_id])

            # Schedule transitive dependents (BFS) — same model
            self._schedule_dependents(fdef, [record_id])

            # Cross-model triggers: if we changed a Many2one, find
            # records on the comodel that are affected
            if fdef.type == "many2one":
                self._trigger_inverse_dependents(fdef, record_id, value)

    def _schedule_dependents(self, fdef: FieldDef, record_ids: list[int]) -> None:
        """BFS through the dependency graph, scheduling all dependents."""
        queue = deque(self._dependents.get(fdef, ()))
        visited: set[FieldDef] = set()
        while queue:
            dep = queue.popleft()
            if dep in visited:
                continue
            visited.add(dep)
            # Schedule on the right record IDs depending on model
            if dep.model_name == fdef.model_name:
                self.engine.schedule(dep, record_ids)
            else:
                # Cross-model: find which records of dep's model are affected
                affected = self._find_affected_records(fdef, dep, record_ids)
                if affected:
                    self.engine.schedule(dep, affected)
            queue.extend(self._dependents.get(dep, ()))

    def _find_affected_records(
        self,
        source_field: FieldDef,
        target_field: FieldDef,
        source_ids: list[int],
    ) -> list[int]:
        """Find records on the target model affected by changes to source records.

        For cross-model dependencies like ``partner_id.name`` on sale.order:
        when ``res.partner.name`` changes (source), find all sale.order records
        where ``partner_id`` points to the changed partner(s).
        """
        # Walk through the dependency path to find the relational link
        target_model = self._models.get(target_field.model_name)
        if target_model is None:
            return []

        # Find a Many2one field on target_model pointing to source_field's model
        for f in target_model.fields.values():
            if f.type == "many2one" and f.comodel == source_field.model_name:
                # Search cache for records pointing to source_ids
                affected = []
                field_cache = self.cache.get_field_data(f)
                if field_cache:
                    for rid, val in field_cache.items():
                        if val is not PENDING and val in source_ids:
                            affected.append(rid)
                return affected
        return []

    def _trigger_inverse_dependents(
        self,
        m2o_field: FieldDef,
        record_id: int,
        new_value: typing.Any,
    ) -> None:
        """When a Many2one changes, trigger cross-model dependents.

        For fields that depend on ``"m2o_field.remote_field"``, schedule
        recomputation when the Many2one target changes.
        """
        # Find cross-model triggers sourced from the comodel
        if m2o_field.comodel is None:
            return
        comodel = self._models.get(m2o_field.comodel)
        if comodel is None:
            return

        for remote_fdef in comodel.fields.values():
            cross_deps = self._cross_model_triggers.get(remote_fdef, set())
            for dep_field in cross_deps:
                if dep_field.model_name == m2o_field.model_name:
                    # The dep_field depends on "m2o.remote_field" — schedule it
                    self.engine.schedule(dep_field, [record_id])

    # ------------------------------------------------------------------
    # Compute execution
    # ------------------------------------------------------------------

    def _call_compute(self, fdef: FieldDef, record_id: int) -> typing.Any:
        """Call a compute function, handling both traditional and pure signatures.

        Traditional: ``fn(env, model, record_id) -> value``
        Pure:        ``fn(**{dep_name: dep_value}) -> value``
        """
        if fdef.pure and fdef.compute is not None:
            return self._call_pure_compute(fdef, record_id)
        if fdef.compute is not None:
            return fdef.compute(self, fdef.model_name, record_id)
        return None

    def _call_pure_compute(self, fdef: FieldDef, record_id: int) -> typing.Any:
        """Call a pure compute function with dependency values as keyword args.

        The function signature determines which values to pass::

            def compute_total(amount: float, qty: float) -> float:
                return amount * qty
        """
        kwargs = {}
        for dep_name in fdef.depends:
            if "." in dep_name:
                kwargs[dep_name.replace(".", "_")] = self.read(
                    fdef.model_name, record_id, dep_name
                )
            else:
                kwargs[dep_name] = self.read(fdef.model_name, record_id, dep_name)
        return fdef.compute(**kwargs)

    def _recompute_field(self, fdef: FieldDef) -> None:
        """Execute the compute function for a field on all pending records.

        After computing, schedules transitive dependents for recomputation
        (mirroring the ORM's ``modified()`` trigger propagation).
        """
        ids = list(self.engine.pending_ids(fdef))
        if not ids:
            return
        for record_id in ids:
            if fdef.compute is not None:
                value = self._call_compute(fdef, record_id)
                self.cache.set_value(fdef, record_id, value)
                self.cache.mark_dirty(fdef, [record_id])
        self.engine.mark_done(fdef, ids)
        # Schedule transitive dependents (like modified() in the real ORM)
        self._schedule_dependents(fdef, ids)
        # Also trigger cross-model dependents
        cross_deps = self._cross_model_triggers.get(fdef, set())
        for dep_field in cross_deps:
            affected = self._find_affected_records(fdef, dep_field, ids)
            if affected:
                self.engine.schedule(dep_field, affected)

    # ------------------------------------------------------------------
    # Flush
    # ------------------------------------------------------------------

    def flush(self) -> None:
        """Flush all dirty fields to DictBackend.

        Uses UnitOfWork's convergence loop for recomputation,
        then writes dirty values to storage.
        """

        def recompute_fn(field):
            self._recompute_field(field)

        def flush_fn(model_names):
            for model_name in model_names:
                model_def = self._models[model_name]
                # Collect per-record updates: {record_id: {field_name: value}}
                updates: dict[int, dict[str, typing.Any]] = {}
                for fdef in model_def.fields.values():
                    # Skip One2many (virtual) and non-stored fields
                    if fdef.type == "one2many" or not fdef.store:
                        continue
                    dirty_ids = self.cache.pop_dirty(fdef)
                    if dirty_ids:
                        for record_id in dirty_ids:
                            value = self.cache.get_value(fdef, record_id, default=None)
                            if value is not PENDING:
                                updates.setdefault(record_id, {})[fdef.name] = value
                if updates:
                    # Separate inserts (new rows) from updates (existing rows)
                    existing_ids = set(self.storage.table_ids(model_name))
                    to_insert = {
                        rid: vals
                        for rid, vals in updates.items()
                        if rid not in existing_ids
                    }
                    to_update = [
                        (rid, vals)
                        for rid, vals in updates.items()
                        if rid in existing_ids
                    ]
                    for rid, vals in to_insert.items():
                        tbl = self.storage._tables.setdefault(model_name, {})
                        tbl[rid] = vals
                    if to_update:
                        self.storage.update_rows(model_name, to_update)

        self.uow.run_flush_loop(recompute_fn, flush_fn)

    # ------------------------------------------------------------------
    # Storage access
    # ------------------------------------------------------------------

    def storage_get(self, model: str, record_id: int, field_name: str) -> typing.Any:
        """Read a value directly from storage (post-flush)."""
        row = self.storage.get_row(model, record_id)
        if row is None:
            return None
        return row.get(field_name)

    def __repr__(self) -> str:
        models = ", ".join(self._models.keys())
        return f"<InMemoryEnvironment models=[{models}]>"
