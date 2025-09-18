"""Standalone dependency graph for ORM fields.

This module provides :class:`ModelGraph`, an isolated data structure that
holds the field dependency graph (triggers, inverses, computed groups,
context dependencies).  It also houses :class:`TriggerTree`, a pure-data
tree structure representing the backwards-traversal plan for field
recomputation, and :class:`_Collector`, a lightweight key→tuple mapping
used for inverses, depends, and context dependencies.

All classes have **no dependency** on Environment, BaseModel, or database
cursors, making them fully testable with pure Python unit tests.

The graph is **static after construction**: built once when the registry
loads, then queried (read-only) by the trigger traversal, ComputeEngine,
and CRUD pipeline.  ModelGraph is the **single source of truth** for all
field metadata — Registry builds into it and delegates reads to it.

Usage from Registry::

    graph = ModelGraph()
    # Registry builds directly into graph's internal collections:
    graph._depends[field] = tuple(depends)
    graph._depends_context[field] = tuple(context_keys)
    # Triggers are built incrementally:
    graph.reset_triggers()
    graph.add_trigger(dep_field, path, [target_field])
    # Query:
    tree = graph.get_trigger_tree([field_a, field_b], select=bool)
"""

from collections import defaultdict
from collections.abc import Callable, Collection, Iterable, Iterator

# ---------------------------------------------------------------------------
# _Collector — lightweight key→tuple mapping (standalone Collector)
# ---------------------------------------------------------------------------


class _Collector(dict):
    """A mapping from keys to tuples, implementing a relation.

    Standalone equivalent of ``odoo.libs.collections.misc.Collector`` —
    kept here so that :class:`ModelGraph` has zero Odoo imports and remains
    fully testable with pure Python.

    Semantically a ``defaultdict(tuple)`` with convenience methods for
    adding individual values and bulk discarding.
    """

    __slots__ = ()

    def __getitem__(self, key):
        return self.get(key, ())

    def __setitem__(self, key, val):
        val = tuple(val)
        if val:
            super().__setitem__(key, val)
        else:
            super().pop(key, None)

    def add(self, key, val):
        """Append *val* to the tuple for *key* (no-op if already present)."""
        vals = self[key]
        if val not in vals:
            self[key] = vals + (val,)

    def discard_keys_and_values(self, excludes) -> None:
        """Remove *excludes* from both keys and values."""
        for key in excludes:
            self.pop(key, None)
        for key, vals in list(self.items()):
            self[key] = tuple(val for val in vals if val not in excludes)


# ---------------------------------------------------------------------------
# TriggerTree — pure data structure
# ---------------------------------------------------------------------------


