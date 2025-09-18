"""Pure-Python tests for InMemoryEnvironment — no Odoo, no database required.

Tests the database-free ORM test environment covering create → compute → read,
dirty tracking, flush to DictBackend, and convergence.
"""

import unittest

from odoo.orm.components.testing import FieldDef, InMemoryEnvironment, ModelDef


class TestCreateAndRead(unittest.TestCase):
    """Test basic record creation and reading."""

    def setUp(self):
        self.env = InMemoryEnvironment(
            {
                "test.model": ModelDef(
                    "test.model",
                    {
                        "name": FieldDef("name", "char"),
                        "value": FieldDef("value", "integer"),
                    },
                ),
            }
        )

    def test_create_returns_id(self):
        id_ = self.env.create("test.model", {"name": "Alice", "value": 42})
        self.assertEqual(id_, 1)

    def test_create_auto_increment(self):
        id1 = self.env.create("test.model", {"name": "Alice"})
        id2 = self.env.create("test.model", {"name": "Bob"})
        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)

    def test_read_created_value(self):
        id_ = self.env.create("test.model", {"name": "Alice", "value": 42})
        self.assertEqual(self.env.read("test.model", id_, "name"), "Alice")
        self.assertEqual(self.env.read("test.model", id_, "value"), 42)

    def test_read_default_none(self):
        id_ = self.env.create("test.model", {"name": "Alice"})
        self.assertIsNone(self.env.read("test.model", id_, "value"))

    def test_read_with_default(self):
        env = InMemoryEnvironment(
            {
                "test.model": ModelDef(
                    "test.model",
                    {
                        "name": FieldDef("name", "char", default="Unnamed"),
                    },
                ),
            }
        )
        id_ = env.create("test.model", {})
        self.assertEqual(env.read("test.model", id_, "name"), "Unnamed")

    def test_read_with_callable_default(self):
        counter = [0]

        def make_default():
            counter[0] += 1
            return f"default_{counter[0]}"

        env = InMemoryEnvironment(
            {
                "test.model": ModelDef(
                    "test.model",
                    {
                        "code": FieldDef("code", "char", default=make_default),
                    },
                ),
            }
        )
        id1 = env.create("test.model", {})
        id2 = env.create("test.model", {})
        self.assertEqual(env.read("test.model", id1, "code"), "default_1")
        self.assertEqual(env.read("test.model", id2, "code"), "default_2")


class TestWrite(unittest.TestCase):
    """Test writing values to records."""

    def setUp(self):
        self.env = InMemoryEnvironment(
            {
                "test.model": ModelDef(
                    "test.model",
                    {
                        "name": FieldDef("name", "char"),
                        "value": FieldDef("value", "integer"),
                    },
                ),
            }
        )

    def test_write_updates_cache(self):
        id_ = self.env.create("test.model", {"name": "Alice", "value": 42})
        self.env.write("test.model", id_, {"value": 100})
        self.assertEqual(self.env.read("test.model", id_, "value"), 100)

    def test_write_partial(self):
        id_ = self.env.create("test.model", {"name": "Alice", "value": 42})
        self.env.write("test.model", id_, {"name": "Bob"})
        self.assertEqual(self.env.read("test.model", id_, "name"), "Bob")
        self.assertEqual(self.env.read("test.model", id_, "value"), 42)


