# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form


class TestCrossdock(common.TransactionCase):

    def test_00_crossdock(self):

        # Create a supplier
        supplier_crossdock = self.env['res.partner'].create({'name': "Crossdocking supplier"})

        # I first create a warehouse with pick-pack-ship and reception in 2 steps
        wh_f = Form(self.env['stock.warehouse'])
        wh_f.name = 'WareHouse PickPackShip'
        wh_f.code = 'whpps'
        wh_f.reception_steps = 'two_steps'
        wh_f.delivery_steps = 'pick_pack_ship'
        wh_pps = wh_f.save()

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
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.ref('base.res_partner_4')
        so_form.warehouse_id = wh_pps
        with so_form.order_line.new() as line:
            line.product_id = cross_shop_product
            line.product_uom_qty = 100.0
        sale_order_crossdock = so_form.save()

        # Confirm sales order
        sale_order_crossdock.action_confirm()

        # Run the scheduler
        self.env['procurement.group'].run_scheduler()

        # Check a quotation was created for the created supplier and confirm it
        self.env['purchase.order'].search([
            ('partner_id', '=', supplier_crossdock.id),
            ('state', '=', 'draft')
        ]).button_confirm()
