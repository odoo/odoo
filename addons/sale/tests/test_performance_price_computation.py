import logging
import time
from contextlib import contextmanager

from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@contextmanager
def timing(description=""):
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    _logger.info("%s: %.4fs", description, elapsed)


class PriceComputationPerformanceBase(TransactionCase):
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

        cls.env["product.pricelist.item"].create(
            [
                {
                    "pricelist_id": cls.pricelist.id,
                    "product_id": product.id,
                    "compute_price": "percentage",
                    "percent_price": 10.0,
                }
                for product in cls.products[:50]
            ]
        )

    def _create_sale_order(self, num_lines):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
            }
        )

        line_vals = []
        for i in range(num_lines):
            product = self.products[i % len(self.products)]
            line_vals.append(
                {
                    "order_id": order.id,
                    "product_id": product.id,
                    "product_qty": 1 + (i % 10),
                }
            )

        self.env["sale.order.line"].create(line_vals)
        return order

    def _count_method_calls(self, model, method_name, func):
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
    def test_01_single_line_computation(self):
        order = self._create_sale_order(1)
        line = order.line_ids[0]

        line.invalidate_recordset(["price_unit", "discount", "pricelist_item_id"])

        with timing("Single line price computation"):
            line._compute_pricelist_item_id()
            line._compute_price_and_discount()

        self.assertTrue(line.price_unit > 0, "Price should be computed")

    def test_02_bulk_line_computation_10_lines(self):
        order = self._create_sale_order(10)

        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        with timing("10 lines price computation"):
            order.line_ids._compute_pricelist_item_id()
            order.line_ids._compute_price_and_discount()

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_03_bulk_line_computation_50_lines(self):
        order = self._create_sale_order(50)

        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        with timing("50 lines price computation"):
            order.line_ids._compute_pricelist_item_id()
            order.line_ids._compute_price_and_discount()

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_04_bulk_line_computation_100_lines(self):
        order = self._create_sale_order(100)

        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        with timing("100 lines price computation"):
            order.line_ids._compute_pricelist_item_id()
            order.line_ids._compute_price_and_discount()

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_05_verify_no_duplicate_pricelist_calls(self):
        order = self._create_sale_order(20)
        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        order.line_ids._compute_pricelist_item_id()

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

        self.assertLessEqual(
            call_count,
            num_regular_lines,
            f"_get_pricelist_price called {call_count} times for {num_regular_lines} lines. "
            f"Expected at most {num_regular_lines} calls (once per line).",
        )
        _logger.info(
            "_get_pricelist_price calls: %s for %s regular lines",
            call_count,
            num_regular_lines,
        )

    def test_06_discount_computation_reuses_prices(self):
        order = self._create_sale_order(20)
        order.line_ids.invalidate_recordset(
            ["price_unit", "discount", "pricelist_item_id"]
        )

        order.line_ids._compute_pricelist_item_id()

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

        self.assertLessEqual(
            call_count,
            num_regular_lines,
            f"_get_pricelist_price_before_discount called {call_count} times for {num_regular_lines} lines.",
        )
        _logger.info(
            "_get_pricelist_price_before_discount calls: %s for %s regular lines",
            call_count,
            num_regular_lines,
        )

    def test_07_full_order_creation_performance(self):
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
                                "product_qty": 1 + (i % 10),
                            },
                        )
                        for i in range(50)
                    ],
                }
            )

        self.assertEqual(len(order.line_ids), 50)
        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_08_price_recomputation_on_quantity_change(self):
        order = self._create_sale_order(50)

        with timing("Update quantity on 50 lines"):
            for line in order.line_ids:
                line.product_qty += 5

        self.assertTrue(all(line.price_unit > 0 for line in order.line_ids))

    def test_09_manual_price_protection_performance(self):
        order = self._create_sale_order(20)

        for line in order.line_ids[:10]:
            line.set_manual_price(999.99)

        call_count = 0
        original_method = type(order.line_ids)._get_pricelist_price

        def counting_wrapper(self):
            nonlocal call_count
            call_count += 1
            return original_method(self)

        type(order.line_ids)._get_pricelist_price = counting_wrapper

        try:
            order.line_ids.invalidate_recordset(["price_unit", "discount"])
            order.line_ids._compute_price_and_discount()
        finally:
            type(order.line_ids)._get_pricelist_price = original_method

        num_lines = len(order.line_ids)
        _logger.info(
            "With %s lines (10 manual): %s pricelist calls", num_lines, call_count
        )

        for line in order.line_ids[:10]:
            self.assertEqual(
                line.price_unit, 999.99, "Manual price should be preserved"
            )


@tagged("post_install", "-at_install", "sale_performance")
class TestPriceComputationCorrectness(PriceComputationPerformanceBase):
    def test_01_prices_match_expected(self):
        order = self._create_sale_order(10)

        for line in order.line_ids:
            self.assertGreater(line.price_unit, 0, "Price should be positive")
            self.assertGreaterEqual(line.discount, 0, "Discount should be non-negative")
            self.assertLess(line.discount, 100, "Discount should be less than 100%")

    def test_02_discount_correctly_applied(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.pricelist.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.products[0].id,
                            "product_qty": 1,
                        },
                    )
                ],
            }
        )

        line = order.line_ids[0]

        discount_enabled = self.env[
            "product.pricelist.item"
        ]._is_discount_feature_enabled()

        if discount_enabled and line.pricelist_item_id._is_discount_shown():
            self.assertAlmostEqual(
                line.discount,
                10.0,
                places=1,
                msg="Discount should be ~10% from pricelist rule",
            )
        else:
            self.assertEqual(line.discount, 0.0)

    def test_03_subtotal_correctly_computed(self):
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
        order = self._create_sale_order(5)

        for line in order.line_ids:
            if not line.is_manual_price():
                self.assertEqual(
                    line.price_unit,
                    line.price_unit_auto,
                    "Auto price should match price_unit for automatic prices",
                )

    def test_05_manual_price_preserves_shadow(self):
        order = self._create_sale_order(1)
        line = order.line_ids[0]

        original_price = line.price_unit
        line.set_manual_price(500.0)

        self.assertEqual(line.price_unit, 500.0, "Manual price should be set")
        self.assertTrue(line.is_manual_price(), "is_manual_price() should return True")
        self.assertAlmostEqual(
            line.price_unit_auto,
            original_price,
            places=2,
            msg="Shadow should reflect pricelist price",
        )
