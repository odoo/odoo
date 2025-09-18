"""Integration tests for ORM components working together.

These tests exercise FieldCache + ComputeEngine + DictBackend in concert,
simulating a simplified ORM lifecycle (create → cache → recompute → flush)
without any Odoo imports.
"""

import unittest

from odoo.orm.components.cache import FieldCache
from odoo.orm.components.compute import ComputeEngine
from odoo.orm.components.storage import DictBackend


class TestCacheComputeLifecycle(unittest.TestCase):
    """Simulate a create → compute → flush lifecycle."""

    def setUp(self):
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        # Use strings as mock field keys
        self.name_field = "name"
        self.total_field = "total"  # stored computed

    def test_create_triggers_compute(self):
        """After creating a record, mark stored-computed fields for recomputation."""
        # Simulate _create: insert cache values
        self.cache.set_value(self.name_field, 1, "Alice")
        self.cache.set_value(self.total_field, 1, None)  # placeholder

        # Mark computed field for recomputation
        self.engine.schedule(self.total_field, [1])

        # Verify state
        self.assertTrue(self.engine.has_pending_field(self.total_field))
        self.assertEqual(self.cache.get_value(self.name_field, 1), "Alice")

    def test_recompute_clears_pending(self):
        """After computing a field, mark it as done."""
        self.cache.set_value(self.total_field, 1, None)
        self.engine.schedule(self.total_field, [1])

        # Simulate recomputation
        self.cache.set_value(self.total_field, 1, 42.0)
        self.engine.mark_done(self.total_field, [1])

        # Verify
        self.assertFalse(self.engine.has_pending_field(self.total_field))
        self.assertEqual(self.cache.get_value(self.total_field, 1), 42.0)

    def test_dirty_tracking_through_flush(self):
        """Dirty fields are collected during flush and cleared after."""
        self.cache.set_value(self.name_field, 1, "Alice")
        self.cache.mark_dirty(self.name_field, [1])

        # Simulate flush: pop dirty, write to storage
        dirty_ids = self.cache.pop_dirty(self.name_field)
        self.assertIn(1, dirty_ids)

        # After pop, field is no longer dirty
        self.assertFalse(self.cache.has_dirty_field(self.name_field))

    def test_protection_prevents_recompute(self):
        """Protected fields are skipped during recomputation."""
        self.engine.schedule(self.total_field, [1, 2, 3])

        # Protect record 2
        self.engine.push_protection()
        self.engine.protect(self.total_field, frozenset([2]))

        # Simulate recompute loop: skip protected records
        pending = self.engine.pending_ids(self.total_field)
        to_recompute = [
            id_
            for id_ in pending
            if not self.engine.is_protected(self.total_field, id_)
        ]
        self.assertEqual(sorted(to_recompute), [1, 3])

        self.engine.pop_protection()
        # After popping, record 2 is no longer protected
        self.assertFalse(self.engine.is_protected(self.total_field, 2))

    def test_invalidation_preserves_dirty(self):
        """invalidate_all() clears non-dirty data but keeps dirty entries intact."""
        self.cache.set_value(self.name_field, 1, "Alice")
        self.cache.set_value(self.total_field, 1, 42.0)  # non-dirty
        self.cache.mark_dirty(self.name_field, [1])

        self.cache.invalidate_all()

        # Dirty data is preserved (flush still needs to read values)
        self.assertTrue(self.cache.has_value(self.name_field, 1))
        self.assertEqual(self.cache.get_value(self.name_field, 1), "Alice")
        self.assertTrue(self.cache.has_dirty_field(self.name_field))
        # Non-dirty data is cleared
        self.assertFalse(self.cache.has_value(self.total_field, 1))


