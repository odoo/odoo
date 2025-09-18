"""
PyO3 Acceleration Candidate Benchmark Suite.

Profiles pure-Python hot paths to identify candidates for Rust PyO3 extensions.
Each benchmark isolates a specific function/operation with clean input/output
boundaries and no ORM callbacks.

Candidates profiled:
1. safe_eval — bytecode validation (assert_valid_codeobj, compile)
2. Iteration utilities — groupby, unique, partition, topological_sort
3. OrderedSet — creation, intersection, union, membership
4. frozendict — creation, hashing
5. HTML/text processing — plaintext2html, html_sanitize

Run with:
    > ./odoo.log && ./core/odoo-bin -c ./conf/odoo.conf -d test_db \
        --test-tags '/test_performance:TestPyO3Candidates' \
        -u test_performance --stop-after-init --workers=0
"""

import gc
import logging

from odoo.tests.benchmark import PerfTimer
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)

N = 2000
WARMUP = 200
TAG = "[PYO3_BENCH]"


def _log_result(timer: PerfTimer, name: str):
    stats = timer.stats(name, warmup=0)
    _logger.info("%s %s", TAG, stats.get("summary", name))
    return stats


@tagged("standard", "pyo3_benchmark")
class TestPyO3Candidates(TransactionCase):
    """Profile pure-Python hot paths for PyO3 acceleration candidates."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.all_stats: list[dict] = []

    def setUp(self):
        super().setUp()
        gc.collect()

    def _bench(self, name: str, func, n: int = N, warmup: int = WARMUP) -> dict:
        timer = PerfTimer()
        for _ in range(warmup):
            func()
        for _ in range(n):
            timer.start()
            func()
            timer.stop()
        stats = _log_result(timer, name)
        self.all_stats.append(stats)
        return stats

    # =====================================================================
    # 1. safe_eval — bytecode validation
    # =====================================================================

    def test_01_safe_eval_compile(self):
        """compile() for a typical domain expression string."""
        from odoo.tools.safe_eval import compile_codeobj

        expr = "[(name, '=', 'test'), (value, '>', 50)]"
        self._bench("safe_eval: compile (domain expr)", lambda: compile_codeobj(expr))

    def test_01_safe_eval_validate(self):
        """assert_valid_codeobj for a compiled expression (cache miss)."""
        from odoo.tools.safe_eval import (
            _SAFE_OPCODES,
            _validated_bytecode_cache,
            assert_valid_codeobj,
            compile_codeobj,
        )

        # Use varying expressions to defeat the cache
        exprs = [f"x + {i}" for i in range(N + WARMUP)]
        codes = [compile_codeobj(e) for e in exprs]
        idx = [0]

        def bench():
            _validated_bytecode_cache.clear()
            assert_valid_codeobj(_SAFE_OPCODES, codes[idx[0]], exprs[idx[0]])
            idx[0] += 1

        self._bench("safe_eval: validate bytecode (cold)", bench)

    def test_01_safe_eval_validate_cached(self):
        """assert_valid_codeobj with cache hit."""
        from odoo.tools.safe_eval import (
            _SAFE_OPCODES,
            assert_valid_codeobj,
            compile_codeobj,
        )

        expr = "partner_id and name == 'test' or value > 50"
        code = compile_codeobj(expr)
        # warm the cache
        assert_valid_codeobj(_SAFE_OPCODES, code, expr)
        self._bench(
            "safe_eval: validate bytecode (cached)",
            lambda: assert_valid_codeobj(_SAFE_OPCODES, code, expr),
        )

    def test_01_safe_eval_full(self):
        """Full safe_eval() call with a realistic expression."""
        from odoo.tools.safe_eval import safe_eval

        ctx = {"name": "test", "value": 42, "active": True}
        expr = "name == 'test' and value > 10 and active"
        self._bench(
            "safe_eval: full eval (bool expr)",
            lambda: safe_eval(expr, dict(ctx)),
        )

    def test_02_safe_eval_complex(self):
        """safe_eval with a more complex expression (list comprehension)."""
        from odoo.tools.safe_eval import safe_eval

        ctx = {"records": list(range(100))}
        expr = "[x for x in records if x > 50]"
        self._bench(
            "safe_eval: list comprehension",
            lambda: safe_eval(expr, dict(ctx)),
        )

    def test_02_safe_eval_domain_str(self):
        """safe_eval of a domain string (most common use case)."""
        from odoo.tools.safe_eval import safe_eval

        ctx = {"uid": 2, "active_id": 1}
        expr = "[('user_id', '=', uid), ('active', '=', True)]"
        self._bench(
            "safe_eval: domain string eval",
            lambda: safe_eval(expr, dict(ctx)),
        )

    # =====================================================================
    # 2. Iteration utilities
    # =====================================================================

    def test_10_groupby_small(self):
        """groupby on 20 items with 5 groups."""
        from odoo.tools import groupby

        items = [(i % 5, f"item_{i}") for i in range(20)]
        self._bench(
            "groupby: 20 items / 5 groups",
            lambda: list(groupby(items, key=lambda x: x[0])),
        )

    def test_10_groupby_large(self):
        """groupby on 500 items with 10 groups."""
        from odoo.tools import groupby

        items = [(i % 10, f"item_{i}") for i in range(500)]
        self._bench(
            "groupby: 500 items / 10 groups",
            lambda: list(groupby(items, key=lambda x: x[0])),
        )

    def test_11_unique_small(self):
        """unique on 50 items with ~25 duplicates."""
        from odoo.tools import unique

        items = list(range(25)) * 2
        self._bench("unique: 50 items (25 unique)", lambda: list(unique(items)))

    def test_11_unique_large(self):
        """unique on 1000 items with ~200 unique."""
        from odoo.tools import unique

        items = list(range(200)) * 5
        self._bench("unique: 1000 items (200 unique)", lambda: list(unique(items)))

    def test_12_partition_small(self):
        """partition on 50 items."""
        from odoo.tools import partition

        items = list(range(50))
        self._bench(
            "partition: 50 items",
            lambda: partition(lambda x: x > 25, items),
        )

    def test_12_partition_large(self):
        """partition on 500 items."""
        from odoo.tools import partition

        items = list(range(500))
        self._bench(
            "partition: 500 items",
            lambda: partition(lambda x: x > 250, items),
        )

    def test_13_topological_sort_small(self):
        """topological_sort on 10 nodes."""
        from odoo.tools import topological_sort

        deps = {
            "a": [],
            "b": ["a"],
            "c": ["a"],
            "d": ["b", "c"],
            "e": ["d"],
            "f": ["c"],
            "g": ["e", "f"],
            "h": ["g"],
            "i": ["h"],
            "j": ["i"],
        }
        self._bench("topo_sort: 10 nodes", lambda: topological_sort(deps))

    def test_13_topological_sort_large(self):
        """topological_sort on 100 nodes (linear chain)."""
        from odoo.tools import topological_sort

        deps = {f"n{i}": [f"n{i-1}"] if i > 0 else [] for i in range(100)}
        self._bench("topo_sort: 100 nodes (chain)", lambda: topological_sort(deps))

    def test_13_topological_sort_wide(self):
        """topological_sort on 100 nodes (wide graph — module loading pattern)."""
        from odoo.tools import topological_sort

        # Simulates module dependency graph: base deps, several mid-level, many leaves
        deps = {"base": []}
        for i in range(10):
            deps[f"mid_{i}"] = ["base"]
        for i in range(90):
            deps[f"leaf_{i}"] = [f"mid_{i % 10}"]
        self._bench("topo_sort: 100 nodes (wide)", lambda: topological_sort(deps))

    # =====================================================================
    # 3. OrderedSet
    # =====================================================================

    def test_20_orderedset_create_small(self):
        """OrderedSet creation from 10 items."""
        from odoo.tools import OrderedSet

        items = list(range(10))
        self._bench("OrderedSet: create(10)", lambda: OrderedSet(items))

    def test_20_orderedset_create_large(self):
        """OrderedSet creation from 500 items."""
        from odoo.tools import OrderedSet

        items = list(range(500))
        self._bench("OrderedSet: create(500)", lambda: OrderedSet(items))

    def test_20_orderedset_create_with_dupes(self):
        """OrderedSet creation from 500 items with duplicates."""
        from odoo.tools import OrderedSet

        items = list(range(100)) * 5
        self._bench("OrderedSet: create(500, 100 unique)", lambda: OrderedSet(items))

    def test_21_orderedset_contains(self):
        """OrderedSet membership test (500 lookups)."""
        from odoo.tools import OrderedSet

        s = OrderedSet(range(500))
        lookups = list(range(0, 1000, 2))  # 500 lookups, half hits

        def bench():
            for x in lookups:
                x in s

        self._bench("OrderedSet: 500 contains checks", bench)

    def test_21_orderedset_intersection(self):
        """OrderedSet intersection of two 200-element sets."""
        from odoo.tools import OrderedSet

        a = OrderedSet(range(200))
        b = OrderedSet(range(100, 300))
        self._bench("OrderedSet: intersect(200, 200)", lambda: a & b)

    def test_21_orderedset_union(self):
        """OrderedSet union of two 200-element sets."""
        from odoo.tools import OrderedSet

        a = OrderedSet(range(200))
        b = OrderedSet(range(100, 300))
        self._bench("OrderedSet: union(200, 200)", lambda: a | b)

    def test_21_orderedset_difference(self):
        """OrderedSet difference of two 200-element sets."""
        from odoo.tools import OrderedSet

        a = OrderedSet(range(200))
        b = OrderedSet(range(100, 300))
        self._bench("OrderedSet: diff(200, 200)", lambda: a - b)

    # =====================================================================
    # 4. frozendict
    # =====================================================================

    def test_30_frozendict_create(self):
        """frozendict creation from a typical env.context dict."""
        from odoo.tools import frozendict

        ctx = {
            "lang": "en_US",
            "tz": "America/Mexico_City",
            "uid": 2,
            "active_test": True,
            "allowed_company_ids": [1],
            "default_type": "out_invoice",
        }
        self._bench("frozendict: create(6 keys)", lambda: frozendict(ctx))

    def test_30_frozendict_hash(self):
        """frozendict hash computation."""
        from odoo.tools import frozendict

        fd = frozendict(
            {
                "lang": "en_US",
                "tz": "America/Mexico_City",
                "uid": 2,
                "active_test": True,
            }
        )

        # Force hash recomputation by creating new instances
        def bench():
            f = frozendict.__new__(frozendict, fd)
            hash(f)

        self._bench("frozendict: hash(4 keys)", bench)

    def test_31_frozendict_lookup(self):
        """frozendict key lookup (10 lookups)."""
        from odoo.tools import frozendict

        fd = frozendict(
            {
                "lang": "en_US",
                "tz": "America/Mexico_City",
                "uid": 2,
                "active_test": True,
                "default_type": "out_invoice",
            }
        )
        keys = list(fd.keys()) * 2  # 10 lookups

        def bench():
            for k in keys:
                fd[k]

        self._bench("frozendict: 10 key lookups", bench)

    # =====================================================================
    # 5. HTML / text processing
    # =====================================================================

    def test_40_plaintext2html_short(self):
        """plaintext2html on a short text."""
        from odoo.tools import plaintext2html

        text = "Hello, this is a test.\nSecond line here."
        self._bench("plaintext2html: 2 lines", lambda: plaintext2html(text))

    def test_40_plaintext2html_long(self):
        """plaintext2html on a longer text."""
        from odoo.tools import plaintext2html

        text = "\n".join(
            f"Line {i}: some content here with https://example.com/page/{i}"
            for i in range(50)
        )
        self._bench("plaintext2html: 50 lines + URLs", lambda: plaintext2html(text))

    def test_41_html_sanitize_short(self):
        """html_sanitize on a short HTML fragment."""
        from odoo.tools import html_sanitize

        html = '<p>Hello <b>world</b></p><script>alert("xss")</script>'
        self._bench("html_sanitize: short fragment", lambda: html_sanitize(html))

    def test_41_html_sanitize_long(self):
        """html_sanitize on a longer HTML (email body)."""
        from odoo.tools import html_sanitize

        html = (
            "<div>"
            + "".join(
                f'<p>Paragraph {i} with <a href="https://example.com/{i}">link</a> '
                f'and <img src="data:image/png;base64,abc"/> and <b>bold</b></p>'
                for i in range(20)
            )
            + "</div>"
        )
        self._bench("html_sanitize: 20-paragraph email", lambda: html_sanitize(html))

    # =====================================================================
    # 6. Miscellaneous hot utilities
    # =====================================================================

    def test_50_clean_context(self):
        """clean_context — strip default_ and search_ keys."""
        from odoo.tools import clean_context

        ctx = {
            "lang": "en_US",
            "tz": "UTC",
            "uid": 2,
            "default_name": "test",
            "default_type": "out_invoice",
            "search_default_filter": True,
            "active_test": True,
            "allowed_company_ids": [1],
            "active_id": 1,
            "active_ids": [1],
        }
        self._bench("clean_context: 10 keys", lambda: clean_context(ctx))

    def test_51_str2bool(self):
        """str2bool — convert string to boolean (used in import)."""
        from odoo.tools import str2bool

        values = ["true", "false", "1", "0", "yes", "no", "True", "False"]

        def bench():
            for v in values:
                str2bool(v)

        self._bench("str2bool: 8 conversions", bench)

    # =====================================================================
    # SUMMARY
    # =====================================================================

    def test_99_summary(self):
        """Print summary table sorted by median time."""
        if not self.all_stats:
            return

        _logger.info("\n" + "=" * 110)
        _logger.info("%s SUMMARY — sorted by p50 (descending)", TAG)
        _logger.info("=" * 110)
        _logger.info(
            "%-55s %10s %10s %10s %6s",
            "Benchmark",
            "p50 (µs)",
            "p95 (µs)",
            "mean (µs)",
            "CV",
        )
        _logger.info("-" * 110)

        by_p50 = sorted(self.all_stats, key=lambda s: s.get("p50_us", 0), reverse=True)
        for s in by_p50:
            _logger.info(
                "%-55s %10.1f %10.1f %10.1f %6.2f",
                s.get("name", "?")[:55],
                s.get("p50_us", 0),
                s.get("p95_us", 0),
                s.get("mean_us", 0),
                s.get("cv", 0),
            )

        # Group by candidate
        categories = {
            "safe_eval": [
                s for s in self.all_stats if "safe_eval" in s.get("name", "")
            ],
            "Iteration (groupby/unique/partition/topo)": [
                s
                for s in self.all_stats
                if any(
                    k in s.get("name", "")
                    for k in ("groupby", "unique", "partition", "topo_sort")
                )
            ],
            "OrderedSet": [
                s for s in self.all_stats if "OrderedSet" in s.get("name", "")
            ],
            "frozendict": [
                s for s in self.all_stats if "frozendict" in s.get("name", "")
            ],
            "HTML/text": [
                s
                for s in self.all_stats
                if any(k in s.get("name", "") for k in ("plaintext", "html_sanitize"))
            ],
        }
        _logger.info("\n" + "-" * 110)
        _logger.info("%s CANDIDATE RANKING (by max p50):", TAG)
        ranked = sorted(
            categories.items(),
            key=lambda kv: max((s.get("p50_us", 0) for s in kv[1]), default=0),
            reverse=True,
        )
        for cat, stats in ranked:
            if stats:
                avg_p50 = sum(s.get("p50_us", 0) for s in stats) / len(stats)
                max_p50 = max(s.get("p50_us", 0) for s in stats)
                _logger.info(
                    "  %-45s  avg p50=%8.1f µs  max p50=%8.1f µs  (%d tests)",
                    cat,
                    avg_p50,
                    max_p50,
                    len(stats),
                )

        _logger.info("=" * 110)
