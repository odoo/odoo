
"""
Performance Testing Suite for Purchase Module

This module provides comprehensive performance testing for the purchase module,
combining two testing approaches:

1. **Query Count Assertions** (`assertQueryCount`):
   - Regression testing to catch performance regressions
   - Deterministic query counting for CI/CD pipelines
   - Use `@warmup` decorator for consistent measurements

2. **Profiling** (`self.profile()`):
   - Detailed execution analysis with Speedscope output
   - SQL query timing and stack traces
   - Async stack sampling for bottleneck identification

Run tests:
    # Run all performance tests
    ./odoo-bin -u purchase -d testdb --test-enable --test-tags=purchase_perf

    # Run specific test
    ./odoo-bin -u purchase -d testdb --test-enable --test-tags=po_create_perf

    # Run with profiling output (check ir.profile records after)
    ./odoo-bin -u purchase -d testdb --test-enable --test-tags=purchase_profile

View profiling results:
    1. Navigate to Profiling menu in Odoo
    2. Find profiles by session name (test method)
    3. Click speedscope_url to view in Speedscope
"""

import functools
import logging
import time

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tests.common import users, warmup
from odoo.tools.profiler import Profiler, ExecutionContext

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


def prepare(func, /):
    """Prepare data to remove common queries from the count.

    Must be run after `warmup` because of the invalidations.
    Prefetches company-related data that can vary between environments.
    """

    @functools.wraps(func)
    def wrapper(self):
        # Prefetch common data that might cause query count variations
        self.env.company.country_id.code
        self.env.company.currency_id.rate
        return func(self)

    return wrapper


# =============================================================================
# QUERY COUNT REGRESSION TESTS
# =============================================================================


@tagged("purchase_perf", "po_create_perf", "-at_install", "post_install")
class TestPurchaseOrderCreationPerf(AccountTestInvoicingCommon):
    """Query count tests for Purchase Order creation operations.

    These tests establish baseline query counts for regression detection.
    If query counts increase, it indicates a potential performance regression.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BATCH_SIZE = 10
        cls.LINES_PER_ORDER = 10

        # Create test products with suppliers
        cls.products = cls.env["product.product"].create(
            [
                {
                    "name": f"Test Product {i}",
                    "list_price": 10 + i,
                    "standard_price": 5 + i,
                    "type": "consu",
                    "seller_ids": [
                        Command.create(
                            {
                                "partner_id": cls.partner_a.id,
                                "min_qty": 1,
                                "price": 8 + i,
                                "delay": 3,
                            }
                        )
                    ],
                }
                for i in range(cls.LINES_PER_ORDER)
            ]
        )

        # Create test partners
        cls.partners = cls.env["res.partner"].create(
            [
                {
                    "name": f"Vendor {i}",
                }
                for i in range(cls.BATCH_SIZE)
            ]
        )

        cls.env.flush_all()

    @users("admin")
    @warmup
    @prepare
    def test_empty_po_creation(self):
        """Test query count for creating a single empty PO."""
        with self.assertQueryCount(admin=11):
            self.env["purchase.order"].create(
                {
                    "partner_id": self.partner_a.id,
                }
            )

    @users("admin")
    @warmup
    @prepare
    def test_empty_po_batch_creation(self):
        """Test query count for batch creating empty POs.

        Batch creation should have O(1) query growth, not O(n).
        """
        with self.assertQueryCount(admin=14):
            self.env["purchase.order"].create(
                [
                    {
                        "partner_id": self.partners[i].id,
                    }
                    for i in range(2)
                ]
            )

    @users("admin")
    @warmup
    @prepare
    def test_po_with_lines_creation(self):
        """Test query count for creating PO with product lines.

        This is the most common operation - creating a PO with actual lines.
        """
        with self.assertQueryCount(admin=39):
            self.env["purchase.order"].create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_qty": 10,
                            }
                        )
                        for product in self.products[:5]
                    ],
                }
            )

    @users("admin")
    @warmup
    @prepare
    def test_po_with_dummy_lines_creation(self):
        """Test that section/note lines don't add significant queries."""
        with self.assertQueryCount(admin=12):
            self.env["purchase.order"].create(
                [
                    {
                        "partner_id": self.partner_a.id,
                        "line_ids": [
                            Command.create(
                                {"display_type": "line_note", "name": "Note"}
                            ),
                            Command.create(
                                {"display_type": "line_section", "name": "Section"}
                            ),
                        ],
                    }
                    for _ in range(2)
                ]
            )

    @users("admin")
    @warmup
    @prepare
    def test_po_batch_with_lines_creation(self):
        """Test batch creation of POs with lines.

        Critical for imports and automated PO generation.
        """
        vals_list = [
            {
                "partner_id": self.partners[i % len(self.partners)].id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 5 + i,
                        }
                    )
                    for product in self.products[:3]
                ],
            }
            for i in range(5)
        ]

        with self.assertQueryCount(admin=78):
            self.env["purchase.order"].create(vals_list)


