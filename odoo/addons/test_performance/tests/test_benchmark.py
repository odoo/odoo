"""
ORM Performance Benchmark Suite for Odoo.

This module provides comprehensive benchmarks to assess ORM layer performance.
Focuses on:
- ORM overhead vs raw SQL
- Recordset operations
- Environment operations
- Cache behavior
- Computed field chains
- Field type performance

Run with:
    ./odoo-bin -c ./conf/odoo.conf -d benchmark_db \
        --test-tags '/test_performance:TestORMBenchmark' -u test_performance \
        --stop-after-init --workers=0

Results are logged to odoo.log with tag [ORM_BENCHMARK].
"""

import gc
import json
import logging
import statistics
from collections.abc import Callable
from datetime import datetime
from typing import Any

from odoo.tests.benchmark import BenchmarkStats, run_benchmark
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.misc import real_time

_logger = logging.getLogger(__name__)

# Benchmark configuration
DEFAULT_ITERATIONS = 50
WARMUP_ITERATIONS = 5


@tagged("standard", "orm_benchmark")
class TestORMBenchmark(TransactionCase):
    """
    Comprehensive ORM performance benchmark suite.

    Measures ORM-specific overhead beyond raw SQL execution.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_results: list[BenchmarkStats] = []
        cls.Model = cls.env["test_performance.base"]
        cls.SimpleModel = cls.env["test_performance.simple.minded"]

        # Pre-create test data
        cls._create_test_data()

    @classmethod
    def _create_test_data(cls):
        """Create test data for benchmarks."""
        existing = cls.Model.search_count([("name", "like", "ORMBench%")])
        if existing < 100:
            _logger.info("[ORM_BENCHMARK] Creating test data...")
            cls.Model.create(
                [{"name": f"ORMBench_{i}", "value": i} for i in range(100)]
            )
            # Create parent-child relationships
            parent = cls.SimpleModel.create({"name": "BenchParent"})
            cls.SimpleModel.create(
                [{"name": f"BenchChild_{i}", "parent_id": parent.id} for i in range(50)]
            )
            _logger.info("[ORM_BENCHMARK] Test data created.")

    def setUp(self):
        super().setUp()
        gc.collect()
        # Warm up
        self.Model.search_count([])

    def _run_benchmark(
        self,
        name: str,
        func: Callable[[], Any],
        iterations: int = DEFAULT_ITERATIONS,
        warmup: int = WARMUP_ITERATIONS,
        setup: Callable[[], None] | None = None,
        invalidate_cache: bool = True,
    ) -> BenchmarkStats:
        """Run a benchmark with statistical analysis."""
        stats = run_benchmark(
            name,
            func,
            iterations=iterations,
            warmup=warmup,
            setup=setup,
            invalidate=self.env.invalidate_all if invalidate_cache else None,
        )
        self.all_results.append(stats)
        _logger.info("[ORM_BENCHMARK] %s", stats.summary())
        return stats

    # =========================================================================
    # RECORDSET CREATION & ACCESS
    # =========================================================================

    def test_01_browse_single(self):
        """Benchmark: browse() single record."""
        record = self.Model.search([], limit=1)
        record_id = record.id

        def bench():
            self.Model.browse(record_id)

        self._run_benchmark(
            "browse() single ID", bench, iterations=100, invalidate_cache=False
        )

    def test_01_browse_multiple(self):
        """Benchmark: browse() multiple records."""
        records = self.Model.search([], limit=50)
        ids = records.ids

        def bench():
            self.Model.browse(ids)

        self._run_benchmark(
            "browse() 50 IDs", bench, iterations=100, invalidate_cache=False
        )

    def test_02_recordset_iteration(self):
        """Benchmark: Iterate over recordset."""
        records = self.Model.search([], limit=100)

        def bench():
            for _rec in records:
                pass

        self._run_benchmark(
            "Recordset iteration (100)",
            bench,
            iterations=100,
            invalidate_cache=False,
        )

    def test_02_recordset_indexing(self):
        """Benchmark: Recordset indexing."""
        records = self.Model.search([], limit=100)

        def bench():
            for i in range(len(records)):
                _ = records[i]

        self._run_benchmark(
            "Recordset indexing (100)",
            bench,
            iterations=100,
            invalidate_cache=False,
        )

    def test_03_recordset_slicing(self):
        """Benchmark: Recordset slicing."""
        records = self.Model.search([], limit=100)

        def bench():
            _ = records[:10]
            _ = records[10:20]
            _ = records[-10:]

        self._run_benchmark(
            "Recordset slicing", bench, iterations=100, invalidate_cache=False
        )

    # =========================================================================
    # RECORDSET OPERATIONS
    # =========================================================================

    def test_10_recordset_union(self):
        """Benchmark: Recordset union (|)."""
        records1 = self.Model.search([], limit=50)
        records2 = self.Model.search([], limit=50, offset=25)

        def bench():
            _ = records1 | records2

        self._run_benchmark(
            "Recordset union (|)", bench, iterations=100, invalidate_cache=False
        )

    def test_10_recordset_intersection(self):
        """Benchmark: Recordset intersection (&)."""
        records1 = self.Model.search([], limit=50)
        records2 = self.Model.search([], limit=50, offset=25)

        def bench():
            _ = records1 & records2

        self._run_benchmark(
            "Recordset intersection (&)",
            bench,
            iterations=100,
            invalidate_cache=False,
        )

    def test_10_recordset_difference(self):
        """Benchmark: Recordset difference (-)."""
        records1 = self.Model.search([], limit=50)
        records2 = self.Model.search([], limit=25)

        def bench():
            _ = records1 - records2

        self._run_benchmark(
            "Recordset difference (-)",
            bench,
            iterations=100,
            invalidate_cache=False,
        )

    def test_11_filtered_lambda(self):
        """Benchmark: filtered() with lambda."""
        records = self.Model.search([], limit=100)
        # Pre-load values
        _ = records.mapped("value")

        def bench():
            records.filtered(lambda r: r.value > 50)

        self._run_benchmark(
            "filtered() lambda (100 records)", bench, invalidate_cache=False
        )

    def test_11_filtered_field(self):
        """Benchmark: filtered() with field name."""
        records = self.SimpleModel.search([], limit=100)
        # Pre-load values
        _ = records.mapped("active")

        def bench():
            records.filtered("active")

        self._run_benchmark(
            "filtered() field name (100 records)", bench, invalidate_cache=False
        )

    def test_12_mapped_field(self):
        """Benchmark: mapped() single field."""
        records = self.Model.search([], limit=100)

        def bench():
            records.mapped("name")

        self._run_benchmark("mapped() single field (100 records)", bench)

    def test_12_mapped_relation(self):
        """Benchmark: mapped() through relation."""
        records = self.Model.search([("partner_id", "!=", False)], limit=50)

        def bench():
            records.mapped("partner_id.name")

        self._run_benchmark("mapped() through relation (50 records)", bench)

    def test_13_sorted_field(self):
        """Benchmark: sorted() by field."""
        records = self.Model.search([], limit=100)
        # Pre-load values
        _ = records.mapped("name")

        def bench():
            records.sorted("name")

        self._run_benchmark(
            "sorted() by field (100 records)", bench, invalidate_cache=False
        )

    def test_13_sorted_lambda(self):
        """Benchmark: sorted() with lambda."""
        records = self.Model.search([], limit=100)
        # Pre-load values
        _ = records.mapped("value")

        def bench():
            records.sorted(lambda r: r.value)

        self._run_benchmark(
            "sorted() lambda (100 records)", bench, invalidate_cache=False
        )

    def test_14_exists(self):
        """Benchmark: exists() check."""
        records = self.Model.search([], limit=100)

        def bench():
            records.exists()

        self._run_benchmark("exists() (100 records)", bench)

    # =========================================================================
    # FIELD ACCESS PATTERNS
    # =========================================================================

    def test_20_field_access_cached(self):
        """Benchmark: Field access (cached)."""
        record = self.Model.search([], limit=1)
        # Pre-load cache
        _ = record.name

        def bench():
            _ = record.name

        self._run_benchmark(
            "Field access (cached)",
            bench,
            iterations=200,
            invalidate_cache=False,
        )

    def test_20_field_access_uncached(self):
        """Benchmark: Field access (uncached, triggers fetch)."""
        record = self.Model.search([], limit=1)

        def bench():
            _ = record.name

        self._run_benchmark("Field access (uncached)", bench)

    def test_21_field_getitem_vs_getattr(self):
        """Benchmark: record['field'] vs record.field."""
        record = self.Model.search([], limit=1)
        _ = record.name  # Pre-cache

        def bench_getattr():
            _ = record.name

        def bench_getitem():
            _ = record["name"]

        self._run_benchmark(
            "Field via getattr",
            bench_getattr,
            iterations=200,
            invalidate_cache=False,
        )
        self._run_benchmark(
            "Field via getitem",
            bench_getitem,
            iterations=200,
            invalidate_cache=False,
        )

    def test_22_multi_field_access(self):
        """Benchmark: Access multiple fields on same record."""
        record = self.Model.search([], limit=1)

        def bench():
            _ = record.name
            _ = record.value
            _ = record.partner_id

        self._run_benchmark("Multi-field access (3 fields)", bench)

    def test_23_relational_field_access(self):
        """Benchmark: Many2one field access."""
        record = self.Model.search([("partner_id", "!=", False)], limit=1)

        def bench():
            _ = record.partner_id.name

        self._run_benchmark("Many2one field access", bench)

    def test_24_one2many_access(self):
        """Benchmark: One2many field access."""
        parent = self.SimpleModel.search([("child_ids", "!=", False)], limit=1)

        def bench():
            _ = list(parent.child_ids)

        self._run_benchmark("One2many field access", bench)

    # =========================================================================
    # ENVIRONMENT OPERATIONS
    # =========================================================================

    def test_30_with_context(self):
        """Benchmark: with_context() overhead."""
        records = self.Model.search([], limit=50)

        def bench():
            records.with_context(key="value")

        self._run_benchmark(
            "with_context()", bench, iterations=100, invalidate_cache=False
        )

    def test_30_with_user(self):
        """Benchmark: with_user() overhead."""
        records = self.Model.search([], limit=50)
        user = self.env.user

        def bench():
            records.with_user(user)

        self._run_benchmark(
            "with_user()", bench, iterations=100, invalidate_cache=False
        )

    def test_31_sudo(self):
        """Benchmark: sudo() overhead."""
        records = self.Model.search([], limit=50)

        def bench():
            records.sudo()

        self._run_benchmark("sudo()", bench, iterations=100, invalidate_cache=False)

    def test_32_env_ref(self):
        """Benchmark: env.ref() lookup."""

        def bench():
            self.env.ref("base.user_admin")

        self._run_benchmark("env.ref()", bench, iterations=100, invalidate_cache=False)

    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================

    def test_40_cache_invalidate_recordset(self):
        """Benchmark: invalidate_recordset()."""
        records = self.Model.search([], limit=100)
        # Pre-load cache
        _ = records.mapped("name")

        def bench():
            records.invalidate_recordset()

        self._run_benchmark(
            "invalidate_recordset() (100 records)",
            bench,
            invalidate_cache=False,
        )

    def test_40_cache_invalidate_model(self):
        """Benchmark: invalidate_model()."""
        records = self.Model.search([], limit=100)
        _ = records.mapped("name")

        def bench():
            records.invalidate_model()

        self._run_benchmark("invalidate_model()", bench, invalidate_cache=False)

    def test_41_prefetch_trigger(self):
        """Benchmark: Prefetch trigger on first access."""
        records = self.Model.search([], limit=100)

        def bench():
            # First access triggers prefetch for all 100 records
            _ = records[0].name

        self._run_benchmark("Prefetch trigger (100 records)", bench)

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================

    def test_50_computed_simple(self):
        """Benchmark: Simple computed field."""
        records = self.Model.search([], limit=50)

        def bench():
            _ = records.mapped("value_pc")

        self._run_benchmark("Computed field (simple)", bench)

    def test_51_computed_with_depends(self):
        """Benchmark: Computed field with @api.depends."""
        records = self.Model.search([], limit=50)

        def bench():
            _ = records.mapped("display_name")

        self._run_benchmark("Computed field (display_name)", bench)

    # =========================================================================
    # WRITE OPERATIONS
    # =========================================================================

    def test_60_write_single_field(self):
        """Benchmark: write() single field."""
        record = self.Model.search([], limit=1)

        def bench():
            record.write({"value": 42})

        self._run_benchmark("write() single field", bench, iterations=30)

    def test_60_write_multiple_fields(self):
        """Benchmark: write() multiple fields."""
        record = self.Model.search([], limit=1)

        def bench():
            record.write({"name": "Updated", "value": 42})

        self._run_benchmark("write() multiple fields", bench, iterations=30)

    def test_61_field_assignment(self):
        """Benchmark: Direct field assignment."""
        record = self.Model.search([], limit=1)

        def bench():
            record.value = 42

        self._run_benchmark("Field assignment", bench, iterations=30)

    def test_62_batch_write(self):
        """Benchmark: write() on multiple records."""
        records = self.Model.search([], limit=50)

        def bench():
            records.write({"value": 42})

        self._run_benchmark("Batch write() (50 records)", bench, iterations=20)

    # =========================================================================
    # CREATE OPERATIONS
    # =========================================================================

    def test_70_create_single(self):
        """Benchmark: create() single record."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Model.create({"name": f"BenchCreate_{counter[0]}"})

        self._run_benchmark("create() single record", bench, iterations=20)

    def test_70_create_batch(self):
        """Benchmark: create() batch."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Model.create(
                [{"name": f"BatchCreate_{counter[0]}_{i}"} for i in range(10)]
            )

        self._run_benchmark("create() batch (10 records)", bench, iterations=15)

    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================

    def test_80_search_simple(self):
        """Benchmark: search() with simple domain."""

        def bench():
            self.Model.search([("value", ">", 50)], limit=50)

        self._run_benchmark("search() simple domain", bench)

    def test_80_search_empty(self):
        """Benchmark: search() with empty domain."""

        def bench():
            self.Model.search([], limit=50)

        self._run_benchmark("search() empty domain", bench)

    def test_81_search_count(self):
        """Benchmark: search_count()."""

        def bench():
            self.Model.search_count([("value", ">", 50)])

        self._run_benchmark("search_count()", bench)

    def test_82_search_read(self):
        """Benchmark: search_read() combined."""

        def bench():
            self.Model.search_read(
                [("value", ">", 50)], fields=["name", "value"], limit=50
            )

        self._run_benchmark("search_read()", bench)

    # =========================================================================
    # ORM vs RAW SQL COMPARISON
    # =========================================================================

    def test_90_orm_vs_raw_read(self):
        """Benchmark: ORM read vs raw SQL."""
        records = self.Model.search([], limit=100)
        ids = list(records.ids)

        def bench_orm():
            records.read(["name", "value"])

        def bench_raw():
            self.env.cr.execute(
                "SELECT id, name, value FROM test_performance_base WHERE id = ANY(%s)",
                [ids],
            )
            self.env.cr.fetchall()

        self._run_benchmark("ORM read() (100 records)", bench_orm)
        self._run_benchmark(
            "Raw SQL SELECT (100 records)", bench_raw, invalidate_cache=False
        )

    def test_91_orm_overhead_calculation(self):
        """Benchmark: Calculate ORM overhead percentage."""
        records = self.Model.search([], limit=100)
        ids = list(records.ids)

        # Measure ORM
        orm_times = []
        for _ in range(50):
            self.env.invalidate_all()
            start = real_time()
            records.read(["name", "value"])
            orm_times.append((real_time() - start) * 1_000_000)

        # Measure raw SQL
        raw_times = []
        for _ in range(50):
            start = real_time()
            self.env.cr.execute(
                "SELECT id, name, value FROM test_performance_base WHERE id = ANY(%s)",
                [ids],
            )
            self.env.cr.fetchall()
            raw_times.append((real_time() - start) * 1_000_000)

        orm_mean = statistics.mean(orm_times)
        raw_mean = statistics.mean(raw_times)
        overhead = orm_mean - raw_mean
        overhead_pct = (overhead / orm_mean) * 100 if orm_mean > 0 else 0

        _logger.info(
            "[ORM_BENCHMARK] ORM OVERHEAD ANALYSIS:\n"
            "  ORM time:      %.1f µs\n"
            "  Raw SQL time:  %.1f µs\n"
            "  ORM overhead:  %.1f µs (%.1f%%)",
            orm_mean,
            raw_mean,
            overhead,
            overhead_pct,
        )

    # =========================================================================
    # SUMMARY
    # =========================================================================

    def test_99_generate_summary(self):
        """Generate final summary."""
        if not self.all_results:
            _logger.info("[ORM_BENCHMARK] No results to summarize.")
            return

        _logger.info("\n" + "=" * 80)
        _logger.info("[ORM_BENCHMARK] FINAL SUMMARY")
        _logger.info("=" * 80)

        # Sort by Python overhead ratio (highest first)
        sorted_by_overhead = sorted(
            self.all_results, key=lambda x: x.python_ratio, reverse=True
        )

        _logger.info("\n[ORM_BENCHMARK] HIGHEST ORM OVERHEAD:")
        _logger.info("-" * 70)
        _logger.info(
            "%-40s %10s %10s %8s",
            "Test Name",
            "Total(µs)",
            "Overhead",
            "Queries",
        )
        _logger.info("-" * 70)
        for stat in sorted_by_overhead[:10]:
            _logger.info(
                "%-40s %10.1f %9.1f%% %8.1f",
                stat.name[:40],
                stat.mean_us,
                stat.python_ratio * 100,
                stat.query_count_mean,
            )

        # Sort by total time
        sorted_by_time = sorted(self.all_results, key=lambda x: x.mean_us, reverse=True)

        _logger.info("\n[ORM_BENCHMARK] SLOWEST OPERATIONS:")
        _logger.info("-" * 70)
        _logger.info(
            "%-40s %10s %10s %10s", "Test Name", "Mean(µs)", "P95(µs)", "StdDev"
        )
        _logger.info("-" * 70)
        for stat in sorted_by_time[:10]:
            _logger.info(
                "%-40s %10.1f %10.1f %10.1f",
                stat.name[:40],
                stat.mean_us,
                stat.p95_us,
                stat.std_dev_us,
            )

        # Zero-query operations (pure Python overhead)
        zero_query_ops = [s for s in self.all_results if s.query_count_mean == 0]
        if zero_query_ops:
            _logger.info("\n[ORM_BENCHMARK] PURE PYTHON OVERHEAD (0 queries):")
            _logger.info("-" * 70)
            for stat in sorted(zero_query_ops, key=lambda x: x.mean_us, reverse=True)[
                :10
            ]:
                _logger.info("  %-40s %10.1f µs", stat.name[:40], stat.mean_us)

        # Summary statistics
        total_overhead = sum(s.python_time_us for s in self.all_results)
        total_db_time = sum(s.db_time_us for s in self.all_results)
        avg_python_ratio = statistics.mean(s.python_ratio for s in self.all_results)

        _logger.info("\n[ORM_BENCHMARK] AGGREGATE STATISTICS:")
        _logger.info("  Total tests:          %d", len(self.all_results))
        _logger.info("  Total ORM overhead:   %.1f µs", total_overhead)
        _logger.info("  Total DB time:        %.1f µs", total_db_time)
        _logger.info("  Average overhead %%:   %.1f%%", avg_python_ratio * 100)

        # Export JSON
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "results": [stat.to_dict() for stat in self.all_results],
            "summary": {
                "total_tests": len(self.all_results),
                "avg_python_ratio": avg_python_ratio,
                "total_overhead_us": total_overhead,
                "total_db_time_us": total_db_time,
            },
        }

        _logger.info("\n[ORM_BENCHMARK] JSON Export:")
        _logger.info(json.dumps(export_data, indent=2, default=str))

        _logger.info("\n[ORM_BENCHMARK] Benchmark complete.")
