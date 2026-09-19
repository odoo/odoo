import annotationlib
import inspect
import unittest
from typing import NamedTuple
from unittest.mock import Mock

from odoo.orm.components.cache import FieldCache
from odoo.orm.components.compute import ComputeEngine
from odoo.orm.components.core import OrmCore


def _present[T](value: T | None) -> T:
    assert value is not None, "the component under test returned None"
    return value


_DELEGATIONS = [
    ("get_value", "cache", "get_value", 2, True),
    ("set_value", "cache", "set_value", 3, False),
    ("get_field_data", "cache", "get_field_data", 1, True),
    ("get_field_data_or_none", "cache", "get_field_data_or_none", 1, True),
    ("mark_dirty", "cache", "mark_dirty", 2, False),
    ("get_dirty", "cache", "get_dirty", 1, True),
    ("pop_dirty", "cache", "pop_dirty", 1, True),
    ("pop_dirty_for_model", "cache", "pop_dirty_for_model", 1, True),
    ("has_dirty_field", "cache", "has_dirty_field", 1, True),
    ("is_any_dirty", "cache", "is_any_dirty", 0, True),
    ("add_patch", "cache", "add_patch", 3, False),
    ("get_patches", "cache", "get_patches", 1, True),
    ("iter_field_items", "cache", "iter_field_items", 0, True),
    ("iter_context_caches", "cache", "iter_context_caches", 1, True),
    ("get_context_data", "cache", "get_context_data", 2, True),
    ("get_context_data_or_none", "cache", "get_context_data_or_none", 2, True),
    ("has_any_cached", "cache", "has_any_cached", 1, True),
    ("has_any_context_cached", "cache", "has_any_context_cached", 1, True),
    ("get_cached_ids", "cache", "get_cached_ids", 1, True),
    ("get_context_cached_ids", "cache", "get_context_cached_ids", 1, True),
    ("iter_cached_fields", "cache", "iter_cached_fields", 0, True),
    ("clear_cache", "cache", "clear", 0, False),
    ("schedule", "engine", "schedule", 2, False),
    ("mark_done", "engine", "mark_done", 2, False),
    ("is_pending", "engine", "is_pending", 2, True),
    ("is_pending_in_tree", "engine", "is_pending_in_tree", 2, True),
    ("has_pending_field", "engine", "has_pending_field", 1, True),
    ("has_pending", "engine", "has_pending", 0, True),
    ("get_pending_ids", "engine", "get_pending_ids", 1, True),
    ("get_pending_fields", "engine", "get_pending_fields", 0, True),
    ("discard_field", "engine", "discard_field", 1, False),
    ("is_protected", "engine", "is_protected", 2, True),
    ("get_protected_ids", "engine", "get_protected_ids", 1, True),
    ("has_any_protected", "engine", "has_any_protected", 0, True),
    ("push_protection", "engine", "push_protection", 0, False),
    ("pop_protection", "engine", "pop_protection", 0, True),
    ("protect", "engine", "protect", 2, False),
]
_NON_PASSTHROUGH = {
    "new_scheduler",
    "get_pending_write",
}

_KWARG_DELEGATIONS = [
    ("invalidate", "cache", "invalidate", 2, ("keep_dirty",), False),
]


class FakeField(NamedTuple):
    model_name: str
    name: str


class TestOrmCoreCache(unittest.TestCase):
    def setUp(self) -> None:
        self.core = OrmCore()
        self.f1 = FakeField("res.partner", "name")
        self.f2 = FakeField("res.partner", "email")

    def test_get_field_data_returns_live_dict(self) -> None:
        self.core._cache.set_value(self.f1, 1, "Alice")
        data = self.core.get_field_data(self.f1)
        self.assertEqual(data[1], "Alice")
        data[2] = "Bob"
        self.assertEqual(self.core._cache.get_value(self.f1, 2), "Bob")

    def test_get_field_data_or_none(self) -> None:
        self.assertIsNone(self.core.get_field_data_or_none(self.f1))
        self.core._cache.set_value(self.f1, 1, "X")
        self.assertIsNotNone(self.core.get_field_data_or_none(self.f1))

    def test_mark_dirty_and_pop(self) -> None:
        self.core.mark_dirty(self.f1, [1, 2])
        self.assertTrue(self.core.has_dirty_field(self.f1))
        self.assertTrue(self.core.is_any_dirty())
        dirty = self.core.pop_dirty(self.f1)
        self.assertEqual(dirty, {1, 2})
        self.assertFalse(self.core.has_dirty_field(self.f1))

    def test_get_dirty(self) -> None:
        self.core.mark_dirty(self.f1, [1, 2])
        dirty = self.core.get_dirty(self.f1)
        self.assertEqual(dirty, {1, 2})
        self.assertTrue(self.core.has_dirty_field(self.f1))

    def test_get_dirty_none(self) -> None:
        self.assertIsNone(self.core.get_dirty(self.f1))

    def test_pop_dirty_empty(self) -> None:
        self.assertIsNone(self.core.pop_dirty(self.f1))

    def test_add_and_get_patches(self) -> None:
        self.core.add_patch(self.f1, 1, 100)
        self.core.add_patch(self.f1, 1, 101)
        patches = _present(self.core.get_patches(self.f1))
        self.assertEqual(patches[1], [100, 101])

    def test_get_patches_none(self) -> None:
        self.assertIsNone(self.core.get_patches(self.f1))

    def test_iter_field_items(self) -> None:
        self.core._cache.set_value(self.f1, 1, "a")
        items = dict(self.core.iter_field_items())
        self.assertIn(self.f1, items)
        self.assertEqual(items[self.f1][1], "a")


