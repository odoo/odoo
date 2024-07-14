# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import fields
from datetime import timedelta
from odoo.tests.common import tagged

@tagged('post_install', '-at_install')
class TestPoSRental(TestPointOfSaleHttpCommon):
    def test_rental_with_lots(self):
        """ Test rental product with lots """
        self.tracked_product_id = self.env['product.product'].create({
            'name': 'Test2',
            'categ_id': self.env.ref('product.product_category_all').id,  # remove category if possible?
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'available_in_pos': True,
            'rent_ok': True,
            'type': 'product',
            'tracking': 'serial',
        })

        # Set Stock quantities

        self.lot_id1 = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "123456789",
            'company_id': self.env.company.id,
        })
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': self.lot_id1.id,
            'location_id': warehouse.lot_stock_id.id,
        })
        quants.action_apply_inventory()

        self.cust1 = self.env['res.partner'].create({
            'name': 'test_rental_1',
            'street': 'street',
            'city': 'city',
            'country_id': self.env.ref('base.be').id, })

        self.sale_order_id = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'partner_invoice_id': self.cust1.id,
            'partner_shipping_id': self.cust1.id,
            'rental_start_date': fields.Datetime.today(),
            'rental_return_date': fields.Datetime.today() + timedelta(days=3),
        })

        self.order_line_id2 = self.env['sale.order.line'].create({
            'order_id': self.sale_order_id.id,
            'product_id': self.tracked_product_id.id,
            'product_uom_qty': 0.0,
            'product_uom': self.tracked_product_id.uom_id.id,
            'price_unit': 250,
        })
        self.order_line_id2.write({'is_rental': True})
        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('stock.group_stock_user').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "OrderLotsRentalTour",
            login="pos_user",
        )
        self.main_pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(self.sale_order_id.order_line.pickedup_lot_ids.name, '123456789')
