# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.tests.common import TransactionCase, Form
from odoo.tools import mute_logger


class TestSaleMrpProcurement(TransactionCase):

    def test_sale_mrp(self):
        warehouse0 = self.env.ref('stock.warehouse0')
        # In order to test the sale_mrp module in OpenERP, I start by creating a new product 'Slider Mobile'
        # I define product category Mobile Products Sellable.

        with mute_logger('odoo.tests.common.onchange'):
            # Suppress warning on "Changing your cost method" when creating a
            # product category
            pc = Form(self.env['product.category'])
        pc.name = 'Mobile Products Sellable'
        product_category_allproductssellable0 = pc.save()

        uom_unit = self.env.ref('uom.product_uom_unit')

        self.assertIn("seller_ids", self.env['product.template'].fields_get())

        # I define product for Slider Mobile.
        product = Form(self.env['product.template'])

        product.categ_id = product_category_allproductssellable0
        product.list_price = 200.0
        product.name = 'Slider Mobile'
        product.standard_price = 189.0
        product.type = 'product'
        product.uom_id = uom_unit
        product.uom_po_id = uom_unit
        product.route_ids.clear()
        product.route_ids.add(warehouse0.manufacture_pull_id.route_id)
        product.route_ids.add(warehouse0.mto_pull_id.route_id)
        product_template_slidermobile0 = product.save()

        with Form(self.env['mrp.bom']) as bom:
            bom.product_tmpl_id = product_template_slidermobile0

        # I create a sale order for product Slider mobile
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.ref('base.res_partner_4')
        with so_form.order_line.new() as line:
            line.product_id = product_template_slidermobile0.product_variant_ids
            line.price_unit = 200
            line.product_uom_qty = 500.0
            line.customer_lead = 7.0
        sale_order_so0 = so_form.save()

        # I confirm the sale order
        sale_order_so0.action_confirm()

        # I verify that a manufacturing order has been generated, and that its name and reference are correct
        mo = self.env['mrp.production'].search([('origin', 'like', sale_order_so0.name)], limit=1)
        self.assertTrue(mo, 'Manufacturing order has not been generated')