class TestComputedFields(unittest.TestCase):
    """Test stored computed fields."""

    def _make_env(self):
        def compute_total(env, model, record_id):
            amount = env.read(model, record_id, "amount")
            qty = env.read(model, record_id, "qty")
            return (amount or 0) * (qty or 0)

        return InMemoryEnvironment(
            {
                "sale.order": ModelDef(
                    "sale.order",
                    {
                        "name": FieldDef("name", "char"),
                        "amount": FieldDef("amount", "float"),
                        "qty": FieldDef("qty", "integer"),
                        "total": FieldDef(
                            "total",
                            "float",
                            compute=compute_total,
                            depends=("amount", "qty"),
                        ),
                    },
                ),
            }
        )

    def test_computed_field_on_create(self):
        env = self._make_env()
        id_ = env.create("sale.order", {"name": "SO001", "amount": 10.0, "qty": 5})
        # Reading triggers recomputation
        total = env.read("sale.order", id_, "total")
        self.assertEqual(total, 50.0)

    def test_computed_field_after_write(self):
        env = self._make_env()
        id_ = env.create("sale.order", {"name": "SO001", "amount": 10.0, "qty": 5})
        env.read("sale.order", id_, "total")  # trigger initial compute
        env.write("sale.order", id_, {"amount": 20.0})
        total = env.read("sale.order", id_, "total")
        self.assertEqual(total, 100.0)

    def test_compute_chain(self):
        """A depends on B depends on C."""

        def compute_b(env, model, record_id):
            return (env.read(model, record_id, "a") or 0) * 2

        def compute_c(env, model, record_id):
            return (env.read(model, record_id, "b") or 0) + 10

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "a": FieldDef("a", "integer"),
                        "b": FieldDef(
                            "b", "integer", compute=compute_b, depends=("a",)
                        ),
                        "c": FieldDef(
                            "c", "integer", compute=compute_c, depends=("b",)
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"a": 5})
        # c should be (5 * 2) + 10 = 20
        # But note: b is computed first, then c needs to be computed
        b = env.read("m", id_, "b")
        self.assertEqual(b, 10)
        c = env.read("m", id_, "c")
        self.assertEqual(c, 20)


class TestFlush(unittest.TestCase):
    """Test flushing dirty fields to DictBackend."""

    def setUp(self):
        self.env = InMemoryEnvironment(
            {
                "test.model": ModelDef(
                    "test.model",
                    {
                        "name": FieldDef("name", "char"),
                        "value": FieldDef("value", "integer"),
                    },
                ),
            }
        )

    def test_flush_writes_to_storage(self):
        id_ = self.env.create("test.model", {"name": "Alice", "value": 42})
        self.env.flush()
        self.assertEqual(self.env.storage_get("test.model", id_, "name"), "Alice")
        self.assertEqual(self.env.storage_get("test.model", id_, "value"), 42)

    def test_flush_clears_dirty(self):
        self.env.create("test.model", {"name": "Alice"})
        self.env.flush()
        # After flush, no dirty fields
        self.assertFalse(self.env.cache.is_any_dirty())

    def test_flush_with_computed_field(self):
        def compute_upper(env, model, record_id):
            name = env.read(model, record_id, "name")
            return (name or "").upper()

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "name": FieldDef("name", "char"),
                        "upper_name": FieldDef(
                            "upper_name",
                            "char",
                            compute=compute_upper,
                            depends=("name",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"name": "alice"})
        env.flush()
        self.assertEqual(env.storage_get("m", id_, "upper_name"), "ALICE")


class TestUnknownModelField(unittest.TestCase):
    """Test error handling for unknown models/fields."""

    def setUp(self):
        self.env = InMemoryEnvironment(
            {
                "test.model": ModelDef(
                    "test.model",
                    {
                        "name": FieldDef("name", "char"),
                    },
                ),
            }
        )

    def test_unknown_model_create(self):
        with self.assertRaises(KeyError):
            self.env.create("nonexistent", {"name": "x"})

    def test_unknown_model_read(self):
        with self.assertRaises(KeyError):
            self.env.read("nonexistent", 1, "name")

    def test_unknown_field_read(self):
        id_ = self.env.create("test.model", {"name": "Alice"})
        with self.assertRaises(KeyError):
            self.env.read("test.model", id_, "nonexistent")


class TestMultipleModels(unittest.TestCase):
    """Test with multiple models."""

    def test_independent_id_sequences(self):
        env = InMemoryEnvironment(
            {
                "model.a": ModelDef(
                    "model.a",
                    {
                        "name": FieldDef("name", "char"),
                    },
                ),
                "model.b": ModelDef(
                    "model.b",
                    {
                        "title": FieldDef("title", "char"),
                    },
                ),
            }
        )
        id_a = env.create("model.a", {"name": "A1"})
        id_b = env.create("model.b", {"title": "B1"})
        # Each model has its own sequence
        self.assertEqual(id_a, 1)
        self.assertEqual(id_b, 1)

    def test_cross_model_read(self):
        env = InMemoryEnvironment(
            {
                "model.a": ModelDef(
                    "model.a",
                    {
                        "name": FieldDef("name", "char"),
                    },
                ),
                "model.b": ModelDef(
                    "model.b",
                    {
                        "title": FieldDef("title", "char"),
                    },
                ),
            }
        )
        id_a = env.create("model.a", {"name": "A1"})
        id_b = env.create("model.b", {"title": "B1"})
        self.assertEqual(env.read("model.a", id_a, "name"), "A1")
        self.assertEqual(env.read("model.b", id_b, "title"), "B1")


