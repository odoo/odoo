"""ORM Internal Hot-Path Micro-Benchmark Suite.

Benchmarks the internal functions that dominate ORM Python time:
- Field convert_to_cache() per type (Phase 1)
- Record iteration / object creation (Phase 2)
- Cache modified() / flush() internals (Phase 3)
- Domain construction / optimization (Phase 6)
- Read group operations (Phase 7)

Each test uses PerfTimer (perf_counter_ns) over 200+ iterations
with 10 warmup rounds and outlier removal.

Run with:
    > ./odoo.log && ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
        --test-tags '/test_performance:TestFieldConversion,/test_performance:TestIteration,\
/test_performance:TestCacheInternals,/test_performance:TestDomainPerf,/test_performance:TestReadGroupPerf,\
/test_performance:TestUnlink' \\
        -u test_performance --stop-after-init --workers=0

Results logged to odoo.log with tag [ORM_PERF].
"""

import base64
import gc
import json
import logging
import time
from datetime import date, datetime

from odoo import Command
from odoo.orm.domain import Domain
from odoo.tests.benchmark import PerfTimer
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

# Configuration
ITERATIONS = 200
WARMUP = 10
BATCH_SIZES = (1, 10, 100)


def _bench(func, n=ITERATIONS, warmup=WARMUP):
    """Run func n+warmup times and return PerfTimer stats."""
    timer = PerfTimer()
    for _ in range(warmup):
        func()
    for _ in range(n):
        timer.start()
        func()
        timer.stop()
    return timer


def _log_result(stats: dict):
    _logger.info("[ORM_PERF] %s", stats.get("summary", stats.get("name", "?")))


# ============================================================================
# Phase 1: Field Type Conversion Benchmarks
# ============================================================================


