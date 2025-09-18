"""Statistical benchmarks for web module operations.

Uses ``run_benchmark()`` from ``odoo.tests.benchmark`` to produce
timing statistics (mean, median, p95, DB vs Python split) for key
web module code paths.  Results are logged with the ``[WEB_BENCHMARK]``
tag for easy extraction.

Run with:
    > ./odoo.log && ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
        --test-tags 'web_benchmark' -u web \
        --stop-after-init --workers=0
    grep "WEB_BENCHMARK" ./odoo.log
"""

import logging

from odoo.tests.benchmark import BenchmarkStats, run_benchmark
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

DEFAULT_ITERATIONS = 30
WARMUP_ITERATIONS = 5


@tagged("post_install", "-at_install", "web_benchmark")
class TestWebBenchmark(TransactionCase):
    """Statistical benchmarks for web module hot paths."""

    all_results: list[BenchmarkStats]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_results = []

        # Categories for many2many search panel benchmark
        cls.categories = cls.env["res.partner.category"].create(
            [{"name": f"BenchCat_{i}"} for i in range(5)]
        )

        cls.country_be = cls.env.ref("base.be")

        # 500 partners for scaling benchmarks
        cls.partners = cls.env["res.partner"].create(
            [
                {
                    "name": f"BenchPartner_{i:04d}",
                    "email": f"bench{i}@test.example.com",
                    "country_id": cls.country_be.id,
                    "category_id": [(6, 0, cls.categories[:3].ids)],
                    "type": "contact",
                }
                for i in range(500)
            ]
        )

        # Parent + 50 children for deep-spec benchmark
        cls.parent_partner = cls.env["res.partner"].create(
            {
                "name": "BenchParent",
                "country_id": cls.country_be.id,
            }
        )
        cls.env["res.partner"].create(
            [
                {
                    "name": f"BenchChild_{i}",
                    "parent_id": cls.parent_partner.id,
                    "country_id": cls.country_be.id,
                }
                for i in range(50)
            ]
        )

    @classmethod
    def tearDownClass(cls):
        if cls.all_results:
            summary = "\n".join(s.summary() for s in cls.all_results)
            _logger.info("[WEB_BENCHMARK] ===== SUMMARY =====\n%s", summary)
        super().tearDownClass()

    def _run_benchmark(
        self,
        name,
        func,
        *,
        iterations=DEFAULT_ITERATIONS,
        warmup=WARMUP_ITERATIONS,
        setup=None,
        invalidate_cache=True,
    ):
        """Run benchmark and log results."""
        stats = run_benchmark(
            name,
            func,
            iterations=iterations,
            warmup=warmup,
            setup=setup,
            invalidate=self.env.invalidate_all if invalidate_cache else None,
        )
        self.all_results.append(stats)
        _logger.info("[WEB_BENCHMARK] %s", stats.summary())
        return stats

    # ------------------------------------------------------------------
    # web_search_read scaling (10 / 100 / 500)
    # ------------------------------------------------------------------

    def test_bench_web_search_read_10(self):
        """Benchmark: web_search_read with limit=10."""
        Partners = self.env["res.partner"]
        domain = [("name", "like", "BenchPartner")]
        spec = {"name": {}, "email": {}, "country_id": {}}

        self._run_benchmark(
            "web_search_read (10 records)",
            lambda: Partners.web_search_read(domain, spec, limit=10),
        )

    def test_bench_web_search_read_100(self):
        """Benchmark: web_search_read with limit=100."""
        Partners = self.env["res.partner"]
        domain = [("name", "like", "BenchPartner")]
        spec = {"name": {}, "email": {}, "country_id": {}}

        self._run_benchmark(
            "web_search_read (100 records)",
            lambda: Partners.web_search_read(domain, spec, limit=100),
        )

    def test_bench_web_search_read_500(self):
        """Benchmark: web_search_read with limit=500."""
        Partners = self.env["res.partner"]
        domain = [("name", "like", "BenchPartner")]
        spec = {"name": {}, "email": {}, "country_id": {}}

        self._run_benchmark(
            "web_search_read (500 records)",
            lambda: Partners.web_search_read(domain, spec, limit=500),
        )

    # ------------------------------------------------------------------
    # web_read with deep nested specification
    # ------------------------------------------------------------------

    def test_bench_web_read_deep_spec(self):
        """Benchmark: web_read with nested many2one + many2many + x2many."""
        partners = self.partners[:100]
        spec = {
            "name": {},
            "country_id": {"fields": {"display_name": {}, "code": {}}},
            "category_id": {"fields": {"display_name": {}, "color": {}}},
        }

        self._run_benchmark(
            "web_read (deep spec, 100 records)",
            lambda: partners.web_read(spec),
        )

    # ------------------------------------------------------------------
    # web_read_group
    # ------------------------------------------------------------------

    def test_bench_web_read_group(self):
        """Benchmark: web_read_group grouped by country_id."""
        Partners = self.env["res.partner"]
        domain = [("name", "like", "BenchPartner")]

        self._run_benchmark(
            "web_read_group (by country_id)",
            lambda: Partners.web_read_group(
                domain,
                groupby=["country_id"],
                aggregates=["__count"],
            ),
        )

    # ------------------------------------------------------------------
    # web_name_search
    # ------------------------------------------------------------------

    def test_bench_web_name_search(self):
        """Benchmark: web_name_search with display_name-only spec (warm)."""
        Partners = self.env["res.partner"]
        spec = {"display_name": {}}

        self._run_benchmark(
            "web_name_search (warm, limit=100)",
            lambda: Partners.web_name_search("BenchPartner", spec, limit=100),
            invalidate_cache=False,
        )

    # ------------------------------------------------------------------
    # search_panel many2many with counters (N+1)
    # ------------------------------------------------------------------

    def test_bench_search_panel_m2m(self):
        """Benchmark: search_panel many2many with counters.

        Quantifies the N+1 cost of per-record search_count() in
        search_panel_select_multi_range (web_search_panel.py:318).
        """
        Partners = self.env["res.partner"]
        domain = [("name", "like", "BenchPartner")]

        self._run_benchmark(
            "search_panel_m2m_counters (5 categories)",
            lambda: Partners.search_panel_select_multi_range(
                "category_id",
                search_domain=domain,
                enable_counters=True,
            ),
        )

    # ------------------------------------------------------------------
    # web_save_multi (N+1: per-record write)
    # ------------------------------------------------------------------

    def test_bench_web_save_multi(self):
        """Benchmark: web_save_multi on 20 records.

        Quantifies the per-record write loop cost
        (web_read.py:113-114).
        """
        partners = self.partners[:20]
        vals_list = [{"name": f"BenchUpdate_{i}"} for i in range(20)]
        spec = {"name": {}}

        self._run_benchmark(
            "web_save_multi (20 records)",
            lambda: partners.web_save_multi(vals_list, spec),
        )
