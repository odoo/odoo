import unittest
from typing import NamedTuple

from odoo.orm.components._protocols import SchedulableField
from odoo.orm.components.cache import FieldCache
from odoo.orm.components.compute import ComputeEngine
from odoo.orm.components.recompute import RecomputeScheduler
from odoo.orm.components.storage import DictBackend
from odoo.orm.components.unit_of_work import UnitOfWork


def _present[T](value: T | None) -> T:
    assert value is not None, "the component under test returned None"
    return value


class TestCacheComputeLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.name_field = "name"
        self.total_field = "total"

    def test_create_triggers_compute(self) -> None:
        self.cache.set_value(self.name_field, 1, "Alice")
        self.cache.set_value(self.total_field, 1, None)

        self.engine.schedule(self.total_field, [1])

        self.assertTrue(self.engine.has_pending_field(self.total_field))
        self.assertEqual(self.cache.get_value(self.name_field, 1), "Alice")

    def test_recompute_clears_pending(self) -> None:
        self.cache.set_value(self.total_field, 1, None)
        self.engine.schedule(self.total_field, [1])

        self.cache.set_value(self.total_field, 1, 42.0)
        self.engine.mark_done(self.total_field, [1])

        self.assertFalse(self.engine.has_pending_field(self.total_field))
        self.assertEqual(self.cache.get_value(self.total_field, 1), 42.0)

    def test_dirty_tracking_through_flush(self) -> None:
        self.cache.set_value(self.name_field, 1, "Alice")
        self.cache.mark_dirty(self.name_field, [1])

        dirty_ids = _present(self.cache.pop_dirty(self.name_field))
        self.assertIn(1, dirty_ids)

        self.assertFalse(self.cache.has_dirty_field(self.name_field))

    def test_protection_prevents_recompute(self) -> None:
        self.engine.schedule(self.total_field, [1, 2, 3])

        self.engine.push_protection()
        self.engine.protect(self.total_field, frozenset([2]))

        pending = self.engine.get_pending_ids(self.total_field)
        to_recompute = [
            id_
            for id_ in pending
            if not self.engine.is_protected(self.total_field, id_)
        ]
        self.assertEqual(sorted(to_recompute), [1, 3])

        self.engine.pop_protection()
        self.assertFalse(self.engine.is_protected(self.total_field, 2))

    def test_invalidation_preserves_dirty(self) -> None:
        self.cache.set_value(self.name_field, 1, "Alice")
        self.cache.set_value(self.total_field, 1, 42.0)
        self.cache.mark_dirty(self.name_field, [1])

        self.cache.invalidate_all()

        self.assertTrue(self.cache.has_value(self.name_field, 1))
        self.assertEqual(self.cache.get_value(self.name_field, 1), "Alice")
        self.assertTrue(self.cache.has_dirty_field(self.name_field))
        self.assertFalse(self.cache.has_value(self.total_field, 1))


