from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import (
    ValuationReconciliationTestCommon,
)


@tagged("post_install", "-at_install")
class TestSaleStockLeadTime(TestSaleStockCommon, ValuationReconciliationTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_product_order.sale_delay = 5.0

    def test_00_product_company_level_delays(self):
        self.env.company.sale_config_id.security_lead = 3.00

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "picking_policy": "direct",
                "warehouse_id": self.company_data["default_warehouse"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.test_product_order.id,
                            "product_qty": 10,
                        },
                    )
                ],
            }
        )

        self.assertEqual(
            order.line_ids.customer_lead, self.test_product_order.sale_delay
        )

        order.action_confirm()

        self.assertTrue(order.picking_ids, "Picking should be created.")

        out_date = (
            order.date_order
            + timedelta(days=self.test_product_order.sale_delay)
            - timedelta(days=self.env.company.sale_config_id.security_lead)
        )
        min_date = order.picking_ids[0].date_planned
        self.assertTrue(
            abs(min_date - out_date) <= timedelta(seconds=1),
            "Schedule date of picking should be equal to: order date + Customer Lead Time - Sales Safety Days.",
        )

    def test_01_product_route_level_delays(self):
        warehouse = self.warehouse_3_steps_pull

        for pull_rule in warehouse.delivery_route_id.rule_ids:
            pull_rule.write({"delay": 2})

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "picking_policy": "direct",
                "warehouse_id": warehouse.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.test_product_order.name,
                            "product_id": self.test_product_order.id,
                            "product_qty": 5,
                            "customer_lead": self.test_product_order.sale_delay,
                        },
                    )
                ],
            }
        )

        order.action_confirm()

        self.assertTrue(order.picking_ids, "Pickings should be created.")

        out = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.out_type_id
        )
        out_min_date = fields.Datetime.from_string(out.date_planned)
        out_date = (
            fields.Datetime.from_string(order.date_order)
            + timedelta(days=self.test_product_order.sale_delay)
            - timedelta(days=out.move_ids[0].rule_id.delay)
        )
        self.assertTrue(
            abs(out_min_date - out_date) <= timedelta(seconds=1),
            "Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.",
        )

        pack = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.pack_type_id
        )
        pack_min_date = fields.Datetime.from_string(pack.date_planned)
        pack_date = out_date - timedelta(days=pack.move_ids[0].rule_id.delay)
        self.assertTrue(
            abs(pack_min_date - pack_date) <= timedelta(seconds=1),
            "Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.",
        )

        pick = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.pick_type_id
        )
        pick_min_date = fields.Datetime.from_string(pick.date_planned)
        pick_date = pack_date - timedelta(days=pick.move_ids[0].rule_id.delay)
        self.assertTrue(
            abs(pick_min_date - pick_date) <= timedelta(seconds=1),
            "Schedule date of pick type picking should be equal to: Schedule date of pack type picking - pull rule delay.",
        )

    def test_02_delivery_date_propagation(self):

        self.env.company.sale_config_id.security_lead = 2.00
        warehouse = self.warehouse_3_steps_pull

        warehouse.delivery_route_id.rule_ids.write({"delay": 5})

        self.test_product_order.write({"is_storable": True, "sale_delay": 30.0})

        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "picking_policy": "direct",
                "warehouse_id": warehouse.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": self.test_product_order.name,
                            "product_id": self.test_product_order.id,
                            "product_qty": 5,
                            "customer_lead": self.test_product_order.sale_delay,
                        },
                    )
                ],
            }
        )

        order.action_confirm()

        self.assertEqual(len(order.picking_ids), 3)

        out = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.out_type_id
        )
        deadline_date = (
            order.date_order
            + timedelta(days=self.test_product_order.sale_delay)
            - timedelta(days=out.move_ids[0].rule_id.delay)
        )
        self.assertAlmostEqual(
            out.date_deadline,
            deadline_date,
            delta=timedelta(seconds=1),
            msg="Deadline date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay.",
        )
        out_date_planned = deadline_date - timedelta(
            days=self.env.company.sale_config_id.security_lead
        )
        self.assertAlmostEqual(
            out.date_planned,
            out_date_planned,
            delta=timedelta(seconds=1),
            msg="Schedule date of ship type picking should be equal to: order date + Customer Lead Time - pull rule delay - security_lead",
        )

        pack = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.pack_type_id
        )
        pack_date_planned = out_date_planned - timedelta(
            days=pack.move_ids[0].rule_id.delay
        )
        self.assertAlmostEqual(
            pack.date_planned,
            pack_date_planned,
            delta=timedelta(seconds=1),
            msg="Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.",
        )
        deadline_date -= timedelta(days=pack.move_ids[0].rule_id.delay)
        self.assertAlmostEqual(
            pack.date_deadline,
            deadline_date,
            delta=timedelta(seconds=1),
            msg="Deadline date of pack type picking should be equal to: Deadline date of ship type picking - pull rule delay.",
        )

        pick = order.picking_ids.filtered(
            lambda r: r.picking_type_id == warehouse.pick_type_id
        )
        pick_date_planned = pack_date_planned - timedelta(
            days=pick.move_ids[0].rule_id.delay
        )
        self.assertAlmostEqual(
            pick.date_planned,
            pick_date_planned,
            delta=timedelta(seconds=1),
            msg="Schedule date of pack type picking should be equal to: Schedule date of ship type picking - pull rule delay.",
        )
        deadline_date -= timedelta(days=pick.move_ids[0].rule_id.delay)
        self.assertAlmostEqual(
            pick.date_deadline,
            deadline_date,
            delta=timedelta(seconds=1),
            msg="Deadline date of pack type picking should be equal to: Deadline date of ship type picking - pull rule delay.",
        )

        new_deadline = deadline_date + timedelta(days=5)
        order.write({"date_commitment": new_deadline})

        self.assertEqual(out.date_deadline, new_deadline)
        new_deadline -= timedelta(days=pack.move_ids[0].rule_id.delay)
        self.assertEqual(pack.date_deadline, new_deadline)
        new_deadline -= timedelta(days=pick.move_ids[0].rule_id.delay)
        self.assertEqual(pick.date_deadline, new_deadline)

        order.date_commitment = False
        new_deadline = order.date_planned
        self.assertEqual(out.date_deadline, new_deadline)
        new_deadline -= timedelta(days=pack.move_ids.rule_id.delay)
        self.assertEqual(pack.date_deadline, new_deadline)
        new_deadline -= timedelta(days=pick.move_ids.rule_id.delay)
        self.assertEqual(pick.date_deadline, new_deadline)

    def test_03_product_company_level_delays(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "picking_policy": "direct",
                "warehouse_id": self.company_data["default_warehouse"].id,
            }
        )

        order_line = self.env["sale.order.line"].create(
            {
                "product_id": self.test_product_order.id,
                "product_qty": 10,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "order_id": order.id,
            }
        )

        self.assertEqual(order_line.customer_lead, self.test_product_order.sale_delay)

        order.action_confirm()

        self.assertTrue(order.picking_ids, "Picking should be created.")

        out_date = (
            order.date_order
            + timedelta(days=self.test_product_order.sale_delay)
            - timedelta(days=self.env.company.sale_config_id.security_lead)
        )
        min_date = order.picking_ids[0].date_planned
        self.assertTrue(
            abs(min_date - out_date) <= timedelta(seconds=1),
            "Schedule date of picking should be equal to: order date + Customer Lead Time - Sales Safety Days.",
        )
