# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, common


class TestDuplicateProducts(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestDuplicateProducts, cls).setUpClass()

        grp_workorder = cls.env.ref('mrp.group_mrp_routings')
        cls.env.user.write({'groups_id': [(4, grp_workorder.id)]})

        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        # Products and lots
        cls.painted_boat = cls.env['product.product'].create({
            'name': 'Painted boat',
            'type': 'product',
            'tracking': 'serial'})
        cls.pb1 = cls.env['stock.lot'].create({
            'company_id': cls.env.company.id,
            'product_id': cls.painted_boat.id,
            'name': 'pb1'})
        cls.blank_boat = cls.env['product.product'].create({
            'name': 'Blank Boat',
            'type': 'product',
            'tracking': 'serial'})
        cls.bb1 = cls.env['stock.lot'].create({
            'company_id': cls.env.company.id,
            'product_id': cls.blank_boat.id,
            'name': 'bb1'})
        cls.painting = cls.env['product.product'].create({
            'name': 'Color Painting',
            'type': 'product',
            'tracking': 'lot'})
        cls.p1 = cls.env['stock.lot'].create({
            'company_id': cls.env.company.id,
            'product_id': cls.painting.id,
            'name': 'p1'})

        # Bill of material
        cls.bom_boat = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.painted_boat.product_tmpl_id.id,
            'product_qty': 1.0})
        cls.operation_1 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Gift Wrap Maching',
            'workcenter_id': cls.workcenter_1.id,
            'bom_id': cls.bom_boat.id,
            'time_cycle': 15,
            'sequence': 1,
        })
        cls.env['mrp.bom.line'].create({
            'product_id': cls.blank_boat.id,
            'product_qty': 1.0,
            'bom_id': cls.bom_boat.id})
        # first painting layer
        cls.env['mrp.bom.line'].create({
            'product_id': cls.painting.id,
            'product_qty': 1.0,
            'bom_id': cls.bom_boat.id})
        # second painting layer
        cls.env['mrp.bom.line'].create({
            'product_id': cls.painting.id,
            'product_qty': 1.0,
            'bom_id': cls.bom_boat.id})

        # Update quantities
        cls.location_1 = cls.env.ref('stock.stock_location_stock')
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.blank_boat, cls.location_1, 1.0, lot_id=cls.bb1)
        Quant._update_available_quantity(cls.painting, cls.location_1, 10.0, lot_id=cls.p1)

    def test_duplicate_without_point(self):
        """ Bom with the same tracked product in 2 bom lines"""
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.painted_boat
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        production.action_confirm()
        production.button_plan()
        self.assertEqual(len(production.workorder_ids), 1, "wrong number of workorders")
        self.assertEqual(production.workorder_ids.state, 'ready', "workorder state should be 'ready'")
        self.assertEqual(len(production.workorder_ids.move_raw_ids.move_line_ids), 3, "Same components are not merged, should be 3 stock move lines")
        painting_moves = production.workorder_ids.move_raw_ids.move_line_ids.filtered(lambda ml: ml.product_id == self.painting)
        self.assertEqual(len(painting_moves), 2, "should be 2 stock move lines for painting")

    def test_duplicate_with_points(self):
        """ Bom with the same non tracked product in 2 bom lines and a quality point
        on this component"""
        self.painting.tracking = 'none'
        self.blank_boat.tracking = 'none'
        self.env['quality.point'].create({
            'product_ids': [(4, self.painted_boat.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.operation_1.id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.painting.id,
        })
        self.env['quality.point'].create({
            'product_ids': [(4, self.painted_boat.id)],
            'picking_type_ids': [(4, self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1).id)],
            'operation_id': self.operation_1.id,
            'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
            'component_id': self.blank_boat.id,
        })
        self.bom_boat.bom_line_ids.write({'operation_id': self.operation_1.id})

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.painted_boat
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        production.action_confirm()
        production.button_plan()
        self.assertEqual(len(production.workorder_ids), 1, "wrong number of workorders")
        self.assertEqual(production.workorder_ids.state, 'ready', "workorder state should be 'ready'")
        self.assertEqual(len(production.workorder_ids.check_ids), 3, "Same components are not merged, should be 3 quality checks")
        painting_checks = production.workorder_ids.check_ids.filtered(lambda check: check.component_id == self.painting)
        self.assertEqual(len(painting_checks), 2, "should be 2 quality checks for painting")

    def test_assignation_1(self):
        """ Bom with the same tracked product in 2 bom lines
        Plan the workorder before reservign quantities """
        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.painted_boat
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        production.action_confirm()
        production.button_plan()
        self.assertEqual(len(production.workorder_ids), 1, "wrong number of workorders")
        self.assertEqual(production.workorder_ids.state, 'ready', "workorder state should be 'ready'")
        self.assertEqual(len(production.workorder_ids.move_raw_ids.move_line_ids), 3, "Same components are not merged, should be 3 moves")
        painting_moves = production.workorder_ids.move_raw_ids.move_line_ids.filtered(lambda ml: ml.product_id == self.painting)
        self.assertEqual(len(painting_moves), 2, "should be 2 stock move lines for painting")
        production.action_assign()
        self.assertEqual(len(production.workorder_ids.move_raw_ids.move_line_ids), 3, "Same components merged, should be 3 stock move lines")
        painting_moves = production.workorder_ids.move_raw_ids.move_line_ids.filtered(lambda ml: ml.product_id == self.painting)
        self.assertEqual(len(painting_moves), 2, "should be 2 stock move lines for painting")

    def test_byproduct_1(self):
        """ Use the same product as component and as byproduct"""
        # Required for `byproduct_ids` to be visible in the view
        self.env.user.groups_id += self.env.ref('mrp.group_mrp_byproducts')
        bom_form = Form(self.bom_boat)
        with bom_form.byproduct_ids.new() as bp:
            bp.product_id = self.painting
            bp.product_qty = 1.0
        bom_form.save()
        self.p2 = self.env['stock.lot'].create({
            'company_id': self.env.company.id,
            'product_id': self.painting.id,
            'name': 'p2'})

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.painted_boat
        mrp_order_form.product_qty = 1
        production = mrp_order_form.save()

        production.action_confirm()
        production.button_plan()

        wo = production.workorder_ids[0]
        wo.button_start()
        # Components
        wo.finished_lot_id = self.pb1
        wo.move_raw_ids[0].move_line_ids[0].lot_id = self.bb1
        wo.move_raw_ids[0].move_line_ids[0].quantity = 1
        # First layer
        wo.move_raw_ids[1].move_line_ids[0].lot_id = self.p1
        wo.move_raw_ids[1].move_line_ids[0].quantity = 1
        # Second layer
        wo.move_raw_ids[2].move_line_ids[0].lot_id = self.p1
        wo.move_raw_ids[2].move_line_ids[0].quantity = 1
        # Byproduct
        wo.move_finished_ids[1].move_line_ids[0].lot_id = self.p2
        wo.move_finished_ids[1].move_line_ids[0].quantity = 1
        wo.move_raw_ids.picked = True
        wo.do_finish()
        production.button_mark_done()

        move_paint_raw = production.move_raw_ids.filtered(lambda move: move.product_id == self.painting)
        self.assertEqual(len(move_paint_raw), 2, 'there should be 2 moves after merge same components')
        self.assertEqual(move_paint_raw.mapped('state'), ['done', 'done'], 'Moves should be done')
        self.assertEqual(move_paint_raw.mapped('quantity'), [1, 1], 'Consumed quantity should be 2')
        self.assertEqual(len(move_paint_raw.move_line_ids), 2, 'their should be 2 move lines')
        self.assertEqual(move_paint_raw.mapped('move_line_ids').mapped('lot_id'), self.p1, 'Wrong lot numbers used')
        move_paint_finished = production.move_finished_ids.filtered(lambda move: move.product_id == self.painting)
        self.assertEqual(move_paint_finished.state, 'done', 'Move should be done')
        self.assertEqual(move_paint_finished.quantity, 1, 'Consumed quantity should be 1')
        self.assertEqual(len(move_paint_finished.move_line_ids), 1, 'their should be 1 move line')
        self.assertEqual(move_paint_finished.move_line_ids.lot_id, self.p2, 'Wrong lot numbers used')
