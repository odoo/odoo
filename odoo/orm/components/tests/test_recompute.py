"""Pure-Python tests for RecomputeScheduler — no Odoo, no database required.

Uses lightweight mock fields (simple objects with ``recursive`` and
``is_stored_computed`` attributes) to prove the scheduler is fully
decoupled from the ORM runtime.
"""

import unittest

from odoo.orm.components.compute import ComputeEngine
from odoo.orm.components.recompute import RecomputeScheduler


class _MockField:
    """Lightweight field stub for testing the scheduler."""

    __slots__ = ("is_stored_computed", "name", "recursive")

    def __init__(self, name, *, stored_computed=False, recursive=False):
        self.name = name
        self.is_stored_computed = stored_computed
        self.recursive = recursive

    def __repr__(self):
        return f"<MockField {self.name}>"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, _MockField) and self.name == other.name


class TestProtection(unittest.TestCase):
    """Protection subtraction: protected IDs are excluded from results."""

    def test_all_protected(self):
        engine = ComputeEngine()
        engine.push_protection()
        field = _MockField("total", stored_computed=True)
        engine.protect(field, frozenset({1, 2, 3}))

        scheduler = RecomputeScheduler(engine)
        result = scheduler.process_entry(field, {1, 2, 3})

        self.assertEqual(result, frozenset())
        self.assertEqual(dict(scheduler.to_recompute), {})

    def test_partial_protection(self):
        engine = ComputeEngine()
        engine.push_protection()
        field = _MockField("total", stored_computed=True)
        engine.protect(field, frozenset({2}))

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field, {1, 2, 3})

        self.assertEqual(scheduler.to_recompute[field], {1, 3})

    def test_no_protection(self):
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field, {1, 2, 3})

        self.assertEqual(scheduler.to_recompute[field], {1, 2, 3})

    def test_protection_on_different_field(self):
        engine = ComputeEngine()
        engine.push_protection()
        field_a = _MockField("a", stored_computed=True)
        field_b = _MockField("b", stored_computed=True)
        engine.protect(field_a, frozenset({1, 2}))

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field_b, {1, 2, 3})

        self.assertEqual(scheduler.to_recompute[field_b], {1, 2, 3})


class TestRouting(unittest.TestCase):
    """Stored-computed → to_recompute, non-stored → to_invalidate."""

    def test_stored_computed_goes_to_recompute(self):
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field, {1, 2})

        self.assertIn(field, scheduler.to_recompute)
        self.assertEqual(scheduler.to_recompute[field], {1, 2})
        self.assertEqual(scheduler.to_invalidate, [])

    def test_non_stored_goes_to_invalidate(self):
        engine = ComputeEngine()
        field = _MockField("display_name", stored_computed=False)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field, {1, 2})

        self.assertEqual(dict(scheduler.to_recompute), {})
        self.assertEqual(len(scheduler.to_invalidate), 1)
        self.assertEqual(scheduler.to_invalidate[0][0], field)
        self.assertEqual(scheduler.to_invalidate[0][1], frozenset({1, 2}))

    def test_multiple_entries_accumulate(self):
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field, {1, 2})
        scheduler.process_entry(field, {3, 4})

        self.assertEqual(scheduler.to_recompute[field], {1, 2, 3, 4})

    def test_multiple_fields(self):
        engine = ComputeEngine()
        field_a = _MockField("a", stored_computed=True)
        field_b = _MockField("b", stored_computed=False)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field_a, {1})
        scheduler.process_entry(field_b, {2})

        self.assertEqual(scheduler.to_recompute[field_a], {1})
        self.assertEqual(scheduler.to_invalidate[0], (field_b, frozenset({2})))


