import unittest

from odoo.libs.collections import OrderedSet
from odoo.orm.components.compute import ComputeEngine
from odoo.orm.components.recompute import RecomputeScheduler


class _MockField:
    __slots__ = ("is_stored_computed", "name", "recursive", "tree_siblings")

    def __init__(
        self,
        name: str,
        *,
        stored_computed: bool = False,
        recursive: bool = False,
        tree_siblings: tuple = (),
    ) -> None:
        self.name = name
        self.is_stored_computed = stored_computed
        self.recursive = recursive
        # a field that shares no table with another stands alone, which is
        # what `Field.tree_siblings` defaults to
        self.tree_siblings = tree_siblings


class TestKnownSubtractionSemantics(unittest.TestCase):
    def test_marked_and_accumulated_with_ordered_sets(self) -> None:
        engine = ComputeEngine(pending_factory=OrderedSet)
        field = _MockField("parent_total", stored_computed=True, recursive=True)
        engine.schedule(field, [10, 11])

        scheduler = RecomputeScheduler(
            engine,
            marked=engine.pending,
            schedule_inline=True,
            set_factory=OrderedSet,
        )
        scheduler.schedule_recompute(field, OrderedSet([20, 21]))
        recursive_ids = scheduler.schedule_recompute(
            field, OrderedSet([10, 20, 30, 11, 21, 31])
        )

        self.assertEqual(recursive_ids, frozenset({30, 31}))
        self.assertEqual(list(engine.get_pending_ids(field)), [10, 11, 20, 21, 30, 31])

    def test_only_marked(self) -> None:
        engine = ComputeEngine()
        field = _MockField("f", stored_computed=True, recursive=True)
        scheduler = RecomputeScheduler(engine, marked={field: {1, 2}})
        self.assertEqual(scheduler.schedule_recompute(field, {1, 2, 3}), frozenset({3}))

    def test_only_accumulated(self) -> None:
        engine = ComputeEngine()
        field = _MockField("f", stored_computed=True, recursive=True)
        scheduler = RecomputeScheduler(engine)
        scheduler.schedule_recompute(field, {1, 2})
        self.assertEqual(scheduler.schedule_recompute(field, {2, 3}), frozenset({3}))

    def test_neither_leaves_ids_untouched(self) -> None:
        engine = ComputeEngine()
        field = _MockField("f", stored_computed=True, recursive=True)
        scheduler = RecomputeScheduler(engine)
        self.assertEqual(scheduler.schedule_recompute(field, {1, 2}), frozenset({1, 2}))

    def test_fully_known_is_a_noop(self) -> None:
        engine = ComputeEngine()
        field = _MockField("f", stored_computed=True, recursive=True)
        scheduler = RecomputeScheduler(engine, marked={field: {1}})
        scheduler.schedule_recompute(field, {2})
        self.assertEqual(scheduler.schedule_recompute(field, {1, 2}), frozenset())
        self.assertEqual(scheduler.to_recompute[field], {2})


class _MembershipOnlyView:
    def __init__(self, keys) -> None:
        self._keys = set(keys)
        self.lookups: list = []

    def __contains__(self, item) -> bool:
        self.lookups.append(item)
        return item in self._keys

    def __iter__(self):
        raise AssertionError("cached_ids must never be iterated (O(|cache|))")

    def __len__(self) -> int:
        return len(self._keys)


class TestCachedIdsIntersection(unittest.TestCase):
    def test_iterates_entry_ids_not_cache(self) -> None:
        engine = ComputeEngine(pending_factory=OrderedSet)
        field = _MockField("display", stored_computed=False, recursive=True)
        scheduler = RecomputeScheduler(
            engine, marked=engine.pending, set_factory=OrderedSet
        )

        cached = _MembershipOnlyView([9, 3, 7, 1])
        recursive_ids = scheduler.schedule_recompute(
            field, OrderedSet([1, 3, 5, 7]), cached_ids=cached
        )

        self.assertEqual(cached.lookups, [1, 3, 5, 7])
        self.assertEqual(recursive_ids, frozenset({1, 3, 7}))
        self.assertEqual(scheduler.to_invalidate, [(field, frozenset({1, 3, 7}))])

    def test_intersection_semantics_with_plain_sets(self) -> None:
        engine = ComputeEngine()
        field = _MockField("display", stored_computed=False, recursive=True)
        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.schedule_recompute(
            field, {1, 2, 3, 4, 5}, cached_ids={2, 4, 99}
        )
        self.assertEqual(recursive_ids, frozenset({2, 4}))

    def test_seen_then_cached_filter_composition(self) -> None:
        engine = ComputeEngine()
        field = _MockField("display", stored_computed=False, recursive=True)
        scheduler = RecomputeScheduler(engine)
        scheduler.schedule_recompute(field, {1, 2}, cached_ids={1, 2})
        recursive_ids = scheduler.schedule_recompute(
            field, {1, 3, 4}, cached_ids={1, 3}
        )
        self.assertEqual(recursive_ids, frozenset({3}))


if __name__ == "__main__":
    unittest.main()