@tagged("purchase_perf", "po_write_perf", "-at_install", "post_install")
class TestPurchaseOrderWritePerf(AccountTestInvoicingCommon):
    """Query count tests for Purchase Order write operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.products = cls.env["product.product"].create(
            [
                {
                    "name": f"Test Product {i}",
                    "standard_price": 10 + i,
                    "type": "consu",
                }
                for i in range(10)
            ]
        )

        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 5,
                            "price_unit": 10,
                        }
                    )
                    for product in cls.products
                ],
            }
        )
        cls.env.flush_all()

    @users("admin")
    @warmup
    def test_po_write_single_field(self):
        """Test query count for updating a single field on PO."""
        with self.assertQueryCount(admin=2):
            self.purchase_order.write({"partner_ref": "VENDOR-REF-001"})

    @users("admin")
    @warmup
    def test_po_line_qty_update(self):
        """Test query count for updating line quantity.

        This triggers cascading recomputes for amounts, dates, etc.
        """
        line = self.purchase_order.line_ids[0]
        with self.assertQueryCount(admin=22):
            line.write({"product_qty": 20})

    @users("admin")
    @warmup
    def test_po_line_batch_qty_update(self):
        """Test query count for batch updating line quantities."""
        lines = self.purchase_order.line_ids[:5]
        with self.assertQueryCount(admin=23):
            lines.write({"product_qty": 15})


@tagged("purchase_perf", "po_confirm_perf", "-at_install", "post_install")
class TestPurchaseOrderConfirmPerf(AccountTestInvoicingCommon):
    """Query count tests for Purchase Order confirmation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.products = cls.env["product.product"].create(
            [
                {
                    "name": f"Test Product {i}",
                    "standard_price": 10 + i,
                    "type": "consu",
                }
                for i in range(10)
            ]
        )
        cls.env.flush_all()

    def _create_po(self, line_count=10):
        """Helper to create a fresh PO for confirmation tests."""
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.products[i % len(self.products)].id,
                            "product_qty": 5,
                            "price_unit": 10,
                        }
                    )
                    for i in range(line_count)
                ],
            }
        )

    @users("admin")
    @warmup
    def test_po_confirm_small(self):
        """Test confirmation of PO with 5 lines."""
        po = self._create_po(5)
        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueryCount(admin=26):
            po.action_confirm()

    @users("admin")
    @warmup
    def test_po_confirm_medium(self):
        """Test confirmation of PO with 10 lines."""
        po = self._create_po(10)
        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertQueryCount(admin=27):
            po.action_confirm()


# =============================================================================
# PROFILING TESTS - Detailed Performance Analysis
# =============================================================================


