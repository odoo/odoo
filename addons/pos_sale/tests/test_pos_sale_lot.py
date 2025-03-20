# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleDataHttpCommon):
    def test_ship_later_lots(self):
        self.env.user.group_ids += self.env.ref('sales_team.group_sale_salesman')
        self.pos_config.open_ui()

        # set up product iwith SN tracing and create two lots (1001, 1002)
        self.stock_warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.company_data['company'].id)],
            limit=1,
        )
        self.product_awesome_item.product_variant_id.write({
            'tracking': 'serial',
            'is_storable': True,
            'lst_price': 10,
        })
        lot1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.product_awesome_item.product_variant_id.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': self.product_awesome_item.product_variant_id.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_awesome_item.product_variant_id.id,
            'inventory_quantity': 1,
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'lot_id': lot1.id
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_awesome_item.product_variant_id.id,
            'inventory_quantity': 1,
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'lot_id': lot2.id
        }).action_apply_inventory()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.product_awesome_item.product_variant_id.id,
                'name': self.product_awesome_item.product_variant_id.name,
                'product_uom_qty': 2,
                'price_unit': self.product_awesome_item.product_variant_id.lst_price,
            })],
        })
        sale_order.action_confirm()

        order = self.make_order_data([
            {
                'product_id': self.product_awesome_item.product_variant_id,
                'qty': 2,
                'discount': 0,
                'pack_lot_ids': [[0, 0, {'lot_name': lot1.name}]],
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 10},
        ], False, False, self.partner_one, True)
        order['date_order'] = fields.Datetime.to_string(fields.Datetime.now())
        order['shipping_date'] = fields.Date.today()

        order_data = self.env['pos.order'].sync_from_ui([order])
        order = self.env['pos.order'].browse(order_data['pos.order'][0]['id'])
        self.assertEqual(order.picking_ids.move_line_ids.lot_id, lot1)
