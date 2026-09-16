import logging

import odoo
from odoo.exceptions import ValidationError

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_logger = logging.getLogger(__name__)


@odoo.tests.tagged("post_install", "-at_install")
class TestAuditVerification2(TestPoSCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product("AuditProd2", self.categ_basic, 100, 50)

    def test_R1_sale_details_grand_total_no_dedup(self):
        report = self.env["report.point_of_sale.report_saledetails"]
        row = {
            "product_id": 1,
            "product_name": "Widget",
            "barcode": False,
            "quantity": 3.0,
            "price_unit": 10.0,
            "discount": 0.0,
            "uom": "Units",
            "total_paid": 30.0,
            "base_amount": 30.0,
            "combo_products_label": False,
        }
        categories = [
            {"name": "Cat A", "products": [dict(row)]},
            {"name": "Cat B", "products": [dict(row)]},
        ]
        _, totals = report._get_total_and_qty_per_category(categories)
        _logger.info("R1 grand totals: %r", totals)
        self.assertEqual(
            totals["qty"],
            6.0,
            "BUG CONFIRMED: grand total qty deduplicated identical rows "
            "(got %s, expected 6.0)" % totals["qty"],
        )
        self.assertEqual(
            totals["total"],
            60.0,
            "BUG CONFIRMED: grand total amount deduplicated identical rows "
            "(got %s, expected 60.0)" % totals["total"],
        )

    def test_R2_preset_slot_usage_lists(self):
        preset = self.env["pos.preset"].create({"name": "AuditPreset2"})
        usage = preset._get_slots_usage()
        _logger.info("R2 empty usage: %r", usage)
        self.assertEqual(usage["2099-01-01 12:00:00"], [])
        self.assertIsInstance(usage["2099-01-01 12:00:00"], list)

    def test_R3_batch_write_per_record_has_deleted_line(self):
        self._start_pos_session(self.cash_pm1, 0)
        orders_map = self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.cash_pm1, 100)],
                    "uuid": "audit-r3-a",
                },
                {
                    "pos_order_lines_ui_args": [(self.product, 1)],
                    "payments": [(self.cash_pm1, 100)],
                    "uuid": "audit-r3-b",
                },
            ]
        )
        order_a = orders_map["audit-r3-a"]
        order_b = orders_map["audit-r3-b"]
        order_a.has_deleted_line = False
        order_b.has_deleted_line = True
        (order_a | order_b).write({"has_deleted_line": True})
        _logger.info(
            "R3 has_deleted_line a=%s b=%s",
            order_a.has_deleted_line,
            order_b.has_deleted_line,
        )
        self.assertTrue(
            order_a.has_deleted_line,
            "BUG CONFIRMED: batch write dropped has_deleted_line for order A "
            "because a sibling order mutated the shared vals dict",
        )
        self.assertTrue(order_b.has_deleted_line)

    def test_R4_tax_not_deletable_when_open_pos_order_uses_it(self):
        self._start_pos_session(self.cash_pm1, 0)
        tax = self.env["account.tax"].create(
            {
                "name": "AuditTaxR4",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
            }
        )
        product = self.create_product(
            "AuditTaxProdR4", self.categ_basic, 100, 50, tax_ids=tax.ids
        )
        self._create_orders(
            [
                {
                    "pos_order_lines_ui_args": [(product, 1)],
                    "payments": [(self.cash_pm1, 110)],
                    "uuid": "audit-r4-0001",
                },
            ]
        )
        tax.invalidate_model(fnames=["is_used"])
        self.assertTrue(
            tax.is_used,
            "a tax carried by an open-session POS order must count as used, so "
            "that it cannot be deleted out from under the closing entry",
        )
        with self.assertRaises(ValidationError):
            tax.unlink()
        self.assertTrue(tax.exists())

        tax.active = False
        self.assertFalse(tax.active)