class TestCacheStorageRoundTrip(unittest.TestCase):
    """Test FieldCache + DictBackend for a full create-read-update-delete cycle."""

    def setUp(self):
        self.cache = FieldCache()
        self.storage = DictBackend()

    def test_create_flush_read(self):
        """Simulate: create in cache → flush to storage → read back."""
        # Create in cache
        self.cache.set_value("name", 1, "Alice")
        self.cache.set_value("email", 1, "alice@example.com")
        self.cache.mark_dirty("name", [1])
        self.cache.mark_dirty("email", [1])

        # Flush to storage
        name_dirty = self.cache.pop_dirty("name")
        email_dirty = self.cache.pop_dirty("email")
        self.assertEqual(name_dirty, {1})
        self.assertEqual(email_dirty, {1})

        # Write to backend
        self.storage.insert_rows(
            "partner",
            ["name", "email"],
            [("Alice", "alice@example.com")],
        )

        # Read back from storage
        rows = self.storage.fetch_rows("partner", [1], ["name", "email"])
        self.assertEqual(rows, [("Alice", "alice@example.com")])

    def test_update_flush(self):
        """Simulate: update in cache → flush dirty to storage."""
        # Initial state in storage
        self.storage.insert_rows("partner", ["name"], [("Alice",)])

        # Update in cache
        self.cache.set_value("name", 1, "Alicia")
        self.cache.mark_dirty("name", [1])

        # Flush
        dirty = self.cache.pop_dirty("name")
        for id_ in dirty:
            value = self.cache.get_value("name", id_)
            self.storage.update_rows("partner", [(id_, {"name": value})])

        # Verify
        rows = self.storage.fetch_rows("partner", [1], ["name"])
        self.assertEqual(rows, [("Alicia",)])
        self.assertFalse(self.cache.has_dirty_field("name"))

    def test_x2many_patches(self):
        """Test deferred x2many additions via cache patches."""
        # Parent record has cached child IDs
        self.cache.set_value("line_ids", 1, (10, 11))

        # New child is created, deferred patch added
        self.cache.add_patch("line_ids", 1, 12)

        # When _update_cache runs, it merges patches
        patches = self.cache.get_patches("line_ids")
        self.assertIsNotNone(patches)
        self.assertEqual(patches[1], [12])


class TestMultiRecordCompute(unittest.TestCase):
    """Test multi-record scheduling and batch operations."""

    def setUp(self):
        self.cache = FieldCache()
        self.engine = ComputeEngine()

    def test_batch_schedule_and_compute(self):
        """Schedule multiple records, compute them in batch."""
        # Create 5 records with pending total computation
        for i in range(1, 6):
            self.cache.set_value("amount", i, i * 10.0)
            self.cache.set_value("total", i, None)
        self.engine.schedule("total", range(1, 6))

        # Verify all pending
        self.assertEqual(len(self.engine.pending_ids("total")), 5)

        # Compute in batch
        for id_ in list(self.engine.pending_ids("total")):
            amount = self.cache.get_value("amount", id_)
            self.cache.set_value("total", id_, amount * 1.16)  # add tax
        self.engine.mark_done("total", range(1, 6))

        # Verify
        self.assertFalse(self.engine.has_pending())
        self.assertAlmostEqual(self.cache.get_value("total", 3), 34.8)

    def test_nested_protection_scopes(self):
        """Nested protection scopes merge correctly and pop cleanly."""
        self.engine.push_protection()
        self.engine.protect("total", frozenset([1, 2]))

        self.engine.push_protection()
        self.engine.protect("total", frozenset([3, 4]))

        # Inner scope sees merged protection
        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertTrue(self.engine.is_protected("total", 3))

        self.engine.pop_protection()
        # After popping inner, 3 and 4 are no longer protected
        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertFalse(self.engine.is_protected("total", 3))

        self.engine.pop_protection()
        self.assertFalse(self.engine.is_protected("total", 1))