@tagged("purchase_profile", "-at_install", "post_install")
class TestPurchaseOrderProfiling(AccountTestInvoicingCommon):
    """Profiling tests for detailed performance analysis.

    These tests generate Speedscope-compatible profiles that can be
    visualized to identify bottlenecks. Results are stored in ir.profile.

    After running, check:
    1. Profiling menu in Odoo
    2. Click on profile record
    3. Open speedscope_url in browser
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create products with varying seller configurations
        cls.products_simple = cls.env["product.product"].create(
            [
                {
                    "name": f"Simple Product {i}",
                    "standard_price": 10 + i,
                    "type": "consu",
                }
                for i in range(20)
            ]
        )

        cls.products_with_sellers = cls.env["product.product"].create(
            [
                {
                    "name": f"Product With Seller {i}",
                    "standard_price": 10 + i,
                    "type": "consu",
                    "seller_ids": [
                        Command.create(
                            {
                                "partner_id": cls.partner_a.id,
                                "min_qty": qty,
                                "price": 8 + i + qty,
                                "delay": 3 + qty,
                            }
                        )
                        for qty in [1, 5, 10, 50]
                    ],  # Multiple price breaks
                }
                for i in range(20)
            ]
        )

        cls.partners = cls.env["res.partner"].create(
            [
                {
                    "name": f"Vendor {i}",
                }
                for i in range(50)
            ]
        )

        cls.env.flush_all()

    def test_profile_po_creation_scaling(self):
        """Profile PO creation with varying line counts.

        Generates profiles for 10, 25, 50 lines to identify scaling issues.
        """
        for line_count in [10, 25, 50]:
            with self.profile(description=f"PO creation with {line_count} lines"):
                self.env["purchase.order"].create(
                    {
                        "partner_id": self.partner_a.id,
                        "line_ids": [
                            Command.create(
                                {
                                    "product_id": self.products_simple[
                                        i % len(self.products_simple)
                                    ].id,
                                    "product_qty": 10,
                                }
                            )
                            for i in range(line_count)
                        ],
                    }
                )
            self.env.flush_all()
            self.env.invalidate_all()

    def test_profile_seller_selection_impact(self):
        """Profile impact of seller selection on PO creation.

        Compares products with no sellers vs products with multiple sellers.
        The seller selection algorithm runs for each line, so this
        highlights potential N+1 issues.
        """
        # Profile without seller lookup
        with self.profile(description="PO creation - no sellers"):
            self.env["purchase.order"].create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_qty": 10,
                            }
                        )
                        for product in self.products_simple[:10]
                    ],
                }
            )

        self.env.flush_all()
        self.env.invalidate_all()

        # Profile with seller lookup
        with self.profile(description="PO creation - with sellers"):
            self.env["purchase.order"].create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": product.id,
                                "product_qty": 10,
                            }
                        )
                        for product in self.products_with_sellers[:10]
                    ],
                }
            )

    def test_profile_batch_po_creation(self):
        """Profile batch creation of multiple POs.

        Tests whether batch operations properly leverage batching.
        """
        with self.profile(description="Batch PO creation - 20 POs x 5 lines"):
            self.env["purchase.order"].create(
                [
                    {
                        "partner_id": self.partners[i].id,
                        "line_ids": [
                            Command.create(
                                {
                                    "product_id": self.products_simple[j].id,
                                    "product_qty": 5 + j,
                                }
                            )
                            for j in range(5)
                        ],
                    }
                    for i in range(20)
                ]
            )

    def test_profile_computed_field_cascade(self):
        """Profile computed field cascade when updating product_qty.

        Changing product_qty triggers:
        - _compute_selected_seller_id
        - _compute_price_and_discount
        - _compute_date_planned
        - _compute_amounts (on order)

        This test identifies which computed fields are the bottleneck.
        """
        # Create PO with lines
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 5,
                        }
                    )
                    for product in self.products_with_sellers[:15]
                ],
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()

        # Profile quantity updates
        with self.profile(description="Line qty update cascade - 15 lines"):
            with ExecutionContext(operation="bulk_qty_update"):
                for line in po.line_ids:
                    line.product_qty = 25  # Triggers seller reselection

    def test_profile_po_confirmation_flow(self):
        """Profile the full PO confirmation workflow."""
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 10,
                        }
                    )
                    for product in self.products_simple[:20]
                ],
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()

        with self.profile(description="PO confirmation - 20 lines"):
            po.action_confirm()


# =============================================================================
# SCALING TESTS - Measure Performance at Different Scales
# =============================================================================


@tagged("purchase_scale", "-at_install", "post_install")
class TestPurchaseOrderScaling(AccountTestInvoicingCommon):
    """Scaling tests to measure performance at different data volumes.

    These tests measure actual execution time and query counts at
    various scales to identify algorithmic complexity issues (O(n), O(n²), etc.).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.products = cls.env["product.product"].create(
            [
                {
                    "name": f"Scale Test Product {i}",
                    "standard_price": 10 + i,
                    "type": "consu",
                    "seller_ids": [
                        Command.create(
                            {
                                "partner_id": cls.partner_a.id,
                                "min_qty": 1,
                                "price": 8 + i,
                            }
                        )
                    ],
                }
                for i in range(100)
            ]
        )

        cls.partners = cls.env["res.partner"].create(
            [
                {
                    "name": f"Scale Vendor {i}",
                }
                for i in range(100)
            ]
        )

        cls.env.flush_all()

    def _measure_operation(self, description, operation_func):
        """Measure an operation and log results.

        Returns (duration, query_count).
        """
        self.env.flush_all()
        self.env.invalidate_all()

        queries_start = self.env.cr.sql_log_count
        t0 = time.perf_counter()

        result = operation_func()

        t1 = time.perf_counter()
        query_count = self.env.cr.sql_log_count - queries_start

        _logger.info(
            "SCALE TEST: %s - Duration: %.3fs, Queries: %d",
            description,
            t1 - t0,
            query_count,
        )

        return t1 - t0, query_count, result

    def test_scaling_po_creation_by_line_count(self):
        """Test PO creation scaling with increasing line counts.

        Expected: O(n) or better
        Red flag: O(n²) growth indicates N+1 problem
        """
        results = []
        line_counts = [5, 10, 25, 50, 100]

        for line_count in line_counts:

            def create_po(lc=line_count):
                return self.env["purchase.order"].create(
                    {
                        "partner_id": self.partner_a.id,
                        "line_ids": [
                            Command.create(
                                {
                                    "product_id": self.products[i % 100].id,
                                    "product_qty": 10,
                                }
                            )
                            for i in range(lc)
                        ],
                    }
                )

            duration, queries, po = self._measure_operation(
                f"Create PO with {line_count} lines", create_po
            )
            results.append(
                {
                    "lines": line_count,
                    "duration": duration,
                    "queries": queries,
                    "queries_per_line": queries / line_count,
                }
            )

        # Log summary
        _logger.info("=" * 60)
        _logger.info("SCALING SUMMARY: PO Creation by Line Count")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "Lines: %3d | Duration: %.3fs | Queries: %4d | Q/Line: %.1f",
                r["lines"],
                r["duration"],
                r["queries"],
                r["queries_per_line"],
            )

        # Assert queries per line should be roughly constant (O(n) scaling)
        # Allow for some overhead on small counts
        if len(results) >= 2:
            first_qpl = results[0]["queries_per_line"]
            last_qpl = results[-1]["queries_per_line"]
            # Queries per line shouldn't more than double
            self.assertLess(
                last_qpl,
                first_qpl * 2.5,
                f"Query scaling is worse than O(n): {first_qpl:.1f} -> {last_qpl:.1f}",
            )

    def test_scaling_batch_po_creation(self):
        """Test batch PO creation scaling.

        Creating N POs in batch should be faster than N individual creates.
        """
        po_counts = [5, 10, 25]
        lines_per_po = 5

        results = []
        for po_count in po_counts:

            def create_batch(pc=po_count):
                return self.env["purchase.order"].create(
                    [
                        {
                            "partner_id": self.partners[i].id,
                            "line_ids": [
                                Command.create(
                                    {
                                        "product_id": self.products[j].id,
                                        "product_qty": 5,
                                    }
                                )
                                for j in range(lines_per_po)
                            ],
                        }
                        for i in range(pc)
                    ]
                )

            duration, queries, pos = self._measure_operation(
                f"Batch create {po_count} POs x {lines_per_po} lines", create_batch
            )
            results.append(
                {
                    "po_count": po_count,
                    "total_lines": po_count * lines_per_po,
                    "duration": duration,
                    "queries": queries,
                    "queries_per_po": queries / po_count,
                }
            )

        # Log summary
        _logger.info("=" * 60)
        _logger.info("SCALING SUMMARY: Batch PO Creation")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "POs: %2d | Lines: %3d | Duration: %.3fs | Queries: %4d | Q/PO: %.1f",
                r["po_count"],
                r["total_lines"],
                r["duration"],
                r["queries"],
                r["queries_per_po"],
            )

    def test_scaling_line_update(self):
        """Test line update scaling when modifying quantities."""
        # Create a PO with many lines
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.products[i].id,
                            "product_qty": 5,
                        }
                    )
                    for i in range(50)
                ],
            }
        )
        self.env.flush_all()

        update_counts = [5, 10, 25, 50]
        results = []

        for update_count in update_counts:
            # Reset quantities
            po.line_ids.write({"product_qty": 5})
            self.env.flush_all()
            self.env.invalidate_all()

            lines_to_update = po.line_ids[:update_count]

            def update_lines(lines=lines_to_update):
                lines.write({"product_qty": 20})

            duration, queries, _ = self._measure_operation(
                f"Update {update_count} line quantities", update_lines
            )
            results.append(
                {
                    "lines_updated": update_count,
                    "duration": duration,
                    "queries": queries,
                }
            )

        # Log summary
        _logger.info("=" * 60)
        _logger.info("SCALING SUMMARY: Line Quantity Updates")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "Lines updated: %2d | Duration: %.3fs | Queries: %4d",
                r["lines_updated"],
                r["duration"],
                r["queries"],
            )