class TestOrmCoreCompute(unittest.TestCase):
    def setUp(self) -> None:
        self.core = OrmCore()
        self.f1 = FakeField("sale.order", "amount")
        self.f2 = FakeField("sale.order", "tax")

    def test_schedule_and_pending(self) -> None:
        self.core.schedule(self.f1, [1, 2])
        self.assertTrue(self.core.has_pending_field(self.f1))
        self.assertTrue(self.core.has_pending())
        self.assertEqual(self.core.get_pending_ids(self.f1), {1, 2})

    def test_is_pending(self) -> None:
        self.core.schedule(self.f1, [1, 2])
        self.assertTrue(self.core.is_pending(self.f1, 1))
        self.assertFalse(self.core.is_pending(self.f1, 3))

    def test_is_pending_no_schedule(self) -> None:
        self.assertFalse(self.core.is_pending(self.f1, 1))

    def test_has_pending_false(self) -> None:
        self.assertFalse(self.core.has_pending_field(self.f1))
        self.assertFalse(self.core.has_pending())

    def test_pending_ids_empty(self) -> None:
        self.assertEqual(self.core.get_pending_ids(self.f1), ())

    def test_mark_done(self) -> None:
        self.core.schedule(self.f1, [1, 2, 3])
        self.core.mark_done(self.f1, [1, 2])
        self.assertEqual(self.core.get_pending_ids(self.f1), {3})

    def test_mark_done_clears_entry(self) -> None:
        self.core.schedule(self.f1, [1])
        self.core.mark_done(self.f1, [1])
        self.assertFalse(self.core.has_pending_field(self.f1))

    def test_pending_fields(self) -> None:
        self.core.schedule(self.f1, [1])
        self.core.schedule(self.f2, [2])
        self.assertEqual(set(self.core.get_pending_fields()), {self.f1, self.f2})

    def test_discard_field(self) -> None:
        self.core.schedule(self.f1, [1, 2])
        self.core.discard_field(self.f1)
        self.assertFalse(self.core.has_pending_field(self.f1))

    def test_discard_field_noop(self) -> None:
        self.core.discard_field(self.f1)

    def test_protection_lifecycle(self) -> None:
        self.core.push_protection()
        self.core.protect(self.f1, frozenset([1, 2]))
        self.assertTrue(self.core.is_protected(self.f1, 1))
        self.assertFalse(self.core.is_protected(self.f1, 3))
        self.assertEqual(self.core.get_protected_ids(self.f1), frozenset([1, 2]))
        self.core.pop_protection()
        self.assertFalse(self.core.is_protected(self.f1, 1))

    def test_protection_stacking(self) -> None:
        self.core.push_protection()
        self.core.protect(self.f1, frozenset([1]))
        self.core.push_protection()
        self.core.protect(self.f1, frozenset([2]))
        self.assertTrue(self.core.is_protected(self.f1, 1))
        self.assertTrue(self.core.is_protected(self.f1, 2))
        self.core.pop_protection()
        self.assertTrue(self.core.is_protected(self.f1, 1))
        self.assertFalse(self.core.is_protected(self.f1, 2))

    def test_new_scheduler_is_bound_to_engine(self) -> None:
        from odoo.orm.components.recompute import RecomputeScheduler

        sched = self.core.new_scheduler()
        self.assertIsInstance(sched, RecomputeScheduler)
        self.assertIs(sched._engine, self.core._engine)
        self.assertIsNot(sched, self.core.new_scheduler())

    def test_new_scheduler_seeds_marked_from_live_pending_in_both_modes(self) -> None:
        self.core.schedule(self.f1, [1, 2])
        batch = self.core.new_scheduler()
        inline = self.core.new_scheduler(inline=True)
        for sched in (batch, inline):
            self.assertIs(sched._marked, self.core._engine.pending)
            self.assertEqual(sched._marked.get(self.f1), {1, 2})
        self.core.schedule(self.f2, [3])
        self.assertEqual(batch._marked.get(self.f2), {3})

    def test_new_scheduler_inline_flag(self) -> None:
        self.assertFalse(self.core.new_scheduler()._inline)
        self.assertTrue(self.core.new_scheduler(inline=True)._inline)

    def test_new_scheduler_propagates_engine_set_factory(self) -> None:

        class TrackingSet(set):
            pass

        core = OrmCore(engine=ComputeEngine(pending_factory=TrackingSet))
        sched = core.new_scheduler()
        self.assertIsInstance(sched.to_recompute["field"], TrackingSet)


