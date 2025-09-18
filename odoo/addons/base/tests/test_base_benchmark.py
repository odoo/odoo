"""Benchmark suite for base module optimized code paths.

Measures absolute timing with statistical analysis for manual profiling.
Not intended for CI — use test_base_perf_regression.py for query count gates.

Run with:
    > ./odoo.log && ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
        --test-tags '/base:TestBaseBenchmark' -u base \
        --stop-after-init --workers=0
    grep "BASE_BENCHMARK" ./odoo.log
"""

import gc
import logging

from odoo.tests.benchmark import BenchmarkStats, run_benchmark
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

DEFAULT_ITERATIONS = 30
WARMUP_ITERATIONS = 5


@tagged("post_install", "-at_install", "base_benchmark")
class TestBaseBenchmark(TransactionCase):
    """Benchmark suite for base module N+1-optimized methods."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_results: list[BenchmarkStats] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _run_benchmark(
        self,
        name: str,
        func,
        *,
        iterations: int = DEFAULT_ITERATIONS,
        warmup: int = WARMUP_ITERATIONS,
        setup=None,
        invalidate_cache: bool = True,
    ) -> BenchmarkStats:
        """Run a benchmark with statistical analysis and log results."""
        stats = run_benchmark(
            name,
            func,
            iterations=iterations,
            warmup=warmup,
            setup=setup,
            invalidate=self.env.invalidate_all if invalidate_cache else None,
        )
        self.all_results.append(stats)
        _logger.info("[BASE_BENCHMARK] %s", stats.summary())
        return stats

    # ------------------------------------------------------------------
    # _check_path: path constraint on window actions
    # ------------------------------------------------------------------

    def test_bench_check_path(self):
        """Benchmark: path constraint validation on 50 window actions."""
        actions = self.env["ir.actions.act_window"].create(
            [
                {
                    "name": f"BenchWindow_{i}",
                    "res_model": "res.partner",
                    "path": f"bench-path-{i}",
                }
                for i in range(50)
            ]
        )

        self._run_benchmark(
            "check_path (50 actions)",
            actions._check_path,
        )

    # ------------------------------------------------------------------
    # _check_barcode_unicity: barcode constraint on partners
    # ------------------------------------------------------------------

    def test_bench_check_barcode(self):
        """Benchmark: barcode uniqueness constraint on 50 partners."""
        partners = self.env["res.partner"].create(
            [
                {"name": f"BenchBC_{i}", "barcode": f"BENCH-BC-{i:04d}"}
                for i in range(50)
            ]
        )

        self._run_benchmark(
            "check_barcode (50 partners)",
            partners._check_barcode_unicity,
        )

    # ------------------------------------------------------------------
    # _get_bindings: action binding loading
    # ------------------------------------------------------------------

    def test_bench_get_bindings(self):
        """Benchmark: cold-cache binding load for res.partner."""
        Actions = self.env["ir.actions.actions"]
        registry = self.registry

        def bench():
            registry.clear_all_caches()
            Actions._get_bindings("res.partner")

        self._run_benchmark(
            "get_bindings cold (res.partner)",
            bench,
            invalidate_cache=True,
        )

    # ------------------------------------------------------------------
    # _compute_partner_share: batch share computation
    # ------------------------------------------------------------------

    def test_bench_compute_partner_share(self):
        """Benchmark: partner_share computation on 100 partners."""
        partners = self.env["res.partner"].create(
            [{"name": f"BenchShare_{i}"} for i in range(100)]
        )

        self._run_benchmark(
            "compute_partner_share (100 partners)",
            partners._compute_partner_share,
        )

    # ------------------------------------------------------------------
    # _compute_same_vat_partner_id: VAT duplicate detection
    # ------------------------------------------------------------------

    def test_bench_compute_same_vat(self):
        """Benchmark: same VAT compute on 20 partners with unique VATs."""
        partners = self.env["res.partner"].create(
            [
                {
                    "name": f"BenchVAT_{i}",
                    "vat": f"BE{i:010d}",
                    "country_id": self.env.ref("base.be").id,
                }
                for i in range(20)
            ]
        )

        self._run_benchmark(
            "compute_same_vat (20 partners)",
            partners._compute_same_vat_partner_id,
        )

    # ------------------------------------------------------------------
    # _compute_is_public: public partner detection
    # ------------------------------------------------------------------

    def test_bench_compute_is_public(self):
        """Benchmark: is_public computation on 50 partners."""
        partners = self.env["res.partner"].create(
            [{"name": f"BenchPublic_{i}"} for i in range(50)]
        )

        self._run_benchmark(
            "compute_is_public (50 partners)",
            partners._compute_is_public,
        )

    # ------------------------------------------------------------------
    # _compute_main_user_id: main user resolution
    # ------------------------------------------------------------------

    def test_bench_compute_main_user_id(self):
        """Benchmark: main_user_id computation on 50 partners."""
        partners = self.env["res.partner"].create(
            [{"name": f"BenchMainUser_{i}"} for i in range(50)]
        )

        self._run_benchmark(
            "compute_main_user_id (50 partners)",
            partners._compute_main_user_id,
        )

    # ------------------------------------------------------------------
    # _selection_target_model: cached model selection
    # ------------------------------------------------------------------

    def test_bench_selection_target_model(self):
        """Benchmark: _selection_target_model on warm cache."""
        ServerAction = self.env["ir.actions.server"]
        # Warm the cache first
        ServerAction._selection_target_model()

        self._run_benchmark(
            "selection_target_model (warm cache)",
            ServerAction._selection_target_model,
            iterations=50,
            invalidate_cache=False,
        )

    # ------------------------------------------------------------------
    # Company init: paperformat initialization
    # ------------------------------------------------------------------

    def test_bench_company_init(self):
        """Benchmark: company init (paperformat default)."""
        Company = self.env["res.company"]

        self._run_benchmark(
            "company_init (paperformat)",
            Company.init,
        )

    # ------------------------------------------------------------------
    # ir.model: batch view_ids, inherited_models, count
    # ------------------------------------------------------------------

    def test_bench_ir_model_view_ids(self):
        """Benchmark: batch view_ids computation on 50 models."""
        models = self.env["ir.model"].search([], limit=50)

        self._run_benchmark(
            "ir_model_view_ids (50 models)",
            models._view_ids,
        )

    def test_bench_ir_model_inherited_models(self):
        """Benchmark: batch inherited_models computation on 50 models."""
        models = self.env["ir.model"].search([], limit=50)

        self._run_benchmark(
            "ir_model_inherited_models (50 models)",
            models._inherited_models,
        )

    def test_bench_ir_model_compute_count(self):
        """Benchmark: batch record count via UNION ALL on 50 models."""
        models = self.env["ir.model"].search([], limit=50)

        self._run_benchmark(
            "ir_model_compute_count (50 models)",
            models._compute_count,
        )

    # ------------------------------------------------------------------
    # ir.model.fields: batch display_name
    # ------------------------------------------------------------------

    def test_bench_ir_model_fields_display_name(self):
        """Benchmark: display_name with ormcache pre-warming on 100 fields."""
        ir_fields = self.env["ir.model.fields"].search([], limit=100)

        def bench():
            # Access display_name to trigger compute via ORM
            ir_fields.mapped("display_name")

        self._run_benchmark(
            "ir_model_fields_display_name (100 fields)",
            bench,
        )
