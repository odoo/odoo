import gc
import json
import logging
import os
import platform
import statistics
import subprocess
from datetime import datetime
from pathlib import Path

import odoo
from odoo.tests.benchmark import BenchmarkCase
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

DEFAULT_ITERATIONS = 50
WARMUP_ITERATIONS = 5


@tagged("standard", "orm_benchmark")
class TestORMBenchmark(BenchmarkCase, TransactionCase):
    benchmark_log_prefix = "ORM_BENCHMARK"
    benchmark_iterations = DEFAULT_ITERATIONS
    benchmark_warmup = WARMUP_ITERATIONS

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env["test_performance.base"]
        cls.SimpleModel = cls.env["test_performance.simple.minded"]

        cls._create_test_data()

    @classmethod
    def _create_test_data(cls):
        existing = cls.Model.search([("name", "like", "ORMBench%")])
        if 0 < len(existing) < 100:
            existing.unlink()
            existing = cls.Model.browse()
        if len(existing) < 100:
            _logger.info("[ORM_BENCHMARK] Creating test data...")
            cls.Model.create(
                [{"name": f"ORMBench_{i}", "value": i} for i in range(100)]
            )
            parent = cls.SimpleModel.create({"name": "BenchParent"})
            cls.SimpleModel.create(
                [{"name": f"BenchChild_{i}", "parent_id": parent.id} for i in range(50)]
            )
            _logger.info("[ORM_BENCHMARK] Test data created.")

    def setUp(self):
        super().setUp()
        gc.collect()
        self.Model.search_count([])

    @staticmethod
    def _append_to_ledger(export_data):
        # a reading nobody keeps is a reading nobody can compare: with
        # ODOO_BENCHMARK_LEDGER naming a file, every run appends one JSON line
        # carrying the commit, so a release knows its costs against the last
        path = os.environ.get("ODOO_BENCHMARK_LEDGER")
        if not path:
            return
        try:
            commit = subprocess.run(
                [
                    "git",
                    "-C",
                    str(Path(odoo.__file__).parent),
                    "rev-parse",
                    "--short",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            ).stdout.strip()
        except OSError, subprocess.SubprocessError:
            commit = None
        line = {
            "timestamp": export_data["timestamp"],
            "commit": commit,
            "python": platform.python_version(),
            "summary": export_data["summary"],
            "results": {
                stat["name"]: {
                    key: stat[key]
                    for key in ("mean_us", "median_us", "p95_us", "query_count")
                    if key in stat
                }
                for stat in export_data["results"]
            },
        }
        with Path(path).open("a", encoding="utf-8") as ledger:
            ledger.write(json.dumps(line, default=str) + "\n")
        _logger.info("[ORM_BENCHMARK] appended to %s", path)

    def test_01_browse_single(self):
        record = self.Model.search([], limit=1)
        record_id = record.id

        def bench():
            self.Model.browse(record_id)

        self._run_benchmark(
            "browse() single ID", bench, iterations=100, invalidate_cache=False
        )

    def test_01_browse_multiple(self):
        records = self.Model.search([], limit=50)
        ids = records.ids

        def bench():
            self.Model.browse(ids)

        self._run_benchmark(
            "browse() 50 IDs", bench, iterations=100, invalidate_cache=False
        )

    def test_02_recordset_iteration(self):
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
        records = self.Model.search([], limit=100)

        def bench():
            _ = records[:10]
            _ = records[10:20]
            _ = records[-10:]

        self._run_benchmark(
            "Recordset slicing", bench, iterations=100, invalidate_cache=False
        )

    def test_10_recordset_union(self):
        records1 = self.Model.search([], limit=50)
        records2 = self.Model.search([], limit=50, offset=25)

        def bench():
            _ = records1 | records2

        self._run_benchmark(
            "Recordset union (|)", bench, iterations=100, invalidate_cache=False
        )

    def test_10_recordset_intersection(self):
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
        records = self.Model.search([], limit=100)
        _ = records.mapped("value")

        def bench():
            records.filtered(lambda r: r.value > 50)

        self._run_benchmark(
            "filtered() lambda (100 records)", bench, invalidate_cache=False
        )

    def test_11_filtered_field(self):
        records = self.SimpleModel.search([], limit=100)
        _ = records.mapped("active")

        def bench():
            records.filtered("active")

        self._run_benchmark(
            "filtered() field name (100 records)", bench, invalidate_cache=False
        )

    def test_12_mapped_field(self):
        records = self.Model.search([], limit=100)

        def bench():
            records.mapped("name")

        self._run_benchmark("mapped() single field (100 records)", bench)

    def test_12_mapped_relation(self):
        records = self.Model.search([("partner_id", "!=", False)], limit=50)

        def bench():
            records.mapped("partner_id.name")

        self._run_benchmark("mapped() through relation (50 records)", bench)

    def test_13_sorted_field(self):
        records = self.Model.search([], limit=100)
        _ = records.mapped("name")

        def bench():
            records.sorted("name")

        self._run_benchmark(
            "sorted() by field (100 records)", bench, invalidate_cache=False
        )

    def test_13_sorted_lambda(self):
        records = self.Model.search([], limit=100)
        _ = records.mapped("value")

        def bench():
            records.sorted(lambda r: r.value)

        self._run_benchmark(
            "sorted() lambda (100 records)", bench, invalidate_cache=False
        )

    def test_14_exists(self):
        records = self.Model.search([], limit=100)

        def bench():
            records.exists()

        self._run_benchmark("exists() (100 records)", bench)

    def test_20_field_access_cached(self):
        record = self.Model.search([], limit=1)
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
        record = self.Model.search([], limit=1)

        def bench():
            _ = record.name

        self._run_benchmark("Field access (uncached)", bench)

    def test_21_field_getitem_vs_getattr(self):
        record = self.Model.search([], limit=1)
        _ = record.name

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
        record = self.Model.search([], limit=1)

        def bench():
            _ = record.name
            _ = record.value
            _ = record.partner_id

        self._run_benchmark("Multi-field access (3 fields)", bench)

    def test_23_relational_field_access(self):
        record = self.Model.search([("partner_id", "!=", False)], limit=1)

        def bench():
            _ = record.partner_id.name

        self._run_benchmark("Many2one field access", bench)

    def test_24_one2many_access(self):
        parent = self.SimpleModel.search([("child_ids", "!=", False)], limit=1)

        def bench():
            _ = list(parent.child_ids)

        self._run_benchmark("One2many field access", bench)

    def test_30_with_context(self):
        records = self.Model.search([], limit=50)

        def bench():
            records.with_context(key="value")

        self._run_benchmark(
            "with_context()", bench, iterations=100, invalidate_cache=False
        )

    def test_30_with_user(self):
        records = self.Model.search([], limit=50)
        user = self.env.user

        def bench():
            records.with_user(user)

        self._run_benchmark(
            "with_user()", bench, iterations=100, invalidate_cache=False
        )

    def test_31_sudo(self):
        records = self.Model.search([], limit=50)

        def bench():
            records.sudo()

        self._run_benchmark("sudo()", bench, iterations=100, invalidate_cache=False)

    def test_32_env_ref(self):

        def bench():
            self.env.ref("base.user_admin")

        self._run_benchmark("env.ref()", bench, iterations=100, invalidate_cache=False)

    def test_40_cache_invalidate_recordset(self):
        records = self.Model.search([], limit=100)
        _ = records.mapped("name")

        def bench():
            records.invalidate_recordset()

        self._run_benchmark(
            "invalidate_recordset() (100 records)",
            bench,
            invalidate_cache=False,
        )

    def test_40_cache_invalidate_model(self):
        records = self.Model.search([], limit=100)
        _ = records.mapped("name")

        def bench():
            records.invalidate_model()

        self._run_benchmark("invalidate_model()", bench, invalidate_cache=False)

    def test_41_prefetch_trigger(self):
        records = self.Model.search([], limit=100)

        def bench():
            _ = records[0].name

        self._run_benchmark("Prefetch trigger (100 records)", bench)

    def test_50_computed_simple(self):
        records = self.Model.search([], limit=50)

        def bench():
            _ = records.mapped("value_pc")

        self._run_benchmark("Computed field (simple)", bench)

    def test_51_computed_with_depends(self):
        records = self.Model.search([], limit=50)

        def bench():
            _ = records.mapped("display_name")

        self._run_benchmark("Computed field (display_name)", bench)

    def test_60_write_single_field(self):
        record = self.Model.search([], limit=1)

        def bench():
            record.write({"value": 42})

        self._run_benchmark("write() single field", bench, iterations=30)

    def test_60_write_multiple_fields(self):
        record = self.Model.search([], limit=1)

        def bench():
            record.write({"name": "Updated", "value": 42})

        self._run_benchmark("write() multiple fields", bench, iterations=30)

    def test_61_field_assignment(self):
        record = self.Model.search([], limit=1)

        def bench():
            record.value = 42

        self._run_benchmark("Field assignment", bench, iterations=30)

    def test_62_batch_write(self):
        records = self.Model.search([], limit=50)

        def bench():
            records.write({"value": 42})

        self._run_benchmark("Batch write() (50 records)", bench, iterations=20)

    def test_70_create_single(self):
        counter = [0]

        def bench():
            counter[0] += 1
            self.Model.create({"name": f"BenchCreate_{counter[0]}"})

        self._run_benchmark("create() single record", bench, iterations=20)

    def test_70_create_batch(self):
        counter = [0]

        def bench():
            counter[0] += 1
            self.Model.create(
                [{"name": f"BatchCreate_{counter[0]}_{i}"} for i in range(10)]
            )

        self._run_benchmark("create() batch (10 records)", bench, iterations=15)

    def test_80_search_simple(self):

        def bench():
            self.Model.search([("value", ">", 50)], limit=50)

        self._run_benchmark("search() simple domain", bench)

    def test_80_search_empty(self):

        def bench():
            self.Model.search([], limit=50)

        self._run_benchmark("search() empty domain", bench)

    def test_81_search_count(self):

        def bench():
            self.Model.search_count([("value", ">", 50)])

        self._run_benchmark("search_count()", bench)

    def test_82_search_read(self):

        def bench():
            self.Model.search_read(
                [("value", ">", 50)], fields=["name", "value"], limit=50
            )

        self._run_benchmark("search_read()", bench)

    def test_90_orm_vs_raw_read(self):
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
        orm_stat = next(
            s for s in self.all_results if s.name == "ORM read() (100 records)"
        )
        raw_stat = next(
            s for s in self.all_results if s.name == "Raw SQL SELECT (100 records)"
        )

        overhead = orm_stat.mean_us - raw_stat.mean_us
        overhead_pct = (
            (overhead / orm_stat.mean_us) * 100 if orm_stat.mean_us > 0 else 0
        )

        _logger.info(
            "[ORM_BENCHMARK] ORM OVERHEAD ANALYSIS:\n"
            "  ORM time:      %.1f µs\n"
            "  Raw SQL time:  %.1f µs\n"
            "  ORM overhead:  %.1f µs (%.1f%%)",
            orm_stat.mean_us,
            raw_stat.mean_us,
            overhead,
            overhead_pct,
        )

    def test_99_generate_summary(self):
        if not self.all_results:
            _logger.info("[ORM_BENCHMARK] No results to summarize.")
            return

        _logger.info("\n%s", "=" * 80)
        _logger.info("[ORM_BENCHMARK] FINAL SUMMARY")
        _logger.info("=" * 80)

        sorted_by_overhead = sorted(
            self.all_results, key=lambda x: x.python_time_us, reverse=True
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

        _logger.info("\n[ORM_BENCHMARK] SLOWEST OPERATIONS:")
        self.log_benchmark_summary()

        zero_query_ops = [s for s in self.all_results if s.query_count_mean == 0]
        if zero_query_ops:
            _logger.info("\n[ORM_BENCHMARK] PURE PYTHON OVERHEAD (0 queries):")
            _logger.info("-" * 70)
            for stat in sorted(zero_query_ops, key=lambda x: x.mean_us, reverse=True)[
                :10
            ]:
                _logger.info("  %-40s %10.1f µs", stat.name[:40], stat.mean_us)

        total_overhead = sum(s.python_time_us for s in self.all_results)
        total_db_time = sum(s.db_time_us for s in self.all_results)
        avg_python_ratio = statistics.mean(s.python_ratio for s in self.all_results)

        _logger.info("\n[ORM_BENCHMARK] AGGREGATE STATISTICS:")
        _logger.info("  Total tests:          %d", len(self.all_results))
        _logger.info("  Total ORM overhead:   %.1f µs", total_overhead)
        _logger.info("  Total DB time:        %.1f µs", total_db_time)
        _logger.info("  Average overhead %%:   %.1f%%", avg_python_ratio * 100)

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
        self._append_to_ledger(export_data)

        _logger.info("\n[ORM_BENCHMARK] Benchmark complete.")
