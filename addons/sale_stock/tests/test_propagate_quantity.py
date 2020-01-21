# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock.tests.common2 import TestStockCommon

from odoo.exceptions import UserError
from odoo.tests import Form


class TestSalePropagate(TestStockCommon):
    def _create_sale_order(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_1.id,
            'partner_invoice_id': self.partner_1.id,
            'partner_shipping_id': self.partner_1.id,
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
            'warehouse_id': self.warehouse_1.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_2.name,
                    'product_id': self.product_2.id,
                    'product_uom_qty': 5,
                    'product_uom': self.uom_unit.id,
                })
            ]
        })
        order.action_confirm()
        return order

    def test_basic_propagate_1(self):
        """Propagation of decreasing quantity to delivery picking."""

        order = self._create_sale_order()
        out = order.picking_ids

        # Decrease quantity on SO
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 3})]})

        # The 3 pickings should be updated as well
        self.assertEqual(out.move_lines[0].product_uom_qty, 3)

    def test_basic_propagate_2(self):
        """Propagation of decreasing quantity through validated picking.

        The ship is returned partially. So the delivered
        quantity < ordered quantity. Decreasing the quantity to be equal to the
        delivery one should not impact any picking
        """
        order = self._create_sale_order()
        out = order.picking_ids
        # Validate all pickings one
        out.move_lines[0].quantity_done = 5
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
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 3})]})

        # The two confirmed picking are updated
        self.assertEqual(len(order.picking_ids), 2)  # 1 ship + 1 return
        self.assertEqual(sorted(order.picking_ids.mapped('state')), ['done'] * 2)
        self.assertEqual(out.move_lines[0].product_uom_qty, 5)

    def test_basic_propagate_3(self):
        """Propagation of decreasing quantity through validated picking.

        The ship is returned partially. So the delivered
        quantity < ordered quantity. Decreasing the quantity on the sale order but
        still superior to the delivery one should create a new picking
        """
        order = self._create_sale_order()

        out = order.picking_ids

        # Validate all pickings one
        out.move_lines[0].quantity_done = 5
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
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 4})]})

        # The two confirmed picking are updated
        self.assertEqual(len(order.picking_ids), 3)  # 3 steps + 1 return
        self.assertEqual(len(order.picking_ids.filtered(lambda p: p.state == 'done')), 2)
        self.assertEqual(out.move_lines[0].product_uom_qty, 5)
        out2 = order.picking_ids.filtered(lambda r: r.state != 'done')
        self.assertEqual(out2.move_lines[0].product_uom_qty, 1)

    def test_basic_propagate_4(self):
        """Propagation of decreasing quantity to validated picking."""

        order = self._create_sale_order()
        out = order.picking_ids

        # Validate the first one
        out.move_lines[0].quantity_done = 5
        out._action_done()

        # Decrease quantity on SO
        with self.assertRaises(UserError):
            order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 3})]})

    def test_propagate_1(self):
        """Propagation of decreasing quantity through confirmed pickings."""
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        order = self._create_sale_order()

        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.out_type_id)
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)

        # Decrease quantity on SO
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 3})]})

        # The 3 pickings should be updated as well
        self.assertEqual(out.move_lines[0].product_uom_qty, 3)
        self.assertEqual(pack.move_lines[0].product_uom_qty, 3)
        self.assertEqual(pick.move_lines[0].product_uom_qty, 3)

    def test_propagate_2(self):
        """Propagation of decreasing quantity through semi validated pickings chain.

        second picking (pack) is validated, Only the last confirmed pickings is
        updated.
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        order = self._create_sale_order()

        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.out_type_id)
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)

        # Validate the first one
        pack.move_lines.quantity_done = 5
        pack._action_done()
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 3})]})

        # The two confirmed picking are updated
        self.assertEqual(out.move_lines[0].product_uom_qty, 3)
        self.assertEqual(pick.move_lines[0].product_uom_qty, 5)

    def test_propagate_3(self):
        """Propagation of decreasing quantity through validated pickings.

        All pickings are validated. The ship is returned partially. So the delivered
        quantity < ordered quantity. Decreasing the quantity on the sale order to
        the delivery one should not update any stock move
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        order = self._create_sale_order()

        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.out_type_id)
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)

        # Validate all pickings one
        pick.move_lines.quantity_done = 5
        pack.move_lines.quantity_done = 5
        out.move_lines.quantity_done = 5
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
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 3})]})

        # The two confirmed picking are updated
        self.assertEqual(len(order.picking_ids), 4)  # 3 steps + 1 return
        self.assertEqual(order.picking_ids.mapped('state'), ['done'] * 4)
        self.assertEqual(pick.move_lines[0].product_uom_qty, 5)
        self.assertEqual(pack.move_lines[0].product_uom_qty, 5)
        self.assertEqual(out.move_lines[0].product_uom_qty, 5)

    def test_propagate_4(self):
        """Propagation of decreasing quantity through validated pickings.

        All pickings are validated. Decreasing the quantity on the sale order
        should trigger an error.
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        order = self._create_sale_order()

        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.out_type_id)
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)

        # Validate all pickings one
        pick.move_lines.quantity_done = 5
        pack.move_lines.quantity_done = 5
        out.move_lines.quantity_done = 5
        order.picking_ids._action_done()
        with self.assertRaises(UserError):
            order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 3})]})

    def test_propagate_5(self):
        """Propagation of decreasing quantity through validated pickings.

        All pickings are validated. The ship is returned partially. So the delivered
        quantity < ordered quantity. Decreasing the quantity on the sale order but
        still superior to the delivery one should create a new chain of picking
        """
        # Update warehouse_1 with Outgoing Shippings pick + pack + ship
        self.warehouse_1.write({'delivery_steps': 'pick_pack_ship'})

        order = self._create_sale_order()

        out = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.out_type_id)
        pack = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id)
        pick = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id)

        # Validate all pickings one
        pick.move_lines.quantity_done = 5
        pack.move_lines.quantity_done = 5
        out.move_lines.quantity_done = 5
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
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 4})]})

        # The two confirmed picking are updated
        self.assertEqual(len(order.picking_ids), 7)  # 3 steps + 1 return
        self.assertEqual(len(order.picking_ids.filtered(lambda p: p.state == 'done')), 4)
        self.assertEqual(len(order.picking_ids.filtered(lambda p: p.state == 'waiting')), 2)
        self.assertEqual(pick.move_lines[0].product_uom_qty, 5)
        self.assertEqual(pack.move_lines[0].product_uom_qty, 5)
        self.assertEqual(out.move_lines[0].product_uom_qty, 5)
        out2 = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.out_type_id and r.state != 'done')
        pack2 = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pack_type_id and r.state != 'done')
        pick2 = order.picking_ids.filtered(lambda r: r.picking_type_id == self.warehouse_1.pick_type_id and r.state != 'done')
        self.assertEqual(pick2.move_lines[0].product_uom_qty, 1)
        self.assertEqual(pack2.move_lines[0].product_uom_qty, 1)
        self.assertEqual(out2.move_lines[0].product_uom_qty, 1)
