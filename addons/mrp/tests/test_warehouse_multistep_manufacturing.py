# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.mrp.tests.common import TestMrpCommon


@tagged('post_install', '-at_install')
class TestMultistepManufacturingWarehouse(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Required for `uom_id` to be visible in the view
        cls.env.user.groups_id += cls.env.ref('uom.group_uom')
        # Required for `manufacture_steps` to be visible in the view
        cls.env.user.groups_id += cls.env.ref('stock.group_adv_location')
        # Create warehouse
        cls.customer_location = cls.env['ir.model.data']._xmlid_to_res_id('stock.stock_location_customers')
        warehouse_form = Form(cls.env['stock.warehouse'])
        warehouse_form.name = 'Test Warehouse'
        warehouse_form.code = 'TWH'
        cls.warehouse = warehouse_form.save()

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Create manufactured product
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Stick'
        product_form.uom_id = cls.uom_unit
        product_form.uom_po_id = cls.uom_unit
        product_form.detailed_type = 'product'
        product_form.route_ids.clear()
        product_form.route_ids.add(cls.warehouse.manufacture_pull_id.route_id)
        product_form.route_ids.add(cls.warehouse.mto_pull_id.route_id)
        cls.finished_product = product_form.save()

        # Create raw product for manufactured product
        product_form = Form(cls.env['product.product'])
        product_form.name = 'Raw Stick'
        product_form.detailed_type = 'product'
        product_form.uom_id = cls.uom_unit
        product_form.uom_po_id = cls.uom_unit
        cls.raw_product = product_form.save()

        # Create bom for manufactured product
        bom_product_form = Form(cls.env['mrp.bom'])
        bom_product_form.product_id = cls.finished_product
        bom_product_form.product_tmpl_id = cls.finished_product.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'normal'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.raw_product
            bom_line.product_qty = 2.0

        cls.bom = bom_product_form.save()

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
        self.assertEqual(self.warehouse.manufacture_pull_id.location_dest_id.id, self.warehouse.lot_stock_id.id)

    def test_01_warehouse_twostep_manufacturing(self):
        """ Warehouse testing for picking before manufacturing """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm'
        self._check_location_and_routes()
        self.assertEqual(len(self.warehouse.pbm_route_id.rule_ids), 2)
        self.assertEqual(self.warehouse.manufacture_pull_id.location_dest_id.id, self.warehouse.lot_stock_id.id)

    def test_02_warehouse_twostep_manufacturing(self):
        """ Warehouse testing for picking ans store after manufacturing """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
        self._check_location_and_routes()
        self.assertEqual(len(self.warehouse.pbm_route_id.rule_ids), 3)
        self.assertEqual(self.warehouse.manufacture_pull_id.location_dest_id.id, self.warehouse.sam_loc_id.id)

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
        production.action_confirm()

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
        self.warehouse.flush_model()
        self.env.ref('stock.route_warehouse0_mto').active = True
        self.env['stock.quant']._update_available_quantity(self.raw_product, self.warehouse.lot_stock_id, 4.0)
        picking_customer = self.env['stock.picking'].create({
            'location_id': self.warehouse.wh_output_stock_loc_id.id,
            'location_dest_id': self.customer_location,
            'partner_id': self.env['ir.model.data']._xmlid_to_res_id('base.res_partner_4'),
            'picking_type_id': self.warehouse.out_type_id.id,
            'state': 'draft',
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
            'origin': 'SOURCEDOCUMENT',
            'state': 'draft',
        })
        picking_customer.action_confirm()
        production_order = self.env['mrp.production'].search([('product_id', '=', self.finished_product.id)])
        self.assertTrue(production_order)
        self.assertEqual(production_order.origin, 'SOURCEDOCUMENT', 'The MO origin should be the SO name')
        self.assertNotEqual(production_order.name, 'SOURCEDOCUMENT', 'The MO name should not be the origin of the move')

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
        self.assertEqual(picking_stock_preprod.state, 'assigned')
        self.assertEqual(picking_stock_postprod.state, 'waiting')
        self.assertEqual(picking_stock_preprod.origin, production_order.name, 'The pre-prod origin should be the MO name')
        self.assertEqual(picking_stock_postprod.origin, 'SOURCEDOCUMENT', 'The post-prod origin should be the SO name')

        picking_stock_preprod.action_assign()
        picking_stock_preprod.move_ids.write({'quantity': 4, 'picked': True})
        picking_stock_preprod._action_done()

        self.assertFalse(sum(self.env['stock.quant']._gather(self.raw_product, self.warehouse.lot_stock_id).mapped('quantity')))
        self.assertTrue(self.env['stock.quant']._gather(self.raw_product, self.warehouse.pbm_loc_id))

        production_order.action_assign()
        self.assertEqual(production_order.reservation_state, 'assigned')
        self.assertEqual(picking_stock_postprod.state, 'waiting')

        produce_form = Form(production_order)
        produce_form.qty_producing = production_order.product_qty
        production_order = produce_form.save()
        production_order.button_mark_done()

        self.assertFalse(sum(self.env['stock.quant']._gather(self.raw_product, self.warehouse.pbm_loc_id).mapped('quantity')))

        self.assertEqual(picking_stock_postprod.state, 'assigned')

        picking_stock_pick = self.env['stock.move'].search([
            ('product_id', '=', self.finished_product.id),
            ('location_id', '=', self.warehouse.lot_stock_id.id),
            ('location_dest_id', '=', self.warehouse.wh_pack_stock_loc_id.id),
            ('picking_type_id', '=', self.warehouse.pick_type_id.id)
        ]).picking_id
        self.assertEqual(picking_stock_pick.move_ids.move_orig_ids.picking_id, picking_stock_postprod)

    def test_cancel_propagation(self):
        """ Test cancelling moves in a 'picking before
        manufacturing' and 'store after manufacturing' process. The propagation of
        cancel depends on the default values on each rule of the chain.
        """
        self.warehouse.manufacture_steps = 'pbm_sam'
        self.warehouse.flush_model()
        self.env['stock.quant']._update_available_quantity(self.raw_product, self.warehouse.lot_stock_id, 4.0)
        picking_customer = self.env['stock.picking'].create({
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.customer_location,
            'partner_id': self.env['ir.model.data']._xmlid_to_res_id('base.res_partner_4'),
            'picking_type_id': self.warehouse.out_type_id.id,
            'state': 'draft',
        })
        self.env['stock.move'].create({
            'name': self.finished_product.name,
            'product_id': self.finished_product.id,
            'product_uom_qty': 2,
            'picking_id': picking_customer.id,
            'product_uom': self.uom_unit.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.customer_location,
            'procure_method': 'make_to_order',
        })
        picking_customer.action_confirm()
        production_order = self.env['mrp.production'].search([('product_id', '=', self.finished_product.id)])
        self.assertTrue(production_order)

        move_stock_preprod = self.env['stock.move'].search([
            ('product_id', '=', self.raw_product.id),
            ('location_id', '=', self.warehouse.lot_stock_id.id),
            ('location_dest_id', '=', self.warehouse.pbm_loc_id.id),
            ('picking_type_id', '=', self.warehouse.pbm_type_id.id)
        ])
        move_stock_postprod = self.env['stock.move'].search([
            ('product_id', '=', self.finished_product.id),
            ('location_id', '=', self.warehouse.sam_loc_id.id),
            ('location_dest_id', '=', self.warehouse.lot_stock_id.id),
            ('picking_type_id', '=', self.warehouse.sam_type_id.id)
        ])

        self.assertTrue(move_stock_preprod)
        self.assertTrue(move_stock_postprod)
        self.assertEqual(move_stock_preprod.state, 'assigned')
        self.assertEqual(move_stock_postprod.state, 'waiting')

        move_stock_preprod._action_cancel()
        self.assertEqual(production_order.state, 'confirmed')
        production_order.action_cancel()
        self.assertTrue(move_stock_postprod.state, 'cancel')

    def test_no_initial_demand(self):
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
        production.move_raw_ids.product_uom_qty = 0
        production.action_confirm()
        production.action_assign()
        self.assertFalse(production.move_raw_ids.move_orig_ids)
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(production.reservation_state, 'assigned')

    def test_manufacturing_3_steps_flexible(self):
        """ Test MO/picking before manufacturing/picking after manufacturing
        components and move_orig/move_dest. Ensure that additional moves are put
        in picking before manufacturing too.
        """
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
        bom = self.env['mrp.bom'].search([
            ('product_id', '=', self.finished_product.id)
        ])
        new_product = self.env['product.product'].create({
            'name': 'New product',
            'type': 'product',
        })
        bom.consumption = 'flexible'
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.finished_product
        production_form.picking_type_id = self.warehouse.manu_type_id
        production = production_form.save()

        production.action_confirm()
        production.is_locked = False
        production_form = Form(production)
        with production_form.move_raw_ids.new() as move:
            move.product_id = new_product
            move.product_uom_qty = 2
        production = production_form.save()
        move_raw_ids = production.move_raw_ids
        self.assertEqual(len(move_raw_ids), 2)
        pbm_move = move_raw_ids.move_orig_ids
        self.assertEqual(len(pbm_move), 2)
        self.assertTrue(new_product in pbm_move.product_id)

    def test_3_steps_and_byproduct(self):
        """ Suppose a warehouse with Manufacture option set to '3 setps' and a product P01 with a reordering rule.
        Suppose P01 has a BoM and this BoM mentions that when some P01 are produced, some P02 are produced too.
        This test ensures that when a MO is generated thanks to the reordering rule, 2 pickings are also
        generated:
            - One to bring the components
            - Another to return the P01 and P02 produced
        """
        warehouse = self.warehouse
        warehouse.manufacture_steps = 'pbm_sam'
        warehouse_stock_location = warehouse.lot_stock_id
        pre_production_location = warehouse.pbm_loc_id
        post_production_location = warehouse.sam_loc_id

        one_unit_uom = self.env.ref('uom.product_uom_unit')
        [two_units_uom, four_units_uom] = self.env['uom.uom'].create([{
            'name': 'x%s' % i,
            'category_id': self.ref('uom.product_uom_categ_unit'),
            'uom_type': 'bigger',
            'factor_inv': i,
        } for i in [2, 4]])

        finished_product = self.env['product.product'].create({
            'name': 'Super Product',
            'route_ids': [(4, self.ref('mrp.route_warehouse0_manufacture'))],
            'type': 'product',
        })
        secondary_product = self.env['product.product'].create({
            'name': 'Secondary',
            'type': 'product',
        })
        component = self.env['product.product'].create({
            'name': 'Component',
            'type': 'consu',
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': two_units_uom.id,
            'bom_line_ids': [(0, 0, {
                'product_id': component.id,
                'product_qty': 1,
                'product_uom_id': one_unit_uom.id,
            })],
            'byproduct_ids': [(0, 0, {
                'product_id': secondary_product.id,
                'product_qty': 1,
                'product_uom_id': four_units_uom.id,
            })],
        })

        self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': warehouse.id,
            'location_id': warehouse_stock_location.id,
            'product_id': finished_product.id,
            'product_min_qty': 2,
            'product_max_qty': 2,
        })

        self.env['procurement.group'].run_scheduler()
        mo = self.env['mrp.production'].search([('product_id', '=', finished_product.id)])
        pickings = mo.picking_ids
        self.assertEqual(len(pickings), 2)

        preprod_picking = pickings[0] if pickings[0].location_id == warehouse_stock_location else pickings[1]
        self.assertEqual(preprod_picking.location_id, warehouse_stock_location)
        self.assertEqual(preprod_picking.location_dest_id, pre_production_location)

        postprod_picking = pickings - preprod_picking
        self.assertEqual(postprod_picking.location_id, post_production_location)
        self.assertEqual(postprod_picking.location_dest_id, warehouse_stock_location)

        byproduct_postprod_move = self.env['stock.move'].search([
            ('product_id', '=', secondary_product.id),
            ('location_id', '=', post_production_location.id),
            ('location_dest_id', '=', warehouse_stock_location.id),
        ])
        self.assertEqual(byproduct_postprod_move.state, 'waiting')
        self.assertEqual(byproduct_postprod_move.group_id.name, mo.name)

    def test_manufacturing_3_steps_trigger_reordering_rules(self):
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'

        with Form(self.raw_product) as p:
            p.route_ids.clear()
            p.route_ids.add(self.warehouse.manufacture_pull_id.route_id)

        # Create an additional BoM for component
        product_form = Form(self.env['product.product'])
        product_form.name = 'Wood'
        product_form.detailed_type = 'product'
        product_form.uom_id = self.uom_unit
        product_form.uom_po_id = self.uom_unit
        self.wood_product = product_form.save()

        # Create bom for manufactured product
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.raw_product
        bom_product_form.product_tmpl_id = self.raw_product.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'normal'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.wood_product
            bom_line.product_qty = 1.0

        bom_product_form.save()

        self.env['stock.quant']._update_available_quantity(
            self.finished_product, self.warehouse.lot_stock_id, -1.0)

        rr_form = Form(self.env['stock.warehouse.orderpoint'])
        rr_form.product_id = self.wood_product
        rr_form.location_id = self.warehouse.lot_stock_id
        rr_form.save()

        rr_form = Form(self.env['stock.warehouse.orderpoint'])
        rr_form.product_id = self.finished_product
        rr_form.location_id = self.warehouse.lot_stock_id
        rr_finish = rr_form.save()

        rr_form = Form(self.env['stock.warehouse.orderpoint'])
        rr_form.product_id = self.raw_product
        rr_form.location_id = self.warehouse.lot_stock_id
        rr_form.save()

        self.env['procurement.group'].run_scheduler()

        pickings_component = self.env['stock.picking'].search(
            [('product_id', '=', self.wood_product.id)])
        self.assertTrue(pickings_component)
        self.assertTrue(rr_finish.name in pickings_component.origin)

    def test_2_steps_and_additional_moves(self):
        """ Suppose a 2-steps configuration. If a user adds a product to an existing draft MO and then
        confirms it, the associated picking should includes this new product"""
        self.warehouse.manufacture_steps = 'pbm'

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.bom.product_id
        mo_form.picking_type_id = self.warehouse.manu_type_id
        mo = mo_form.save()

        component_move = mo.move_raw_ids[0]
        mo.with_context(default_raw_material_production_id=mo.id).move_raw_ids = [
            [0, 0, {
                'location_id': component_move.location_id.id,
                'location_dest_id': component_move.location_dest_id.id,
                'picking_type_id': component_move.picking_type_id.id,
                'product_id': self.product_2.id,
                'name': self.product_2.display_name,
                'product_uom_qty': 1,
                'product_uom': self.product_2.uom_id.id,
                'warehouse_id': component_move.warehouse_id.id,
                'raw_material_production_id': mo.id,
            }]
        ]

        mo.action_confirm()

        self.assertEqual(self.bom.bom_line_ids.product_id + self.product_2, mo.picking_ids.move_ids.product_id)

    def test_manufacturing_complex_product_3_steps(self):
        """ Test MO/picking after manufacturing a complex product which uses
        manufactured components. Ensure that everything is created and picked
        correctly.
        """

        self.warehouse.mto_pull_id.route_id.active = True
        # Creating complex product which trigger another manufacture

        routes = self.warehouse.manufacture_pull_id.route_id + self.warehouse.mto_pull_id.route_id
        self.complex_product = self.env['product.product'].create({
            'name': 'Arrow',
            'type': 'product',
            'route_ids': [(6, 0, routes.ids)],
        })

        # Create raw product for manufactured product
        self.raw_product_2 = self.env['product.product'].create({
            'name': 'Raw Iron',
            'type': 'product',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
        })

        self.finished_product.route_ids = [(6, 0, routes.ids)]

        # Create bom for manufactured product
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
        production.action_confirm()
        self.env.invalidate_all()

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

        # Check move locations
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

        subproduction = self.env['mrp.production'].browse(production.id+1)
        sfp_pickings = subproduction.picking_ids.sorted('id')

        # SFP Production: 2 pickings, 1 group
        self.assertEqual(len(sfp_pickings), 2)
        self.assertEqual(sfp_pickings.mapped('group_id'), subproduction.procurement_group_id)

        # Move Raw Stick - Stock -> Preprocessing
        picking = sfp_pickings[0]
        self.assertEqual(len(picking.move_ids), 1)
        picking.move_ids[0].product_id = self.raw_product

        # Move SFP - PostProcessing -> Stock
        picking = sfp_pickings[1]
        self.assertEqual(len(picking.move_ids), 1)
        picking.move_ids[0].product_id = self.finished_product

        # Main production 2 pickings, 1 group
        pickings = production.picking_ids.sorted('id')
        self.assertEqual(len(pickings), 2)
        self.assertEqual(pickings.mapped('group_id'), production.procurement_group_id)

        # Move 2 components Stock -> Preprocessing
        picking = pickings[0]
        self.assertEqual(len(picking.move_ids), 2)
        picking.move_ids[0].product_id = self.finished_product
        picking.move_ids[1].product_id = self.raw_product_2

        # Move FP PostProcessing -> Stock
        picking = pickings[1]
        self.assertEqual(len(picking.move_ids), 1)
        picking.product_id = self.complex_product

    def test_child_parent_relationship_on_backorder_creation(self):
        """ Test Child Mo and Source Mo in 2/3-step production for reorder
            rules in backorder using order points with the help of run scheduler """

        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'

        rr_form = Form(self.env['stock.warehouse.orderpoint'])
        rr_form.product_id = self.finished_product
        rr_form.product_min_qty = 20
        rr_form.product_max_qty = 40
        rr_form.save()

        self.env['procurement.group'].run_scheduler()

        mo = self.env['mrp.production'].search([('product_id', '=', self.finished_product.id)])
        mo_form = Form(mo)
        mo_form.qty_producing = 20
        mo = mo_form.save()

        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        self.assertEqual(mo.mrp_production_child_count, 0, "Children MOs counted as existing where there should be none")
        self.assertEqual(mo.mrp_production_source_count, 0, "Source MOs counted as existing where there should be none")
        self.assertEqual(mo.mrp_production_backorder_count, 2)

    def test_source_location_on_merge_mo_3_steps(self):
        """Check that default values are correct after merging mos when 3-step manufacturing"""

        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'

        # picking with non default location
        picking_type = self.env['stock.picking.type'].create({
            'name': 'Manufacturing',
            'code': 'mrp_operation',
            'warehouse_id': warehouse.id,
            'default_location_src_id': self.warehouse.pbm_loc_id.copy().id,
            'default_location_dest_id': self.warehouse.sam_loc_id.copy().id,
            'sequence_code': 'TMP',
            'sequence_id': self.env['ir.sequence'].create({
                'code': 'mrp.production',
                'name': 'tmp_production_sequence',
            }).id,
        })

        mo1_form = Form(self.env['mrp.production'])
        mo1_form.product_id = self.finished_product
        mo1_form.picking_type_id = picking_type
        mo1 = mo1_form.save()
        mo1.action_confirm()

        mo2_form = Form(self.env['mrp.production'])
        mo2_form.product_id = self.finished_product
        mo2_form.picking_type_id = picking_type
        mo2 = mo2_form.save()
        mo2.action_confirm()

        action = (mo1 + mo2).action_merge()
        mo = self.env[action['res_model']].browse(action['res_id'])

        self.assertEqual(picking_type.default_location_src_id, mo.move_raw_ids.location_id,
            "The default source location of the merged mo should be the same as the 1st of the original MOs")
        self.assertEqual(picking_type, mo.picking_type_id,
            "The operation type of the merged mo should be the same as the 1st of the original MOs")

    def test_manufacturing_bom_from_reordering_rules(self):
        """
            Check that the manufacturing order is created with the BoM set in the reording rule:
                - Create a product with 2 bill of materials,
                - Create an orderpoint for this product specifying the 2nd BoM that must be used,
                - Check that the MO has been created with the 2nd BoM
        """
        manufacturing_route = self.env['stock.rule'].search([
            ('action', '=', 'manufacture')]).route_id
        with Form(self.warehouse) as warehouse:
            warehouse.manufacture_steps = 'pbm_sam'
        finished_product = self.env['product.product'].create({
            'name': 'Product',
            'type': 'product',
            'route_ids': manufacturing_route,
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': finished_product.uom_id.id,
            'type': 'normal',
        })
        bom_2 = self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': finished_product.uom_id.id,
            'type': 'normal',
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Orderpoint for P1',
            'product_id': self.finished_product.id,
            'product_min_qty': 1,
            'product_max_qty': 1,
            'route_id': manufacturing_route.id,
            'bom_id': bom_2.id,
        })
        self.env['procurement.group'].run_scheduler()
        mo = self.env['mrp.production'].search([('product_id', '=', self.finished_product.id)])
        self.assertEqual(len(mo), 1)
        self.assertEqual(mo.product_qty, 1.0)
        self.assertEqual(mo.bom_id, bom_2)
