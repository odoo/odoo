# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
    def test_ship_later_lots(self):
        self.env.user.group_ids += self.env.ref('account.group_account_manager')
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.twenty_dollars_no_tax.product_variant_id.write({
            'tracking': 'serial',
            'is_storable': True,
            'taxes_id': []
        })
        lot_1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'company_id': self.env.company.id,
        })
        lot_2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'inventory_quantity': 1,
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_1.id
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'inventory_quantity': 1,
            'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_2.id
        }).action_apply_inventory()

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_stva.id,
            'order_line': [(0, 0, {
                'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
                'name': self.twenty_dollars_no_tax.product_variant_id.name,
                'price_unit': self.twenty_dollars_no_tax.product_variant_id.lst_price,
                'product_uom_qty': 2,
            })],
        })
        sale_order.action_confirm()
        order, _ = self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_stva.id,
                'shipping_date': fields.Date.today(),
            },
            'line_data': [{
                'product_id': self.twenty_dollars_no_tax.product_variant_id.id,
                'pack_lot_ids': [[0, 0, {'lot_name': lot_1.name}]],
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            }],
            'payment_data': [
                {'payment_method_id': self.pos_config_usd.payment_method_ids[0].id}
            ]
        })
        self.assertEqual(order.picking_ids.move_line_ids.lot_id, lot_1)
