# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMultistepManufacturing(TestMrpCommon):

    def setUp(self):
        super(TestMultistepManufacturing, self).setUp()

        self.MrpProduction = self.env['mrp.production']
        # Create warehouse
        warehouse_form = Form(self.env['stock.warehouse'])
        warehouse_form.name = 'Test'
        warehouse_form.code = 'Test'
        self.warehouse = warehouse_form.save()

        self.uom_unit = self.env.ref('uom.product_uom_unit')

        # Create manufactured product
        product_form = Form(self.env['product.product'])
        product_form.name = 'Stick'
        product_form.uom_id = self.uom_unit
        product_form.uom_po_id = self.uom_unit
        product_form.route_ids.clear()
        product_form.route_ids.add(self.warehouse.manufacture_pull_id.route_id)
        product_form.route_ids.add(self.warehouse.mto_pull_id.route_id)
        self.product_manu = product_form.save()

        # Create raw product for manufactured product
        product_form = Form(self.env['product.product'])
        product_form.name = 'Raw Stick'
        product_form.uom_id = self.uom_unit
        product_form.uom_po_id = self.uom_unit
        self.product_raw = product_form.save()

        # Create bom for manufactured product
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.product_manu
        bom_product_form.product_tmpl_id = self.product_manu.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'normal'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.product_raw
            bom_line.product_qty = 2.0
        self.bom_prod_manu = bom_product_form.save()

        # Create sale order
        sale_form = Form(self.env['sale.order'])
        sale_form.partner_id = self.env.ref('base.res_partner_1')
        sale_form.picking_policy = 'direct'
        sale_form.warehouse_id = self.warehouse
        with sale_form.order_line.new() as line:
            line.name = self.product_manu.name
            line.product_id = self.product_manu
            line.product_uom_qty = 1.0
            line.product_uom = self.uom_unit
            line.price_unit = 10.0
        self.sale_order = sale_form.save()

    def test_00_manufacturing_step_one(self):
        """ Testing for Step-1 """
        # Change steps of manufacturing.
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'mrp_one_step'
        # Confirm sale order.
        self.sale_order.action_confirm()
        # Check all procurements for created sale order
        mo_procurement = self.MrpProduction.search([('origin', '=', self.sale_order.name)])
        # Get manufactured procurement
        self.assertEqual(mo_procurement.location_src_id.id, self.warehouse.lot_stock_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")
        self.assertEqual(len(mo_procurement), 1, "No Procurement !")

    def test_01_manufacturing_step_two(self):
        """ Testing for Step-2 """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm'
        self.sale_order.action_confirm()
        # Get manufactured procurement
        mo_procurement = self.MrpProduction.search([('origin', '=', self.sale_order.name)])
        self.assertEqual(mo_procurement.location_src_id.id, self.warehouse.pbm_loc_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")

        self.assertEqual(len(mo_procurement), 1, "No Procurement !")
