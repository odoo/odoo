import unittest
from typing import NamedTuple

from odoo.orm.components.cache import FieldCache
from odoo.orm.components.compute import ComputeEngine
from odoo.orm.components.unit_of_work import (
    SNAPSHOT_AFTER,
    STALL_REPEATS,
    ConvergenceResult,
    UnitOfWork,
)


class _MockField(NamedTuple):
    model_name: str
    name: str


def _field(model_name: str, name: str) -> _MockField:
    return _MockField(model_name, name)


class TestDirtyModels(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.uow = UnitOfWork(self.cache, self.engine)

    def test_no_dirty(self) -> None:
        self.assertEqual(self.uow.get_dirty_model_names(), [])

    def test_single_dirty_field(self) -> None:
        f = _field("sale.order", "amount_total")
        self.cache.set_value(f, 1, 100)
        self.cache.mark_dirty(f, [1])
        self.assertEqual(self.uow.get_dirty_model_names(), ["sale.order"])

    def test_multiple_dirty_models(self) -> None:
        f1 = _field("sale.order", "amount")
        f2 = _field("account.move", "total")
        self.cache.set_value(f1, 1, 100)
        self.cache.mark_dirty(f1, [1])
        self.cache.set_value(f2, 2, 200)
        self.cache.mark_dirty(f2, [2])
        models = self.uow.get_dirty_model_names()
        self.assertEqual(len(models), 2)
        self.assertIn("sale.order", models)
        self.assertIn("account.move", models)

    def test_unique_models(self) -> None:
        f1 = _field("sale.order", "amount")
        f2 = _field("sale.order", "state")
        self.cache.set_value(f1, 1, 100)
        self.cache.mark_dirty(f1, [1])
        self.cache.set_value(f2, 1, "draft")
        self.cache.mark_dirty(f2, [1])
        self.assertEqual(self.uow.get_dirty_model_names(), ["sale.order"])


class TestRunRecomputeLoop(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.uow = UnitOfWork(self.cache, self.engine, max_iterations=10)

    def test_no_pending(self) -> None:
        result = self.uow.recompute_until_converged(lambda f: None)
        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 0)

    def test_single_field_converges(self) -> None:
        f = _field("m", "total")
        self.engine.schedule(f, [1, 2])

        def recompute(field):
            self.cache.set_value(field, 1, 10)
            self.cache.set_value(field, 2, 20)
            self.engine.mark_done(field, [1, 2])

        result = self.uow.recompute_until_converged(recompute)
        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 1)

    def test_cascading_compute(self) -> None:
        f_a = _field("m", "subtotal")
        f_b = _field("m", "total")
        self.engine.schedule(f_a, [1])

        def recompute(field):
            if field is f_a:
                self.cache.set_value(f_a, 1, 100)
                self.engine.mark_done(f_a, [1])
                self.engine.schedule(f_b, [1])
            elif field is f_b:
                self.cache.set_value(f_b, 1, 110)
                self.engine.mark_done(f_b, [1])

        result = self.uow.recompute_until_converged(recompute)
        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 2)

    def test_max_iterations_non_convergent(self) -> None:
        f = _field("m", "cycle")
        self.engine.schedule(f, [1])
        uow = UnitOfWork(self.cache, self.engine, max_iterations=3)

        def recompute(field):
            self.engine.mark_done(field, [1])
            self.engine.schedule(field, [1])

        result = uow.recompute_until_converged(recompute)
        self.assertFalse(result.converged)
        self.assertEqual(result.iterations, 3)

    def test_only_real_ids_count(self) -> None:
        f = _field("m", "total")
        self.engine.schedule(f, [0])
        result = self.uow.recompute_until_converged(lambda field: None)
        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 0)