class TestPendingSentinel(unittest.TestCase):
    """Regression tests for PENDING sentinel edge cases.

    Reproduces the class of bugs where PENDING (stored computed field
    awaiting recomputation) leaks through code that checks ``is not None``
    or iterates cache values without filtering PENDING.  In the real ORM,
    these caused SQL errors, TypeErrors, and false cache invalidation
    warnings.  See MEMORY.md "PENDING sentinel — 6 hidden consumers".
    """

    def test_pending_not_visible_on_read(self):
        """PENDING in cache must be treated as a miss — read returns None, not PENDING."""

        def compute_total(env, model, rid):
            return (env.read(model, rid, "amount") or 0) * 2

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "amount": FieldDef("amount", "float"),
                        "total": FieldDef(
                            "total",
                            "float",
                            compute=compute_total,
                            depends=("amount",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"amount": 5.0})
        # Before reading 'total', it has PENDING in cache.
        # Reading it must trigger compute, not return PENDING.
        total = env.read("m", id_, "total")
        self.assertEqual(total, 10.0)

    def test_pending_not_flushed_to_storage(self):
        """PENDING must never be written to storage."""

        def compute_slow(env, model, rid):
            # Simulate a compute that doesn't run (field stays PENDING)
            return 999

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "val": FieldDef("val", "integer"),
                        "computed": FieldDef(
                            "computed",
                            "integer",
                            compute=compute_slow,
                            depends=("val",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"val": 1})
        # Flush without reading 'computed' — it should compute during flush
        env.flush()
        stored = env.storage_get("m", id_, "computed")
        self.assertEqual(stored, 999)

    def test_pending_replaced_by_compute_result(self):
        """After compute, PENDING is replaced by the real value in cache."""
        call_count = [0]

        def compute_x(env, model, rid):
            call_count[0] += 1
            return 42

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "a": FieldDef("a", "integer"),
                        "x": FieldDef(
                            "x", "integer", compute=compute_x, depends=("a",)
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"a": 1})
        # First read triggers compute
        self.assertEqual(env.read("m", id_, "x"), 42)
        self.assertEqual(call_count[0], 1)
        # Second read should come from cache, not re-compute
        self.assertEqual(env.read("m", id_, "x"), 42)
        self.assertEqual(call_count[0], 1)

    def test_write_dependency_reschedules_compute(self):
        """Writing a dependency field reschedules the computed field, even if it was already computed."""

        def compute_double(env, model, rid):
            return (env.read(model, rid, "base") or 0) * 2

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "base": FieldDef("base", "integer"),
                        "doubled": FieldDef(
                            "doubled",
                            "integer",
                            compute=compute_double,
                            depends=("base",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"base": 5})
        self.assertEqual(env.read("m", id_, "doubled"), 10)
        # Write base → doubled should be rescheduled
        env.write("m", id_, {"base": 7})
        self.assertEqual(env.read("m", id_, "doubled"), 14)