class TestOrmCoreFindPendingWrite(unittest.TestCase):
    def setUp(self) -> None:
        self.core = OrmCore()
        self.f_a = FakeField("res.partner", "a")
        self.f_b = FakeField("res.partner", "b")

    def test_none_when_nothing_dirty(self) -> None:
        self.assertIsNone(self.core.get_pending_write([self.f_a], [1, 2]))

    def test_ids_none_matches_any_dirty_entry(self) -> None:
        self.core.mark_dirty(self.f_a, [7])
        self.assertEqual(self.core.get_pending_write([self.f_a], None), (self.f_a, [7]))

    def test_reports_only_the_overlap(self) -> None:
        self.core.mark_dirty(self.f_a, [1, 5, 9])
        self.assertEqual(
            self.core.get_pending_write([self.f_a], [9, 5]), (self.f_a, [5, 9])
        )

    def test_iterator_ids_survive_a_clean_first_field(self) -> None:
        self.core.mark_dirty(self.f_a, [99])
        self.core.mark_dirty(self.f_b, [1])
        found = self.core.get_pending_write([self.f_a, self.f_b], (i for i in (1, 2)))
        self.assertEqual(found, (self.f_b, [1]))

    def test_iterator_ids_match_list_ids(self) -> None:
        self.core.mark_dirty(self.f_a, [99])
        self.core.mark_dirty(self.f_b, [1])
        fields = [self.f_a, self.f_b]
        self.assertEqual(
            self.core.get_pending_write(fields, iter([1, 2])),
            self.core.get_pending_write(fields, [1, 2]),
        )


class TestOrmCoreLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        self.core = OrmCore()
        self.f1 = FakeField("x", "a")

    def test_clear_cache_only(self) -> None:
        self.core._cache.set_value(self.f1, 1, "v")
        self.core.schedule(self.f1, [1])
        self.core.clear_cache()
        self.assertIsNone(self.core._cache.get_value(self.f1, 1, None))
        self.assertTrue(self.core.has_pending_field(self.f1))


class TestOrmCoreConstructor(unittest.TestCase):
    def test_default_creates_components(self) -> None:
        core = OrmCore()
        self.assertIsInstance(core._cache, FieldCache)
        self.assertIsInstance(core._engine, ComputeEngine)

    def test_custom_components(self) -> None:
        from odoo.libs.collections import OrderedSet

        cache = FieldCache(dirty_factory=OrderedSet)
        engine = ComputeEngine(pending_factory=OrderedSet)
        core = OrmCore(cache=cache, engine=engine)
        self.assertIs(core._cache, cache)
        self.assertIs(core._engine, engine)

    def test_repr(self) -> None:
        core = OrmCore()
        r = repr(core)
        self.assertIn("OrmCore", r)
        self.assertIn("FieldCache", r)
        self.assertIn("ComputeEngine", r)


