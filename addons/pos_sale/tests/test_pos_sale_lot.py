# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleCommon):
    def test_ship_later_lots(self):
        # open pos session
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # set up product iwith SN tracing and create two lots (1001, 1002)
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.product = self.env['product.product'].create({
            'name': 'Product A',
            'tracking': 'serial',
            'is_storable': True,
            'lst_price': 10,
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        lot1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': self.product.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 1,
            'location_id': self.stock_location.id,
            'lot_id': lot1.id
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 1,
            'location_id': self.stock_location.id,
            'lot_id': lot2.id
        }).action_apply_inventory()

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_uom_qty': 2,
                'product_uom': self.product.uom_id.id,
                'price_unit': self.product.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        pos_order = {
           'amount_paid': 10,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': 10,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': partner_test.id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [[0, 0, {'lot_name': lot1.name}]],
              'price_unit': 10,
              'product_id': self.product.id,
              'price_subtotal': 10,
              'price_subtotal_incl': 10,
              'sale_order_line_id': sale_order.order_line[0].id,
              'sale_order_origin_id': sale_order.id,
              'qty': 1,
              'tax_ids': []}]],
           'name': 'Order 00044-003-0014',
           'session_id': current_session.id,
           'sequence_number': self.pos_config.journal_id.id,
           'shipping_date': fields.Date.today(),
           'payment_ids': [[0,
             0,
             {'amount': 10,
              'name': fields.Datetime.now(),
              'payment_method_id': self.pos_config.payment_method_ids[0].id}]],
           'uuid': '00044-003-0014',
           'last_order_preparation_change': '{}',
           'user_id': self.env.uid}

        order = self.env['pos.order'].sync_from_ui([pos_order])
        self.assertEqual(self.env['pos.order'].browse(order['pos.order'][0]['id']).picking_ids.move_line_ids.lot_id, lot1)
        self.assertEqual(sale_order.picking_ids.move_line_ids.lot_id, lot2)