class TestRunFlushLoop(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.uow = UnitOfWork(self.cache, self.engine, max_iterations=10)

    def test_no_dirty(self) -> None:
        result = self.uow.flush_until_converged(
            recompute_fn=lambda f: None,
            flush_fn=lambda models: None,
        )
        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 0)

    def test_single_flush(self) -> None:
        f = _field("sale.order", "amount")
        self.cache.set_value(f, 1, 100)
        self.cache.mark_dirty(f, [1])
        flushed_models = []

        def flush(models):
            flushed_models.extend(models)
            self.cache.pop_dirty(f)

        result = self.uow.flush_until_converged(
            recompute_fn=lambda field: None,
            flush_fn=flush,
        )
        self.assertTrue(result.converged)
        self.assertEqual(flushed_models, ["sale.order"])

    def test_flush_triggers_recompute(self) -> None:
        f_amount = _field("sale.order", "amount")
        f_tax = _field("sale.order", "tax")
        self.cache.set_value(f_amount, 1, 100)
        self.cache.mark_dirty(f_amount, [1])
        flush_count = [0]

        def recompute(field):
            self.cache.set_value(field, 1, 10)
            self.engine.mark_done(field, [1])
            self.cache.mark_dirty(field, [1])

        def flush(models):
            flush_count[0] += 1
            if flush_count[0] == 1:
                self.cache.pop_dirty(f_amount)
                self.engine.schedule(f_tax, [1])
            else:
                self.cache.pop_dirty(f_tax)

        result = self.uow.flush_until_converged(
            recompute_fn=recompute,
            flush_fn=flush,
        )
        self.assertTrue(result.converged)
        self.assertEqual(flush_count[0], 2)

    def test_iterations_count_working_passes_only(self) -> None:
        f = _field("m", "total")
        self.engine.schedule(f, [1])

        def recompute(field):
            self.cache.set_value(field, 1, 10)
            self.engine.mark_done(field, [1])

        result = self.uow.flush_until_converged(
            recompute_fn=recompute,
            flush_fn=lambda models: self.fail("nothing dirty, must not flush"),
        )
        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 1)

    def test_iterations_zero_when_nothing_to_do(self) -> None:
        result = self.uow.flush_until_converged(
            recompute_fn=lambda f: None,
            flush_fn=lambda models: None,
        )
        self.assertTrue(result.converged)
        self.assertEqual(result.iterations, 0)

    def test_iterations_count_flush_passes(self) -> None:
        f1 = _field("m", "a")
        f2 = _field("m", "b")
        self.cache.mark_dirty(f1, [1])
        calls = [0]

        def flush(models):
            calls[0] += 1
            if calls[0] == 1:
                self.cache.pop_dirty(f1)
                self.cache.mark_dirty(f2, [1])
            else:
                self.cache.pop_dirty(f2)

        result = self.uow.flush_until_converged(
            recompute_fn=lambda field: None,
            flush_fn=flush,
        )
        self.assertTrue(result.converged)
        self.assertEqual(calls[0], 2)
        self.assertEqual(result.iterations, 2)

    def test_converged_result_has_no_stalled_fields(self) -> None:
        f = _field("m", "a")
        self.cache.mark_dirty(f, [1, 2])
        calls = [0]

        def flush(models):
            if calls[0] == 1:
                self.cache.pop_dirty(f)
            calls[0] += 1

        result = self.uow.flush_until_converged(
            recompute_fn=lambda field: None,
            flush_fn=flush,
        )
        self.assertTrue(result.converged)
        self.assertEqual(result.stalled_fields, [])

    def test_recompute_non_convergence_propagates(self) -> None:
        f = _field("m", "cycle")
        self.engine.schedule(f, [1])
        uow = UnitOfWork(self.cache, self.engine, max_iterations=3)
        flush_called = [False]

        def recompute(field):
            self.engine.mark_done(field, [1])
            self.engine.schedule(field, [1])

        def flush(models):
            flush_called[0] = True

        result = uow.flush_until_converged(
            recompute_fn=recompute,
            flush_fn=flush,
        )
        self.assertFalse(result.converged)
        self.assertFalse(
            flush_called[0], "flush should not be called when recompute stalls"
        )
        self.assertTrue(len(result.stalled_fields) > 0)


class TestLoopExhaustionConsistency(unittest.TestCase):
    def test_flush_exhaustion_with_pending_recompute_is_not_converged(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=3)
        f_dirty = _field("m", "a")
        f_computed = _field("m", "b")
        cache.set_value(f_dirty, 1, 10)
        cache.mark_dirty(f_dirty, [1])
        state = {"flush": 0}

        def recompute_fn(field):
            engine.mark_done(field, list(engine.get_pending_ids(field)))

        def flush_fn(_models):
            state["flush"] += 1
            cache.pop_dirty(f_dirty)
            if state["flush"] < uow.max_iterations:
                cache.set_value(f_dirty, state["flush"] + 1, 10)
                cache.mark_dirty(f_dirty, [state["flush"] + 1])
            else:
                engine.schedule(f_computed, [1, 2, 3])

        result = uow.flush_until_converged(recompute_fn, flush_fn)
        self.assertFalse(result.converged)
        self.assertIn("m.b", result.stalled_fields)

    def test_recompute_convergence_on_last_iteration_clears_stalled(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=3)
        f = _field("m", "total")
        engine.schedule(f, [1])
        state = {"n": 0}

        def recompute_fn(_field):
            state["n"] += 1
            if state["n"] >= 3:
                engine.mark_done(f, [1])

        result = uow.recompute_until_converged(recompute_fn)
        self.assertFalse(engine.get_pending_fields_with_real_ids())
        self.assertTrue(result.converged)
        self.assertEqual(result.stalled_fields, [])


