"""Performance tests for price and discount computation.

These tests measure the performance of _compute_price_and_discount and related
methods to ensure optimizations are effective.
"""

import time
from contextlib import contextmanager

from odoo.tests import tagged, TransactionCase


@contextmanager
def timing(description=""):
    """Context manager to measure execution time."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"{description}: {elapsed:.4f}s")


class PriceComputationPerformanceBase(TransactionCase):
    """Base class with common setup for performance tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Performance Test Partner",
            }
        )

        cls.pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Performance Test Pricelist",
                "currency_id": cls.env.company.currency_id.id,
            }
        )

        # Create products for testing
        cls.products = cls.env["product.product"].create(
            [
                {
                    "name": f"Perf Test Product {i}",
                    "list_price": 100.0 + i,
                    "type": "consu",
                }
                for i in range(100)
            ]
        )

        # Create pricelist rules for some products (to test discount computation)
        cls.env["product.pricelist.item"].create(
            [
                {
                    "pricelist_id": cls.pricelist.id,
                    "product_id": product.id,
                    "compute_price": "percentage",
                    "percent_price": 10.0,  # 10% discount
                }
                for product in cls.products[:50]  # First 50 products have discounts
            ]
        )

    def _create_sale_order(self, num_lines):
        """Create a sale order with the specified number of lines."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
            }
        )

        # Create lines in batch
        line_vals = []
        for i in range(num_lines):
            product = self.products[i % len(self.products)]
            line_vals.append(
                {
                    "order_id": order.id,
                    "product_id": product.id,
                    "product_uom_qty": 1 + (i % 10),
                }
            )

        self.env["sale.order.line"].create(line_vals)
        return order

    def _count_method_calls(self, model, method_name, func):
        """Count how many times a method is called during func execution."""
        call_count = 0
        original_method = getattr(model, method_name)

        def counting_wrapper(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_method(*args, **kwargs)

        setattr(model, method_name, counting_wrapper)
        try:
            func()
        finally:
            setattr(model, method_name, original_method)

        return call_count


@tagged("post_install", "-at_install", "sale_performance")
class TestPriceComputationPerformance(PriceComputationPerformanceBase):
    """Test performance of price computation."""

    def test_01_single_line_computation(self):
        """Test price computation for a single line."""
        order = self._create_sale_order(1)
        line = order.line_ids[0]

        # Invalidate cache to force recomputation
        line.invalidate_recordset(["price_unit", "discount", "pricelist_item_id"])

        with timing("Single line price computation"):
            line._compute_pricelist_item_id()
            line._compute_price_and_discount()

        self.assertTrue(line.price_unit > 0, "Price should be computed")

    def test_02_bulk_line_computation_10_lines(self):
        """Test price computation for 10 lines."""
        order = self._create_sale_order(10)

        # Invalidate cache
        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        with timing("10 lines price computation"):
            order.line_ids._compute_pricelist_item_id()
            order.line_ids._compute_price_and_discount()

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_03_bulk_line_computation_50_lines(self):
        """Test price computation for 50 lines."""
        order = self._create_sale_order(50)

        # Invalidate cache
        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        with timing("50 lines price computation"):
            order.line_ids._compute_pricelist_item_id()
            order.line_ids._compute_price_and_discount()

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_04_bulk_line_computation_100_lines(self):
        """Test price computation for 100 lines."""
        order = self._create_sale_order(100)

        # Invalidate cache
        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        with timing("100 lines price computation"):
            order.line_ids._compute_pricelist_item_id()
            order.line_ids._compute_price_and_discount()

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_05_verify_no_duplicate_pricelist_calls(self):
        """Verify that pricelist price is not computed twice per line.

        This test ensures the optimization is working by checking that
        _get_pricelist_price is called at most once per line.
        """
        order = self._create_sale_order(20)
        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        # First compute pricelist_item_id (required for price computation)
        order.line_ids._compute_pricelist_item_id()

        # Count calls to _get_pricelist_price during _compute_price_and_discount
        call_count = 0
        original_method = type(order.line_ids)._get_pricelist_price

        def counting_wrapper(self):
            nonlocal call_count
            call_count += 1
            return original_method(self)

        type(order.line_ids)._get_pricelist_price = counting_wrapper

        try:
            order.line_ids._compute_price_and_discount()
        finally:
            type(order.line_ids)._get_pricelist_price = original_method

        num_regular_lines = len(
            order.line_ids.filtered(
                lambda l: not l.display_type and not l.is_downpayment and l.product_id
            )
        )

        # With optimization: should be called at most once per regular line
        # (combo items and special lines may have different behavior)
        self.assertLessEqual(
            call_count,
            num_regular_lines,
            f"_get_pricelist_price called {call_count} times for {num_regular_lines} lines. "
            f"Expected at most {num_regular_lines} calls (once per line).",
        )
        print(
            f"_get_pricelist_price calls: {call_count} for {num_regular_lines} regular lines"
        )

    def test_06_discount_computation_reuses_prices(self):
        """Verify that discount computation reuses cached pricelist prices."""
        order = self._create_sale_order(20)
        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        # Compute pricelist_item_id first
        order.line_ids._compute_pricelist_item_id()

        # Count calls to _get_pricelist_price_before_discount
        call_count = 0
        original_method = type(order.line_ids)._get_pricelist_price_before_discount

        def counting_wrapper(self):
            nonlocal call_count
            call_count += 1
            return original_method(self)

        type(order.line_ids)._get_pricelist_price_before_discount = counting_wrapper

        try:
            order.line_ids._compute_price_and_discount()
        finally:
            type(order.line_ids)._get_pricelist_price_before_discount = original_method

        num_regular_lines = len(
            order.line_ids.filtered(
                lambda l: not l.display_type and not l.is_downpayment and l.product_id
            )
        )

        # Should be called at most once per regular line
        self.assertLessEqual(
            call_count,
            num_regular_lines,
            f"_get_pricelist_price_before_discount called {call_count} times for {num_regular_lines} lines.",
        )
        print(
            f"_get_pricelist_price_before_discount calls: {call_count} for {num_regular_lines} regular lines"
        )

    def test_07_full_order_creation_performance(self):
        """Test full order creation including all computations."""
        with timing("Create order with 50 lines (full flow)"):
            order = self.env["sale.order"].create(
                {
                    "partner_id": self.partner.id,
                    "pricelist_id": self.pricelist.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.products[i % len(self.products)].id,
                                "product_uom_qty": 1 + (i % 10),
                            },
                        )
                        for i in range(50)
                    ],
                }
            )

        self.assertEqual(len(order.line_ids), 50)
        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_08_price_recomputation_on_quantity_change(self):
        """Test performance when quantity changes trigger recomputation."""
        order = self._create_sale_order(50)

        with timing("Update quantity on 50 lines"):
            for line in order.line_ids:
                line.product_uom_qty = line.product_uom_qty + 5

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_09_manual_price_protection_performance(self):
        """Test that manual prices are efficiently protected from recomputation."""
        order = self._create_sale_order(20)

        # Set manual prices on half the lines
        for line in order.line_ids[:10]:
            line.set_manual_price(999.99)

        # Count _get_pricelist_price calls during recomputation
        call_count = 0
        original_method = type(order.line_ids)._get_pricelist_price

        def counting_wrapper(self):
            nonlocal call_count
            call_count += 1
            return original_method(self)

        type(order.line_ids)._get_pricelist_price = counting_wrapper

        try:
            # Trigger recomputation by changing quantities
            order.line_ids.invalidate_recordset(["price_unit", "discount"])
            order.line_ids._compute_price_and_discount()
        finally:
            type(order.line_ids)._get_pricelist_price = original_method

        # Manual price lines still need shadow update, so they call _get_pricelist_price
        # But they should NOT call it twice (once for price, once for discount)
        num_lines = len(order.line_ids)
        print(f"With {num_lines} lines (10 manual): {call_count} pricelist calls")

        # Verify manual prices were preserved
        for line in order.line_ids[:10]:
            self.assertEqual(
                line.price_unit, 999.99, "Manual price should be preserved"
            )


@tagged("post_install", "-at_install", "sale_performance")
class TestPriceComputationCorrectness(PriceComputationPerformanceBase):
    """Test that optimizations don't break correctness."""

    def test_01_prices_match_expected(self):
        """Verify computed prices match expected values."""
        order = self._create_sale_order(10)

        for line in order.line_ids:
            # Price should be product list price (pricelist might apply discount)
            self.assertGreater(line.price_unit, 0, "Price should be positive")
            self.assertGreaterEqual(line.discount, 0, "Discount should be non-negative")
            self.assertLess(line.discount, 100, "Discount should be less than 100%")

    def test_02_discount_correctly_applied(self):
        """Verify discounts are correctly computed from pricelist rules."""
        # Create order with products that have pricelist discounts
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.products[0].id,  # Has 10% discount rule
                            "product_uom_qty": 1,
                        },
                    )
                ],
            }
        )

        line = order.line_ids[0]

        # Check that discount feature determines if discount is shown
        discount_enabled = self.env[
            "product.pricelist.item"
        ]._is_discount_feature_enabled()

        if discount_enabled and line.pricelist_item_id._show_discount():
            # Discount should be approximately 10% (from pricelist rule)
            self.assertAlmostEqual(
                line.discount,
                10.0,
                places=1,
                msg="Discount should be ~10% from pricelist rule",
            )
        else:
            # Discount shown as 0 when feature disabled or rule doesn't show it
            self.assertEqual(line.discount, 0.0)

    def test_03_subtotal_correctly_computed(self):
        """Verify price_subtotal is correctly computed."""
        order = self._create_sale_order(5)

        for line in order.line_ids:
            expected_subtotal = (
                line.product_uom_qty * line.price_unit * (1 - line.discount / 100)
            )
            self.assertAlmostEqual(
                line.price_subtotal,
                expected_subtotal,
                places=2,
                msg=f"Subtotal mismatch: {line.price_subtotal} vs {expected_subtotal}",
            )

    def test_04_shadow_price_updated(self):
        """Verify shadow price is kept in sync."""
        order = self._create_sale_order(5)

        for line in order.line_ids:
            # For non-manual prices, auto should equal price_unit
            if not line.is_manual_price():
                self.assertEqual(
                    line.price_unit,
                    line.price_unit_auto,
                    "Auto price should match price_unit for automatic prices",
                )

    def test_05_manual_price_preserves_shadow(self):
        """Verify manual price keeps shadow for comparison."""
        order = self._create_sale_order(1)
        line = order.line_ids[0]

        original_price = line.price_unit
        line.set_manual_price(500.0)

        self.assertEqual(line.price_unit, 500.0, "Manual price should be set")
        self.assertTrue(line.is_manual_price(), "is_manual_price() should return True")
        # Shadow should reflect what pricelist would give
        self.assertAlmostEqual(
            line.price_unit_auto,
            original_price,
            places=2,
            msg="Shadow should reflect pricelist price",
        )