@tagged("standard", "orm_perf")
class TestFieldConversion(TransactionCase):
    """Benchmark convert_to_cache() for every field type."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.all_types"]
        cls.record = cls.Model.create({"name": "bench_convert"})
        cls.partner = cls.env["res.partner"].search([], limit=1)
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _bench_convert(self, field_name, value, name=None):
        """Benchmark convert_to_cache for a specific field."""
        field = self.Model._fields[field_name]
        record = self.record
        label = name or f"convert_to_cache({field.type}:{field_name})"

        timer = _bench(lambda: field.convert_to_cache(value, record))
        stats = timer.stats(label, warmup=0)
        _log_result(stats)
        self.results.append(stats)
        return stats

    def test_01_boolean(self):
        self._bench_convert("f_boolean", True)
        self._bench_convert("f_boolean", 1, "convert_to_cache(boolean:from_int)")
        self._bench_convert("f_boolean", False)

    def test_02_integer(self):
        self._bench_convert("f_integer", 42)
        self._bench_convert("f_integer", 0)
        self._bench_convert("f_integer", None, "convert_to_cache(integer:None)")

    def test_03_float(self):
        self._bench_convert("f_float", 3.14159)
        self._bench_convert("f_float", 0.0)

    def test_04_monetary(self):
        self._bench_convert("f_monetary", 99.99)

    def test_05_char(self):
        self._bench_convert("f_char", "hello world")
        self._bench_convert("f_char", "x" * 255, "convert_to_cache(char:255)")
        self._bench_convert("f_char", None, "convert_to_cache(char:None)")
        self._bench_convert("f_char", False, "convert_to_cache(char:False)")

    def test_06_text(self):
        self._bench_convert("f_text", "Short text.")
        self._bench_convert("f_text", "x" * 10000, "convert_to_cache(text:10k)")

    def test_07_date(self):
        self._bench_convert("f_date", "2025-06-15")
        self._bench_convert("f_date", date(2025, 6, 15), "convert_to_cache(date:obj)")
        self._bench_convert("f_date", False, "convert_to_cache(date:False)")

    def test_08_datetime(self):
        self._bench_convert("f_datetime", "2025-06-15 10:30:00")
        self._bench_convert(
            "f_datetime",
            datetime(2025, 6, 15, 10, 30),
            "convert_to_cache(datetime:obj)",
        )
        self._bench_convert("f_datetime", False, "convert_to_cache(datetime:False)")

    def test_09_selection(self):
        self._bench_convert("f_selection", "draft")
        self._bench_convert("f_selection", "cancel")
        self._bench_convert("f_selection", False, "convert_to_cache(selection:False)")

    def test_10_many2one_int(self):
        self._bench_convert(
            "f_many2one", self.partner.id, "convert_to_cache(many2one:int)"
        )

    def test_10_many2one_record(self):
        self._bench_convert(
            "f_many2one", self.partner, "convert_to_cache(many2one:record)"
        )

    def test_10_many2one_tuple(self):
        self._bench_convert(
            "f_many2one",
            (self.partner.id, "Name"),
            "convert_to_cache(many2one:tuple)",
        )

    def test_10_many2one_none(self):
        self._bench_convert("f_many2one", None, "convert_to_cache(many2one:None)")

    def test_11_json(self):
        small = {"key": "value", "num": 42}
        self._bench_convert("f_json", small, "convert_to_cache(json:small)")
        large = {"k" + str(i): list(range(10)) for i in range(50)}
        self._bench_convert("f_json", large, "convert_to_cache(json:large)")
        self._bench_convert("f_json", None, "convert_to_cache(json:None)")

    def test_12_binary(self):
        small_b64 = base64.b64encode(b"hello world").decode()
        self._bench_convert("f_binary", small_b64, "convert_to_cache(binary:small)")

    def test_13_html(self):
        html = "<p>Hello <b>world</b></p>"
        self._bench_convert("f_html", html, "convert_to_cache(html:small)")

    def test_90_convert_to_record(self):
        """Benchmark convert_to_record for key field types."""
        record = self.record
        for fname, cache_val, label in [
            ("f_integer", 42, "convert_to_record(integer)"),
            ("f_char", "hello", "convert_to_record(char)"),
            ("f_boolean", True, "convert_to_record(boolean)"),
            ("f_date", date(2025, 6, 15), "convert_to_record(date)"),
            ("f_many2one", self.partner.id, "convert_to_record(many2one)"),
        ]:
            field = self.Model._fields[fname]
            timer = _bench(lambda f=field, v=cache_val: f.convert_to_record(v, record))
            stats = timer.stats(label, warmup=0)
            _log_result(stats)
            self.results.append(stats)

    def test_91_convert_to_read(self):
        """Benchmark convert_to_read for key field types."""
        record = self.record
        for fname, cache_val, label in [
            ("f_integer", 42, "convert_to_read(integer)"),
            ("f_char", "hello", "convert_to_read(char)"),
            ("f_boolean", True, "convert_to_read(boolean)"),
            ("f_selection", "draft", "convert_to_read(selection)"),
        ]:
            field = self.Model._fields[fname]
            timer = _bench(lambda f=field, v=cache_val: f.convert_to_read(v, record))
            stats = timer.stats(label, warmup=0)
            _log_result(stats)
            self.results.append(stats)

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === FIELD CONVERSION SUMMARY ===")
        by_time = sorted(self.results, key=lambda r: r.get("p50_us", 0), reverse=True)
        for r in by_time[:20]:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Phase 1b: Field __get__ (Descriptor Access) Benchmarks
# ============================================================================


@tagged("standard", "orm_perf", "field_get")
class TestFieldGet(TransactionCase):
    """Benchmark Field.__get__ (record.field_name) for every scalar type.

    This directly measures the hot path optimized by the per-class __get__
    specialization (Change 3 in the Python 3.12+ modernization plan).
    Each access goes through the descriptor protocol: access check → cache
    lookup → convert_to_record.  The specialized overrides inline the
    conversion for the cache-hit case.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.all_types"]
        cls.partner = cls.env["res.partner"].search([], limit=1)
        cls.record = cls.Model.create(
            {
                "name": "get_bench",
                "f_integer": 42,
                "f_float": 3.14,
                "f_monetary": 99.99,
                "f_boolean": True,
                "f_char": "hello world",
                "f_text": "longer text for benchmarking",
                "f_date": "2025-06-15",
                "f_datetime": "2025-06-15 10:30:00",
                "f_selection": "draft",
                "f_many2one": cls.partner.id,
                "f_json": {"key": "value"},
                "f_html": "<p>Hello</p>",
            }
        )
        # Ensure cache is warm
        cls.record.read(list(cls.Model._fields))
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def _bench_get(self, field_name, label=None, n=ITERATIONS):
        """Benchmark record.field_name (Field.__get__) with warm cache."""
        record = self.record
        label = label or f"__get__({field_name})"

        # Access via getattr to go through descriptor protocol
        def bench():
            getattr(record, field_name)

        timer = _bench(bench, n=n)
        stats = timer.stats(label, warmup=0)
        self._log(stats)
        return stats

    def test_01_integer(self):
        self._bench_get("f_integer")

    def test_02_float(self):
        self._bench_get("f_float")

    def test_03_monetary(self):
        self._bench_get("f_monetary")

    def test_04_boolean(self):
        self._bench_get("f_boolean")

    def test_05_char(self):
        self._bench_get("f_char")

    def test_06_text(self):
        self._bench_get("f_text")

    def test_07_date(self):
        self._bench_get("f_date")

    def test_08_datetime(self):
        self._bench_get("f_datetime")

    def test_09_selection(self):
        self._bench_get("f_selection")

    def test_10_many2one(self):
        self._bench_get("f_many2one")

    def test_11_json(self):
        self._bench_get("f_json")

    def test_12_html(self):
        self._bench_get("f_html")

    def test_13_name(self):
        """Char field (translated)."""
        self._bench_get("name", "__get__(name/char)")

    def test_20_multi_field_access(self):
        """Benchmark accessing 9 scalar fields in sequence (form view pattern)."""
        record = self.record

        def bench():
            _ = record.f_integer
            _ = record.f_float
            _ = record.f_boolean
            _ = record.f_char
            _ = record.f_text
            _ = record.f_date
            _ = record.f_datetime
            _ = record.f_selection
            _ = record.f_monetary

        timer = _bench(bench, n=ITERATIONS)
        self._log(timer.stats("__get__(9_scalars_seq)", warmup=0))

    def test_21_multi_record_access(self):
        """Benchmark field access across 100 records (list view pattern)."""
        Base = self.env["test_performance.base"]
        records = Base.search([], limit=100)
        if len(records) < 100:
            Base.create(
                [{"name": f"multi_{i}", "value": i} for i in range(100 - len(records))]
            )
            records = Base.search([], limit=100)
        # Warm cache
        records.read(["value", "name"])

        def bench():
            for rec in records:
                _ = rec.value

        timer = _bench(bench, n=50, warmup=5)
        self._log(timer.stats("__get__(integer×100_records)", warmup=0))

    def test_30_specialized_vs_base(self):
        """A/B comparison: specialized __get__ vs base Field.__get__.

        Temporarily removes each scalar class's __get__ override, measures the
        base class path, then restores.  Compares against the specialized times
        collected earlier in this test class.
        """
        from odoo.orm.fields import misc, numeric, selection, temporal
        from odoo.orm.fields.base import Field

        record = self.record
        # Warm cache
        record.read(list(self.Model._fields))

        # Classes that have specialized __get__ and their test fields
        test_cases = [
            (numeric.Integer, "f_integer", "__get__(integer)"),
            (numeric.Float, "f_float", "__get__(float)"),
            (numeric.Monetary, "f_monetary", "__get__(monetary)"),
            (misc.Boolean, "f_boolean", "__get__(boolean)"),
            (selection.Selection, "f_selection", "__get__(selection)"),
            (temporal.Date, "f_date", "__get__(date)"),
            (temporal.Datetime, "f_datetime", "__get__(datetime)"),
        ]

        base_get = Field.__get__

        _logger.info("\n[ORM_PERF] === SPECIALIZED vs BASE Field.__get__ ===")
        _logger.info(
            "[ORM_PERF] %-20s %10s %10s %8s",
            "Field",
            "Spec p50",
            "Base p50",
            "Speedup",
        )
        _logger.info("[ORM_PERF] %s", "-" * 55)

        for _field_cls, fname, label in test_cases:
            field = self.Model._fields[fname]
            spec_get = type(field).__get__

            # Measure specialized (current)
            def bench_spec(f=field, r=record, g=spec_get):
                g(f, r)

            timer_spec = _bench(bench_spec, n=500, warmup=20)
            s_spec = timer_spec.stats(f"spec:{label}", warmup=0)

            # Measure base (bypass override)
            def bench_base(f=field, r=record, g=base_get):
                g(f, r)

            timer_base = _bench(bench_base, n=500, warmup=20)
            s_base = timer_base.stats(f"base:{label}", warmup=0)

            speedup = (
                s_base["p50_us"] / s_spec["p50_us"]
                if s_spec["p50_us"] > 0
                else float("inf")
            )
            _logger.info(
                "[ORM_PERF] %-20s %9.1fµs %9.1fµs %7.2fx",
                fname,
                s_spec["p50_us"],
                s_base["p50_us"],
                speedup,
            )
            self.results.append(s_spec)
            self.results.append(s_base)

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === FIELD __GET__ SUMMARY ===")
        by_time = sorted(self.results, key=lambda r: r.get("p50_us", 0), reverse=True)
        for r in by_time:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Phase 2: Record Iteration & Object Creation