class TestRecursiveStoredComputed(unittest.TestCase):
    """Recursive stored-computed fields: cycle detection via marked + to_recompute."""

    def test_recursive_returns_ids_for_traversal(self):
        engine = ComputeEngine()
        field = _MockField("parent_total", stored_computed=True, recursive=True)

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(field, {1, 2, 3})

        self.assertEqual(recursive_ids, frozenset({1, 2, 3}))
        self.assertEqual(scheduler.to_recompute[field], {1, 2, 3})

    def test_non_recursive_returns_empty(self):
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True, recursive=False)

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(field, {1, 2, 3})

        self.assertEqual(recursive_ids, frozenset())

    def test_cycle_detection_via_marked(self):
        """IDs already in `marked` (engine.pending) are skipped."""
        engine = ComputeEngine()
        field = _MockField("parent_total", stored_computed=True, recursive=True)
        # Simulate IDs already pending from a previous call
        marked = {field: {1, 2}}

        scheduler = RecomputeScheduler(engine, marked=marked)
        recursive_ids = scheduler.process_entry(field, {1, 2, 3})

        # Only ID 3 is new
        self.assertEqual(recursive_ids, frozenset({3}))
        self.assertEqual(scheduler.to_recompute[field], {3})

    def test_cycle_detection_via_accumulation(self):
        """IDs accumulated in to_recompute from earlier entries are skipped."""
        engine = ComputeEngine()
        field = _MockField("parent_total", stored_computed=True, recursive=True)

        scheduler = RecomputeScheduler(engine)
        # First entry marks {1, 2}
        scheduler.process_entry(field, {1, 2})
        # Second entry tries {2, 3} — ID 2 should be skipped
        recursive_ids = scheduler.process_entry(field, {2, 3})

        self.assertEqual(recursive_ids, frozenset({3}))
        self.assertEqual(scheduler.to_recompute[field], {1, 2, 3})

    def test_cycle_detection_marked_plus_accumulated(self):
        """Both marked (external) and accumulated (internal) IDs are excluded."""
        engine = ComputeEngine()
        field = _MockField("parent_total", stored_computed=True, recursive=True)
        marked = {field: {1}}

        scheduler = RecomputeScheduler(engine, marked=marked)
        scheduler.process_entry(field, {2})  # marks {2}
        recursive_ids = scheduler.process_entry(field, {1, 2, 3})

        # 1 is in marked, 2 is in to_recompute → only 3
        self.assertEqual(recursive_ids, frozenset({3}))

    def test_all_known_returns_empty(self):
        engine = ComputeEngine()
        field = _MockField("parent_total", stored_computed=True, recursive=True)
        marked = {field: {1, 2, 3}}

        scheduler = RecomputeScheduler(engine, marked=marked)
        recursive_ids = scheduler.process_entry(field, {1, 2, 3})

        self.assertEqual(recursive_ids, frozenset())
        # Nothing added to to_recompute
        self.assertNotIn(field, scheduler.to_recompute)


class TestRecursiveNonStored(unittest.TestCase):
    """Recursive non-stored fields: filter to cached IDs only."""

    def test_filter_to_cached_ids(self):
        engine = ComputeEngine()
        field = _MockField("display", stored_computed=False, recursive=True)

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(
            field,
            {1, 2, 3, 4, 5},
            cached_ids={2, 4},
        )

        # Only IDs 2 and 4 are in cache
        self.assertEqual(recursive_ids, frozenset({2, 4}))
        self.assertEqual(len(scheduler.to_invalidate), 1)
        self.assertEqual(scheduler.to_invalidate[0][1], frozenset({2, 4}))

    def test_no_cached_ids_skips(self):
        engine = ComputeEngine()
        field = _MockField("display", stored_computed=False, recursive=True)

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(
            field,
            {1, 2, 3},
            cached_ids=set(),
        )

        self.assertEqual(recursive_ids, frozenset())
        self.assertEqual(scheduler.to_invalidate, [])

    def test_cached_ids_none_means_no_filter(self):
        """When cached_ids is None, all IDs are processed (no filter)."""
        engine = ComputeEngine()
        field = _MockField("display", stored_computed=False, recursive=True)

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(
            field,
            {1, 2, 3},
            cached_ids=None,
        )

        self.assertEqual(recursive_ids, frozenset({1, 2, 3}))

    def test_cycle_detection_non_stored(self):
        """Non-stored recursive: IDs processed in earlier entries are skipped.

        This prevents infinite loops in cyclic hierarchies (e.g. A parent of B,
        B parent of A) where deferred invalidation can't break the cycle.
        """
        engine = ComputeEngine()
        field = _MockField("display", stored_computed=False, recursive=True)

        scheduler = RecomputeScheduler(engine)
        # First round: process {1, 2}
        r1 = scheduler.process_entry(field, {1, 2}, cached_ids={1, 2, 3})
        self.assertEqual(r1, frozenset({1, 2}))

        # Second round (simulating recursive traversal returning same IDs):
        # {1, 2} already seen → only {3} is new
        r2 = scheduler.process_entry(field, {1, 2, 3}, cached_ids={1, 2, 3})
        self.assertEqual(r2, frozenset({3}))

        # Third round: all IDs already seen → empty
        r3 = scheduler.process_entry(field, {1, 2, 3}, cached_ids={1, 2, 3})
        self.assertEqual(r3, frozenset())

    def test_cycle_detection_non_stored_interacts_with_cached(self):
        """Cycle detection is applied BEFORE cached_ids filter."""
        engine = ComputeEngine()
        field = _MockField("display", stored_computed=False, recursive=True)

        scheduler = RecomputeScheduler(engine)
        # First: process {1, 2} (both cached)
        scheduler.process_entry(field, {1, 2}, cached_ids={1, 2})

        # Second: {1, 3, 4}, cached={1, 3}
        # 1 already seen → removed. {3, 4} remain. cached={1,3} → {3}
        r2 = scheduler.process_entry(field, {1, 3, 4}, cached_ids={1, 3})
        self.assertEqual(r2, frozenset({3}))