class TestStallDetection(unittest.TestCase):
    def test_recompute_cycle_stops_long_before_the_cap(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=1000)
        f = _field("m", "cycle")
        engine.schedule(f, [1, 2])
        passes = [0]

        def recompute_fn(field):
            passes[0] += 1
            engine.mark_done(field, [1, 2])
            engine.schedule(field, [1, 2])

        result = uow.recompute_until_converged(recompute_fn)
        self.assertFalse(result.converged)
        self.assertEqual(result.stalled_fields, ["m.cycle"])
        self.assertEqual(passes[0], SNAPSHOT_AFTER + STALL_REPEATS)
        self.assertEqual(result.iterations, SNAPSHOT_AFTER + STALL_REPEATS)

    def test_changing_pending_set_is_not_a_stall(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(
            cache, engine, max_iterations=SNAPSHOT_AFTER + STALL_REPEATS + 4
        )
        f = _field("m", "walk")
        engine.schedule(f, [1])
        state = {"n": 1}

        def recompute_fn(field):
            engine.mark_done(field, list(engine.get_pending_ids(field)))
            state["n"] += 1
            engine.schedule(field, [state["n"]])

        result = uow.recompute_until_converged(recompute_fn)
        self.assertFalse(result.converged)
        self.assertEqual(result.iterations, uow.max_iterations)

    def test_flush_cycle_stops_long_before_the_cap(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=1000)
        f = _field("m", "a")
        cache.set_value(f, 1, 10)
        cache.mark_dirty(f, [1])
        flushes = [0]

        def flush_fn(_models):
            flushes[0] += 1
            cache.pop_dirty(f)
            cache.mark_dirty(f, [1])

        result = uow.flush_until_converged(lambda field: None, flush_fn)
        self.assertFalse(result.converged)
        self.assertEqual(result.stalled_fields, ["m.a"])
        self.assertEqual(flushes[0], SNAPSHOT_AFTER + STALL_REPEATS)

    def test_converging_flush_is_unaffected(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=1000)
        f = _field("m", "a")
        cache.set_value(f, 1, 10)
        cache.mark_dirty(f, [1])

        def _flush(_m: list[str]) -> None:
            cache.pop_dirty(f)

        result = uow.flush_until_converged(lambda field: None, _flush)
        self.assertTrue(result.converged)
        self.assertEqual(result.stalled_fields, [])


class TestConvergenceResult(unittest.TestCase):
    def test_defaults(self) -> None:
        r = ConvergenceResult()
        self.assertEqual(r.iterations, 0)
        self.assertTrue(r.converged)
        self.assertEqual(r.stalled_fields, [])


if __name__ == "__main__":
    unittest.main()


class TestStallDetectorPeriod(unittest.TestCase):
    """A compute cycle of period two never shows the same snapshot twice in a
    row; the detector must still stop it long before the iteration cap."""

    def test_recompute_ping_pong_stops_long_before_the_cap(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=1000)
        a = _field("m", "a")
        b = _field("m", "b")
        engine.schedule(a, [1])
        passes = [0]

        def recompute_fn(field):
            passes[0] += 1
            engine.mark_done(field, [1])
            engine.schedule(b if field is a else a, [1])

        result = uow.recompute_until_converged(recompute_fn)
        self.assertFalse(result.converged)
        self.assertIn(result.stalled_fields, (["m.a"], ["m.b"]))
        self.assertLess(passes[0], 2 * (SNAPSHOT_AFTER + STALL_REPEATS) + 2)
        self.assertLess(result.iterations, uow.max_iterations)

    def test_flush_ping_pong_stops_long_before_the_cap(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=1000)
        a = _field("model.a", "x")
        b = _field("model.b", "y")
        cache.mark_dirty(a, [1])
        flushes = [0]

        def flush_fn(model_names):
            flushes[0] += 1
            for name in model_names:
                cache.pop_dirty_for_model(name)
            cache.mark_dirty(b if "model.a" in model_names else a, [1])

        result = uow.flush_until_converged(lambda field: None, flush_fn)
        self.assertFalse(result.converged)
        self.assertLess(flushes[0], 2 * (SNAPSHOT_AFTER + STALL_REPEATS) + 2)
        self.assertLess(result.iterations, uow.max_iterations)

    def test_a_walk_through_distinct_snapshots_is_still_not_a_stall(self) -> None:
        cache = FieldCache()
        engine = ComputeEngine()
        uow = UnitOfWork(cache, engine, max_iterations=SNAPSHOT_AFTER + 40)
        f = _field("m", "walk")
        engine.schedule(f, [1])
        state = {"n": 1}

        def recompute_fn(field):
            engine.mark_done(field, list(engine.get_pending_ids(field)))
            state["n"] += 1
            engine.schedule(field, [state["n"]])

        result = uow.recompute_until_converged(recompute_fn)
        self.assertFalse(result.converged)
        self.assertEqual(result.iterations, uow.max_iterations)
