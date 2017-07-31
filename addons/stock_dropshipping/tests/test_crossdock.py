# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestCrossdock(common.TransactionCase):

    def test_00_crossdock(self):

        # Create a supplier
        supplier_crossdock = self.env['res.partner'].create({'name': "Crossdocking supplier"})

        # I first create a warehouse with pick-pack-ship and reception in 2 steps
        wh_pps = self.env['stock.warehouse'].create({
            'name': 'WareHouse PickPackShip',
            'code': 'whpps',
            'reception_steps': 'two_steps',
            'delivery_steps': 'pick_pack_ship'
        })

        # Check that cross-dock route is active
        self.assertTrue(wh_pps.crossdock_route_id.active,
            "Crossdock route should be active when reception_steps is not in 'single_step'")

        # Create new product without any routes
        cross_shop_product = self.env['product.product'].create({
            'name': "PCE",
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_1').id,
            'list_price': 100.0,
            'standard_price': 70.0,
            'seller_ids': [(0, 0, {
                'delay': 1,
                'name': supplier_crossdock.id,
                'min_qty': 2.0
            })]
        })

        # Create a sales order with a line of 100 PCE incoming shipment with route_id crossdock shipping
        sale_order_crossdock = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_4').id,
            'warehouse_id': wh_pps.id,
            'note': 'Create Sales Order',
            'order_line': [(0, 0, {
                'product_id': cross_shop_product.id,
                'product_uom_qty': 100.0,
                'product_uom': self.env.ref('product.product_uom_unit').id,
                'route_id': wh_pps.crossdock_route_id.id,
            })]
        })

        # Confirm sales order
        sale_order_crossdock.action_confirm()

        # Run the scheduler
        self.env['procurement.group'].run_scheduler()

        # Check a quotation was created for the created supplier and confirm it
        self.env['purchase.order'].search([
            ('partner_id', '=', supplier_crossdock.id),
            ('state', '=', 'draft')
        ]).button_confirm()
