from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from .common import TestSaleStockCommon


@tagged("post_install", "-at_install")
class TestSaleStockRegressions(TestSaleStockCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Regression Customer"})
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )

    def _storable(self, name, qty=0.0):
        product = self.env["product.product"].create(
            {"name": name, "is_storable": True, "type": "consu"}
        )
        if qty:
            self.env["stock.quant"]._update_available_quantity(
                product, self.warehouse.lot_stock_id, qty
            )
        return product

    def _return(self, picking, quantity):
        wizard = (
            self.env["stock.return.picking"]
            .with_context(active_id=picking.id, active_model="stock.picking")
            .create({})
        )
        for line in wizard.product_return_moves:
            line.quantity = quantity
        return_picking = wizard._create_return()
        return_picking.move_ids.write({"quantity": quantity, "picked": True})
        return_picking._action_done()
        return return_picking

    def _order(self, lines, **vals):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "warehouse_id": self.warehouse.id,
                "line_ids": [
                    Command.create({"product_id": p.id, "product_qty": q})
                    for p, q in lines
                ],
                **vals,
            }
        )
        order.action_confirm()
        return order

    def test_qty_at_date_does_not_accumulate_across_lines(self):
        a = self._storable("QAD A", 100)
        b = self._storable("QAD B", 100)
        c = self._storable("QAD C", 100)
        order = self._order([(a, 5), (b, 7), (c, 11)])
        self.env.invalidate_all()

        self.assertEqual(
            order.line_ids.mapped("qty_available_today"),
            [5.0, 7.0, 11.0],
            "a line's available quantity absorbed the earlier lines' moves",
        )
        self.assertEqual(
            order.line_ids.mapped("qty_free_today"),
            [5.0, 7.0, 11.0],
        )

    def test_qty_at_date_same_product_on_two_lines(self):
        product = self._storable("QAD SAME", 100)
        order = self._order([(product, 3), (product, 4)])
        self.env.invalidate_all()
        self.assertEqual(order.line_ids.mapped("qty_available_today"), [3.0, 4.0])

    def test_qty_at_date_excludes_done_moves(self):
        product = self._storable("QAD PART", 100)
        order = self._order([(product, 10)])
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 4, "picked": True})
        picking._action_done()
        self.env.invalidate_all()
        self.assertEqual(order.line_ids.qty_available_today, 6.0)

    def test_on_time_rate_counts_confirmed_orders(self):
        product = self._storable("OTR OK", 100)
        order = self._order(
            [(product, 10)],
            date_commitment=fields.Datetime.now() + timedelta(days=7),
        )
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking._action_done()
        self.env.invalidate_all()
        self.assertEqual(self.customer.customer_on_time_rate, 100.0)

    def test_on_time_rate_counts_late_delivery_as_zero(self):
        product = self._storable("OTR LATE", 100)
        order = self._order(
            [(product, 10)],
            date_commitment=fields.Datetime.now() - timedelta(days=7),
        )
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking._action_done()
        self.env.invalidate_all()
        self.assertEqual(self.customer.customer_on_time_rate, 0.0)

    def test_on_time_rate_without_history_is_negative_sentinel(self):
        partner = self.env["res.partner"].create({"name": "No history"})
        self.assertEqual(partner.customer_on_time_rate, -1)

    def test_on_time_rate_converts_the_delivered_quantity(self):
        uom_dozen = self.env.ref("uom.product_uom_dozen")
        product = self._storable("OTR UOM", 1000)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "warehouse_id": self.warehouse.id,
                "date_commitment": fields.Datetime.now() + timedelta(days=7),
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 1,
                            "product_uom_id": uom_dozen.id,
                        }
                    )
                ],
            }
        )
        order.action_confirm()
        picking = order.picking_ids
        for move in picking.move_ids:
            move.write({"quantity": move.product_uom_qty, "picked": True})
        picking._action_done()
        self.env.invalidate_all()
        self.assertEqual(self.customer.customer_on_time_rate, 100.0)

    def test_delay_report_records_are_readable(self):
        product = self._storable("DELAY RPT", 100)
        order = self._order(
            [(product, 6)],
            date_commitment=fields.Datetime.now() + timedelta(days=7),
        )
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 6, "picked": True})
        picking._action_done()
        self.env.invalidate_all()

        rows = self.env["customer.delay.report"].search(
            [("partner_id", "=", self.customer.id)]
        )
        self.assertTrue(rows)
        self.assertEqual(rows[0].qty_total, 6.0)
        self.assertEqual(rows[0].partner_id, self.customer)
        self.assertEqual(rows[0].on_time_rate, 100.0)
        self.assertTrue(rows.mapped("partner_id.name"))
        self.assertTrue(rows.read())
        self.assertTrue(
            self.env["customer.delay.report"].search([("on_time_rate", ">", 50)])
        )

    def test_delay_report_is_scoped_to_the_company(self):
        self.assertIn("company_id", self.env["customer.delay.report"]._fields)
        rules = (
            self.env["ir.rule"]
            .sudo()
            .search([("model_id.model", "=", "customer.delay.report")])
        )
        self.assertTrue(rules, "no record rule scopes the report to a company")

    def test_search_late_availability_negation_is_the_complement(self):
        product = self._storable("LATE MIX", 2)
        order = self._order([(product, 5)])
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 2, "picked": True})
        picking._action_done()
        self.env.invalidate_all()

        states = order.picking_ids.mapped("products_availability_state")
        self.assertIn("late", states)
        self.assertTrue(order.late_availability)

        Order = self.env["sale.order"]
        self.assertIn(
            order,
            Order.search([("id", "=", order.id), ("late_availability", "=", True)]),
        )
        self.assertNotIn(
            order,
            Order.search([("id", "=", order.id), ("late_availability", "=", False)]),
        )

    def test_cannot_return_a_delivery_that_never_shipped(self):
        product = self._storable("RET GUARD", 100)
        order = self._order([(product, 5)])
        picking = order.picking_ids
        self.assertNotEqual(picking.state, "done")
        self.assertFalse(picking._can_return())
        with self.assertRaises(UserError):
            self.env["stock.return.picking"].create({"picking_id": picking.id})

    def test_a_done_delivery_can_still_be_returned(self):
        product = self._storable("RET OK", 100)
        order = self._order([(product, 5)])
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 5, "picked": True})
        picking._action_done()
        self.assertTrue(picking._can_return())

    def test_write_line_ids_on_several_orders(self):
        product = self._storable("MULTI W", 100)
        first = self._order([(product, 5)])
        second = self._order([(product, 6)])
        (first | second).write(
            {"line_ids": [Command.update(first.line_ids[0].id, {"price_unit": 3.0})]}
        )
        self.assertEqual(first.line_ids[0].price_unit, 3.0)

    def test_reassigning_pickings_in_one_batch_moves_every_line(self):
        product = self._storable("REASSIGN", 100)
        first = self._order([(product, 2)])
        second = self._order([(product, 2)])
        target = self._order([(product, 2)])

        pickings = first.picking_ids | second.picking_ids
        pickings.write({"sale_id": target.id})
        self.env.invalidate_all()

        for picking in pickings:
            self.assertEqual(
                picking.move_ids.sale_line_id.order_id,
                target,
                "a batched reassignment left the moves on their old order",
            )

    def test_move_type_follows_the_picking_policy(self):
        product = self._storable("MOVE TYPE", 100)
        order = self._order([(product, 5)], picking_policy="direct")
        self.assertEqual(order.picking_ids.move_type, "direct")
        order.picking_policy = "one"
        self.env.flush_all()
        self.assertEqual(order.picking_ids.move_type, "one")

    def test_expense_policy_follows_is_storable(self):
        template = self.env["product.template"].create(
            {"name": "EXP POLICY", "type": "consu", "is_storable": False}
        )
        template.expense_policy = "cost"
        template.is_storable = True
        self.env.flush_all()
        self.assertEqual(template.expense_policy, "no")

    def test_json_popover_declares_its_dependency(self):
        field = self.env["sale.order"]._fields["json_popover"]
        self.assertTrue(
            list(self.env.registry.field_depends.get(field, ())),
            "json_popover declares no dependency and never refreshes",
        )

    def test_lot_sale_orders_refresh_after_a_delivery(self):
        product = self.env["product.product"].create(
            {"name": "LOT SO", "is_storable": True, "type": "consu", "tracking": "lot"}
        )
        lot = self.env["stock.lot"].create(
            {"name": "LOT-SO-1", "product_id": product.id}
        )
        self.env["stock.quant"]._update_available_quantity(
            product, self.warehouse.lot_stock_id, 10, lot_id=lot
        )
        self.assertEqual(lot.sale_order_count, 0)
        order = self._order([(product, 3)])
        picking = order.picking_ids
        picking.move_ids.move_line_ids.quantity = 3
        picking.move_ids.picked = True
        picking._action_done()
        self.env.flush_all()
        self.assertEqual(lot.sale_order_count, 1)

    def test_compute_and_prepare_transferred_qty_agree(self):
        product = self._storable("QTY AGREE", 100)
        order = self._order([(product, 7)])
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 4, "picked": True})
        picking._action_done()
        self.env.invalidate_all()
        line = order.line_ids
        self.assertEqual(line.qty_transferred, 4.0)
        self.assertEqual(line._prepare_qty_transferred()[line], line.qty_transferred)

    def test_on_time_rate_ignores_a_later_return(self):
        product = self._storable("OTR RETURN", 100)
        order = self._order(
            [(product, 10)],
            date_commitment=fields.Datetime.now() + timedelta(days=7),
        )
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking._action_done()
        self._return(picking, 3)
        self.env.invalidate_all()
        self.assertEqual(
            self.customer.customer_on_time_rate,
            100.0,
            "a return move was counted as an extra on-time delivery",
        )

    def test_delay_report_ignores_a_later_return(self):
        product = self._storable("DELAY RETURN", 100)
        order = self._order(
            [(product, 10)],
            date_commitment=fields.Datetime.now() + timedelta(days=7),
        )
        picking = order.picking_ids
        picking.move_ids.write({"quantity": 10, "picked": True})
        picking._action_done()
        self._return(picking, 3)
        self.env.invalidate_all()

        row = self.env["customer.delay.report"].search(
            [("partner_id", "=", self.customer.id), ("product_id", "=", product.id)]
        )
        self.assertEqual(row.qty_total, 10.0)
        self.assertEqual(
            row.on_time_rate,
            100.0,
            "a return move was counted as extra on-time quantity",
        )