class TestProtectionWithRecursive(unittest.TestCase):
    """Protection subtraction applies BEFORE cycle detection."""

    def test_protected_subtracted_before_cycle_check(self):
        engine = ComputeEngine()
        engine.push_protection()
        field = _MockField("parent_total", stored_computed=True, recursive=True)
        engine.protect(field, frozenset({2}))

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(field, {1, 2, 3})

        # ID 2 is protected → removed before cycle detection
        self.assertEqual(recursive_ids, frozenset({1, 3}))
        self.assertEqual(scheduler.to_recompute[field], {1, 3})

    def test_protection_plus_cached_filter(self):
        engine = ComputeEngine()
        engine.push_protection()
        field = _MockField("display", stored_computed=False, recursive=True)
        engine.protect(field, frozenset({1}))

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(
            field,
            {1, 2, 3, 4},
            cached_ids={2, 3},
        )

        # 1 is protected, then filter to cached {2, 3}
        self.assertEqual(recursive_ids, frozenset({2, 3}))


class TestClear(unittest.TestCase):
    """Clear resets all accumulated state."""

    def test_clear(self):
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field, {1, 2})
        self.assertEqual(scheduler.to_recompute[field], {1, 2})

        scheduler.clear()
        self.assertEqual(dict(scheduler.to_recompute), {})
        self.assertEqual(scheduler.to_invalidate, [])


class TestRepr(unittest.TestCase):
    """Repr includes summary counts."""

    def test_repr_empty(self):
        engine = ComputeEngine()
        scheduler = RecomputeScheduler(engine)
        self.assertIn("recompute=0f/0e", repr(scheduler))
        self.assertIn("invalidate=0f/0e", repr(scheduler))

    def test_repr_with_data(self):
        engine = ComputeEngine()
        field_a = _MockField("a", stored_computed=True)
        field_b = _MockField("b", stored_computed=False)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field_a, {1, 2, 3})
        scheduler.process_entry(field_b, {4, 5})

        r = repr(scheduler)
        self.assertIn("recompute=1f/3e", r)
        self.assertIn("invalidate=1f/2e", r)


class TestEdgeCases(unittest.TestCase):
    """Edge cases and boundary conditions."""

    def test_empty_ids(self):
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True)

        scheduler = RecomputeScheduler(engine)
        recursive_ids = scheduler.process_entry(field, set())

        self.assertEqual(recursive_ids, frozenset())
        self.assertNotIn(field, scheduler.to_recompute)

    def test_frozenset_input(self):
        """Input IDs can be frozenset (immutable)."""
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(field, frozenset({1, 2}))

        self.assertEqual(scheduler.to_recompute[field], {1, 2})

    def test_marked_is_live_reference(self):
        """Marked dict is a live reference — mutations are visible."""
        engine = ComputeEngine()
        field = _MockField("parent_total", stored_computed=True, recursive=True)
        marked = {field: set()}

        scheduler = RecomputeScheduler(engine, marked=marked)
        scheduler.process_entry(field, {1, 2})

        # Now mutate the live marked dict (simulating engine.pending changes)
        marked[field].add(3)
        recursive_ids = scheduler.process_entry(field, {1, 2, 3, 4})

        # 1, 2 in to_recompute, 3 in marked → only 4 is new
        self.assertEqual(recursive_ids, frozenset({4}))

    def test_create_flag_does_not_affect_scheduling(self):
        """The create flag is for the caller's traversal, not scheduling."""
        engine = ComputeEngine()
        field = _MockField("total", stored_computed=True)

        s1 = RecomputeScheduler(engine)
        s1.process_entry(field, {1}, create=True)
        s2 = RecomputeScheduler(engine)
        s2.process_entry(field, {1}, create=False)

        self.assertEqual(s1.to_recompute[field], s2.to_recompute[field])

    def test_interleaved_stored_and_non_stored(self):
        """Multiple entries with different field types accumulate correctly."""
        engine = ComputeEngine()
        stored = _MockField("total", stored_computed=True)
        non_stored = _MockField("display", stored_computed=False)

        scheduler = RecomputeScheduler(engine)
        scheduler.process_entry(stored, {1})
        scheduler.process_entry(non_stored, {2})
        scheduler.process_entry(stored, {3})
        scheduler.process_entry(non_stored, {4})

        self.assertEqual(scheduler.to_recompute[stored], {1, 3})
        self.assertEqual(len(scheduler.to_invalidate), 2)
        all_invalidated = {id_ for _, ids in scheduler.to_invalidate for id_ in ids}
        self.assertEqual(all_invalidated, {2, 4})


if __name__ == "__main__":
    unittest.main()
