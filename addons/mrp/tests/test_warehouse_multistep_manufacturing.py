# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMultistepManufacturingWarehouse(TestMrpCommon):

    def setUp(self):
        super(TestMultistepManufacturingWarehouse, self).setUp()
        # Create warehouse
        self.customer_location = self.env['ir.model.data'].xmlid_to_res_id('stock.stock_location_customers')
        warehouse_form = Form(self.env['stock.warehouse'])
        warehouse_form.name = 'Test Warehouse'
        warehouse_form.code = 'TWH'
        self.warehouse = warehouse_form.save()

        self.uom_unit = self.env.ref('uom.product_uom_unit')

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

        # Create raw product for manufactured product
        product_form = Form(self.env['product.product'])
        product_form.name = 'Raw Stick'
        product_form.type = 'product'
        product_form.uom_id = self.uom_unit
        product_form.uom_po_id = self.uom_unit
        self.raw_product = product_form.save()

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

    def _check_location_and_routes(self):
        # Check manufacturing pull rule.
        self.assertTrue(self.warehouse.manufacture_pull_id)
        self.assertTrue(self.warehouse.manufacture_pull_id.active, self.warehouse.manufacture_to_resupply)
        self.assertTrue(self.warehouse.manufacture_pull_id.route_id)
        # Check new routes created or not.
        self.assertTrue(self.warehouse.pbm_route_id)
        # Check location should be created and linked to warehouse.
        self.assertTrue(self.warehouse.pbm_loc_id)
        self.assertEqual(self.warehouse.pbm_loc_id.active, self.warehouse.manufacture_steps != 'mrp_one_step', "Input location must be de-active for single step only.")
        self.assertTrue(self.warehouse.manu_type_id.active)

    def test_00_create_warehouse(self):
        """ Warehouse testing for direct manufacturing """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'mrp_one_step'
        self._check_location_and_routes()
        # Check locations of existing pull rule
        self.assertFalse(self.warehouse.pbm_route_id.rule_ids, 'only the update of global manufacture route should happen.')
        self.assertEqual(self.warehouse.manufacture_pull_id.location_id.id, self.warehouse.lot_stock_id.id)

    def test_01_warehouse_twostep_manufacturing(self):
        """ Warehouse testing for picking before manufacturing """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm'
        self._check_location_and_routes()
        self.assertEqual(len(self.warehouse.pbm_route_id.rule_ids), 2)
        self.assertEqual(self.warehouse.manufacture_pull_id.location_id.id, self.warehouse.lot_stock_id.id)

    def test_02_warehouse_twostep_manufacturing(self):
        """ Warehouse testing for picking ans store after manufacturing """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
        self._check_location_and_routes()
        self.assertEqual(len(self.warehouse.pbm_route_id.rule_ids), 3)
        self.assertEqual(self.warehouse.manufacture_pull_id.location_id.id, self.warehouse.sam_loc_id.id)

    def test_manufacturing_3_steps(self):
        """ Test MO/picking before manufacturing/picking after manufacturing
        components and move_orig/move_dest. Ensure that everything is created
        correctly.
        """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.finished_product
        production_form.picking_type_id = self.warehouse.manu_type_id
        production = production_form.save()

        move_raw_ids = production.move_raw_ids
        self.assertEqual(len(move_raw_ids), 1)
        self.assertEqual(move_raw_ids.product_id, self.raw_product)
        self.assertEqual(move_raw_ids.picking_type_id, self.warehouse.manu_type_id)
        pbm_move = move_raw_ids.move_orig_ids
        self.assertEqual(len(pbm_move), 1)
        self.assertEqual(pbm_move.location_id, self.warehouse.lot_stock_id)
        self.assertEqual(pbm_move.location_dest_id, self.warehouse.pbm_loc_id)
        self.assertEqual(pbm_move.picking_type_id, self.warehouse.pbm_type_id)
        self.assertFalse(pbm_move.move_orig_ids)

        move_finished_ids = production.move_finished_ids
        self.assertEqual(len(move_finished_ids), 1)
        self.assertEqual(move_finished_ids.product_id, self.finished_product)
        self.assertEqual(move_finished_ids.picking_type_id, self.warehouse.manu_type_id)
        sam_move = move_finished_ids.move_dest_ids
        self.assertEqual(len(sam_move), 1)
        self.assertEqual(sam_move.location_id, self.warehouse.sam_loc_id)
        self.assertEqual(sam_move.location_dest_id, self.warehouse.lot_stock_id)
        self.assertEqual(sam_move.picking_type_id, self.warehouse.sam_type_id)
        self.assertFalse(sam_move.move_dest_ids)

    def test_manufacturing_complex_product_3_steps(self):
        """ Test MO/picking after manufacturing a complex product which uses
        manufactured components. Ensure that everything is created and picked
        correctly.
        """
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

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.complex_product
        production_form.picking_type_id = self.warehouse.manu_type_id
        production = production_form.save()

        move_raw_ids = production.move_raw_ids
        self.assertEqual(len(move_raw_ids), 2)
        sfp_move_raw_id, raw_move_raw_id = move_raw_ids
        self.assertEqual(sfp_move_raw_id.product_id, self.finished_product)
        self.assertEqual(raw_move_raw_id.product_id, self.raw_product_2)

        for move_raw_id in move_raw_ids:
            self.assertEqual(move_raw_id.picking_type_id, self.warehouse.manu_type_id)

            pbm_move = move_raw_id.move_orig_ids
            self.assertEqual(len(pbm_move), 1)
            self.assertEqual(pbm_move.location_id, self.warehouse.lot_stock_id)
            self.assertEqual(pbm_move.location_dest_id, self.warehouse.pbm_loc_id)
            self.assertEqual(pbm_move.picking_type_id, self.warehouse.pbm_type_id)

        move_finished_ids = production.move_finished_ids
        self.assertEqual(len(move_finished_ids), 1)
        self.assertEqual(move_finished_ids.product_id, self.complex_product)
        self.assertEqual(move_finished_ids.picking_type_id, self.warehouse.manu_type_id)
        sam_move = move_finished_ids.move_dest_ids
        self.assertEqual(len(sam_move), 1)
        self.assertEqual(sam_move.location_id, self.warehouse.sam_loc_id)
        self.assertEqual(sam_move.location_dest_id, self.warehouse.lot_stock_id)
        self.assertEqual(sam_move.picking_type_id, self.warehouse.sam_type_id)
        self.assertFalse(sam_move.move_dest_ids)

        pickings = production.picking_ids.sorted('id', reverse=True)
        self.assertEqual(len(pickings), 3)

        # Picking: SFP PostProcessing -> Stock
        ## Stick from Subprocess
        picking = pickings[1]
        self.assertEqual(len(picking.move_lines), 1)
        picking.product_id = self.finished_product

        # Picking: PC Stock -> Preprocessing
        ## Stick
        ## Raw Iron
        picking = pickings[0]
        self.assertEqual(len(picking.move_lines), 2)
        picking.move_lines[0].product_id = self.finished_product
        picking.move_lines[1].product_id = self.raw_product_2

        # Picking: SFP PostProcessing -> Stock
        ## Arrow from this process
        picking = pickings[2]
        self.assertEqual(len(picking.move_lines), 1)
        picking.product_id = self.complex_product


    def test_manufacturing_flow(self):
        """ Simulate a pick pack ship delivery combined with a picking before
        manufacturing and store after manufacturing. Also ensure that the MO and
        the moves to stock are created with the generic pull rules.
        In order to trigger the rule we create a picking to the customer with
        the 'make to order' procure method
        """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
            warehouse.delivery_steps = 'pick_pack_ship'
        self.env['stock.quant']._update_available_quantity(self.raw_product, self.warehouse.lot_stock_id, 4.0)
        picking_customer = self.env['stock.picking'].create({
            'location_id': self.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': self.customer_location,
            'partner_id': self.env['ir.model.data'].xmlid_to_res_id('base.res_partner_4'),
            'picking_type_id': self.warehouse.out_type_id.id,
        })
        self.env['stock.move'].create({
            'name': self.finished_product.name,
            'product_id': self.finished_product.id,
            'product_uom_qty': 2,
            'product_uom': self.uom_unit.id,
            'picking_id': picking_customer.id,
            'location_id': self.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': self.customer_location,
            'procure_method': 'make_to_order',
            'state': 'draft',
        })
        picking_customer.action_confirm()
        production_order = self.env['mrp.production'].search([('product_id', '=', self.finished_product.id)])
        self.assertTrue(production_order)

        picking_stock_preprod = self.env['stock.move'].search([
            ('product_id', '=', self.raw_product.id),
            ('location_id', '=', self.warehouse.lot_stock_id.id),
            ('location_dest_id', '=', self.warehouse.pbm_loc_id.id),
            ('picking_type_id', '=', self.warehouse.pbm_type_id.id)
        ]).picking_id
        picking_stock_postprod = self.env['stock.move'].search([
            ('product_id', '=', self.finished_product.id),
            ('location_id', '=', self.warehouse.sam_loc_id.id),
            ('location_dest_id', '=', self.warehouse.lot_stock_id.id),
            ('picking_type_id', '=', self.warehouse.sam_type_id.id)
        ]).picking_id

        self.assertTrue(picking_stock_preprod)
        self.assertTrue(picking_stock_postprod)
        self.assertEqual(picking_stock_preprod.state, 'confirmed')
        self.assertEqual(picking_stock_postprod.state, 'waiting')

        picking_stock_preprod.action_assign()
        picking_stock_preprod.move_line_ids.qty_done = 4
        picking_stock_preprod.action_done()

        self.assertFalse(sum(self.env['stock.quant']._gather(self.raw_product, self.warehouse.lot_stock_id).mapped('quantity')))
        self.assertTrue(self.env['stock.quant']._gather(self.raw_product, self.warehouse.pbm_loc_id))

        production_order.action_assign()
        self.assertEqual(production_order.availability, 'assigned')
        self.assertEqual(picking_stock_postprod.state, 'waiting')

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production_order.id,
            'active_ids': [production_order.id],
        }))
        produce_form.product_qty = production_order.product_qty
        product_produce = produce_form.save()
        product_produce.do_produce()
        production_order.button_mark_done()

        self.assertFalse(sum(self.env['stock.quant']._gather(self.raw_product, self.warehouse.pbm_loc_id).mapped('quantity')))

        self.assertEqual(picking_stock_postprod.state, 'assigned')

        picking_stock_pick = self.env['stock.move'].search([
            ('product_id', '=', self.finished_product.id),
            ('location_id', '=', self.warehouse.lot_stock_id.id),
            ('location_dest_id', '=', self.warehouse.wh_pack_stock_loc_id.id),
            ('picking_type_id', '=', self.warehouse.pick_type_id.id)
        ]).picking_id
        self.assertEqual(picking_stock_pick.move_lines.move_orig_ids.picking_id, picking_stock_postprod)
