import logging
import threading
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from odoo.libs.accel import get_trigger_trees as _get_trigger_trees
from odoo.libs.collections import Collector
from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Iterator

    from ._protocols import FieldLike


_Collector = Collector

_debug = DebugLog(__name__)
_logger = logging.getLogger(__name__)

_TREE_NODE_BUDGET = 20_000


def _measure(node: tuple) -> tuple[int, int]:
    nodes, depth = 1, 0
    for _label, child in node[1]:
        child_nodes, child_depth = _measure(child)
        nodes += child_nodes
        depth = max(depth, child_depth + 1)
    return nodes, depth


def _get_stored_compute_adjacency(triggers: defaultdict) -> dict:
    all_targets: set = set()
    for dep_field, paths in triggers.items():
        for targets in paths.values():
            for target in targets:
                if target.store and target.compute:
                    all_targets.add(target)
                    if dep_field.store and dep_field.compute:
                        all_targets.add(dep_field)

    adjacency: dict = {field: set() for field in all_targets}
    for dep_field, paths in triggers.items():
        if dep_field not in all_targets:
            continue
        dep_adjacency = adjacency[dep_field]
        for targets in paths.values():
            for target in targets:
                if target in all_targets and target is not dep_field:
                    dep_adjacency.add(target)
    return adjacency


def _condense_components(
    adjacency: dict, sccs: list
) -> tuple[dict, list[set[int]], list[int]]:
    component_of: dict = {}
    for component_index, component in enumerate(sccs):
        for field in component:
            component_of[field] = component_index
    component_adjacency: list[set[int]] = [set() for _ in sccs]
    component_in_degree: list[int] = [0] * len(sccs)
    for field, dependents in adjacency.items():
        source = component_of[field]
        source_adjacency = component_adjacency[source]
        for dependent in dependents:
            sink = component_of[dependent]
            if sink != source and sink not in source_adjacency:
                source_adjacency.add(sink)
                component_in_degree[sink] += 1
    return component_of, component_adjacency, component_in_degree