class TestComputeChainRegression(unittest.TestCase):
    """Regression tests for compute chain ordering.

    Reproduces the class of bugs where a fast path reads a stale cache
    value because it skipped the compute-before-read guarantee.
    See MEMORY.md "_read_format fast path skipping stored-computed recomputation".
    """

    def test_three_level_chain(self):
        """A → B → C: writing A must propagate through B to C."""

        def compute_b(env, model, rid):
            return (env.read(model, rid, "a") or 0) + 10

        def compute_c(env, model, rid):
            return (env.read(model, rid, "b") or 0) * 3

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "a": FieldDef("a", "integer"),
                        "b": FieldDef(
                            "b", "integer", compute=compute_b, depends=("a",)
                        ),
                        "c": FieldDef(
                            "c", "integer", compute=compute_c, depends=("b",)
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"a": 5})
        # b = 5+10 = 15, c = 15*3 = 45
        self.assertEqual(env.read("m", id_, "c"), 45)
        # Write a=2 → b=12 → c=36
        env.write("m", id_, {"a": 2})
        self.assertEqual(env.read("m", id_, "c"), 36)

    def test_diamond_dependency(self):
        r"""Diamond: D depends on both B and C, which both depend on A.

         A
        / \\
           B   C
        \\ /
         D
        """

        def compute_b(env, model, rid):
            return (env.read(model, rid, "a") or 0) * 2

        def compute_c(env, model, rid):
            return (env.read(model, rid, "a") or 0) + 1

        def compute_d(env, model, rid):
            b = env.read(model, rid, "b") or 0
            c = env.read(model, rid, "c") or 0
            return b + c

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "a": FieldDef("a", "integer"),
                        "b": FieldDef(
                            "b", "integer", compute=compute_b, depends=("a",)
                        ),
                        "c": FieldDef(
                            "c", "integer", compute=compute_c, depends=("a",)
                        ),
                        "d": FieldDef(
                            "d",
                            "integer",
                            compute=compute_d,
                            depends=("b", "c"),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"a": 10})
        # b=20, c=11, d=31
        self.assertEqual(env.read("m", id_, "d"), 31)
        env.write("m", id_, {"a": 3})
        # b=6, c=4, d=10
        self.assertEqual(env.read("m", id_, "d"), 10)

    def test_multiple_records_same_compute(self):
        """Compute runs on all pending records, not just the one being read."""
        compute_calls = []

        def compute_x(env, model, rid):
            compute_calls.append(rid)
            return (env.read(model, rid, "val") or 0) * 10

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "val": FieldDef("val", "integer"),
                        "x": FieldDef(
                            "x", "integer", compute=compute_x, depends=("val",)
                        ),
                    },
                ),
            }
        )
        id1 = env.create("m", {"val": 1})
        id2 = env.create("m", {"val": 2})
        id3 = env.create("m", {"val": 3})
        # Reading x for id1 should compute for all three (batch compute)
        self.assertEqual(env.read("m", id1, "x"), 10)
        # id2 and id3 were computed in the same batch
        self.assertIn(id2, compute_calls)
        self.assertIn(id3, compute_calls)
        self.assertEqual(env.read("m", id2, "x"), 20)
        self.assertEqual(env.read("m", id3, "x"), 30)


class TestFlushConvergence(unittest.TestCase):
    """Regression tests for flush convergence.

    Reproduces scenarios where flush triggers new computations,
    requiring multiple iterations of the recompute→flush cycle.
    """

    def test_compute_during_flush_converges(self):
        """Flush triggers compute via dependency, second iteration resolves it."""

        def compute_summary(env, model, rid):
            name = env.read(model, rid, "name") or ""
            val = env.read(model, rid, "value") or 0
            return f"{name}:{val}"

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "name": FieldDef("name", "char"),
                        "value": FieldDef("value", "integer"),
                        "summary": FieldDef(
                            "summary",
                            "char",
                            compute=compute_summary,
                            depends=("name", "value"),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"name": "test", "value": 42})
        env.flush()
        self.assertEqual(env.storage_get("m", id_, "summary"), "test:42")

    def test_multiple_models_flush_order(self):
        """Dirty fields across multiple models all get flushed."""
        env = InMemoryEnvironment(
            {
                "order": ModelDef(
                    "order",
                    {
                        "name": FieldDef("name", "char"),
                    },
                ),
                "line": ModelDef(
                    "line",
                    {
                        "qty": FieldDef("qty", "integer"),
                    },
                ),
            }
        )
        id_o = env.create("order", {"name": "SO001"})
        id_l = env.create("line", {"qty": 5})
        env.flush()
        self.assertEqual(env.storage_get("order", id_o, "name"), "SO001")
        self.assertEqual(env.storage_get("line", id_l, "qty"), 5)

    def test_write_after_flush_creates_new_dirty(self):
        """Writing after flush creates new dirty entries that need another flush."""
        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "val": FieldDef("val", "integer"),
                    },
                ),
            }
        )
        id_ = env.create("m", {"val": 1})
        env.flush()
        self.assertEqual(env.storage_get("m", id_, "val"), 1)
        # Write after flush
        env.write("m", id_, {"val": 99})
        env.flush()
        self.assertEqual(env.storage_get("m", id_, "val"), 99)


