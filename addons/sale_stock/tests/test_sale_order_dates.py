from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


@tagged("post_install", "-at_install")
class TestSaleExpectedDate(ValuationReconciliationTestCommon):
    def test_sale_order_date_planned(self):
        Product = self.env["product.product"]

        product_A = Product.create(
            {
                "name": "Product A",
                "is_storable": True,
                "sale_delay": 5,
                "uom_id": 1,
            }
        )
        product_B = Product.create(
            {
                "name": "Product B",
                "is_storable": True,
                "sale_delay": 10,
                "uom_id": 1,
            }
        )
        product_C = Product.create(
            {
                "name": "Product C",
                "is_storable": True,
                "sale_delay": 15,
                "uom_id": 1,
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            product_A, self.company_data["default_warehouse"].lot_stock_id, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            product_B, self.company_data["default_warehouse"].lot_stock_id, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            product_C, self.company_data["default_warehouse"].lot_stock_id, 10
        )

        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.env["res.partner"]
                    .create({"name": "A Customer"})
                    .id,
                    "picking_policy": "direct",
                    "line_ids": [
                        Command.create({"product_id": product_A.id, "product_qty": 5}),
                        Command.create({"product_id": product_B.id, "product_qty": 5}),
                        Command.create({"product_id": product_C.id, "product_qty": 5}),
                    ],
                }
            )
        )

        date_planned = fields.Datetime.now() + timedelta(days=5)
        self.assertAlmostEqual(
            date_planned,
            sale_order.date_planned,
            msg="Wrong expected date on sale order!",
            delta=timedelta(seconds=1),
        )

        sale_order.write({"picking_policy": "one"})
        date_planned = fields.Datetime.now() + timedelta(days=15)
        self.assertAlmostEqual(
            date_planned,
            sale_order.date_planned,
            msg="Wrong expected date on sale order!",
            delta=timedelta(seconds=1),
        )

        sale_order.action_confirm()

        confirm_date = fields.Datetime.now() + timedelta(days=5)
        sale_order.write({"date_order": confirm_date})

        date_planned = confirm_date + timedelta(days=15)
        self.assertAlmostEqual(
            date_planned,
            sale_order.date_planned,
            msg="Wrong expected date on sale order!",
            delta=timedelta(seconds=1),
        )

        sale_order.write({"picking_policy": "direct"})
        date_planned = confirm_date + timedelta(days=5)
        self.assertAlmostEqual(
            date_planned,
            sale_order.date_planned,
            msg="Wrong expected date on sale order!",
            delta=timedelta(seconds=1),
        )

        picking = sale_order.picking_ids[0]
        picking.move_ids.picked = True
        picking._action_done()
        self.assertEqual(picking.state, "done", "Picking not processed correctly!")
        self.assertEqual(
            fields.Date.today(),
            sale_order.date_effective.date(),
            "Wrong effective date on sale order!",
        )

    def test_sale_order_commitment_date(self):

        new_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.env["res.partner"]
                    .create({"name": "A Partner"})
                    .id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.env["product.product"]
                                .create(
                                    {
                                        "name": "A product",
                                        "is_storable": True,
                                    }
                                )
                                .id,
                                "price_unit": 750,
                            }
                        )
                    ],
                    "date_commitment": "2010-07-12",
                }
            )
        )
        new_order.action_confirm()
        security_delay = timedelta(
            days=new_order.company_id.sale_config_id.security_lead
        )
        commitment_date = fields.Datetime.from_string(new_order.date_commitment)
        right_date = commitment_date - security_delay
        for line in new_order.line_ids:
            self.assertEqual(
                line.move_ids[0].date,
                right_date,
                "The expected date for the Stock Move is wrong",
            )

    def test_expected_date_with_storable_product(self):
        sale_delay = 10.0
        self.product.sale_delay = sale_delay

        sale_order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.partner.id,
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.product.id,
                                "product_qty": 1000,
                            }
                        )
                    ],
                }
            )
        )

        self.assertEqual(
            sale_order.date_planned, fields.Datetime.now() + timedelta(days=sale_delay)
        )

        sale_order.write(
            {
                "line_ids": [
                    Command.create(
                        {
                            "product_id": self.service_product.id,
                            "product_qty": 1000,
                        }
                    )
                ],
            }
        )
        self.assertEqual(
            sale_order.date_planned, fields.Datetime.now() + timedelta(days=sale_delay)
        )

    def test_invoice_delivery_date(self):
        self.env["stock.quant"]._update_available_quantity(
            self.test_product_order,
            self.company_data["default_warehouse"].lot_stock_id,
            75.0,
        )
        order = (
            self.env["sale.order"]
            .sudo()
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "picking_policy": "one",
                    "line_ids": [
                        Command.create(
                            {
                                "product_id": self.test_product_order.id,
                                "product_qty": 100.0,
                            }
                        )
                    ],
                }
            )
        )
        order.action_confirm()
        picking_1 = order.picking_ids
        picking_1.move_ids.picked = True
        invoice = order._create_invoices()
        self.assertFalse(invoice.delivery_date)
        picking_1._action_done()
        self.assertTrue(
            order.date_effective, "Effective date should exist after done picking"
        )
        effective_date = order.date_effective.date()
        self.assertEqual(
            invoice.delivery_date,
            effective_date,
            "Default invoice delivery date should equal effective date",
        )

        self.env["stock.quant"]._update_available_quantity(
            self.test_product_order,
            self.company_data["default_warehouse"].lot_stock_id,
            25.0,
        )
        with freeze_time(effective_date + timedelta(days=3)):
            custom_delivery_date = fields.Date.today()
            picking_2 = (order.picking_ids - picking_1).check_singleton()
            picking_2.move_ids.write({"quantity": 25.0, "picked": True})
            picking_2._action_done()
            self.assertEqual(
                invoice.delivery_date,
                effective_date,
                "Invoice delivery date should default to earliest picking date",
            )
            product_line = invoice.line_ids[0]
            invoice.write(
                {
                    "delivery_date": custom_delivery_date,
                    "line_ids": [Command.update(product_line.id, {"quantity": 0.0})],
                }
            )
            product_line.quantity += 75.0
            self.assertEqual(
                invoice.delivery_date,
                custom_delivery_date,
                "Custom invoice delivery shouldn't change after line change",
            )
            invoice.action_post()
            self.assertEqual(
                invoice.delivery_date,
                custom_delivery_date,
                "Custom invoice delivery shouldn't change posting invoice",
            )
            invoice.action_draft()
            self.assertEqual(
                invoice.delivery_date,
                custom_delivery_date,
                "Custom invoice delivery shouldn't change resetting to draft invoice",
            )