class TestOrmCoreDelegationConsistency(unittest.TestCase):
    def setUp(self) -> None:
        self.cache = FieldCache()
        self.engine = ComputeEngine()
        self.core = OrmCore(cache=self.cache, engine=self.engine)
        self.f1 = FakeField("m", "f")

    def test_get_field_data_is_same_object(self) -> None:
        self.cache.set_value(self.f1, 1, "v")
        self.assertIs(
            self.core.get_field_data(self.f1),
            self.cache.get_field_data(self.f1),
        )

    def test_pending_ids_same_object(self) -> None:
        self.core.schedule(self.f1, [1, 2])
        self.assertIs(
            self.core.get_pending_ids(self.f1),
            self.engine.get_pending_ids(self.f1),
        )

    def test_has_pending_field_matches_engine(self) -> None:
        self.assertEqual(
            self.core.has_pending_field(self.f1),
            self.engine.has_pending_field(self.f1),
        )
        self.core.schedule(self.f1, [1])
        self.assertEqual(
            self.core.has_pending_field(self.f1),
            self.engine.has_pending_field(self.f1),
        )

    def test_has_pending_matches_engine(self) -> None:
        self.assertEqual(self.core.has_pending(), self.engine.has_pending())
        self.core.schedule(self.f1, [1])
        self.assertEqual(self.core.has_pending(), self.engine.has_pending())

    def test_is_pending_matches_engine(self) -> None:
        self.core.schedule(self.f1, [1])
        self.assertEqual(
            self.core.is_pending(self.f1, 1),
            self.engine.is_pending(self.f1, 1),
        )
        self.assertEqual(
            self.core.is_pending(self.f1, 999),
            self.engine.is_pending(self.f1, 999),
        )

    def test_get_dirty_matches_cache(self) -> None:
        self.assertIs(
            self.core.get_dirty(self.f1),
            self.cache.get_dirty(self.f1),
        )
        self.core.mark_dirty(self.f1, [1])
        self.assertIs(
            self.core.get_dirty(self.f1),
            self.cache.get_dirty(self.f1),
        )

    def test_dirty_matches_cache(self) -> None:
        self.core.mark_dirty(self.f1, [1])
        self.assertEqual(
            self.core.has_dirty_field(self.f1),
            self.cache.has_dirty_field(self.f1),
        )

    def test_protection_matches_engine(self) -> None:
        self.core.push_protection()
        self.core.protect(self.f1, frozenset([1]))
        self.assertEqual(
            self.core.is_protected(self.f1, 1),
            self.engine.is_protected(self.f1, 1),
        )
        self.assertEqual(
            self.core.get_protected_ids(self.f1),
            self.engine.get_protected_ids(self.f1),
        )


class TestOrmCoreDelegationDrift(unittest.TestCase):
    def test_pass_throughs_delegate_by_same_name(self) -> None:
        for orm_method, target, underlying, arity, returns in _DELEGATIONS:
            with self.subTest(method=orm_method):
                cache = Mock(spec=FieldCache)
                engine = Mock(spec=ComputeEngine)
                core = OrmCore(cache=cache, engine=engine)
                target_obj = cache if target == "cache" else engine
                args = tuple(object() for _ in range(arity))

                result = getattr(core, orm_method)(*args)

                underlying_mock = getattr(target_obj, underlying)
                underlying_mock.assert_called_once_with(*args)
                if returns:
                    self.assertIs(result, underlying_mock.return_value)

    def test_kwarg_pass_throughs_delegate_by_same_name(self) -> None:
        for (
            orm_method,
            target,
            underlying,
            arity,
            kwarg_names,
            returns,
        ) in _KWARG_DELEGATIONS:
            with self.subTest(method=orm_method):
                cache = Mock(spec=FieldCache)
                engine = Mock(spec=ComputeEngine)
                core = OrmCore(cache=cache, engine=engine)
                target_obj = cache if target == "cache" else engine
                args = tuple(object() for _ in range(arity))
                kwargs = {name: object() for name in kwarg_names}

                result = getattr(core, orm_method)(*args, **kwargs)

                underlying_mock = getattr(target_obj, underlying)
                underlying_mock.assert_called_once_with(*args, **kwargs)
                if returns:
                    self.assertIs(result, underlying_mock.return_value)

    def test_every_pass_through_keeps_the_signature_it_forwards(self) -> None:
        # a parameter the component grows and the forwarder does not is a
        # kwarg Layer 1 cannot pass; names and kinds must match, defaults may
        # differ (get_value's sentinel dispatches on presence)
        components = {"cache": FieldCache, "engine": ComputeEngine}
        rows = [row[:3] for row in _DELEGATIONS] + [
            row[:3] for row in _KWARG_DELEGATIONS
        ]
        for orm_method, target, underlying in rows:
            with self.subTest(method=orm_method):
                forwarder = inspect.signature(
                    getattr(OrmCore, orm_method),
                    annotation_format=annotationlib.Format.STRING,
                )
                forwarded = inspect.signature(
                    getattr(components[target], underlying),
                    annotation_format=annotationlib.Format.STRING,
                )
                self.assertEqual(
                    [(p.name, p.kind) for p in forwarder.parameters.values()],
                    [(p.name, p.kind) for p in forwarded.parameters.values()],
                    f"OrmCore.{orm_method} and {components[target].__name__}.{underlying} disagree",
                )

    def test_table_covers_every_pass_through(self) -> None:
        documented = {row[0] for row in _DELEGATIONS}
        documented |= {row[0] for row in _KWARG_DELEGATIONS}
        public = {
            name
            for name in vars(OrmCore)
            if not name.startswith("_") and callable(getattr(OrmCore, name))
        }
        self.assertEqual(public - _NON_PASSTHROUGH, documented)


if __name__ == "__main__":
    unittest.main()