class TestUnitOfWorkIntegration(unittest.TestCase):
    """Test UnitOfWork convergence loop with FieldCache + ComputeEngine.

    Exercises the full recompute→flush cycle using callbacks that
    directly manipulate the component data structures.
    """

    def setUp(self):
        from collections import namedtuple

        from odoo.orm.components.unit_of_work import UnitOfWork

        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.uow = UnitOfWork(self.cache, self.engine)
        self.MockField = namedtuple("MockField", ["model_name", "name"])
        self.storage = DictBackend()

    def _field(self, model, name):
        return self.MockField(model, name)

    def test_recompute_then_flush_lifecycle(self):
        """Full lifecycle: schedule → recompute → dirty → flush → storage."""
        f_val = self._field("m", "val")
        f_double = self._field("m", "double")

        # Create record
        self.cache.set_value(f_val, 1, 5)
        self.cache.mark_dirty(f_val, [1])
        self.engine.schedule(f_double, [1])

        def recompute_fn(field):
            if field == f_double:
                val = self.cache.get_value(f_val, 1)
                self.cache.set_value(f_double, 1, val * 2)
                self.cache.mark_dirty(f_double, [1])
                self.engine.mark_done(f_double, [1])

        flushed_models = []

        def flush_fn(model_names):
            flushed_models.extend(model_names)
            for model_name in model_names:
                # Pop dirty and write to storage
                for field in [f_val, f_double]:
                    if field.model_name == model_name:
                        dirty_ids = self.cache.pop_dirty(field)
                        if dirty_ids:
                            for id_ in dirty_ids:
                                tbl = self.storage._tables.setdefault(model_name, {})
                                tbl.setdefault(id_, {})[field.name] = (
                                    self.cache.get_value(field, id_)
                                )

        result = self.uow.run_flush_loop(recompute_fn, flush_fn)
        self.assertTrue(result.converged)
        self.assertIn("m", flushed_models)
        row = self.storage.get_row("m", 1)
        self.assertEqual(row["val"], 5)
        self.assertEqual(row["double"], 10)

    def test_cascading_recompute_converges(self):
        """A→B→C compute chain converges within the loop."""
        f_a = self._field("m", "a")
        f_b = self._field("m", "b")
        f_c = self._field("m", "c")

        self.cache.set_value(f_a, 1, 3)
        self.cache.mark_dirty(f_a, [1])
        self.engine.schedule(f_b, [1])

        def recompute_fn(field):
            if field == f_b:
                val = self.cache.get_value(f_a, 1)
                self.cache.set_value(f_b, 1, val * 2)
                self.cache.mark_dirty(f_b, [1])
                self.engine.mark_done(f_b, [1])
                # Recomputing B triggers C
                self.engine.schedule(f_c, [1])
            elif field == f_c:
                val = self.cache.get_value(f_b, 1)
                self.cache.set_value(f_c, 1, val + 100)
                self.cache.mark_dirty(f_c, [1])
                self.engine.mark_done(f_c, [1])

        def flush_fn(model_names):
            for model_name in model_names:
                for field in [f_a, f_b, f_c]:
                    if field.model_name == model_name:
                        self.cache.pop_dirty(field)

        result = self.uow.run_flush_loop(recompute_fn, flush_fn)
        self.assertTrue(result.converged)
        self.assertEqual(self.cache.get_value(f_c, 1), 106)  # (3*2) + 100


class TestRecomputeSchedulerIntegration(unittest.TestCase):
    """Test RecomputeScheduler with ComputeEngine for protection and cycle detection."""

    def setUp(self):
        from collections import namedtuple

        from odoo.orm.components.recompute import RecomputeScheduler

        self.engine = ComputeEngine()
        self.MockField = namedtuple(
            "MockField",
            ["model_name", "name", "recursive", "is_stored_computed"],
        )
        self.RecomputeScheduler = RecomputeScheduler

    def _field(self, model, name, recursive=False, stored_computed=True):
        return self.MockField(model, name, recursive, stored_computed)

    def test_protection_subtracted_from_schedule(self):
        """Protected IDs are excluded from the recompute schedule."""
        f = self._field("m", "total")
        self.engine.push_protection()
        self.engine.protect(f, frozenset([2, 3]))

        scheduler = self.RecomputeScheduler(self.engine, marked={})
        scheduler.process_entry(f, {1, 2, 3, 4}, create=False)

        # Records 2 and 3 are protected — only 1 and 4 scheduled
        self.assertEqual(scheduler.to_recompute[f], {1, 4})
        self.engine.pop_protection()

    def test_non_stored_routed_to_invalidate(self):
        """Non-stored computed fields go to to_invalidate, not to_recompute."""
        f = self._field("m", "display_name", stored_computed=False)

        scheduler = self.RecomputeScheduler(self.engine, marked={})
        scheduler.process_entry(f, {1, 2, 3}, create=False)

        self.assertEqual(len(scheduler.to_recompute), 0)
        self.assertEqual(len(scheduler.to_invalidate), 1)
        self.assertEqual(scheduler.to_invalidate[0], (f, frozenset({1, 2, 3})))

    def test_recursive_cycle_detection(self):
        """Recursive stored-computed field prevents re-scheduling already-marked IDs."""
        f = self._field("m", "parent_path", recursive=True, stored_computed=True)

        # Pre-mark ID 1 as already pending
        self.engine.schedule(f, [1])
        scheduler = self.RecomputeScheduler(self.engine, marked=self.engine.pending)

        # Process entry with IDs including already-pending ID 1
        recursive_ids = scheduler.process_entry(f, {1, 2, 3}, create=False)

        # ID 1 excluded (already marked), IDs 2 and 3 scheduled
        self.assertEqual(scheduler.to_recompute[f], {2, 3})
        # Recursive IDs returned for further traversal (also without 1)
        self.assertEqual(recursive_ids, frozenset({2, 3}))


if __name__ == "__main__":
    unittest.main()
