# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests.common import tagged

from .common import PurchaseTestCommon


@tagged('post_install', '-at_install')
class TestUninstallPurchaseStock(PurchaseTestCommon):
    def test_qty_received_method(self):
        partner = self.env['res.partner'].create({'name': 'Test Partner'})
        purchase_order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'state': 'purchase',
            'order_line': [fields.Command.create({
                'product_id': self.product.id,
            })],
        })
        order_line = purchase_order.order_line
        stock_move = order_line.move_ids

        self.assertEqual(order_line.product_id.is_storable, True)

        stock_move.quantity = 1
        stock_move.picked = True
        stock_move.picking_id.button_validate()

        self.assertEqual(purchase_order.order_line.qty_received, 1)

        stock_moves_option = self.env['ir.model.fields.selection'].search([
            ('field_id.model', '=', 'purchase.order.line'),
            ('field_id.name', '=', 'qty_received_method'),
            ('value', '=', 'stock_moves'),
        ])

        stock_moves_option.sudo().with_context(force_delete=True).unlink()

        self.assertEqual(order_line.qty_received_method, 'manual')
        self.assertEqual(order_line.qty_received, 1)