class TriggerTree(dict):
    __slots__ = ("root",)
    root: Collection

    def __init__(self, root: Collection = (), *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.root = tuple(root)

    def __bool__(self) -> bool:
        return bool(self.root or len(self))

    def __repr__(self) -> str:
        return f"TriggerTree(root={self.root!r}, {super().__repr__()})"

    def increase(self, key: Any) -> TriggerTree:
        try:
            return self[key]
        except KeyError:
            subtree = self[key] = TriggerTree()
            return subtree

    def iter_depth_first(self) -> Iterator[TriggerTree]:
        yield self
        for subtree in self.values():
            yield from subtree.iter_depth_first()

    @classmethod
    def merge(cls, trees: list[TriggerTree], select: Callable = bool) -> TriggerTree:
        if len(trees) == 1:
            return trees[0]._filtered(select)

        root_fields: list[Any] = []
        subtrees_to_merge: dict[Any, list[TriggerTree]] = defaultdict(list)

        for tree in trees:
            root_fields.extend(tree.root)
            for label, subtree in tree.items():
                subtrees_to_merge[label].append(subtree)

        seen: set[Any] = set()
        unique_root: list[Any] = []
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
        root = self.root
        filtered_root = [f for f in root if select(f)]
        children_changed = False
        filtered_children: list[tuple[Any, TriggerTree]] = []
        for label, subtree in self.items():
            filtered_sub = subtree._filtered(select)
            if filtered_sub is not subtree:
                children_changed = True
            if filtered_sub:
                filtered_children.append((label, filtered_sub))
        if len(filtered_root) == len(root) and not children_changed:
            return self
        result = TriggerTree(filtered_root)
        for label, filtered_sub in filtered_children:
            result[label] = filtered_sub
        return result


class _TriggerIndex:
    __slots__ = ("field_ids", "fields", "meta", "payload")

    def __init__(
        self, triggers: defaultdict, fact_of: Callable[[Any], Any] | None = None
    ) -> None:
        self.field_ids: dict[Any, int] = {}
        self.fields: list[Any] = []
        self.payload = [
            (
                self._get_or_create_field_id(dep),
                [
                    (
                        [self._get_or_create_field_id(f) for f in path],
                        [self._get_or_create_field_id(t) for t in targets],
                    )
                    for path, targets in buckets.items()
                ],
            )
            for dep, buckets in triggers.items()
        ]
        strings: dict[Any, int] = {}
        facts: dict[Any, int] = {}
        self.meta = [
            (
                getattr(field, "is_many2one", False),
                getattr(field, "is_one2many", False),
                strings.setdefault(getattr(field, "name", None), len(strings)),
                strings.setdefault(getattr(field, "inverse_name", None), len(strings)),
                strings.setdefault(getattr(field, "model_name", None), len(strings)),
                strings.setdefault(getattr(field, "comodel_name", None), len(strings)),
                facts.setdefault(fact_of(field) if fact_of else field, len(facts)),
            )
            for field in self.fields
        ]

    def _get_or_create_field_id(self, field: Any) -> int:
        field_id = self.field_ids.get(field)
        if field_id is None:
            field_id = self.field_ids[field] = len(self.fields)
            self.fields.append(field)
        return field_id

    def get_trees(self, fields: list[Any] | None) -> dict[Any, TriggerTree]:
        wanted = None if fields is None else [self.field_ids[f] for f in fields]
        if _debug.perf.enabled:
            return self._get_trees_one_by_one(wanted)
        return {
            self.fields[field_id]: self._wrap(node)
            for field_id, node in _get_trigger_trees(self.payload, self.meta, wanted)
        }

    # One native call builds every tree before returning, so a tree that grows
    # without bound names no field. With the perf channel on, each tree is
    # built alone, measured, and logged before the next.
    def _get_trees_one_by_one(self, wanted: list[int] | None) -> dict[Any, TriggerTree]:
        if wanted is None:
            wanted = [field_id for field_id, _buckets in self.payload]
        trees = {}
        for field_id in wanted:
            field = self.fields[field_id]
            _debug.pipeline("model_graph.tree_building", field=field)
            with _debug.perf("model_graph.tree_built", field=field) as span:
                [(_, node)] = _get_trigger_trees(self.payload, self.meta, [field_id])
                nodes, depth = _measure(node)
                span.set(nodes=nodes, depth=depth)
            if nodes > _TREE_NODE_BUDGET:
                _logger.warning(
                    "trigger tree of %s holds %d nodes (depth %d), over the budget "
                    "of %d; a dependency cycle through a path is the usual cause",
                    field,
                    nodes,
                    depth,
                    _TREE_NODE_BUDGET,
                )
            trees[field] = self._wrap(node)
        return trees

    def _wrap(self, node: tuple) -> TriggerTree:
        root, children = node
        fields = self.fields
        tree = TriggerTree([fields[i] for i in root])
        for label, child in children:
            tree[fields[label]] = self._wrap(child)
        return tree


class _TriggerState:
    __slots__ = (
        "fact_of",
        "index",
        "merged",
        "modifying_relations",
        "path_fields",
        "recompute_order",
        "trees",
        "triggers",
    )

    def __init__(
        self, triggers: defaultdict, fact_of: Callable[[Any], Any] | None = None
    ) -> None:
        self.triggers = triggers
        self.fact_of = fact_of
        self.index: _TriggerIndex | None = None
        self.trees: dict[Any, TriggerTree] = {}
        self.merged: dict[tuple, TriggerTree] = {}
        self.modifying_relations: dict[Any, bool] = {}
        self.path_fields: frozenset | None = None
        self.recompute_order: dict[Any, int] | None = None

    def get_index(self) -> _TriggerIndex:
        index = self.index
        if index is None:
            index = self.index = _TriggerIndex(self.triggers, self.fact_of)
        return index

    def get_path_fields(self) -> frozenset:
        path_fields = self.path_fields
        if path_fields is None:
            path_fields = self.path_fields = frozenset(
                field
                for paths in self.triggers.values()
                for path in paths
                for field in path
            )
        return path_fields


_MERGED_CACHE_MAX = 512


def _get_empty_triggers() -> defaultdict:
    return defaultdict(lambda: defaultdict(list))


class ModelGraph:
    __slots__ = (
        "_computed",
        "_depends",
        "_depends_context",
        "_epoch",
        "_invalidation_barrier",
        "_inverses",
        "_publish_lock",
        "_state",
    )

    def __init__(self) -> None:
        self._inverses: _Collector = _Collector()
        self._depends: _Collector = _Collector()
        self._depends_context: _Collector = _Collector()
        self._computed: dict[Any, list] = {}
        self._state: _TriggerState = _TriggerState(_get_empty_triggers())
        self._epoch: int = 0
        self._invalidation_barrier: bool = False
        self._publish_lock = threading.Lock()

    @property
    def _triggers(self) -> defaultdict:
        return self._state.triggers

    @property
    def _trigger_trees(self) -> dict[Any, TriggerTree]:
        return self._state.trees

    @property
    def _modifying_relations(self) -> dict[Any, bool]:
        return self._state.modifying_relations

    @property
    def _recompute_order(self) -> dict[Any, int] | None:
        return self._state.recompute_order

    def add_trigger(self, dep_field: Any, path: tuple, targets: Iterable) -> None:
        with self._publish_lock:
            state = self._state
            bucket = state.triggers[dep_field][path]
            for target in targets:
                if target not in bucket:
                    bucket.append(target)
            state.index = None
            state.trees.pop(dep_field, None)
            state.merged.clear()
            state.modifying_relations.clear()
            state.path_fields = None
            state.recompute_order = None

    def reset_triggers(self) -> None:
        with self._publish_lock:
            self._state = _TriggerState(_get_empty_triggers())

    def set_triggers(
        self,
        triggers: defaultdict,
        *,
        epoch: int | None = None,
        fact_of: Callable[[Any], Any] | None = None,
    ) -> bool:
        state = _TriggerState(triggers, fact_of)
        with self._publish_lock:
            if epoch is not None and (
                self._invalidation_barrier or epoch != self._epoch
            ):
                _debug.logic(
                    "model_graph.set_triggers.rejected",
                    epoch=epoch,
                    current_epoch=self._epoch,
                    barrier=self._invalidation_barrier,
                )
                return False
            self._state = state
        _debug.lifecycle(
            "model_graph.triggers_published",
            epoch=self._epoch,
            fields=len(triggers),
        )
        return True

    @property
    def trigger_epoch(self) -> int:
        return self._epoch

    def begin_invalidation(self) -> None:
        with self._publish_lock:
            self._epoch += 1
            self._invalidation_barrier = True
        _debug.lifecycle("model_graph.invalidation_begin", epoch=self._epoch)

    def end_invalidation(self) -> None:
        with self._publish_lock:
            self._epoch += 1
            self._invalidation_barrier = False
        _debug.lifecycle("model_graph.invalidation_end", epoch=self._epoch)

    def reset_field_metadata(self) -> None:
        self._inverses.clear()
        self._depends.clear()
        self._depends_context.clear()
        self._computed.clear()

    def clear_caches(self) -> None:
        _debug.lifecycle("model_graph.caches_cleared", epoch=self._epoch)
        with self._publish_lock:
            self._state = _TriggerState(self._state.triggers, self._state.fact_of)

    def discard_fields(self, fields: Collection) -> None:
        discarded = set(fields)
        for f in discarded:
            self._depends.pop(f, None)
            self._depends_context.pop(f, None)
            self._computed.pop(f, None)

        self._inverses.discard_keys_and_values(fields)

        old_triggers = self._state.triggers
        new_triggers = _get_empty_triggers()
        for dep, buckets in old_triggers.items():
            if dep in discarded:
                continue
            for path, targets in buckets.items():
                kept = [t for t in targets if t not in discarded]
                if kept:
                    new_triggers[dep][path] = kept

        _debug.lifecycle(
            "model_graph.fields_discarded",
            fields=len(discarded),
            triggers_before=len(old_triggers),
            triggers_after=len(new_triggers),
        )
        with self._publish_lock:
            self._state = _TriggerState(new_triggers, self._state.fact_of)

    def has_triggers(self, field: Any) -> bool:
        return field in self._state.triggers

    def get_trigger_tree(
        self, fields: list[Any], select: Callable = bool
    ) -> TriggerTree:
        state = self._state
        key = tuple(fields)
        structure = state.merged.get(key)
        if structure is None:
            trees = [
                self._get_field_trigger_tree(state, field)
                for field in fields
                if field in state.triggers
            ]
            structure = TriggerTree.merge(trees, bool)
            _debug.perf.count(
                "model_graph.trigger_tree_merged",
                fields=len(fields),
                trees=len(trees),
                cached=len(state.merged),
            )
            if len(state.merged) >= _MERGED_CACHE_MAX:
                _debug.logic(
                    "model_graph.merged_cache_evicted", entries=len(state.merged)
                )
                state.merged.clear()
            state.merged[key] = structure
        return structure._filtered(select)

    def get_field_trigger_tree(self, field: Any) -> TriggerTree:
        return self._get_field_trigger_tree(self._state, field)

    def _get_field_trigger_tree(self, state: _TriggerState, field: Any) -> TriggerTree:
        try:
            return state.trees[field]
        except KeyError:
            pass

        if field not in state.triggers:
            return TriggerTree()

        self._add_missing_trees(state)
        return state.trees[field]

    @staticmethod
    def _add_missing_trees(state: _TriggerState) -> None:
        missing = [field for field in state.triggers if field not in state.trees]
        if missing:
            with _debug.perf("model_graph.trees_built", missing=len(missing)):
                state.trees.update(state.get_index().get_trees(missing))

    def get_dependent_fields(self, field: Any) -> Iterator[Any]:
        return self._get_dependent_fields(self._state, field)

    def _get_dependent_fields(self, state: _TriggerState, field: Any) -> Iterator[Any]:
        if field not in state.triggers:
            return
        for tree in self._get_field_trigger_tree(state, field).iter_depth_first():
            yield from tree.root

    def is_modifying_relations(self, field: Any) -> bool:
        return self._is_modifying_relations(self._state, field)

    def _is_modifying_relations(self, state: _TriggerState, field: Any) -> bool:
        if field not in state.triggers:
            return False

        try:
            return state.modifying_relations[field]
        except KeyError:
            pass

        path_fields = state.get_path_fields()
        result = self._modifies_relations(field, path_fields) or any(
            self._modifies_relations(dep, path_fields)
            for dep in self._get_dependent_fields(state, field)
        )
        state.modifying_relations[field] = result
        return result

    def _modifies_relations(self, field: Any, path_fields: frozenset) -> bool:
        return bool(self._inverses.get(field, ())) or field in path_fields

    @property
    def recompute_order(self) -> dict[Any, int]:
        state = self._state
        order = state.recompute_order
        if order is None:
            with _debug.perf(
                "model_graph.recompute_order", triggers=len(state.triggers)
            ) as span:
                order = state.recompute_order = self._get_recompute_order(
                    state.triggers
                )
                span.set(fields=len(order))
        return order

    @staticmethod
    def _get_recompute_order(
        triggers: defaultdict,
    ) -> dict[FieldLike, int]:
        adjacency = _get_stored_compute_adjacency(triggers)
        sccs = _get_strongly_connected_components(adjacency)
        _, component_adjacency, component_in_degree = _condense_components(
            adjacency, sccs
        )

        queue: list[int] = [
            index for index, degree in enumerate(component_in_degree) if degree == 0
        ]
        order: dict[FieldLike, int] = {}
        priority = 0
        while queue:
            next_queue: list[int] = []
            for index in queue:
                for field in sccs[index]:
                    order[field] = priority
                for sink in component_adjacency[index]:
                    component_in_degree[sink] -= 1
                    if component_in_degree[sink] == 0:
                        next_queue.append(sink)
            queue = next_queue
            priority += 1

        return order

    def freeze(self) -> None:
        state = self._state
        with _debug.perf("model_graph.freeze", fields=len(state.triggers)) as span:
            self._add_missing_trees(state)
            for field in state.triggers:
                self._is_modifying_relations(state, field)
            if state.recompute_order is None:
                state.recompute_order = self._get_recompute_order(state.triggers)
            span.set(trees=len(state.trees), ordered=len(state.recompute_order or ()))

    def set_inverses(self, inverses: _Collector) -> None:
        self._inverses = inverses

    def set_computed(self, computed: dict[Any, list]) -> None:
        self._computed = computed

    @property
    def published_triggers(self) -> defaultdict:
        return self._state.triggers

    @property
    def field_inverses(self) -> _Collector:
        return self._inverses

    @property
    def field_depends(self) -> _Collector:
        return self._depends

    @property
    def field_depends_context(self) -> _Collector:
        return self._depends_context

    @property
    def field_computed(self) -> dict[Any, list]:
        return self._computed


def _get_strongly_connected_components(
    adjacency: dict[Any, set[Any]],
) -> list[list[Any]]:
    index_of: dict[Any, int] = {}
    lowlink: dict[Any, int] = {}
    on_stack: set[Any] = set()
    stack: list[Any] = []
    components: list[list[Any]] = []
    next_index = 0

    for root, root_successors in adjacency.items():
        if root in index_of:
            continue
        index_of[root] = lowlink[root] = next_index
        next_index += 1
        stack.append(root)
        on_stack.add(root)
        work: list[tuple[Any, Iterator[Any]]] = [(root, iter(root_successors))]
        while work:
            node, successors = work[-1]
            advanced = False
            for successor in successors:
                if successor not in index_of:
                    index_of[successor] = lowlink[successor] = next_index
                    next_index += 1
                    stack.append(successor)
                    on_stack.add(successor)
                    work.append((successor, iter(adjacency[successor])))
                    advanced = True
                    break
                if successor in on_stack and index_of[successor] < lowlink[node]:
                    lowlink[node] = index_of[successor]
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
            if lowlink[node] == index_of[node]:
                component: list[Any] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member is node:
                        break
                components.append(component)

    return components
