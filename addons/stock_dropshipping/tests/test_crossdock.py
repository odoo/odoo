# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form
from odoo.tools import mute_logger


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

        p_f = Form(self.env['product.template'])
        p_f.name = 'PCE'
        p_f.type = 'product'
        p_f.categ_id = self.env.ref('product.product_category_1')
        p_f.list_price = 100.0
        with p_f.seller_ids.new() as seller:
            seller.name = supplier_crossdock
        p_f.route_ids.add(wh_pps.crossdock_route_id)
        cross_shop_product = p_f.save()

        std_price_wiz = Form(self.env['stock.change.standard.price'].with_context(active_id=p_f.id, active_model='product.template'))
        std_price_wiz.new_price = 70.0
        std_price_wiz.save()

        # Create a sales order with a line of 100 PCE incoming shipment with route_id crossdock shipping
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.ref('base.res_partner_4')
        so_form.warehouse_id = wh_pps

        with mute_logger('odoo.tests.common.onchange'):
            # otherwise complains that there's not enough inventory and
            # apparently that's normal according to @jco and @sle
            with so_form.order_line.new() as line:
                line.product_id = cross_shop_product.product_variant_ids
                line.product_uom_qty = 100.0
            sale_order_crossdock = so_form.save()

        # Confirm sales order
        sale_order_crossdock.action_confirm()

        # Run the scheduler
        self.env['procurement.group'].run_scheduler()

        # Check a quotation was created for the created supplier and confirm it
        po = self.env['purchase.order'].search([
            ('partner_id', '=', supplier_crossdock.id),
            ('state', '=', 'draft')
        ])
        self.assertTrue(po, "an RFQ should have been created by the scheduler")
        po.button_confirm()
