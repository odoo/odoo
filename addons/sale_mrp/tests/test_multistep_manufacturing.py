# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMultistepManufacturing(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Required for `uom_id ` to be visible in the view
        cls.env.user.groups_id += cls.env.ref('uom.group_uom')
        # Required for `manufacture_steps` to be visible in the view
        cls.env.user.groups_id += cls.env.ref('stock.group_adv_location')
        # Required for `product_id` to be visible in the view
        cls.env.user.groups_id += cls.env.ref('product.group_product_variant')

        cls.env.ref('stock.route_warehouse0_mto').active = True
        cls.MrpProduction = cls.env['mrp.production']
        # Create warehouse
        warehouse_form = Form(cls.env['stock.warehouse'])
        warehouse_form.name = 'Test'
        warehouse_form.code = 'Test'
        cls.warehouse = warehouse_form.save()
        cls.warehouse.mto_pull_id.route_id.rule_ids.procure_method = "make_to_order"

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Create manufactured product
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Stick'
        product_form.uom_id = cls.uom_unit
        product_form.uom_po_id = cls.uom_unit
        product_form.route_ids.clear()
        product_form.route_ids.add(cls.warehouse.manufacture_pull_id.route_id)
        product_form.route_ids.add(cls.warehouse.mto_pull_id.route_id)
        cls.product_manu = product_form.save()

        # Create raw product for manufactured product
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Raw Stick'
        product_form.uom_id = cls.uom_unit
        product_form.uom_po_id = cls.uom_unit
        cls.product_raw = product_form.save()

        # Create bom for manufactured product
        bom_product_form = Form(cls.env['mrp.bom'])
        bom_product_form.product_id = cls.product_manu
        bom_product_form.product_tmpl_id = cls.product_manu.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'normal'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.product_raw
            bom_line.product_qty = 2.0
        cls.bom_prod_manu = bom_product_form.save()

        # Create sale order
        sale_form = Form(cls.env['sale.order'])
        sale_form.partner_id = cls.env['res.partner'].create({'name': 'My Test Partner'})
        sale_form.picking_policy = 'direct'
        sale_form.warehouse_id = cls.warehouse
        with sale_form.order_line.new() as line:
            line.name = cls.product_manu.name
            line.product_id = cls.product_manu
            line.product_uom_qty = 1.0
            line.product_uom = cls.uom_unit
            line.price_unit = 10.0
        cls.sale_order = sale_form.save()

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
        mo = self.env['mrp.production'].search([
            ('origin', '=', self.sale_order.name),
            ('product_id', '=', self.product_manu.id),
        ])
        self.assertEqual(self.sale_order.action_view_mrp_production()['res_id'], mo.id)
        self.assertEqual(mo_procurement.location_src_id.id, self.warehouse.pbm_loc_id.id, "Source loction does not match.")
        self.assertEqual(mo_procurement.location_dest_id.id, self.warehouse.lot_stock_id.id, "Destination location does not match.")

        self.assertEqual(len(mo_procurement), 1, "No Procurement !")

    def test_cancel_multilevel_manufacturing(self):
        """ Testing for multilevel Manufacturing orders.
            When user creates multi-level manufacturing orders,
            and then cancelles child manufacturing order,
            an activity should be generated on parent MO, to notify user that
            demands from child MO has been cancelled.
        """

        product_form = Form(self.env['product.product'])
        product_form.name = 'Screw'
        self.product_screw = product_form.save()

        # Add routes for manufacturing and make to order to the raw material product
        with Form(self.product_raw) as p1:
            p1.route_ids.clear()
            p1.route_ids.add(self.warehouse_1.manufacture_pull_id.route_id)
            p1.route_ids.add(self.warehouse_1.mto_pull_id.route_id)

        # New BoM for raw material product, it will generate another Production order i.e. child Production order
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.product_raw
        bom_product_form.product_tmpl_id = self.product_raw.product_tmpl_id
        bom_product_form.product_qty = 1.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.product_screw
            bom_line.product_qty = 5.0
        self.bom_prod_manu = bom_product_form.save()

        # create MO from sale order.
        self.sale_order.action_confirm()
        # Find child MO.
        child_manufaturing = self.env['mrp.production'].search([('product_id', '=', self.product_raw.id)])
        self.assertTrue((len(child_manufaturing.ids) == 1), 'Manufacturing order of raw material must be generated.')
        # Cancel child MO.
        child_manufaturing.action_cancel()
        manufaturing_from_so = self.env['mrp.production'].search([('product_id', '=', self.product_manu.id)])
        # Check if activity is generated or not on parent MO.
        exception = self.env['mail.activity'].search([('res_model', '=', 'mrp.production'),
                                                      ('res_id', '=', manufaturing_from_so.id)])
        self.assertEqual(len(exception.ids), 1, 'When user cancelled child manufacturing, exception must be generated on parent manufacturing.')

    def test_manufacturing_step_three(self):
        """ Testing for Step-3 """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
        self.sale_order.action_confirm()

        mo = self.env['mrp.production'].search([
            ('origin', '=', self.sale_order.name),
            ('product_id', '=', self.product_manu.id),
        ])

        self.assertEqual(self.sale_order.mrp_production_count, 1)
        self.assertEqual(mo.sale_order_count, 1)

        self.assertEqual(self.sale_order.action_view_mrp_production()['res_id'], mo.id)
        self.assertEqual(mo.action_view_sale_orders()['res_id'], self.sale_order.id)
