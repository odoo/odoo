"""
SQL Performance Benchmark Suite for Odoo.

This module provides comprehensive benchmarks to assess the performance
of the synchronous SQL implementation in Odoo. Results can be used to
identify bottlenecks and theorize benefits of async implementation.

Run with:
    ./odoo-bin -c ./conf/odoo.conf -d benchmark_db \
        --test-tags '/test_performance:TestSQLBenchmark' -u test_performance \
        --stop-after-init --workers=0

Results are logged to odoo.log with tag [SQL_BENCHMARK].
"""

import gc
import json
import logging
import statistics
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from odoo.tests.benchmark import (
    OUTLIER_PERCENTILE,
    BenchmarkStats,
    run_benchmark,
)
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

# Benchmark configuration
DEFAULT_ITERATIONS = 50  # Number of times to run each test
WARMUP_ITERATIONS = 5  # Warmup runs (excluded from stats)


@tagged("standard", "sql_benchmark")
class TestSQLBenchmark(TransactionCase):
    """
    Comprehensive SQL performance benchmark suite.

    Measures:
    - Query execution timing with statistical analysis
    - Query count per operation
    - DB wait time vs Python processing time ratio
    - Variance and consistency metrics
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_results: list[BenchmarkStats] = []
        cls.Partner = cls.env["res.partner"]
        cls.User = cls.env["res.users"]
        cls.Country = cls.env["res.country"]

        # Pre-create test data
        cls._create_test_data()

    @classmethod
    def _create_test_data(cls):
        """Create test data for benchmarks."""
        # Create test partners if needed
        existing = cls.Partner.search_count([("name", "like", "BenchmarkPartner%")])
        if existing < 100:
            _logger.info("[SQL_BENCHMARK] Creating test data...")
            partners_data = [
                {
                    "name": f"BenchmarkPartner_{i}",
                    "email": f"benchmark{i}@test.com",
                    "phone": f"+1555{i:04d}",
                    "is_company": i % 3 == 0,
                    "country_id": (
                        cls.env.ref("base.mx").id
                        if i % 2 == 0
                        else cls.env.ref("base.us").id
                    ),
                }
                for i in range(100)
            ]
            cls.Partner.create(partners_data)
            _logger.info("[SQL_BENCHMARK] Test data created.")

    def setUp(self):
        super().setUp()
        # Force garbage collection before each test
        gc.collect()
        # Warm up connection pool
        self.Partner.search_count([])

    def _run_benchmark(
        self,
        name: str,
        func: Callable[[], Any],
        iterations: int = DEFAULT_ITERATIONS,
        warmup: int = WARMUP_ITERATIONS,
        setup: Callable[[], None] | None = None,
        teardown: Callable[[], None] | None = None,
    ) -> BenchmarkStats:
        """Run a benchmark function multiple times and collect statistics."""
        stats = run_benchmark(
            name,
            func,
            iterations=iterations,
            warmup=warmup,
            setup=setup,
            teardown=teardown,
            invalidate=self.env.invalidate_all,
        )
        self.all_results.append(stats)
        _logger.info("[SQL_BENCHMARK] %s", stats.summary("ms"))
        return stats

    # =========================================================================
    # SINGLE RECORD OPERATIONS
    # =========================================================================

    def test_01_single_record_read_by_id(self):
        """Benchmark: Read single record by ID."""
        partner = self.Partner.search([], limit=1)

        def bench():
            self.Partner.browse(partner.id).read(
                ["name", "email", "phone", "country_id"]
            )

        self._run_benchmark("Single Record Read (by ID)", bench)

    def test_02_single_record_create(self):
        """Benchmark: Create single record."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Partner.create(
                {
                    "name": f"BenchCreate_{counter[0]}_{time.time()}",
                    "email": "bench@test.com",
                }
            )

        self._run_benchmark("Single Record Create", bench, iterations=30)

    def test_03_single_record_write(self):
        """Benchmark: Update single record."""
        partner = self.Partner.create({"name": "WriteTest"})

        def bench():
            partner.write({"name": f"Updated_{time.time()}"})

        self._run_benchmark("Single Record Write", bench)

    def test_04_single_record_unlink(self):
        """Benchmark: Delete single record."""

        def setup():
            self._partner_to_delete = self.Partner.create({"name": "ToDelete"})

        def bench():
            self._partner_to_delete.unlink()

        self._run_benchmark("Single Record Unlink", bench, setup=setup, iterations=30)

    # =========================================================================
    # SEARCH OPERATIONS
    # =========================================================================

    def test_10_search_simple_domain(self):
        """Benchmark: Search with simple domain."""

        def bench():
            self.Partner.search([("is_company", "=", True)], limit=50)

        self._run_benchmark("Search Simple Domain (limit=50)", bench)

    def test_11_search_complex_domain(self):
        """Benchmark: Search with complex multi-field domain."""

        def bench():
            self.Partner.search(
                [
                    ("is_company", "=", True),
                    "|",
                    ("country_id.code", "=", "MX"),
                    ("country_id.code", "=", "US"),
                    ("email", "!=", False),
                ],
                limit=100,
            )

        self._run_benchmark("Search Complex Domain (limit=100)", bench)

    def test_12_search_with_order(self):
        """Benchmark: Search with ordering."""

        def bench():
            self.Partner.search(
                [("is_company", "=", True)], order="name desc, id", limit=100
            )

        self._run_benchmark("Search with ORDER BY (limit=100)", bench)

    def test_13_search_count(self):
        """Benchmark: Count records matching domain."""

        def bench():
            self.Partner.search_count([("is_company", "=", True)])

        self._run_benchmark("Search Count", bench)

    def test_14_search_read_combined(self):
        """Benchmark: Search and read in one call."""

        def bench():
            self.Partner.search_read(
                [("is_company", "=", True)],
                fields=["name", "email", "phone", "country_id"],
                limit=50,
            )

        self._run_benchmark("Search Read Combined (limit=50)", bench)

    # =========================================================================
    # BATCH OPERATIONS
    # =========================================================================

    def test_20_batch_create_10(self):
        """Benchmark: Create 10 records in batch."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Partner.create(
                [
                    {
                        "name": f"Batch10_{counter[0]}_{i}",
                        "email": f"b{i}@test.com",
                    }
                    for i in range(10)
                ]
            )

        self._run_benchmark("Batch Create (10 records)", bench, iterations=20)

    def test_21_batch_create_100(self):
        """Benchmark: Create 100 records in batch."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Partner.create(
                [
                    {
                        "name": f"Batch100_{counter[0]}_{i}",
                        "email": f"b{i}@test.com",
                    }
                    for i in range(100)
                ]
            )

        self._run_benchmark("Batch Create (100 records)", bench, iterations=10)

    def test_22_batch_write(self):
        """Benchmark: Update multiple records."""
        partners = self.Partner.search(
            [("name", "like", "BenchmarkPartner%")], limit=50
        )

        def bench():
            partners.write({"phone": f"+1555{int(time.time()) % 10000:04d}"})

        self._run_benchmark("Batch Write (50 records)", bench)

    def test_23_batch_read(self):
        """Benchmark: Read multiple records."""
        partners = self.Partner.search([], limit=100)

        def bench():
            partners.read(["name", "email", "phone", "country_id", "is_company"])

        self._run_benchmark("Batch Read (100 records, 5 fields)", bench)

    # =========================================================================
    # RELATIONAL FIELD OPERATIONS
    # =========================================================================

    def test_30_relational_many2one_access(self):
        """Benchmark: Access Many2one related fields."""
        partners = self.Partner.search([("country_id", "!=", False)], limit=50)

        def bench():
            for p in partners:
                _ = p.country_id.name
                _ = p.country_id.code

        self._run_benchmark("Many2one Access (50 records)", bench)

    def test_31_relational_one2many_access(self):
        """Benchmark: Access One2many related records."""
        countries = self.Country.search([], limit=10)

        def bench():
            for c in countries:
                _ = len(c.state_ids)
                for state in c.state_ids[:5]:
                    _ = state.name

        self._run_benchmark("One2many Access (10 countries)", bench)

    def test_32_relational_deep_traversal(self):
        """Benchmark: Deep relational field traversal."""
        partners = self.Partner.search([("country_id", "!=", False)], limit=20)

        def bench():
            for p in partners:
                # Partner -> Country -> Currency -> Company
                _ = p.country_id.currency_id.name if p.country_id.currency_id else None

        self._run_benchmark("Deep Relational Traversal (3 levels)", bench)

    # =========================================================================
    # COMPUTED FIELDS
    # =========================================================================

    def test_40_computed_field_access(self):
        """Benchmark: Access computed fields (display_name)."""
        partners = self.Partner.search([], limit=100)

        def bench():
            for p in partners:
                _ = p.display_name

        self._run_benchmark("Computed Field Access (100 records)", bench)

    def test_41_computed_field_with_depends(self):
        """Benchmark: Computed fields with dependencies."""
        users = self.User.search([], limit=20)

        def bench():
            for u in users:
                # Access computed fields that depend on other fields
                _ = u.display_name
                _ = u.partner_id.display_name

        self._run_benchmark("Computed Fields with Dependencies (20 users)", bench)

    # =========================================================================
    # RAW SQL vs ORM
    # =========================================================================

    def test_50_raw_sql_select(self):
        """Benchmark: Raw SQL SELECT."""

        def bench():
            self.env.cr.execute("""
                SELECT id, name, email, phone
                FROM res_partner
                WHERE is_company = true
                LIMIT 100
            """)
            self.env.cr.fetchall()

        self._run_benchmark("Raw SQL SELECT (100 rows)", bench)

    def test_51_orm_equivalent_select(self):
        """Benchmark: ORM equivalent of raw SQL."""

        def bench():
            self.Partner.search_read(
                [("is_company", "=", True)],
                fields=["name", "email", "phone"],
                limit=100,
            )

        self._run_benchmark("ORM Equivalent SELECT (100 rows)", bench)

    def test_52_raw_sql_insert(self):
        """Benchmark: Raw SQL INSERT."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.env.cr.execute(
                """
                INSERT INTO res_partner (name, email, active, create_uid, write_uid, create_date, write_date)
                VALUES (%s, %s, true, %s, %s, NOW(), NOW())
            """,
                (
                    f"RawSQL_{counter[0]}",
                    "raw@test.com",
                    self.env.uid,
                    self.env.uid,
                ),
            )

        self._run_benchmark("Raw SQL INSERT", bench, iterations=30)

    # =========================================================================
    # TRANSACTION PATTERNS
    # =========================================================================

    def test_60_savepoint_overhead(self):
        """Benchmark: Savepoint creation and release overhead."""

        def bench():
            with self.env.cr.savepoint():
                self.Partner.search_count([])

        self._run_benchmark("Savepoint Overhead", bench)

    def test_61_multiple_queries_single_transaction(self):
        """Benchmark: Multiple queries in single transaction."""

        def bench():
            self.Partner.search_count([("is_company", "=", True)])
            self.Partner.search_count([("is_company", "=", False)])
            self.Partner.search([("country_id", "!=", False)], limit=10)
            self.Country.search_count([])

        self._run_benchmark("Multiple Queries (4 queries, 1 transaction)", bench)

    # =========================================================================
    # CACHE BEHAVIOR
    # =========================================================================

    def test_70_cache_hit_single(self):
        """Benchmark: Cache hit on single record."""
        partner = self.Partner.search([], limit=1)
        # Pre-populate cache
        _ = partner.name

        def bench():
            # Should hit cache
            _ = partner.name

        self._run_benchmark("Cache Hit (single field)", bench, iterations=100)

    def test_71_cache_miss_single(self):
        """Benchmark: Cache miss on single record."""
        partner = self.Partner.search([], limit=1)

        def setup():
            self.env.invalidate_all()

        def bench():
            _ = partner.name

        self._run_benchmark("Cache Miss (single field)", bench, setup=setup)

    def test_72_prefetch_behavior(self):
        """Benchmark: ORM prefetch behavior."""
        partners = self.Partner.search([], limit=100)
        self.env.invalidate_all()

        def bench():
            # First access triggers prefetch for all 100
            for p in partners:
                _ = p.name

        self._run_benchmark("Prefetch (100 records)", bench)

    # =========================================================================
    # CONCURRENT SIMULATION
    # =========================================================================

    def test_80_sequential_operations(self):
        """Benchmark: Sequential independent operations."""

        def bench():
            # Simulate what could be parallelized with async
            self.Partner.search_count([("is_company", "=", True)])
            self.Partner.search_count([("is_company", "=", False)])
            self.Country.search_count([])
            self.User.search_count([])

        self._run_benchmark("Sequential Operations (4 counts)", bench)

    # =========================================================================
    # SCALING ANALYSIS - Critical for async benefit assessment
    # =========================================================================

    def test_85_scaling_batch_create_1(self):
        """Benchmark: Create 1 record (baseline)."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Partner.create(
                {"name": f"Scale1_{counter[0]}", "email": "scale@test.com"}
            )

        self._run_benchmark("Scale: Create 1 record", bench, iterations=30)

    def test_85_scaling_batch_create_5(self):
        """Benchmark: Create 5 records."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Partner.create(
                [
                    {
                        "name": f"Scale5_{counter[0]}_{i}",
                        "email": f"s{i}@test.com",
                    }
                    for i in range(5)
                ]
            )

        self._run_benchmark("Scale: Create 5 records", bench, iterations=30)

    def test_85_scaling_batch_create_25(self):
        """Benchmark: Create 25 records."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Partner.create(
                [
                    {
                        "name": f"Scale25_{counter[0]}_{i}",
                        "email": f"s{i}@test.com",
                    }
                    for i in range(25)
                ]
            )

        self._run_benchmark("Scale: Create 25 records", bench, iterations=20)

    def test_85_scaling_batch_create_50(self):
        """Benchmark: Create 50 records."""
        counter = [0]

        def bench():
            counter[0] += 1
            self.Partner.create(
                [
                    {
                        "name": f"Scale50_{counter[0]}_{i}",
                        "email": f"s{i}@test.com",
                    }
                    for i in range(50)
                ]
            )

        self._run_benchmark("Scale: Create 50 records", bench, iterations=15)

    def test_86_scaling_search_10(self):
        """Benchmark: Search limit=10."""

        def bench():
            self.Partner.search([], limit=10)

        self._run_benchmark("Scale: Search limit=10", bench)

    def test_86_scaling_search_50(self):
        """Benchmark: Search limit=50."""

        def bench():
            self.Partner.search([], limit=50)

        self._run_benchmark("Scale: Search limit=50", bench)

    def test_86_scaling_search_200(self):
        """Benchmark: Search limit=200."""

        def bench():
            self.Partner.search([], limit=200)

        self._run_benchmark("Scale: Search limit=200", bench)

    def test_86_scaling_search_500(self):
        """Benchmark: Search limit=500."""

        def bench():
            self.Partner.search([], limit=500)

        self._run_benchmark("Scale: Search limit=500", bench)

    # =========================================================================
    # ASYNC POTENTIAL - Operations that could benefit from parallelization
    # =========================================================================

    def test_90_independent_reads_2_tables(self):
        """Benchmark: 2 independent table reads (async potential: high)."""

        def bench():
            # These two queries are completely independent
            self.Partner.search_read([("is_company", "=", True)], limit=50)
            self.Country.search_read([], limit=50)

        self._run_benchmark("Independent: 2 table reads", bench)

    def test_90_independent_reads_4_tables(self):
        """Benchmark: 4 independent table reads (async potential: very high)."""

        def bench():
            # All four queries are completely independent
            self.Partner.search_read([("is_company", "=", True)], limit=30)
            self.Country.search_read([], limit=30)
            self.User.search_read([], fields=["name", "login"], limit=30)
            self.env["res.currency"].search_read([], limit=30)

        self._run_benchmark("Independent: 4 table reads", bench)

    def test_91_dependent_chain(self):
        """Benchmark: Dependent query chain (async potential: low)."""

        def bench():
            # Each query depends on the previous one
            partner = self.Partner.search([("country_id", "!=", False)], limit=1)
            if partner:
                country = partner.country_id
                currency = country.currency_id
                if currency:
                    _ = currency.rate

        self._run_benchmark("Dependent: Query chain", bench)

    def test_92_mixed_independent_dependent(self):
        """Benchmark: Mix of independent and dependent queries."""

        def bench():
            # Independent group 1
            companies = self.Partner.search([("is_company", "=", True)], limit=20)
            self.Country.search([], limit=20)

            # Dependent on group 1
            for company in companies[:5]:
                _ = company.country_id.name

        self._run_benchmark("Mixed: Independent + Dependent", bench)

    def test_93_n_plus_one_pattern(self):
        """Benchmark: Classic N+1 query pattern (async potential: medium)."""
        partners = self.Partner.search([("country_id", "!=", False)], limit=20)
        self.env.invalidate_all()

        def bench():
            # This causes N+1 queries without proper prefetching
            return [{
                        "name": p.name,
                        "country": p.country_id.name,
                        "currency": (
                            p.country_id.currency_id.name
                            if p.country_id.currency_id
                            else None
                        ),
                    } for p in partners]

        self._run_benchmark("N+1 Pattern (20 records, 3 levels)", bench)

    def test_94_bulk_field_access(self):
        """Benchmark: Bulk field access pattern (async potential: low - uses prefetch)."""
        partners = self.Partner.search([], limit=100)
        self.env.invalidate_all()

        def bench():
            # ORM prefetch should optimize this
            names = partners.mapped("name")
            emails = partners.mapped("email")
            phones = partners.mapped("phone")
            return names, emails, phones

        self._run_benchmark("Bulk mapped() access (100 records, 3 fields)", bench)

    # =========================================================================
    # QUERY COMPLEXITY ANALYSIS
    # =========================================================================

    def test_95_simple_where(self):
        """Benchmark: Simple WHERE clause."""

        def bench():
            self.Partner.search([("active", "=", True)], limit=100)

        self._run_benchmark("Query: Simple WHERE", bench)

    def test_95_multiple_conditions(self):
        """Benchmark: Multiple AND conditions."""

        def bench():
            self.Partner.search(
                [
                    ("active", "=", True),
                    ("is_company", "=", True),
                    ("email", "!=", False),
                ],
                limit=100,
            )

        self._run_benchmark("Query: Multiple AND conditions", bench)

    def test_95_or_conditions(self):
        """Benchmark: OR conditions."""

        def bench():
            self.Partner.search(
                [
                    "|",
                    "|",
                    ("name", "ilike", "bench"),
                    ("email", "ilike", "bench"),
                    ("phone", "ilike", "555"),
                ],
                limit=100,
            )

        self._run_benchmark("Query: OR conditions", bench)

    def test_95_join_condition(self):
        """Benchmark: Query requiring JOIN."""

        def bench():
            self.Partner.search(
                [
                    ("country_id.code", "in", ["MX", "US", "CA"]),
                ],
                limit=100,
            )

        self._run_benchmark("Query: JOIN condition", bench)

    def test_96_aggregation_group_by(self):
        """Benchmark: Aggregation with GROUP BY."""

        def bench():
            self.Partner._read_group(
                domain=[("active", "=", True)],
                groupby=["country_id"],
                aggregates=["__count"],
            )

        self._run_benchmark("Query: GROUP BY aggregation", bench)

    # =========================================================================
    # SUMMARY AND EXPORT
    # =========================================================================

    def test_99_generate_summary(self):
        """Generate final summary and export results."""
        if not self.all_results:
            _logger.info("[SQL_BENCHMARK] No results to summarize.")
            return

        _logger.info("\n" + "=" * 80)
        _logger.info("[SQL_BENCHMARK] FINAL SUMMARY")
        _logger.info("=" * 80)

        # Sort by DB time ratio (highest first - best candidates for async)
        sorted_by_db_ratio = sorted(
            self.all_results, key=lambda x: x.db_ratio, reverse=True
        )

        _logger.info("\n[SQL_BENCHMARK] TOP CANDIDATES FOR ASYNC (by DB wait %%):")
        _logger.info("-" * 70)
        _logger.info("%-45s %8s %8s %8s", "Test Name", "Mean(ms)", "DB%", "Queries")
        _logger.info("-" * 70)
        for stat in sorted_by_db_ratio[:10]:
            _logger.info(
                "%-45s %8.3f %7.1f%% %8.1f",
                stat.name[:45],
                stat.mean_ms,
                stat.db_ratio * 100,
                stat.query_count_mean,
            )

        # Sort by total time (slowest first)
        sorted_by_time = sorted(self.all_results, key=lambda x: x.mean_ms, reverse=True)

        _logger.info("\n[SQL_BENCHMARK] SLOWEST OPERATIONS:")
        _logger.info("-" * 70)
        _logger.info("%-45s %8s %8s %8s", "Test Name", "Mean(ms)", "P95(ms)", "StdDev")
        _logger.info("-" * 70)
        for stat in sorted_by_time[:10]:
            _logger.info(
                "%-45s %8.3f %8.3f %8.3f",
                stat.name[:45],
                stat.mean_ms,
                stat.p95_ms,
                stat.std_dev_ms,
            )

        # Sort by variance (most inconsistent first)
        sorted_by_cv = sorted(self.all_results, key=lambda x: x.cv, reverse=True)

        _logger.info("\n[SQL_BENCHMARK] MOST VARIABLE OPERATIONS (inconsistent):")
        _logger.info("-" * 70)
        _logger.info("%-45s %8s %8s %8s", "Test Name", "CV", "Min(ms)", "Max(ms)")
        _logger.info("-" * 70)
        for stat in sorted_by_cv[:5]:
            _logger.info(
                "%-45s %8.3f %8.3f %8.3f",
                stat.name[:45],
                stat.cv,
                stat.min_ms,
                stat.max_ms,
            )

        # Export to JSON for external analysis
        export_data = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "iterations": DEFAULT_ITERATIONS,
                "warmup": WARMUP_ITERATIONS,
                "outlier_percentile": OUTLIER_PERCENTILE,
            },
            "results": [stat.to_dict() for stat in self.all_results],
            "summary": {
                "total_tests": len(self.all_results),
                "avg_db_ratio": statistics.mean(s.db_ratio for s in self.all_results),
                "avg_query_count": statistics.mean(
                    s.query_count_mean for s in self.all_results
                ),
            },
        }

        _logger.info("\n[SQL_BENCHMARK] JSON Export:")
        _logger.info(json.dumps(export_data, indent=2, default=str))

        _logger.info("\n" + "=" * 80)
        _logger.info("[SQL_BENCHMARK] ASYNC BENEFIT ANALYSIS")
        _logger.info("=" * 80)

        # 1. DB Wait Time Analysis
        high_db_ratio = [s for s in self.all_results if s.db_ratio > 0.6]
        medium_db_ratio = [s for s in self.all_results if 0.3 <= s.db_ratio <= 0.6]
        low_db_ratio = [s for s in self.all_results if s.db_ratio < 0.3]

        _logger.info("\n1. DB WAIT TIME DISTRIBUTION:")
        _logger.info(
            "   High DB wait (>60%%):    %d operations (%.1f%%)",
            len(high_db_ratio),
            (
                len(high_db_ratio) / len(self.all_results) * 100
                if self.all_results
                else 0
            ),
        )
        _logger.info(
            "   Medium DB wait (30-60%%): %d operations (%.1f%%)",
            len(medium_db_ratio),
            (
                len(medium_db_ratio) / len(self.all_results) * 100
                if self.all_results
                else 0
            ),
        )
        _logger.info(
            "   Low DB wait (<30%%):     %d operations (%.1f%%)",
            len(low_db_ratio),
            (
                len(low_db_ratio) / len(self.all_results) * 100
                if self.all_results
                else 0
            ),
        )

        if high_db_ratio:
            avg_db_time = statistics.mean(s.db_time_ms for s in high_db_ratio)
            total_db_wait = sum(s.db_time_ms for s in high_db_ratio)
            _logger.info("\n   High-ratio operations stats:")
            _logger.info("   - Average DB wait: %.3f ms", avg_db_time)
            _logger.info("   - Total DB wait:   %.3f ms", total_db_wait)

        # 2. Independent Operations Analysis
        _logger.info("\n2. INDEPENDENT OPERATIONS ANALYSIS:")
        independent_tests = [s for s in self.all_results if "Independent" in s.name]
        if independent_tests:
            for test in independent_tests:
                # Calculate theoretical async speedup
                # If queries run in parallel, time = max(individual query times) instead of sum
                estimated_parallel_time = (
                    test.db_time_ms / test.query_count_mean
                    if test.query_count_mean > 0
                    else test.mean_ms
                )
                speedup = (
                    test.mean_ms / estimated_parallel_time
                    if estimated_parallel_time > 0
                    else 1
                )
                _logger.info("   %s:", test.name)
                _logger.info(
                    "      Current (sync):  %.3f ms (%d queries)",
                    test.mean_ms,
                    int(test.query_count_mean),
                )
                _logger.info(
                    "      Theoretical async speedup: %.2fx",
                    min(speedup, test.query_count_mean),
                )

        # 3. Scaling Analysis
        _logger.info("\n3. SCALING ANALYSIS:")
        scale_create_tests = [
            s for s in self.all_results if s.name.startswith("Scale: Create")
        ]
        scale_search_tests = [
            s for s in self.all_results if s.name.startswith("Scale: Search")
        ]

        if scale_create_tests:
            _logger.info("   Batch Create scaling:")
            for test in sorted(scale_create_tests, key=lambda x: x.mean_ms):
                # Extract record count from name
                _logger.info(
                    "      %s: %.3f ms (%.3f ms/record avg)",
                    test.name,
                    test.mean_ms,
                    test.mean_ms / max(1, test.query_count_mean),
                )

        if scale_search_tests:
            _logger.info("   Search scaling:")
            for test in sorted(scale_search_tests, key=lambda x: x.mean_ms):
                _logger.info("      %s: %.3f ms", test.name, test.mean_ms)

        # 4. Query Complexity Impact
        _logger.info("\n4. QUERY COMPLEXITY IMPACT:")
        query_tests = [s for s in self.all_results if s.name.startswith("Query:")]
        if query_tests:
            baseline = next((t for t in query_tests if "Simple WHERE" in t.name), None)
            if baseline:
                _logger.info("   Baseline (Simple WHERE): %.3f ms", baseline.mean_ms)
                for test in query_tests:
                    if test != baseline:
                        overhead = (
                            ((test.mean_ms - baseline.mean_ms) / baseline.mean_ms * 100)
                            if baseline.mean_ms > 0
                            else 0
                        )
                        _logger.info(
                            "   %s: %.3f ms (%+.1f%% vs baseline)",
                            test.name,
                            test.mean_ms,
                            overhead,
                        )

        # 5. Theoretical Async Benefits Summary
        _logger.info("\n5. THEORETICAL ASYNC BENEFITS:")
        total_sync_time = sum(s.mean_ms for s in self.all_results)
        total_db_time = sum(s.db_time_ms for s in self.all_results)
        total_python_time = sum(s.python_time_ms for s in self.all_results)

        _logger.info("   Total benchmark time (sync): %.3f ms", total_sync_time)
        _logger.info(
            "   Total DB wait time:          %.3f ms (%.1f%%)",
            total_db_time,
            total_db_time / total_sync_time * 100 if total_sync_time > 0 else 0,
        )
        _logger.info(
            "   Total Python time:           %.3f ms (%.1f%%)",
            total_python_time,
            (total_python_time / total_sync_time * 100 if total_sync_time > 0 else 0),
        )

        # Estimate potential savings from async
        # Conservative: assume 50% of DB wait time could be parallelized
        potential_savings = total_db_time * 0.5
        _logger.info(
            "\n   POTENTIAL ASYNC SAVINGS (conservative 50%% parallelization):"
        )
        _logger.info("   - Estimated time saved: %.3f ms", potential_savings)
        _logger.info(
            "   - Potential speedup:    %.1f%%",
            (potential_savings / total_sync_time * 100 if total_sync_time > 0 else 0),
        )

        # 6. Recommendations
        _logger.info("\n6. RECOMMENDATIONS:")
        if high_db_ratio:
            _logger.info(
                "   - %d operations spend >60%% time waiting for DB",
                len(high_db_ratio),
            )
            _logger.info("     These are prime candidates for async optimization")
        if independent_tests:
            _logger.info(
                "   - Independent multi-table reads could benefit from parallel execution"
            )
        _logger.info("   - Consider psycopg3 migration for hybrid sync/async support")

        _logger.info("\n" + "=" * 80)
        _logger.info("[SQL_BENCHMARK] Benchmark complete.")
        _logger.info("=" * 80)