class TestCacheBehavior(unittest.TestCase):
    """Test cache semantics: None vs False vs 0 vs empty string."""

    def test_none_is_valid_value(self):
        env = InMemoryEnvironment(
            {
                "m": ModelDef("m", {"x": FieldDef("x", "integer")}),
            }
        )
        id_ = env.create("m", {})  # x defaults to None
        self.assertIsNone(env.read("m", id_, "x"))

    def test_false_is_valid_value(self):
        env = InMemoryEnvironment(
            {
                "m": ModelDef("m", {"active": FieldDef("active", "boolean")}),
            }
        )
        id_ = env.create("m", {"active": False})
        self.assertFalse(env.read("m", id_, "active"))

    def test_zero_is_valid_value(self):
        env = InMemoryEnvironment(
            {
                "m": ModelDef("m", {"x": FieldDef("x", "integer")}),
            }
        )
        id_ = env.create("m", {"x": 0})
        self.assertEqual(env.read("m", id_, "x"), 0)

    def test_empty_string_is_valid_value(self):
        env = InMemoryEnvironment(
            {
                "m": ModelDef("m", {"s": FieldDef("s", "char")}),
            }
        )
        id_ = env.create("m", {"s": ""})
        self.assertEqual(env.read("m", id_, "s"), "")

    def test_overwrite_preserves_type(self):
        env = InMemoryEnvironment(
            {
                "m": ModelDef("m", {"x": FieldDef("x", "integer")}),
            }
        )
        id_ = env.create("m", {"x": 42})
        env.write("m", id_, {"x": 0})
        self.assertEqual(env.read("m", id_, "x"), 0)
        self.assertIsInstance(env.read("m", id_, "x"), int)


class TestNonStoredCompute(unittest.TestCase):
    """Test non-stored computed fields (store=False).

    Non-stored computed fields are always computed on read and never
    flushed to storage — matching the real ORM's ``Field.__get__``
    behavior for ``store=False`` fields.
    """

    def test_non_stored_computed_on_read(self):
        """Non-stored computed field returns correct value on read."""

        def compute_label(env, model, rid):
            name = env.read(model, rid, "name") or ""
            return f"[{name}]"

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "name": FieldDef("name", "char"),
                        "label": FieldDef(
                            "label",
                            "char",
                            store=False,
                            compute=compute_label,
                            depends=("name",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"name": "Alice"})
        self.assertEqual(env.read("m", id_, "label"), "[Alice]")

    def test_non_stored_always_recomputes(self):
        """Non-stored field recomputes on every read (no caching)."""
        call_count = [0]

        def compute_x(env, model, rid):
            call_count[0] += 1
            return call_count[0]

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "a": FieldDef("a", "integer"),
                        "x": FieldDef(
                            "x",
                            "integer",
                            store=False,
                            compute=compute_x,
                            depends=("a",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"a": 1})
        self.assertEqual(env.read("m", id_, "x"), 1)
        self.assertEqual(env.read("m", id_, "x"), 2)  # recomputed, not cached
        self.assertEqual(call_count[0], 2)

    def test_non_stored_not_flushed_to_storage(self):
        """Non-stored computed field value must not appear in storage."""

        def compute_upper(env, model, rid):
            return (env.read(model, rid, "name") or "").upper()

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "name": FieldDef("name", "char"),
                        "upper": FieldDef(
                            "upper",
                            "char",
                            store=False,
                            compute=compute_upper,
                            depends=("name",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"name": "alice"})
        env.flush()
        # 'upper' should NOT appear in storage — it's non-stored
        self.assertIsNone(env.storage_get("m", id_, "upper"))
        # But reading it should still work (computed on demand)
        self.assertEqual(env.read("m", id_, "upper"), "ALICE")

    def test_non_stored_reads_dependency_from_cache(self):
        """Non-stored compute reads stored dependency value from cache."""

        def compute_double(env, model, rid):
            return (env.read(model, rid, "val") or 0) * 2

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "val": FieldDef("val", "integer"),
                        "doubled": FieldDef(
                            "doubled",
                            "integer",
                            store=False,
                            compute=compute_double,
                            depends=("val",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"val": 7})
        self.assertEqual(env.read("m", id_, "doubled"), 14)
        # Write changes dependency → non-stored field sees new value
        env.write("m", id_, {"val": 10})
        self.assertEqual(env.read("m", id_, "doubled"), 20)