class TestCacheStorageRoundTrip(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.storage = DictBackend()

    def test_create_flush_read(self) -> None:
        self.cache.set_value("name", 1, "Alice")
        self.cache.set_value("email", 1, "alice@example.com")
        self.cache.mark_dirty("name", [1])
        self.cache.mark_dirty("email", [1])

        name_dirty = self.cache.pop_dirty("name")
        email_dirty = self.cache.pop_dirty("email")
        self.assertEqual(name_dirty, {1})
        self.assertEqual(email_dirty, {1})

        self.storage.insert_rows(
            "partner",
            ["name", "email"],
            [("Alice", "alice@example.com")],
        )

        rows = self.storage.get_row_tuples("partner", [1], ["name", "email"])
        self.assertEqual(rows, [("Alice", "alice@example.com")])

    def test_update_flush(self) -> None:
        self.storage.insert_rows("partner", ["name"], [("Alice",)])

        self.cache.set_value("name", 1, "Alicia")
        self.cache.mark_dirty("name", [1])

        dirty = _present(self.cache.pop_dirty("name"))
        for id_ in dirty:
            value = self.cache.get_value("name", id_)
            self.storage.update_rows("partner", [(id_, {"name": value})])

        rows = self.storage.get_row_tuples("partner", [1], ["name"])
        self.assertEqual(rows, [("Alicia",)])
        self.assertFalse(self.cache.has_dirty_field("name"))

    def test_x2many_patches(self) -> None:
        self.cache.set_value("line_ids", 1, (10, 11))

        self.cache.add_patch("line_ids", 1, 12)

        patches = _present(self.cache.get_patches("line_ids"))
        self.assertEqual(patches[1], [12])


class TestMultiRecordCompute(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()

    def test_batch_schedule_and_compute(self) -> None:
        for i in range(1, 6):
            self.cache.set_value("amount", i, i * 10.0)
            self.cache.set_value("total", i, None)
        self.engine.schedule("total", range(1, 6))

        self.assertEqual(len(self.engine.get_pending_ids("total")), 5)

        for id_ in list(self.engine.get_pending_ids("total")):
            amount = self.cache.get_value("amount", id_)
            self.cache.set_value("total", id_, amount * 1.16)
        self.engine.mark_done("total", range(1, 6))

        self.assertFalse(self.engine.has_pending())
        self.assertAlmostEqual(self.cache.get_value("total", 3), 34.8)

    def test_nested_protection_scopes(self) -> None:
        self.engine.push_protection()
        self.engine.protect("total", frozenset([1, 2]))

        self.engine.push_protection()
        self.engine.protect("total", frozenset([3, 4]))

        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertTrue(self.engine.is_protected("total", 3))

        self.engine.pop_protection()
        self.assertTrue(self.engine.is_protected("total", 1))
        self.assertFalse(self.engine.is_protected("total", 3))

        self.engine.pop_protection()
        self.assertFalse(self.engine.is_protected("total", 1))


class TestUnitOfWorkIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.uow = UnitOfWork(self.cache, self.engine)
        self.MockField = _MockField
        self.storage = DictBackend()

    def _field(self, model: str, name: str) -> _MockField:
        return self.MockField(model, name)

    def test_recompute_then_flush_lifecycle(self) -> None:
        f_val = self._field("m", "val")
        f_double = self._field("m", "double")

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
                for field in (f_val, f_double):
                    if field.model_name == model_name:
                        dirty_ids = self.cache.pop_dirty(field)
                        if dirty_ids:
                            self.storage.upsert_rows(
                                model_name,
                                [
                                    (
                                        id_,
                                        {field.name: self.cache.get_value(field, id_)},
                                    )
                                    for id_ in dirty_ids
                                ],
                            )

        result = self.uow.flush_until_converged(recompute_fn, flush_fn)
        self.assertTrue(result.converged)
        self.assertIn("m", flushed_models)
        row = _present(self.storage.get_row("m", 1))
        self.assertEqual(row["val"], 5)
        self.assertEqual(row["double"], 10)

    def test_cascading_recompute_converges(self) -> None:
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
                self.engine.schedule(f_c, [1])
            elif field == f_c:
                val = self.cache.get_value(f_b, 1)
                self.cache.set_value(f_c, 1, val + 100)
                self.cache.mark_dirty(f_c, [1])
                self.engine.mark_done(f_c, [1])

        def flush_fn(model_names):
            for model_name in model_names:
                for field in (f_a, f_b, f_c):
                    if field.model_name == model_name:
                        self.cache.pop_dirty(field)

        result = self.uow.flush_until_converged(recompute_fn, flush_fn)
        self.assertTrue(result.converged)
        self.assertEqual(self.cache.get_value(f_c, 1), 106)


class _MockField(NamedTuple):
    model_name: str
    name: str


class _MockSchedulableField(NamedTuple):
    model_name: str
    name: str
    recursive: bool
    is_stored_computed: bool
    tree_siblings: tuple = ()


class TestRecomputeSchedulerIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ComputeEngine()
        self.RecomputeScheduler = RecomputeScheduler

    def _field(
        self,
        model: str,
        name: str,
        recursive: bool = False,
        stored_computed: bool = True,
    ) -> SchedulableField:
        return _MockSchedulableField(model, name, recursive, stored_computed)

    def test_protection_subtracted_from_schedule(self) -> None:
        f = self._field("m", "total")
        self.engine.push_protection()
        self.engine.protect(f, frozenset([2, 3]))

        scheduler = self.RecomputeScheduler(self.engine, marked={})
        scheduler.schedule_recompute(f, {1, 2, 3, 4})

        self.assertEqual(scheduler.to_recompute[f], {1, 4})
        self.engine.pop_protection()

    def test_non_stored_routed_to_invalidate(self) -> None:
        f = self._field("m", "display_name", stored_computed=False)

        scheduler = self.RecomputeScheduler(self.engine, marked={})
        scheduler.schedule_recompute(f, {1, 2, 3})

        self.assertEqual(len(scheduler.to_recompute), 0)
        self.assertEqual(len(scheduler.to_invalidate), 1)
        self.assertEqual(scheduler.to_invalidate[0], (f, frozenset({1, 2, 3})))

    def test_recursive_cycle_detection(self) -> None:
        f = self._field("m", "parent_path", recursive=True, stored_computed=True)

        self.engine.schedule(f, [1])
        scheduler = self.RecomputeScheduler(self.engine, marked=self.engine.pending)

        recursive_ids = scheduler.schedule_recompute(f, {1, 2, 3})

        self.assertEqual(scheduler.to_recompute[f], {2, 3})
        self.assertEqual(recursive_ids, frozenset({2, 3}))


if __name__ == "__main__":
    unittest.main()
