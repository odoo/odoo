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

    def test_sale_mrp_pickings(self):
        """ Test sale of multiple mrp products in MTO
        to avoid generating multiple deliveries
        to the customer location
        """

        # Create warehouse
        self.customer_location = self.env['ir.model.data'].xmlid_to_res_id('stock.stock_location_customers')
        warehouse_form = Form(self.env['stock.warehouse'])
        warehouse_form.name = 'Test Warehouse'
        warehouse_form.code = 'TWH'
        self.warehouse = warehouse_form.save()

        self.uom_unit = self.env.ref('uom.product_uom_unit')

        # Create raw product for manufactured product
        product_form = Form(self.env['product.product'])
        product_form.name = 'Raw Stick'
        product_form.type = 'product'
        product_form.uom_id = self.uom_unit
        product_form.uom_po_id = self.uom_unit
        self.raw_product = product_form.save()

        # Create manufactured product
        product_form = Form(self.env['product.product'])
        product_form.name = 'Stick'
        product_form.uom_id = self.uom_unit
        product_form.uom_po_id = self.uom_unit
        product_form.type = 'product'
        product_form.route_ids.clear()
        product_form.route_ids.add(self.warehouse.manufacture_pull_id.route_id)
        product_form.route_ids.add(self.warehouse.mto_pull_id.route_id)
        self.finished_product = product_form.save()

        # Create manifactured product which uses another manifactured
        product_form = Form(self.env['product.product'])
        product_form.name = 'Arrow'
        product_form.type = 'product'
        product_form.route_ids.clear()
        product_form.route_ids.add(self.warehouse.manufacture_pull_id.route_id)
        product_form.route_ids.add(self.warehouse.mto_pull_id.route_id)
        self.complex_product = product_form.save()

        ## Create raw product for manufactured product
        product_form = Form(self.env['product.product'])
        product_form.name = 'Raw Iron'
        product_form.type = 'product'
        product_form.uom_id = self.uom_unit
        product_form.uom_po_id = self.uom_unit
        self.raw_product_2 = product_form.save()

        # Create bom for manufactured product
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.finished_product
        bom_product_form.product_tmpl_id = self.finished_product.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'normal'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.raw_product
            bom_line.product_qty = 2.0

        self.bom = bom_product_form.save()

        ## Create bom for manufactured product
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.complex_product
        bom_product_form.product_tmpl_id = self.complex_product.product_tmpl_id
        with bom_product_form.bom_line_ids.new() as line:
            line.product_id = self.finished_product
            line.product_qty = 1.0
        with bom_product_form.bom_line_ids.new() as line:
            line.product_id = self.raw_product_2
            line.product_qty = 1.0

        self.complex_bom = bom_product_form.save()

        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.env.ref('base.res_partner_4')
        with so_form.order_line.new() as line:
            line.product_id = self.complex_product
            line.price_unit = 1
            line.product_uom_qty = 1
        with so_form.order_line.new() as line:
            line.product_id = self.finished_product
            line.price_unit = 1
            line.product_uom_qty = 1
        sale_order_so0 = so_form.save()

        sale_order_so0.action_confirm()

        pickings = sale_order_so0.picking_ids

        # One delivery...
        self.assertEqual(len(pickings), 1)

        # ...with two products
        move_lines = pickings[0].move_lines
        self.assertEqual(len(move_lines), 2)