# ============================================================================


@tagged("standard", "orm_perf")
class TestIteration(TransactionCase):
    """Benchmark recordset iteration, browse, __hash__, __eq__."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        # Ensure 1000 records exist
        existing = cls.Model.search_count([])
        if existing < 1000:
            cls.Model.create(
                [
                    {"name": f"iter_bench_{i}", "value": i}
                    for i in range(1000 - existing)
                ]
            )
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_iter_sizes(self):
        """Benchmark __iter__ for different recordset sizes."""
        for size in (1, 10, 100, 1000):
            records = self.Model.search([], limit=size)

            def iterate(rs=records):
                for _ in rs:
                    pass

            timer = _bench(iterate, n=ITERATIONS if size <= 100 else 50)
            self._log(timer.stats(f"__iter__({size} records)", warmup=0))

    def test_02_browse(self):
        """Benchmark browse() for different input types."""
        records = self.Model.search([], limit=100)
        ids = records.ids
        single_id = ids[0]

        timer = _bench(lambda: self.Model.browse(single_id))
        self._log(timer.stats("browse(single_int)", warmup=0))

        timer = _bench(lambda: self.Model.browse(ids))
        self._log(timer.stats("browse(100_ids)", warmup=0))

        timer = _bench(lambda: self.Model.browse(tuple(ids)))
        self._log(timer.stats("browse(100_tuple)", warmup=0))

    def test_03_hash(self):
        """Benchmark __hash__ for recordsets."""
        records = self.Model.search([], limit=100)
        single = records[0]

        timer = _bench(lambda: hash(single))
        self._log(timer.stats("__hash__(single)", warmup=0))

        timer = _bench(lambda: hash(records))
        self._log(timer.stats("__hash__(100)", warmup=0))

    def test_04_eq(self):
        """Benchmark __eq__ for recordsets."""
        r1 = self.Model.search([], limit=100)
        r2 = self.Model.search([], limit=100)
        r3 = self.Model.search([], limit=50)

        timer = _bench(lambda: r1 == r2)
        self._log(timer.stats("__eq__(same_100)", warmup=0))

        timer = _bench(lambda: r1 == r3)
        self._log(timer.stats("__eq__(diff_100v50)", warmup=0))

    def test_05_ids_property(self):
        """Benchmark .ids property access."""
        records = self.Model.search([], limit=100)

        timer = _bench(lambda: records.ids)
        self._log(timer.stats(".ids(100)", warmup=0))

    def test_06_len(self):
        """Benchmark len() on recordsets."""
        records = self.Model.search([], limit=100)

        timer = _bench(lambda: len(records))
        self._log(timer.stats("len(100)", warmup=0))

    def test_07_bool(self):
        """Benchmark bool() on recordsets."""
        records = self.Model.search([], limit=100)
        empty = self.Model.browse()

        timer = _bench(lambda: bool(records))
        self._log(timer.stats("bool(100_records)", warmup=0))

        timer = _bench(lambda: bool(empty))
        self._log(timer.stats("bool(empty)", warmup=0))

    def test_08_contains(self):
        """Benchmark __contains__ (in operator)."""
        records = self.Model.search([], limit=100)
        target = records[50]

        timer = _bench(lambda: target in records)
        self._log(timer.stats("__contains__(100)", warmup=0))

    def test_09_concat(self):
        """Benchmark recordset concatenation."""
        r1 = self.Model.search([], limit=50)
        r2 = self.Model.search([], limit=50, offset=50)

        timer = _bench(lambda: r1 + r2)
        self._log(timer.stats("concat(50+50)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === ITERATION SUMMARY ===")
        by_time = sorted(self.results, key=lambda r: r.get("p50_us", 0), reverse=True)
        for r in by_time:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Phase 3: Cache & Recomputation Internals
# ============================================================================


@tagged("standard", "orm_perf")
class TestCacheInternals(TransactionCase):
    """Benchmark modified(), flush_model(), _flush(), cache operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        cls.AllTypes = cls.env["test_performance.all_types"]
        existing = cls.Model.search_count([])
        if existing < 100:
            cls.Model.create(
                [
                    {"name": f"cache_bench_{i}", "value": i}
                    for i in range(100 - existing)
                ]
            )
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_modified_simple(self):
        """Benchmark modified() for a simple scalar field."""
        record = self.Model.search([], limit=1)
        field = self.Model._fields["value"]

        def bench():
            record.modified([field.name])

        timer = _bench(bench)
        self._log(timer.stats("modified(scalar_field)", warmup=0))

    def test_02_modified_relational(self):
        """Benchmark modified() for a relational field."""
        record = self.Model.search([("partner_id", "!=", False)], limit=1)
        if not record:
            return

        def bench():
            record.modified(["partner_id"])

        timer = _bench(bench)
        self._log(timer.stats("modified(many2one_field)", warmup=0))

    def test_03_modified_computed_chain(self):
        """Benchmark modified() for a field triggering stored compute."""
        record = self.Model.search([], limit=1)

        def bench():
            record.modified(
                ["value"]
            )  # triggers value_pc, computed_value, indirect_computed_value

        timer = _bench(bench)
        self._log(timer.stats("modified(computed_chain)", warmup=0))

    def test_04_flush_model_clean(self):
        """Benchmark flush_model() when nothing is dirty."""
        records = self.Model.search([], limit=100)
        # Make sure nothing is dirty
        self.env.flush_all()

        def bench():
            records.flush_model()

        timer = _bench(bench)
        self._log(timer.stats("flush_model(clean)", warmup=0))

    def test_05_flush_model_dirty(self):
        """Benchmark flush_model() with dirty records."""
        record = self.Model.search([], limit=1)

        def bench():
            record.value = record.value + 1  # make dirty
            record.flush_model()

        timer = _bench(bench, n=50)
        self._log(timer.stats("flush_model(1_dirty)", warmup=0))

    def test_06_flush_all_clean(self):
        """Benchmark flush_all() when nothing is dirty."""
        self.env.flush_all()

        def bench():
            self.env.flush_all()

        timer = _bench(bench)
        self._log(timer.stats("flush_all(clean)", warmup=0))

    def test_07_invalidate_all(self):
        """Benchmark invalidate_all()."""
        records = self.Model.search([], limit=100)
        _ = records.mapped("name")  # populate cache

        def bench():
            self.env.invalidate_all()

        timer = _bench(bench)
        self._log(timer.stats("invalidate_all()", warmup=0))

    def test_08_invalidate_recordset(self):
        """Benchmark invalidate_recordset()."""
        records = self.Model.search([], limit=100)
        _ = records.mapped("name")

        def bench():
            records.invalidate_recordset()

        timer = _bench(bench)
        self._log(timer.stats("invalidate_recordset(100)", warmup=0))

    def test_09_get_cache(self):
        """Benchmark Field._get_cache() — the inner cache dict lookup."""
        field = self.Model._fields["name"]
        env = self.env

        timer = _bench(lambda: field._get_cache(env))
        self._log(timer.stats("Field._get_cache()", warmup=0))

    def test_10_update_cache(self):
        """Benchmark Field._update_cache() — single record cache write."""
        field = self.Model._fields["name"]
        record = self.Model.search([], limit=1)

        def bench():
            field._update_cache(record, "bench_value")

        timer = _bench(bench)
        self._log(timer.stats("Field._update_cache(1)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === CACHE INTERNALS SUMMARY ===")
        by_time = sorted(self.results, key=lambda r: r.get("p50_us", 0), reverse=True)
        for r in by_time:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Phase 4 supplement: Unlink benchmark
# ============================================================================


@tagged("standard", "orm_perf")
class TestUnlink(TransactionCase):
    """Benchmark unlink() operations missing from test_orm_benchmark."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_unlink_single(self):
        """Benchmark unlink() single record."""

        def bench():
            rec = self.Model.create({"name": "unlinkme"})
            rec.unlink()

        timer = _bench(bench, n=50, warmup=5)
        self._log(timer.stats("unlink(single)", warmup=0))

    def test_02_unlink_batch(self):
        """Benchmark unlink() batch."""

        def bench():
            recs = self.Model.create([{"name": f"unlinkme_{i}"} for i in range(10)])
            recs.unlink()

        timer = _bench(bench, n=30, warmup=3)
        self._log(timer.stats("unlink(batch_10)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === UNLINK SUMMARY ===")
        for r in self.results:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Phase 6: Domain Processing
# ============================================================================


@tagged("standard", "orm_perf")
class TestDomainPerf(TransactionCase):
    """Benchmark Domain construction, optimization, and SQL generation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_domain_construct_simple(self):
        """Benchmark Domain() construction from a simple leaf list."""
        leaf = [("name", "=", "test")]

        timer = _bench(lambda: Domain(leaf))
        self._log(timer.stats("Domain(simple_leaf)", warmup=0))

    def test_02_domain_construct_multi(self):
        """Benchmark Domain() with multiple leaves."""
        leaves = [
            ("name", "=", "test"),
            ("value", ">", 10),
            ("active", "=", True),
        ]

        timer = _bench(lambda: Domain(leaves))
        self._log(timer.stats("Domain(3_leaves)", warmup=0))

    def test_03_domain_construct_nested(self):
        """Benchmark Domain() with nested boolean operators."""
        nested = [
            "|",
            ("name", "=", "a"),
            "&",
            ("value", ">", 10),
            ("active", "=", True),
        ]

        timer = _bench(lambda: Domain(nested))
        self._log(timer.stats("Domain(nested_or_and)", warmup=0))

    def test_04_domain_combine_and(self):
        """Benchmark Domain AND combination."""
        d1 = Domain([("name", "=", "test")])
        d2 = Domain([("value", ">", 10)])

        timer = _bench(lambda: d1 & d2)
        self._log(timer.stats("Domain AND (&)", warmup=0))

    def test_05_domain_combine_or(self):
        """Benchmark Domain OR combination."""
        d1 = Domain([("name", "=", "test")])
        d2 = Domain([("value", ">", 10)])

        timer = _bench(lambda: d1 | d2)
        self._log(timer.stats("Domain OR (|)", warmup=0))

    def test_06_domain_negate(self):
        """Benchmark Domain negation."""
        d = Domain([("name", "=", "test")])

        timer = _bench(lambda: ~d)
        self._log(timer.stats("Domain NOT (~)", warmup=0))

    def test_07_domain_bool_true(self):
        """Benchmark Domain TRUE constant."""
        timer = _bench(lambda: Domain(True))
        self._log(timer.stats("Domain(True)", warmup=0))

    def test_08_domain_bool_false(self):
        """Benchmark Domain FALSE constant."""
        timer = _bench(lambda: Domain(False))
        self._log(timer.stats("Domain(False)", warmup=0))

    def test_10_domain_to_sql(self):
        """Benchmark Domain to SQL conversion via _search."""
        domain = [("name", "like", "bench"), ("value", ">", 10)]
        model = self.Model.sudo()
        # Warm up to ensure model is loaded
        model.search(domain, limit=1)

        def bench():
            model._search(domain, limit=10)

        timer = _bench(bench, n=100)
        self._log(timer.stats("_search(2_leaf_domain)", warmup=0))

    def test_11_domain_to_sql_complex(self):
        """Benchmark complex domain SQL generation."""
        domain = [
            "|",
            "&",
            ("name", "like", "bench"),
            ("value", ">", 10),
            "&",
            ("partner_id", "!=", False),
            ("value", "<", 50),
        ]
        model = self.Model.sudo()
        model.search(domain, limit=1)

        def bench():
            model._search(domain, limit=10)

        timer = _bench(bench, n=100)
        self._log(timer.stats("_search(complex_domain)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === DOMAIN SUMMARY ===")
        by_time = sorted(self.results, key=lambda r: r.get("p50_us", 0), reverse=True)
        for r in by_time:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Phase 7: Read Group Operations
# ============================================================================


@tagged("standard", "orm_perf")
class TestReadGroupPerf(TransactionCase):
    """Benchmark _read_group() operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        # Ensure enough data
        existing = cls.Model.search_count([])
        if existing < 100:
            cls.Model.create(
                [
                    {"name": f"rg_bench_{i}", "value": i % 20}
                    for i in range(100 - existing)
                ]
            )
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_read_group_simple(self):
        """Benchmark _read_group() with single grouping."""
        model = self.Model.sudo()

        def bench():
            model._read_group([], groupby=["value"], aggregates=["__count"])

        timer = _bench(bench, n=50)
        self._log(timer.stats("_read_group(group_by_value)", warmup=0))

    def test_02_read_group_with_domain(self):
        """Benchmark _read_group() with domain filter."""
        model = self.Model.sudo()

        def bench():
            model._read_group(
                [("value", ">", 5)], groupby=["value"], aggregates=["__count"]
            )

        timer = _bench(bench, n=50)
        self._log(timer.stats("_read_group(domain+group)", warmup=0))

    def test_03_read_group_multi_agg(self):
        """Benchmark _read_group() with multiple aggregates."""
        model = self.Model.sudo()

        def bench():
            model._read_group(
                [],
                groupby=["partner_id"],
                aggregates=["__count", "value:sum", "value:avg"],
            )

        timer = _bench(bench, n=50)
        self._log(timer.stats("_read_group(multi_agg)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === READ GROUP SUMMARY ===")
        for r in self.results:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Phase 8: Optimized Hot-Path Micro-Benchmarks
# ============================================================================


@tagged("standard", "orm_perf")
class TestHotPaths(TransactionCase):
    """Benchmark the specific internal methods optimized during the ORM
    acceleration project: _read_format fast path, grouped() traversal,
    _to_prefetch set-based filtering, and ensure_computed().
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        cls.AllTypes = cls.env["test_performance.all_types"]
        # Ensure 200 records exist
        existing = cls.Model.search_count([])
        if existing < 200:
            cls.Model.create(
                [{"name": f"hp_bench_{i}", "value": i} for i in range(200 - existing)]
            )
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    # --- _read_format ---

    def test_01_read_format_10_records(self):
        """Benchmark _read_format (via read()) for 10 records, 3 fields."""
        records = self.Model.search([], limit=10)
        fnames = ["name", "value", "partner_id"]

        def bench():
            self.env.invalidate_all()
            records.read(fnames)

        timer = _bench(bench, n=100, warmup=10)
        self._log(timer.stats("read(10rec×3fields)", warmup=0))

    def test_02_read_format_100_records(self):
        """Benchmark _read_format (via read()) for 100 records, 3 fields."""
        records = self.Model.search([], limit=100)
        fnames = ["name", "value", "partner_id"]

        def bench():
            self.env.invalidate_all()
            records.read(fnames)

        timer = _bench(bench, n=50, warmup=5)
        self._log(timer.stats("read(100rec×3fields)", warmup=0))

    def test_03_read_format_cached(self):
        """Benchmark _read_format when cache is already warm (fast path)."""
        records = self.Model.search([], limit=100)
        fnames = ["name", "value", "partner_id"]
        records.read(fnames)  # warm cache

        def bench():
            records.read(fnames)

        timer = _bench(bench, n=200, warmup=10)
        self._log(timer.stats("read(100rec×3fields,cached)", warmup=0))

    # --- grouped ---

    def test_10_grouped_by_field(self):
        """Benchmark grouped() by field name."""
        records = self.Model.search([], limit=100)
        _ = records.mapped("value")  # warm cache

        def bench():
            records.grouped("value")

        timer = _bench(bench, n=100, warmup=10)
        self._log(timer.stats("grouped(field,100)", warmup=0))

    def test_11_grouped_by_lambda(self):
        """Benchmark grouped() with lambda key."""
        records = self.Model.search([], limit=100)
        _ = records.mapped("value")

        def bench():
            records.grouped(lambda r: r.value % 10)

        timer = _bench(bench, n=100, warmup=10)
        self._log(timer.stats("grouped(lambda,100)", warmup=0))

    # --- _to_prefetch ---

    def test_20_to_prefetch(self):
        """Benchmark Field._to_prefetch — set-based filtering of prefetch IDs."""
        records = self.Model.search([], limit=200)
        field = self.Model._fields["name"]
        record = records[0]
        records.read(["name"])  # warm cache so seen set is large

        def bench():
            field._to_prefetch(record)

        timer = _bench(bench, n=200, warmup=10)
        self._log(timer.stats("_to_prefetch(200,all_cached)", warmup=0))

    def test_21_to_prefetch_cold(self):
        """Benchmark Field._to_prefetch with cold cache (all IDs must be checked)."""
        records = self.Model.search([], limit=200)
        field = self.Model._fields["name"]
        record = records[0]

        def bench():
            self.env.invalidate_all()
            field._to_prefetch(record)

        timer = _bench(bench, n=100, warmup=10)
        self._log(timer.stats("_to_prefetch(200,cold)", warmup=0))

    # --- ensure_computed ---

    def test_30_ensure_computed_noop(self):
        """Benchmark ensure_computed() when field is not pending (no-op)."""
        records = self.Model.search([], limit=100)
        field = self.Model._fields["value_pc"]
        self.env.flush_all()  # nothing pending

        def bench():
            field.ensure_computed(records)

        timer = _bench(bench, n=500, warmup=20)
        self._log(timer.stats("ensure_computed(noop)", warmup=0))

    def test_31_ensure_computed_non_stored(self):
        """Benchmark ensure_computed() for a non-stored computed field (no-op)."""
        records = self.Model.search([], limit=100)
        field = self.Model._fields["computed_value"]

        def bench():
            field.ensure_computed(records)

        timer = _bench(bench, n=500, warmup=20)
        self._log(timer.stats("ensure_computed(non_stored)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === HOT-PATH SUMMARY ===")
        by_time = sorted(self.results, key=lambda r: r.get("p50_us", 0), reverse=True)
        for r in by_time:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


# ============================================================================
# Cross-cutting: Full Pipeline Benchmarks
# ============================================================================


@tagged("standard", "orm_perf")
class TestFullPipeline(TransactionCase):
    """End-to-end benchmarks measuring complete ORM pipelines."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.all_types"]
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_create_all_types(self):
        """Benchmark create() with all field types populated."""
        partner = self.env["res.partner"].search([], limit=1)
        vals = {
            "name": "fullpipe",
            "f_integer": 42,
            "f_float": 3.14,
            "f_char": "hello",
            "f_text": "A longer text value.",
            "f_boolean": True,
            "f_date": "2025-06-15",
            "f_datetime": "2025-06-15 10:30:00",
            "f_selection": "open",
            "f_json": {"key": "value"},
            "f_many2one": partner.id,
        }

        counter = [0]

        def bench():
            counter[0] += 1
            v = dict(vals)
            v["name"] = f"fullpipe_{counter[0]}"
            self.Model.create(v)

        timer = _bench(bench, n=30, warmup=3)
        self._log(timer.stats("create(all_types)", warmup=0))

    def test_02_write_all_types(self):
        """Benchmark write() with multiple field types."""
        record = self.Model.create({"name": "write_bench"})

        counter = [0]

        def bench():
            counter[0] += 1
            record.write(
                {
                    "f_integer": counter[0],
                    "f_char": f"updated_{counter[0]}",
                    "f_selection": "open" if counter[0] % 2 else "draft",
                    "f_date": "2025-07-01",
                }
            )

        timer = _bench(bench, n=50, warmup=5)
        self._log(timer.stats("write(4_mixed_fields)", warmup=0))

    def test_03_read_all_types(self):
        """Benchmark read() with all field types."""
        record = self.Model.create(
            {
                "name": "read_bench",
                "f_integer": 42,
                "f_char": "test",
                "f_date": "2025-06-15",
                "f_selection": "open",
            }
        )

        fnames = [
            "name",
            "f_integer",
            "f_float",
            "f_char",
            "f_text",
            "f_boolean",
            "f_date",
            "f_datetime",
            "f_selection",
        ]

        def bench():
            self.env.invalidate_all()
            record.read(fnames)

        timer = _bench(bench, n=50, warmup=5)
        self._log(timer.stats("read(9_fields)", warmup=0))

    def test_04_search_fetch(self):
        """Benchmark search_fetch() — search + cache population."""
        # Create some records (keep under COPY_THRESHOLD to avoid binary COPY numeric bug)
        for i in range(20):
            self.Model.create({"name": f"sf_{i}", "f_integer": i})
        model = self.Model.sudo()

        def bench():
            self.env.invalidate_all()
            model.search_fetch(
                [("f_integer", ">", 5)],
                ["name", "f_integer", "f_char"],
                limit=50,
            )

        timer = _bench(bench, n=50, warmup=5)
        self._log(timer.stats("search_fetch(3_fields)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === FULL PIPELINE SUMMARY ===")
        by_time = sorted(self.results, key=lambda r: r.get("p50_us", 0), reverse=True)
        for r in by_time:
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))

        # Collect ALL results from all test classes
        all_results = []
        for cls_results in [
            getattr(TestFieldConversion, "results", []),
            getattr(TestFieldGet, "results", []),
            getattr(TestIteration, "results", []),
            getattr(TestCacheInternals, "results", []),
            getattr(TestUnlink, "results", []),
            getattr(TestDomainPerf, "results", []),
            getattr(TestReadGroupPerf, "results", []),
            getattr(TestHotPaths, "results", []),
            self.results,
        ]:
            all_results.extend(cls_results)

        if all_results:
            _logger.info(
                "\n[ORM_PERF] === AGGREGATE REPORT (%d benchmarks) ===",
                len(all_results),
            )
            _logger.info("[ORM_PERF] TOP 20 SLOWEST (by p50):")
            by_time = sorted(
                all_results, key=lambda r: r.get("p50_us", 0), reverse=True
            )
            for r in by_time[:20]:
                _logger.info("[ORM_PERF]   %s", r.get("summary", ""))

            _logger.info("\n[ORM_PERF] JSON Export:")
            export = {
                "timestamp": datetime.now().isoformat(),
                "total_benchmarks": len(all_results),
                "results": all_results,
            }
            _logger.info(json.dumps(export, indent=2, default=str))


# ============================================================================
# Rust Acceleration Targets — Baselines for uncovered hot paths
# ============================================================================


@tagged("standard", "accel_baseline")
class TestAccelClone(TransactionCase):
    """Baseline: fast_clone vs copy.deepcopy on representative JSON data."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.results: list[dict] = []
        cls.flat_small = {
            "id": 1,
            "name": "test",
            "active": True,
            "value": 3.14,
        }
        cls.flat_large = {f"field_{i}": f"value_{i}" for i in range(50)}
        cls.nested = {
            "id": 1,
            "partner": {
                "id": 10,
                "name": "P",
                "country": {"id": 5, "code": "MX"},
            },
            "lines": [
                {
                    "id": j,
                    "product": {"id": j * 10, "name": f"prod_{j}"},
                    "qty": j * 1.5,
                }
                for j in range(10)
            ],
        }
        cls.list_of_dicts = [
            {"id": i, "name": f"rec_{i}", "val": i * 0.1, "active": i % 2 == 0}
            for i in range(100)
        ]
        cls.properties_blob = {
            "definitions": [
                {
                    "name": f"prop_{i}",
                    "type": "char" if i % 3 == 0 else "integer",
                    "string": f"Property {i}",
                    "default": f"default_{i}" if i % 3 == 0 else i,
                }
                for i in range(20)
            ],
            "values": {f"prop_{i}": f"val_{i}" if i % 3 == 0 else i for i in range(20)},
        }

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_clone_flat_small(self):
        from odoo.libs.json.fast_clone import fast_clone

        data = self.flat_small
        timer = _bench(lambda: fast_clone(data))
        self._log(timer.stats("fast_clone(flat_4keys)", warmup=0))

    def test_02_clone_flat_large(self):
        from odoo.libs.json.fast_clone import fast_clone

        data = self.flat_large
        timer = _bench(lambda: fast_clone(data))
        self._log(timer.stats("fast_clone(flat_50keys)", warmup=0))

    def test_03_clone_nested(self):
        from odoo.libs.json.fast_clone import fast_clone

        data = self.nested
        timer = _bench(lambda: fast_clone(data))
        self._log(timer.stats("fast_clone(nested_3lvl)", warmup=0))

    def test_04_clone_list_of_dicts(self):
        from odoo.libs.json.fast_clone import fast_clone

        data = self.list_of_dicts
        timer = _bench(lambda: fast_clone(data))
        self._log(timer.stats("fast_clone(100_dicts)", warmup=0))

    def test_05_clone_properties(self):
        from odoo.libs.json.fast_clone import fast_clone

        data = self.properties_blob
        timer = _bench(lambda: fast_clone(data))
        self._log(timer.stats("fast_clone(properties)", warmup=0))

    def test_10_deepcopy_flat_small(self):
        import copy

        data = self.flat_small
        timer = _bench(lambda: copy.deepcopy(data))
        self._log(timer.stats("deepcopy(flat_4keys)", warmup=0))

    def test_11_deepcopy_nested(self):
        import copy

        data = self.nested
        timer = _bench(lambda: copy.deepcopy(data))
        self._log(timer.stats("deepcopy(nested_3lvl)", warmup=0))

    def test_12_deepcopy_list_of_dicts(self):
        import copy

        data = self.list_of_dicts
        timer = _bench(lambda: copy.deepcopy(data))
        self._log(timer.stats("deepcopy(100_dicts)", warmup=0))

    def test_13_deepcopy_properties(self):
        import copy

        data = self.properties_blob
        timer = _bench(lambda: copy.deepcopy(data))
        self._log(timer.stats("deepcopy(properties)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === CLONE BASELINE ===")
        clones = [r for r in self.results if "fast_clone" in r.get("name", "")]
        deeps = [r for r in self.results if "deepcopy" in r.get("name", "")]
        for r in sorted(clones, key=lambda x: x.get("p50_us", 0)):
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))
        for r in sorted(deeps, key=lambda x: x.get("p50_us", 0)):
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


@tagged("standard", "accel_baseline")
class TestAccelMappedFiltered(TransactionCase):
    """Baseline: mapped/filtered with string field names at scale."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        existing = cls.Model.search_count([])
        if existing < 1000:
            cls.Model.create(
                [{"name": f"mf_{i}", "value": i} for i in range(1000 - existing)]
            )
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_mapped_int_10(self):
        records = self.Model.search([], limit=10)
        records.read(["value"])
        timer = _bench(lambda: records.mapped("value"))
        self._log(timer.stats("mapped('value',10)", warmup=0))

    def test_02_mapped_int_100(self):
        records = self.Model.search([], limit=100)
        records.read(["value"])
        timer = _bench(lambda: records.mapped("value"))
        self._log(timer.stats("mapped('value',100)", warmup=0))

    def test_03_mapped_int_1000(self):
        records = self.Model.search([], limit=1000)
        records.read(["value"])
        timer = _bench(lambda: records.mapped("value"), n=100)
        self._log(timer.stats("mapped('value',1000)", warmup=0))

    def test_04_mapped_char_100(self):
        records = self.Model.search([], limit=100)
        records.read(["name"])
        timer = _bench(lambda: records.mapped("name"))
        self._log(timer.stats("mapped('name',100)", warmup=0))

    def test_05_mapped_m2o_100(self):
        records = self.Model.search([], limit=100)
        records.read(["partner_id"])
        timer = _bench(lambda: records.mapped("partner_id"), n=100)
        self._log(timer.stats("mapped('partner_id',100)", warmup=0))

    def test_10_filtered_int_100(self):
        records = self.Model.search([], limit=100)
        records.read(["value"])
        timer = _bench(lambda: records.filtered("value"))
        self._log(timer.stats("filtered('value',100)", warmup=0))

    def test_11_filtered_int_1000(self):
        records = self.Model.search([], limit=1000)
        records.read(["value"])
        timer = _bench(lambda: records.filtered("value"), n=100)
        self._log(timer.stats("filtered('value',1000)", warmup=0))

    def test_12_filtered_name_100(self):
        records = self.Model.search([], limit=100)
        records.read(["name"])
        timer = _bench(lambda: records.filtered("name"))
        self._log(timer.stats("filtered('name',100)", warmup=0))

    def test_13_filtered_lambda_100(self):
        records = self.Model.search([], limit=100)
        records.read(["value"])
        timer = _bench(lambda: records.filtered(lambda r: r.value))
        self._log(timer.stats("filtered(lambda,100)", warmup=0))

    def test_20_sorted_field_100(self):
        records = self.Model.search([], limit=100)
        records.read(["value"])
        timer = _bench(lambda: records.sorted("value"), n=100)
        self._log(timer.stats("sorted('value',100)", warmup=0))

    def test_21_sorted_field_1000(self):
        records = self.Model.search([], limit=1000)
        records.read(["value"])
        timer = _bench(lambda: records.sorted("value"), n=50)
        self._log(timer.stats("sorted('value',1000)", warmup=0))

    def test_22_sorted_reverse_100(self):
        records = self.Model.search([], limit=100)
        records.read(["value"])
        timer = _bench(lambda: records.sorted("value", reverse=True), n=100)
        self._log(timer.stats("sorted('value',100,rev)", warmup=0))

    def test_23_sorted_lambda_100(self):
        records = self.Model.search([], limit=100)
        records.read(["value"])
        timer = _bench(lambda: records.sorted(lambda r: r.value), n=100)
        self._log(timer.stats("sorted(lambda,100)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === MAPPED/FILTERED/SORTED BASELINE ===")
        for r in sorted(self.results, key=lambda x: x.get("p50_us", 0), reverse=True):
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


@tagged("standard", "accel_baseline")
class TestAccelFieldCache(TransactionCase):
    """Baseline: FieldCache standalone operations (no ORM layer)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def _make_cache(self, n_records=1000):
        from odoo.orm.components.cache import FieldCache

        cache = FieldCache()
        f = "field_0"
        ids = tuple(range(1, n_records + 1))
        for id_ in ids:
            cache.set_value(f, id_, f"v_{id_}")
        return cache, f, ids

    def test_01_get_value_hit(self):
        cache, f, _ = self._make_cache(1000)
        timer = _bench(lambda: cache.get_value(f, 500))
        self._log(timer.stats("cache.get_value(hit)", warmup=0))

    def test_02_get_value_miss(self):
        cache, f, _ = self._make_cache(1000)
        timer = _bench(lambda: cache.get_value(f, 99999, None))
        self._log(timer.stats("cache.get_value(miss)", warmup=0))

    def test_03_set_value(self):
        from odoo.orm.components.cache import FieldCache

        cache = FieldCache()
        f = "test"
        ctr = [0]

        def bench():
            ctr[0] += 1
            cache.set_value(f, ctr[0], ctr[0])

        timer = _bench(bench)
        self._log(timer.stats("cache.set_value()", warmup=0))

    def test_04_insert_if_absent_100(self):
        from odoo.orm.components.cache import FieldCache

        cache = FieldCache()
        f = "test"
        ids = tuple(range(100))
        vals = tuple(range(100))
        timer = _bench(lambda: cache.insert_if_absent(f, ids, vals))
        self._log(timer.stats("cache.insert_if_absent(100)", warmup=0))

    def test_05_insert_if_absent_1000(self):
        from odoo.orm.components.cache import FieldCache

        cache = FieldCache()
        f = "test"
        ids = tuple(range(1000))
        vals = tuple(range(1000))
        timer = _bench(lambda: cache.insert_if_absent(f, ids, vals))
        self._log(timer.stats("cache.insert_if_absent(1000)", warmup=0))

    def test_06_update_batch_1(self):
        cache, f, _ = self._make_cache(100)
        timer = _bench(lambda: cache.update_batch(f, (42,), "x"))
        self._log(timer.stats("cache.update_batch(1)", warmup=0))

    def test_07_update_batch_100(self):
        cache, f, ids = self._make_cache(100)
        timer = _bench(lambda: cache.update_batch(f, ids, "x"))
        self._log(timer.stats("cache.update_batch(100)", warmup=0))

    def test_08_update_batch_1000(self):
        from odoo.orm.components.cache import FieldCache

        cache = FieldCache()
        f = "test"
        ids = tuple(range(1000))
        timer = _bench(lambda: cache.update_batch(f, ids, "x"))
        self._log(timer.stats("cache.update_batch(1000)", warmup=0))

    def test_09_invalidate_100(self):
        cache, f, ids = self._make_cache(1000)
        inv_ids = ids[:100]

        def bench():
            for id_ in inv_ids:
                cache.set_value(f, id_, "x")
            cache.invalidate_field(f, inv_ids)

        timer = _bench(bench, n=ITERATIONS)
        self._log(timer.stats("cache.invalidate(100of1000)", warmup=0))

    def test_10_mark_dirty_100(self):
        from odoo.orm.components.cache import FieldCache

        cache = FieldCache()
        f = "test"
        ids = list(range(100))
        timer = _bench(lambda: cache.mark_dirty(f, ids))
        self._log(timer.stats("cache.mark_dirty(100)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === FIELDCACHE STANDALONE BASELINE ===")
        for r in sorted(self.results, key=lambda x: x.get("p50_us", 0), reverse=True):
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))


@tagged("standard", "accel_baseline")
class TestAccelPrimitives(TransactionCase):
    """Baseline: NewId and OriginIds primitives."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.results: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _log(self, stats):
        _log_result(stats)
        self.results.append(stats)

    def test_01_newid_create(self):
        from odoo.orm.primitives import NewId

        timer = _bench(lambda: NewId(origin=42))
        self._log(timer.stats("NewId(origin=42)", warmup=0))

    def test_02_newid_hash(self):
        from odoo.orm.primitives import NewId

        nid = NewId(origin=42)
        timer = _bench(lambda: hash(nid))
        self._log(timer.stats("hash(NewId)", warmup=0))

    def test_03_newid_eq(self):
        from odoo.orm.primitives import NewId

        a, b = NewId(origin=42), NewId(origin=42)
        timer = _bench(lambda: a == b)
        self._log(timer.stats("NewId.__eq__(same)", warmup=0))

    def test_04_newid_lt_int(self):
        from odoo.orm.primitives import NewId

        nid = NewId(origin=10)
        timer = _bench(lambda: nid < 20)
        self._log(timer.stats("NewId.__lt__(int)", warmup=0))

    def test_10_originids_int(self):
        from odoo.orm.helpers import OriginIds

        ids = tuple(range(1, 1001))
        oid = OriginIds(ids)

        def bench():
            for _ in oid:
                pass

        timer = _bench(bench, n=ITERATIONS)
        self._log(timer.stats("OriginIds(1000_int)", warmup=0))

    def test_11_originids_mixed(self):
        from odoo.orm.helpers import OriginIds
        from odoo.orm.primitives import NewId

        ids = tuple(NewId(origin=i) if i % 3 == 0 else i for i in range(1, 501))
        oid = OriginIds(ids)

        def bench():
            for _ in oid:
                pass

        timer = _bench(bench, n=ITERATIONS)
        self._log(timer.stats("OriginIds(500_mixed)", warmup=0))

    def test_12_originids_all_newid(self):
        from odoo.orm.helpers import OriginIds
        from odoo.orm.primitives import NewId

        ids = tuple(NewId(origin=i) for i in range(1, 501))
        oid = OriginIds(ids)

        def bench():
            for _ in oid:
                pass

        timer = _bench(bench, n=ITERATIONS)
        self._log(timer.stats("OriginIds(500_newid)", warmup=0))

    def test_99_summary(self):
        if not self.results:
            return
        _logger.info("\n[ORM_PERF] === PRIMITIVES BASELINE ===")
        for r in sorted(self.results, key=lambda x: x.get("p50_us", 0), reverse=True):
            _logger.info("[ORM_PERF]   %s", r.get("summary", ""))
