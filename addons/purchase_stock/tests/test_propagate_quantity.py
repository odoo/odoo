# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import Form
from .common import PurchaseTestCommon


class TestPurchasePropagation(PurchaseTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)

    def _create_purchase_order(self):
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_1.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_2.name,
                    'product_id': self.product_2.id,
                    'product_qty': 5,
                    'product_uom': self.product_2.uom_po_id.id,
                    'price_unit': 10,
                    'date_planned': datetime.now(),
                })]
        })
        purchase_order.button_confirm()
        return purchase_order

    def test_basic_propagate_1(self):
        """Propagation of decreasing quantity to receipt picking."""

        order = self._create_purchase_order()
        out = order.picking_ids

        # Decrease quantity on SO
        order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 3})]})

        # The 3 pickings should be updated as well
        self.assertEqual(out.move_lines[0].product_uom_qty, 3)

    def test_basic_propagate_2(self):
        """Propagation of decreasing quantity through validated picking.

        The receipt is returned partially. So the delivered
        quantity < ordered quantity. Decreasing the quantity to be equal to the
        received one should not impact any picking.
        """
        order = self._create_purchase_order()

        out = order.picking_ids

        # Validate all pickings one
        out.move_lines[0].move_line_ids[0].qty_done = 5
        order.picking_ids._action_done()
        # Return 2 quantity from the ship
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=out.ids,
                active_id=out.ids[0],
                active_model='stock.picking'
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 2
        return_pick._action_done()
        order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 3})]})

        # The two confirmed picking are updated
        self.assertEqual(len(order.picking_ids), 2)  # 1 receipt + 1 return
        self.assertEqual(sorted(order.picking_ids.mapped('state')), ['done'] * 2)
        self.assertEqual(out.move_lines[0].product_uom_qty, 5)

    def test_basic_propagate_3(self):
        """Propagation of decreasing quantity through validated picking.

        The receipt is returned partially. So the received
        quantity < ordered quantity. Decreasing the quantity on the purchase order
        but still superior to the receipt one should create a new picking.
        """
        order = self._create_purchase_order()

        out = order.picking_ids

        # Validate all pickings one
        out.move_lines[0].move_line_ids[0].qty_done = 5
        order.picking_ids._action_done()
        # Return 2 quantity from the ship
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=out.ids,
                active_id=out.ids[0],
                active_model='stock.picking'
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 2
        return_pick._action_done()
        order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 4})]})

        # The two confirmed picking are updated
        self.assertEqual(len(order.picking_ids), 3)  # 1 receipt + 1 return + 1 extra
        self.assertEqual(sorted(order.picking_ids.mapped('state')), ['assigned'] + ['done'] * 2)
        self.assertEqual(out.move_lines[0].product_uom_qty, 5)
        out2 = order.picking_ids.filtered(lambda r: r.state != 'done')
        self.assertEqual(out2.move_lines[0].product_uom_qty, 1)

    def test_basic_propagate_4(self):
        """Propagation of decreasing quantity to validated picking."""

        order = self._create_purchase_order()
        out = order.picking_ids

        # Validate the first one
        out.move_lines.quantity_done = 5
        out._action_done()

        # Decrease quantity on PO
        with self.assertRaises(UserError):
            order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 3})]})

    def test_propagate_1(self):
        """Propagation of decreasing quantity through confirmed pickings."""
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse.write({'reception_steps': 'three_steps'})

        order = self._create_purchase_order()
        picking_ids = self.env['stock.picking'].search([('origin', '=', order.name)])

        self.assertEqual(len(picking_ids), 3)

        # Decrease quantity on SO
        order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 3})]})

        # The 3 pickings should be updated as well
        for pick in picking_ids:
            self.assertEqual(pick.move_lines.product_uom_qty, 3)

    def test_propagate_2(self):
        """Propagation of decreasing quantity through semi validated pickings chain.

        second picking (pack) is validated, Only the last confirmed pickings is
        updated.
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse.write({'reception_steps': 'three_steps'})

        order = self._create_purchase_order()
        picking_ids = self.env['stock.picking'].search([('origin', '=', order.name)])
        input = picking_ids.filtered(lambda r: r.picking_type_id == order.picking_type_id)
        warehouse = order.picking_type_id.warehouse_id
        internals = picking_ids.filtered(lambda r: r.picking_type_id == warehouse.int_type_id).sorted(lambda p: p.name)
        # Validate the first one
        internals[0].move_lines.quantity_done = 5
        internals[0]._action_done()
        order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 3})]})

        # The two confirmed picking are updated
        self.assertEqual(internals[1].move_lines.product_uom_qty, 5)
        self.assertEqual(input.move_lines.product_uom_qty, 3)

    def test_propagate_3(self):
        """Propagation of decreasing quantity through validated pickings.

        All pickings are validated. The ship is returned partially. So the delivered
        quantity < received quantity. Decreasing the quantity on the purchase order to
        the receipt one should not update any stock move
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse.write({'reception_steps': 'three_steps'})

        order = self._create_purchase_order()
        picking_ids = self.env['stock.picking'].search([('origin', '=', order.name)]).sorted(lambda p: p.id)

        # Validate all pickings
        for picking_id in picking_ids:
            picking_id.move_lines.quantity_done = 5
            picking_id._action_done()

        # Return 2 quantity from the input
        input = picking_ids.filtered(lambda r: r.picking_type_id == order.picking_type_id)
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=input.ids,
                active_id=input.ids[0],
                active_model='stock.picking'
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 2
        return_pick._action_done()
        order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 3})]})

        # The two confirmed picking are updated
        all_picking_ids = picking_ids | return_pick
        self.assertEqual(len(all_picking_ids), 4)  # 3 steps + 1 return
        self.assertEqual(all_picking_ids.mapped('state'), ['done'] * 4)
        for picking_id in picking_ids:
            self.assertEqual(picking_id.move_lines.product_uom_qty, 5)

    def test_propagate_4(self):
        """Propagation of decreasing quantity through validated pickings.

        All pickings are validated. Decreasing the quantity on the purchase order
        should trigger an error.
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse.write({'reception_steps': 'three_steps'})

        order = self._create_purchase_order()

        picking_ids = self.env['stock.picking'].search([('origin', '=', order.name)]).sorted(lambda p: p.id)

        # Validate all pickings
        for picking_id in picking_ids:
            picking_id.move_lines.quantity_done = 5
            picking_id._action_done()

        with self.assertRaises(UserError):
            order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 3})]})

    def test_propagate_5(self):
        """Propagation of decreasing quantity through validated pickings.

        All pickings are validated. The input is returned partially. So the received
        quantity < ordered quantity. Decreasing the quantity on the purchase order
        but still superior to the receipt one should create a new chain of picking
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse.write({'reception_steps': 'three_steps'})

        order = self._create_purchase_order()

        picking_ids = self.env['stock.picking'].search([('origin', '=', order.name)]).sorted(lambda p: p.id)

        # Validate all pickings
        for picking_id in picking_ids:
            picking_id.move_lines.quantity_done = 5
            picking_id._action_done()
        # Return 2 quantity from the ship
        input = picking_ids.filtered(lambda r: r.picking_type_id == order.picking_type_id)
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=input.ids,
                active_id=input.ids[0],
                active_model='stock.picking'
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.action_assign()
        return_pick.move_lines.quantity_done = 2
        return_pick._action_done()
        order.write({'order_line': [(1, order.order_line[0].id, {'product_qty': 4})]})

        for picking_id in picking_ids:
            self.assertEqual(picking_id.move_lines.product_uom_qty, 5)

        picking_ids = self.env['stock.picking'].search([('origin', '=', order.name)]).sorted(lambda p: p.id) | return_pick
        self.assertEqual(len(picking_ids), 7)  # 3 steps two times + 1 return

        # 4 done (first chain and the return), 1 assigned (input picking), 2 waitings (two internal transfer)
        self.assertEqual(sorted(picking_ids.mapped('state')), ['assigned'] + ['done'] * 4 + ['waiting'] * 2)

        for picking_id in picking_ids.filtered(lambda p: p.state != 'done'):
            self.assertEqual(picking_id.move_lines[0].product_uom_qty, 1)