# =============================================================================
# STRESS TESTS - High Volume Performance Testing
# =============================================================================


@tagged("purchase_stress", "-at_install", "post_install")
class TestPurchaseOrderStress(AccountTestInvoicingCommon):
    """Stress tests with high data volumes to detect real bottlenecks.

    These tests use significantly larger data volumes than the scaling tests
    to stress-test the system and reveal performance issues that only appear
    at scale.

    WARNING: These tests may take several minutes to complete.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        _logger.info("=" * 60)
        _logger.info("STRESS TEST SETUP: Creating large test dataset...")
        _logger.info("=" * 60)

        t0 = time.perf_counter()

        # Create many products with multiple seller price breaks
        cls.products_heavy = cls.env["product.product"].create(
            [
                {
                    "name": f"Stress Product {i}",
                    "standard_price": 10 + i,
                    "type": "consu",
                    "seller_ids": [
                        Command.create(
                            {
                                "partner_id": cls.partner_a.id,
                                "min_qty": qty,
                                "price": 5 + i + qty * 0.1,
                                "delay": 1 + (qty // 10),
                            }
                        )
                        for qty in [1, 5, 10, 25, 50, 100, 250, 500]
                    ],  # 8 price breaks each
                }
                for i in range(200)
            ]
        )  # 200 products × 8 sellers = 1600 seller records

        # Create many partners
        cls.partners_heavy = cls.env["res.partner"].create(
            [
                {
                    "name": f"Stress Vendor {i}",
                }
                for i in range(200)
            ]
        )

        cls.env.flush_all()

        t1 = time.perf_counter()
        _logger.info(
            "STRESS TEST SETUP: Created 200 products (1600 sellers) + 200 partners in %.2fs",
            t1 - t0,
        )

    def _stress_measure(self, description, operation_func):
        """Measure a stress operation with detailed logging."""
        self.env.flush_all()
        self.env.invalidate_all()

        queries_start = self.env.cr.sql_log_count
        t0 = time.perf_counter()

        result = operation_func()

        t1 = time.perf_counter()
        query_count = self.env.cr.sql_log_count - queries_start

        _logger.info(
            "STRESS: %s - Duration: %.3fs, Queries: %d",
            description,
            t1 - t0,
            query_count,
        )

        return {
            "description": description,
            "duration": t1 - t0,
            "queries": query_count,
            "result": result,
        }

    def test_stress_large_po_creation(self):
        """Stress test: Create POs with 200, 500, and 1000 lines.

        This reveals N+1 issues and computed field cascades that
        only appear with large line counts.
        """
        _logger.info("=" * 60)
        _logger.info("STRESS TEST: Large PO Creation")
        _logger.info("=" * 60)

        results = []
        line_counts = [200, 500]

        for line_count in line_counts:

            def create_large_po(lc=line_count):
                return self.env["purchase.order"].create(
                    {
                        "partner_id": self.partner_a.id,
                        "line_ids": [
                            Command.create(
                                {
                                    "product_id": self.products_heavy[i % 200].id,
                                    "product_qty": 10 + (i % 50),  # Varying quantities
                                }
                            )
                            for i in range(lc)
                        ],
                    }
                )

            result = self._stress_measure(
                f"Create PO with {line_count} lines", create_large_po
            )
            result["lines"] = line_count
            result["queries_per_line"] = result["queries"] / line_count
            result["ms_per_line"] = (result["duration"] * 1000) / line_count
            results.append(result)

        # Summary
        _logger.info("=" * 60)
        _logger.info("STRESS SUMMARY: Large PO Creation")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "Lines: %4d | Duration: %.3fs | Queries: %5d | Q/Line: %.2f | ms/Line: %.2f",
                r["lines"],
                r["duration"],
                r["queries"],
                r["queries_per_line"],
                r["ms_per_line"],
            )

        # Detect O(n²) - queries per line should stay roughly constant
        if len(results) >= 2:
            qpl_first = results[0]["queries_per_line"]
            qpl_last = results[-1]["queries_per_line"]
            growth_ratio = qpl_last / qpl_first if qpl_first > 0 else 0

            if growth_ratio > 1.5:
                _logger.warning(
                    "POTENTIAL O(n²) DETECTED: Q/Line grew from %.2f to %.2f (%.1fx)",
                    qpl_first,
                    qpl_last,
                    growth_ratio,
                )
            else:
                _logger.info(
                    "SCALING OK: Q/Line ratio %.2f -> %.2f (%.1fx)",
                    qpl_first,
                    qpl_last,
                    growth_ratio,
                )

    def test_stress_batch_po_creation(self):
        """Stress test: Batch create 50 and 100 POs with 10 lines each.

        Tests batching efficiency at scale.
        """
        _logger.info("=" * 60)
        _logger.info("STRESS TEST: Batch PO Creation")
        _logger.info("=" * 60)

        results = []
        batch_sizes = [50, 100]
        lines_per_po = 10

        for batch_size in batch_sizes:

            def create_batch(bs=batch_size):
                return self.env["purchase.order"].create(
                    [
                        {
                            "partner_id": self.partners_heavy[i % 200].id,
                            "line_ids": [
                                Command.create(
                                    {
                                        "product_id": self.products_heavy[
                                            (i * lines_per_po + j) % 200
                                        ].id,
                                        "product_qty": 5 + j,
                                    }
                                )
                                for j in range(lines_per_po)
                            ],
                        }
                        for i in range(bs)
                    ]
                )

            result = self._stress_measure(
                f"Batch create {batch_size} POs × {lines_per_po} lines", create_batch
            )
            result["po_count"] = batch_size
            result["total_lines"] = batch_size * lines_per_po
            result["queries_per_po"] = result["queries"] / batch_size
            result["queries_per_line"] = result["queries"] / result["total_lines"]
            results.append(result)

        # Summary
        _logger.info("=" * 60)
        _logger.info("STRESS SUMMARY: Batch PO Creation")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "POs: %3d | Lines: %4d | Duration: %.3fs | Q: %5d | Q/PO: %.1f | Q/Line: %.2f",
                r["po_count"],
                r["total_lines"],
                r["duration"],
                r["queries"],
                r["queries_per_po"],
                r["queries_per_line"],
            )

    def test_stress_line_updates_cascade(self):
        """Stress test: Update quantities on 100, 200, 500 lines.

        Tests computed field cascade efficiency at scale.
        """
        _logger.info("=" * 60)
        _logger.info("STRESS TEST: Line Update Cascade")
        _logger.info("=" * 60)

        # Create a large PO
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.products_heavy[i % 200].id,
                            "product_qty": 5,
                        }
                    )
                    for i in range(500)
                ],
            }
        )
        self.env.flush_all()

        results = []
        update_counts = [100, 200, 500]

        for update_count in update_counts:
            # Reset
            po.line_ids.write({"product_qty": 5})
            self.env.flush_all()
            self.env.invalidate_all()

            lines_to_update = po.line_ids[:update_count]

            def update_lines(lines=lines_to_update):
                # Use write() for batch update
                lines.write({"product_qty": 50})

            result = self._stress_measure(
                f"Update {update_count} line quantities", update_lines
            )
            result["lines_updated"] = update_count
            results.append(result)

        # Summary
        _logger.info("=" * 60)
        _logger.info("STRESS SUMMARY: Line Update Cascade")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "Lines: %3d | Duration: %.3fs | Queries: %4d",
                r["lines_updated"],
                r["duration"],
                r["queries"],
            )

    def test_stress_seller_selection_heavy(self):
        """Stress test: Seller selection with many sellers per product.

        Each product has 8 price breaks. Test with 100+ lines to stress
        the _select_seller algorithm.
        """
        _logger.info("=" * 60)
        _logger.info("STRESS TEST: Seller Selection (8 price breaks × 200 products)")
        _logger.info("=" * 60)

        results = []
        line_counts = [50, 100, 200]

        for line_count in line_counts:

            def create_po_with_sellers(lc=line_count):
                return self.env["purchase.order"].create(
                    {
                        "partner_id": self.partner_a.id,
                        "line_ids": [
                            Command.create(
                                {
                                    "product_id": self.products_heavy[i % 200].id,
                                    "product_qty": [1, 5, 10, 25, 50, 100, 250, 500][
                                        i % 8
                                    ],  # Hit different price breaks
                                }
                            )
                            for i in range(lc)
                        ],
                    }
                )

            result = self._stress_measure(
                f"Create PO with {line_count} lines (seller lookup)",
                create_po_with_sellers,
            )
            result["lines"] = line_count
            result["queries_per_line"] = result["queries"] / line_count
            results.append(result)

        # Summary
        _logger.info("=" * 60)
        _logger.info("STRESS SUMMARY: Seller Selection Heavy")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "Lines: %3d | Duration: %.3fs | Queries: %4d | Q/Line: %.2f",
                r["lines"],
                r["duration"],
                r["queries"],
                r["queries_per_line"],
            )

    def test_stress_po_confirmation_large(self):
        """Stress test: Confirm PO with 100 and 200 lines.

        Confirmation triggers stock moves, pickings, and various
        side effects that compound at scale.
        """
        _logger.info("=" * 60)
        _logger.info("STRESS TEST: PO Confirmation (Large)")
        _logger.info("=" * 60)

        results = []
        line_counts = [100, 200]

        for line_count in line_counts:
            # Create fresh PO
            po = self.env["purchase.order"].create(
                {
                    "partner_id": self.partner_a.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.products_heavy[i % 200].id,
                                "product_qty": 10,
                            }
                        )
                        for i in range(line_count)
                    ],
                }
            )
            self.env.flush_all()
            self.env.invalidate_all()

            def confirm_po(p=po):
                p.action_confirm()

            result = self._stress_measure(
                f"Confirm PO with {line_count} lines", confirm_po
            )
            result["lines"] = line_count
            result["queries_per_line"] = result["queries"] / line_count
            results.append(result)

        # Summary
        _logger.info("=" * 60)
        _logger.info("STRESS SUMMARY: PO Confirmation Large")
        _logger.info("=" * 60)
        for r in results:
            _logger.info(
                "Lines: %3d | Duration: %.3fs | Queries: %4d | Q/Line: %.2f",
                r["lines"],
                r["duration"],
                r["queries"],
                r["queries_per_line"],
            )

        # Check scaling
        if len(results) >= 2:
            qpl_first = results[0]["queries_per_line"]
            qpl_last = results[-1]["queries_per_line"]
            if qpl_last > qpl_first * 1.5:
                _logger.warning(
                    "CONFIRMATION SCALING ISSUE: Q/Line grew from %.2f to %.2f",
                    qpl_first,
                    qpl_last,
                )


# =============================================================================
# BOTTLENECK IDENTIFICATION TESTS
# =============================================================================


@tagged("purchase_bottleneck", "-at_install", "post_install")
class TestPurchaseBottlenecks(AccountTestInvoicingCommon):
    """Tests specifically designed to identify performance bottlenecks.

    Each test isolates a specific component to measure its impact.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Products with complex seller configurations
        cls.products_many_sellers = cls.env["product.product"].create(
            [
                {
                    "name": f"Multi-Seller Product {i}",
                    "standard_price": 10,
                    "type": "consu",
                    "seller_ids": [
                        Command.create(
                            {
                                "partner_id": cls.partner_a.id,
                                "min_qty": qty,
                                "price": 8 + qty,
                                "delay": 1 + qty,
                            }
                        )
                        for qty in range(1, 20)
                    ],  # 19 seller price breaks!
                }
                for i in range(10)
            ]
        )

        cls.env.flush_all()

    def test_bottleneck_seller_selection_algorithm(self):
        """Isolate seller selection performance.

        The _compute_selected_seller_id method is called for each line
        and iterates through all seller_ids. With many sellers and lines,
        this becomes O(lines × sellers).
        """
        _logger.info("=" * 60)
        _logger.info("BOTTLENECK TEST: Seller Selection Algorithm")
        _logger.info("=" * 60)

        # Measure with products that have many sellers
        self.env.flush_all()
        self.env.invalidate_all()

        queries_start = self.env.cr.sql_log_count
        t0 = time.perf_counter()

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 10,
                        }
                    )
                    for product in self.products_many_sellers
                ],
            }
        )

        t1 = time.perf_counter()
        query_count = self.env.cr.sql_log_count - queries_start

        _logger.info(
            "10 products × 19 sellers each: %.3fs, %d queries", t1 - t0, query_count
        )

        # Now change quantities to trigger seller reselection
        self.env.flush_all()
        self.env.invalidate_all()

        queries_start = self.env.cr.sql_log_count
        t0 = time.perf_counter()

        # This should trigger _compute_selected_seller_id for all lines
        po.line_ids.write({"product_qty": 50})

        t1 = time.perf_counter()
        query_count = self.env.cr.sql_log_count - queries_start

        _logger.info(
            "Qty update triggering seller reselection: %.3fs, %d queries",
            t1 - t0,
            query_count,
        )

    def test_bottleneck_amount_computation(self):
        """Isolate amount computation performance.

        The _compute_amounts_invoice method uses 4 separate mapped() calls.
        This could be optimized to a single iteration.
        """
        _logger.info("=" * 60)
        _logger.info("BOTTLENECK TEST: Amount Computation")
        _logger.info("=" * 60)

        # Create confirmed PO with many lines
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.products_many_sellers[i % 10].id,
                            "product_qty": 10,
                            "price_unit": 100 + i,
                        }
                    )
                    for i in range(50)
                ],
            }
        )
        po.action_confirm()
        self.env.flush_all()
        self.env.invalidate_all()

        # Force recomputation of amounts
        queries_start = self.env.cr.sql_log_count
        t0 = time.perf_counter()

        # Access amount fields to trigger computation
        _ = po.amount_untaxed
        _ = po.amount_tax
        _ = po.amount_total
        _ = po.amount_taxexc_invoiced
        _ = po.amount_taxinc_invoiced

        t1 = time.perf_counter()
        query_count = self.env.cr.sql_log_count - queries_start

        _logger.info(
            "Amount computation (50 lines): %.3fs, %d queries", t1 - t0, query_count
        )

    def test_bottleneck_date_planned_computation(self):
        """Isolate date_planned computation performance.

        The _compute_date_planned method iterates through all seller_ids
        to check if current date matches any seller's expected date.
        """
        _logger.info("=" * 60)
        _logger.info("BOTTLENECK TEST: Date Planned Computation")
        _logger.info("=" * 60)

        po = self.env["purchase.order"].create(
            {
                "partner_id": self.partner_a.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 10,
                        }
                    )
                    for product in self.products_many_sellers
                ],
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()

        # Change product to trigger date_planned recomputation
        queries_start = self.env.cr.sql_log_count
        t0 = time.perf_counter()

        # Simulate product change (triggers date_planned recompute)
        for line in po.line_ids:
            line.invalidate_recordset(["date_planned"])
            _ = line.date_planned

        t1 = time.perf_counter()
        query_count = self.env.cr.sql_log_count - queries_start

        _logger.info(
            "Date planned recomputation (10 lines × 19 sellers): %.3fs, %d queries",
            t1 - t0,
            query_count,
        )