class TriggerTree(dict):
    r"""Tree of field triggers for backwards dependency traversal.

    Each node contains:
    - ``root``: collection of fields that need recomputation when the
      trigger fires at this level of the tree.
    - dict entries: ``{edge_field: subtree}`` for traversing backwards
      along relational fields.

    For instance, assume that G depends on F, H depends on X.F, I depends
    on W.X.F, and J depends on Y.F.  The triggers of F will be the tree::

                                     [G]
                                   X/   \\Y
                                 [H]     [J]
                               W/
                             [I]

    This tree provides perfect support for the trigger mechanism:
    when F is modified on records,
     - mark G to recompute on records,
     - mark H to recompute on inverse(X, records),
     - mark I to recompute on inverse(W, inverse(X, records)),
     - mark J to recompute on inverse(Y, records).
    """

    __slots__ = ("root",)
    root: Collection

    def __init__(self, root: Collection = (), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root

    def __bool__(self) -> bool:
        return bool(self.root or len(self))

    def __repr__(self) -> str:
        return f"TriggerTree(root={self.root!r}, {super().__repr__()})"

    def increase(self, key) -> TriggerTree:
        """Return the subtree for *key*, creating it if absent."""
        try:
            return self[key]
        except KeyError:
            subtree = self[key] = TriggerTree()
            return subtree

    def depth_first(self) -> Iterator[TriggerTree]:
        """Yield all nodes in depth-first order."""
        yield self
        for subtree in self.values():
            yield from subtree.depth_first()

    @classmethod
    def merge(cls, trees: list[TriggerTree], select: Callable = bool) -> TriggerTree:
        """Merge trigger trees into a single tree.

        The function *select* is called on every field to determine which
        fields should be kept in the tree nodes.  This enables discarding
        some fields from the tree nodes (e.g. non-stored computed fields
        with no cached data).
        """
        # Fast path: single tree — skip merge overhead (defaultdict, dedup).
        # For the common case (single-field write), this avoids ~15 Python
        # operations and returns the cached tree directly when all root
        # fields pass ``select`` and the tree has no subtrees.
        if len(trees) == 1:
            return trees[0]._filtered(select)

        root_fields: list = []
        subtrees_to_merge: dict = defaultdict(list)

        for tree in trees:
            root_fields.extend(tree.root)
            for label, subtree in tree.items():
                subtrees_to_merge[label].append(subtree)

        # deduplicate while preserving order
        seen: set = set()
        unique_root: list = []
        for field in root_fields:
            if field not in seen:
                seen.add(field)
                unique_root.append(field)

        result = cls([field for field in unique_root if select(field)])
        for label, subtrees in subtrees_to_merge.items():
            subtree = cls.merge(subtrees, select)
            if subtree:
                result[label] = subtree

        return result

    def _filtered(self, select: Callable) -> TriggerTree:
        """Return a filtered copy of this tree, or ``self`` if nothing
        was filtered out.  Avoids allocations in the common case where
        all root fields pass *select*.
        """
        root = self.root
        filtered_root = [f for f in root if select(f)]
        # Root-only tree (no subtrees) where all fields pass: return self
        if len(filtered_root) == len(root) and not len(self):
            return self
        result = TriggerTree(filtered_root)
        for label, subtree in self.items():
            filtered_sub = subtree._filtered(select)
            if filtered_sub:
                result[label] = filtered_sub
        return result


# ---------------------------------------------------------------------------
# ModelGraph — frozen dependency graph
# ---------------------------------------------------------------------------


class ModelGraph:
    """Frozen directed graph of field dependencies.

    Static after construction — all query methods are read-only.
    Constructed once when the registry loads, then shared immutably
    by Transaction, ComputeEngine, and the trigger traversal.

    Internal data structures:

    * ``_triggers``: raw trigger data —
      ``{dep_field: {path: list_of_target_fields}}``
    * ``_inverses``: ``{field: tuple_of_inverse_fields}``
    * ``_depends``: ``{field: tuple_of_dependency_fields}``
    * ``_depends_context``: ``{field: tuple_of_context_keys}``
    * ``_computed``: ``{field: list_of_co_computed_fields}``

    The ``_trigger_trees`` dict is a lazy cache of per-field TriggerTrees
    computed from ``_triggers`` on first access.
    """

    __slots__ = (
        "_computed",
        "_depends",
        "_depends_context",
        "_inverses",
        "_modifying_relations",
        "_recompute_order",
        "_trigger_trees",
        "_triggers",
    )

    def __init__(self) -> None:
        # Raw trigger data: {dep_field: {path_tuple: set_of_target_fields}}
        self._triggers: defaultdict = defaultdict(lambda: defaultdict(list))
        # Field inverses: _Collector {field: tuple_of_inverse_fields}
        self._inverses: _Collector = _Collector()
        # Field dependencies: _Collector {field: tuple_of_dependency_fields}
        self._depends: _Collector = _Collector()
        # Context dependencies: _Collector {field: tuple_of_context_keys}
        self._depends_context: _Collector = _Collector()
        # Computed groups: {field: [field, co_field1, ...]}
        self._computed: dict = {}
        # Lazy caches
        self._trigger_trees: dict = {}
        self._modifying_relations: dict = {}
        self._recompute_order: list | None = None

    # ------------------------------------------------------------------
    # Construction API
    # ------------------------------------------------------------------

    def add_trigger(self, dep_field, path: tuple, targets: Iterable) -> None:
        """Register that *targets* depend on *dep_field* via *path*.

        :param dep_field: the dependency field (hashable key)
        :param path: tuple of relational fields to inverse-traverse
        :param targets: fields that need recomputation
        """
        bucket = self._triggers[dep_field][path]
        for target in targets:
            if target not in bucket:
                bucket.append(target)

    def reset_triggers(self) -> None:
        """Reset trigger data to empty state for rebuilding.

        Called at the start of trigger construction (Registry._field_triggers)
        before incrementally adding triggers via :meth:`add_trigger`.
        Also clears the lazily-computed trigger tree caches.
        """
        self._triggers = defaultdict(lambda: defaultdict(list))
        self.clear_caches()

    def reset_field_metadata(self) -> None:
        """Reset all field metadata collections to empty state.

        Called during full registry setup (``setup_models(model_names=None)``)
        to clear stale metadata before rebuilding.  Does NOT clear triggers
        or caches — those are handled separately.
        """
        self._inverses = _Collector()
        self._depends = _Collector()
        self._depends_context = _Collector()
        self._computed = {}

    def clear_caches(self) -> None:
        """Clear the lazily-computed caches (trigger trees, modifying relations).

        Called when the registry is invalidated (e.g. field setup, module reload).
        """
        self._trigger_trees.clear()
        self._modifying_relations.clear()
        self._recompute_order = None

    def discard_fields(self, fields: Collection) -> None:
        """Remove *fields* from all internal data structures.

        Called when fields are removed from the registry (e.g. custom field
        deletion).  Also clears trigger caches.
        """
        for f in fields:
            self._depends.pop(f, None)
            self._depends_context.pop(f, None)
            self._computed.pop(f, None)
            self._triggers.pop(f, None)

        # Discard from inverses (keys and values)
        self._inverses.discard_keys_and_values(fields)

        self.clear_caches()

    # ------------------------------------------------------------------
    # Query API — trigger trees
    # ------------------------------------------------------------------

    def has_triggers(self, field) -> bool:
        """Return whether *field* has any dependents (is in the trigger map)."""
        return field in self._triggers

    def get_trigger_tree(self, fields: list, select: Callable = bool) -> TriggerTree:
        """Return the merged trigger tree for *fields*.

        The function *select* is called on every target field; only those
        for which it returns True are included.
        """
        trees = [
            self.get_field_trigger_tree(field)
            for field in fields
            if field in self._triggers
        ]
        return TriggerTree.merge(trees, select)

    def get_field_trigger_tree(self, field) -> TriggerTree:
        """Return the trigger tree for a single field.

        Computed lazily from the transitive closure of ``_triggers`` and
        cached in ``_trigger_trees``.
        """
        try:
            return self._trigger_trees[field]
        except KeyError:
            pass

        triggers = self._triggers
        if field not in triggers:
            return TriggerTree()

        def transitive_triggers(field, prefix=(), seen=()):
            if field in seen or field not in triggers:
                return
            for path, targets in triggers[field].items():
                full_path = _concat_paths(prefix, path, self._inverses)
                yield full_path, targets
                for target in targets:
                    yield from transitive_triggers(target, full_path, seen + (field,))

        tree = TriggerTree()
        for path, targets in transitive_triggers(field):
            current = tree
            for label in path:
                current = current.increase(label)
            if current.root:
                # Merge targets, preserving order and deduplicating
                existing = set(current.root)
                current.root = list(current.root) + [
                    t for t in targets if t not in existing
                ]
            else:
                current.root = list(targets)

        self._trigger_trees[field] = tree
        return tree

    def get_dependent_fields(self, field) -> Iterator:
        """Return an iterable of all fields that depend on *field*."""
        if field not in self._triggers:
            return
        for tree in self.get_field_trigger_tree(field).depth_first():
            yield from tree.root

    def is_modifying_relations(self, field) -> bool:
        """Return whether modifying *field* might change dependent records.

        True if *field* has triggers AND (field is relational, or has
        inverses, or any of its dependents are relational / have inverses).
        """
        try:
            return self._modifying_relations[field]
        except KeyError:
            pass

        result = field in self._triggers and bool(
            _is_relational(field)
            or self._inverses.get(field, ())
            or any(
                _is_relational(dep) or self._inverses.get(dep, ())
                for dep in self.get_dependent_fields(field)
            )
        )
        self._modifying_relations[field] = result
        return result

    # ------------------------------------------------------------------
    # Topological ordering for recomputation
    # ------------------------------------------------------------------

    @property
    def recompute_order(self) -> dict:
        """Return a priority map ``{field: int}`` for recomputation ordering.

        Fields with lower priority values should be recomputed first.
        Dependencies come before their dependents — if field B depends on
        field A, then ``order[A] < order[B]``.

        Computed lazily from ``_triggers`` via Kahn's algorithm (BFS
        topological sort).  Cycles are broken by assigning equal priority
        to all fields in the cycle — the convergence loop handles those.

        Used by :class:`UnitOfWork` to process pending recomputations in
        dependency order, reducing the number of convergence iterations
        from O(depth) to O(1) for acyclic dependency chains.
        """
        if self._recompute_order is None:
            self._recompute_order = self._compute_recompute_order()
        return self._recompute_order

    def _compute_recompute_order(self) -> dict:
        """Compute topological ordering of stored-computed fields.

        Uses Kahn's algorithm: fields with no unsatisfied dependencies
        are processed first, then their dependents become available.

        Only considers stored-computed target fields from the trigger map
        (non-stored computed fields are invalidated, not recomputed).

        Returns ``{field: priority_int}`` where lower = should compute first.
        """
        # Build adjacency: field → set of fields it triggers (direct dependents)
        # Only from stored-computed trigger targets (root-level in trigger trees)
        adjacency: dict = {}  # field → set of direct dependents
        in_degree: dict = {}  # field → number of dependencies

        # Collect all stored-computed fields that appear as trigger targets
        all_targets: set = set()
        for dep_field, paths in self._triggers.items():
            for targets in paths.values():
                for target in targets:
                    if getattr(target, "store", False) and getattr(
                        target, "compute", None
                    ):
                        all_targets.add(target)
                        if dep_field in all_targets or (
                            getattr(dep_field, "store", False)
                            and getattr(dep_field, "compute", None)
                        ):
                            all_targets.add(dep_field)

        # Initialize
        for field in all_targets:
            adjacency.setdefault(field, set())
            in_degree.setdefault(field, 0)

        # Build edges: dep_field → target means "when dep_field changes,
        # target needs recomputation".  So dep_field must be computed first.
        for dep_field, paths in self._triggers.items():
            if dep_field not in all_targets:
                continue
            for targets in paths.values():
                for target in targets:
                    if target in all_targets and target is not dep_field:
                        if target not in adjacency.get(dep_field, ()):
                            adjacency.setdefault(dep_field, set()).add(target)
                            in_degree[target] = in_degree.get(target, 0) + 1

        # Kahn's BFS
        queue = [f for f in all_targets if in_degree.get(f, 0) == 0]
        order: dict = {}
        priority = 0

        while queue:
            # Process all fields at this priority level
            next_queue = []
            for field in queue:
                order[field] = priority
                for dependent in adjacency.get(field, ()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)
            queue = next_queue
            priority += 1

        # Fields in cycles get max priority (processed last, convergence
        # loop handles them).  This is safe because cycles are rare and
        # the existing loop already handles them.
        for field in all_targets:
            if field not in order:
                order[field] = priority

        return order

    # ------------------------------------------------------------------
    # Direct access — backward-compatible properties
    # ------------------------------------------------------------------

    @property
    def field_inverses(self) -> dict:
        """Direct access to the inverses mapping."""
        return self._inverses

    @property
    def field_depends(self) -> dict:
        """Direct access to the field dependencies mapping."""
        return self._depends

    @property
    def field_depends_context(self) -> dict:
        """Direct access to the context dependencies mapping."""
        return self._depends_context

    @property
    def field_computed(self) -> dict:
        """Direct access to the computed-groups mapping."""
        return self._computed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _concat_paths(seq1: tuple, seq2: tuple, inverses: dict) -> tuple:
    """Concatenate two path segments, cancelling m2o→o2m round-trips.

    When a many2one field at the end of *seq1* is immediately followed by
    its inverse one2many at the start of *seq2*, the pair cancels out
    (navigating to the parent then back to children is a no-op).
    """
    if seq1 and seq2:
        f1, f2 = seq1[-1], seq2[0]
        if (
            _field_type(f1) == "many2one"
            and _field_type(f2) == "one2many"
            and _field_attr(f2, "inverse_name") == _field_attr(f1, "name")
            and _field_attr(f1, "model_name") == _field_attr(f2, "comodel_name")
            and _field_attr(f1, "comodel_name") == _field_attr(f2, "model_name")
        ):
            return _concat_paths(seq1[:-1], seq2[1:], inverses)
    return seq1 + seq2


def _field_type(field) -> str:
    """Get the type of a field, supporting both real Field objects and mock objects."""
    return getattr(field, "type", "")


def _field_attr(field, attr: str):
    """Get an attribute from a field, returning None if not present."""
    return getattr(field, attr, None)


def _is_relational(field) -> bool:
    """Check if a field is relational."""
    return getattr(field, "relational", False)