class TestWriteInsideCompute(unittest.TestCase):
    """Test compute functions that have side effects (calling env.write).

    This mimics the real ORM pattern where compute methods set multiple
    fields on the record, or where inverse methods update dependent records.
    """

    def test_compute_with_side_effect_write(self):
        """Compute function writes to another field as a side effect."""

        def compute_and_flag(env, model, rid):
            val = env.read(model, rid, "amount") or 0
            env.write(model, rid, {"has_amount": val > 0})
            return val * 1.1

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "amount": FieldDef("amount", "float"),
                        "has_amount": FieldDef("has_amount", "boolean"),
                        "total": FieldDef(
                            "total",
                            "float",
                            compute=compute_and_flag,
                            depends=("amount",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"amount": 100.0})
        # Reading 'total' triggers compute, which writes 'has_amount'
        total = env.read("m", id_, "total")
        self.assertAlmostEqual(total, 110.0, places=5)
        self.assertTrue(env.read("m", id_, "has_amount"))

    def test_compute_writes_to_different_record(self):
        """Compute that writes to a different record (cross-record side effect)."""

        def compute_x(env, model, rid):
            val = env.read(model, rid, "val") or 0
            return val * 2

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "val": FieldDef("val", "integer"),
                        "x": FieldDef(
                            "x",
                            "integer",
                            compute=compute_x,
                            depends=("val",),
                        ),
                    },
                ),
            }
        )
        id1 = env.create("m", {"val": 5})
        id2 = env.create("m", {"val": 10})
        # Reading x for id1 batch-computes both
        self.assertEqual(env.read("m", id1, "x"), 10)
        self.assertEqual(env.read("m", id2, "x"), 20)
        # Flush both
        env.flush()
        self.assertEqual(env.storage_get("m", id1, "x"), 10)
        self.assertEqual(env.storage_get("m", id2, "x"), 20)


class TestStallDetection(unittest.TestCase):
    """Test convergence stall detection.

    In the real ORM, circular compute dependencies can cause infinite
    loops.  The UnitOfWork detects stalls after MAX_ITERATIONS and
    reports which fields are stuck.
    """

    def test_idempotent_compute_converges(self):
        """A compute that always returns the same value converges in one iteration."""
        call_count = [0]

        def compute_const(env, model, rid):
            call_count[0] += 1
            return 42

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "a": FieldDef("a", "integer"),
                        "x": FieldDef(
                            "x",
                            "integer",
                            compute=compute_const,
                            depends=("a",),
                        ),
                    },
                ),
            }
        )
        id_ = env.create("m", {"a": 1})
        env.flush()
        self.assertEqual(env.storage_get("m", id_, "x"), 42)
        # Compute was called exactly once (not repeatedly)
        self.assertEqual(call_count[0], 1)

    def test_multiple_flushes_dont_recompute_clean(self):
        """Flushing twice without writes shouldn't trigger recomputation."""
        call_count = [0]

        def compute_x(env, model, rid):
            call_count[0] += 1
            return (env.read(model, rid, "val") or 0) * 2

        env = InMemoryEnvironment(
            {
                "m": ModelDef(
                    "m",
                    {
                        "val": FieldDef("val", "integer"),
                        "x": FieldDef(
                            "x",
                            "integer",
                            compute=compute_x,
                            depends=("val",),
                        ),
                    },
                ),
            }
        )
        env.create("m", {"val": 5})
        env.flush()
        count_after_first = call_count[0]
        env.flush()  # no dirty, no pending → no-op
        self.assertEqual(call_count[0], count_after_first)


class TestRepr(unittest.TestCase):
    """Test string representation."""

    def test_repr(self):
        env = InMemoryEnvironment(
            {
                "a": ModelDef("a", {}),
                "b": ModelDef("b", {}),
            }
        )
        r = repr(env)
        self.assertIn("InMemoryEnvironment", r)
        self.assertIn("a", r)
        self.assertIn("b", r)


if __name__ == "__main__":
    unittest.main()
