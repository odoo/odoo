# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form

from .test_common import TestQualityMrpCommon


class TestQualityCheck(TestQualityMrpCommon):

    def test_00_production_quality_check(self):

        """Test quality check on production order and its backorder."""

        # Create Quality Point for product Laptop Customized with Manufacturing Operation Type.
        self.qality_point_test1 = self.env['quality.point'].create({
            'product_ids': [(4, self.product_id)],
            'picking_type_ids': [(4, self.picking_type_id)],
        })

        # Check that quality point created.
        assert self.qality_point_test1, "First Quality Point not created for Laptop Customized."

        # Create Production Order of Laptop Customized to produce 5.0 Unit.
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.env['product.product'].browse(self.product_id)
        production_form.product_qty = 5.0
        self.mrp_production_qc_test1 = production_form.save()

        # Check that Production Order of Laptop Customized to produce 5.0 Unit is created.
        assert self.mrp_production_qc_test1, "Production Order not created."

        # Perform check availability and produce product.
        self.mrp_production_qc_test1.action_confirm()
        self.mrp_production_qc_test1.action_assign()

        mo_form = Form(self.mrp_production_qc_test1)
        mo_form.qty_producing = self.mrp_production_qc_test1.product_qty - 1
        mo_form.lot_producing_id = self.lot_product_27_0
        details_operation_form = Form(self.mrp_production_qc_test1.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.lot_product_product_drawer_drawer_0
        details_operation_form.save()

        self.mrp_production_qc_test1 = mo_form.save()
        self.mrp_production_qc_test1.move_raw_ids[0].picked = True
        # Check Quality Check for Production is created and check it's state is 'none'.
        self.assertEqual(len(self.mrp_production_qc_test1.check_ids), 1)
        self.assertEqual(self.mrp_production_qc_test1.check_ids.quality_state, 'none')

        # 'Pass' Quality Checks of production order.
        self.mrp_production_qc_test1.check_ids.do_pass()

        # Set MO Done and create backorder
        action = self.mrp_production_qc_test1.button_mark_done()
        consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        action = consumption_warning.save().action_confirm()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()

        # Now check state of quality check.
        self.assertEqual(self.mrp_production_qc_test1.check_ids.quality_state, 'pass')
        # Check that the Quality Check was created on the backorder
        self.assertEqual(len(self.mrp_production_qc_test1.procurement_group_id.mrp_production_ids[-1].check_ids), 1)

    def test_01_production_quality_check_product(self):
        """ Test quality check on production order with type move_line for tracked and non-tracked manufactured product
        """

        product_without_tracking = self.env['product.product'].create({
            'name': 'Product not tracked',
            'type': 'product',
            'tracking': 'none',
        })

        # Create Quality Point for product Drawer with Manufacturing Operation Type.
        self.env['quality.point'].create({
            'product_ids': [self.product_id],
            'picking_type_ids': [self.picking_type_id],
            'measure_on': 'move_line',
            'testing_percentage_within_lot': 50,
        })
        # Create Quality Point for component Drawer Case Black with Manufacturing Operation Type.
        self.env['quality.point'].create({
            'product_ids': [self.product.bom_ids.bom_line_ids[0].product_id.id],
            'picking_type_ids': [self.picking_type_id],
            'measure_on': 'move_line',
        })
        # Create Quality Point for all products with Manufacturing Operation Type.
        # This should apply for all products but not to the components of a MO
        self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'measure_on': 'move_line',
        })

        # Create Production Order of Drawer to produce 5.0 Unit.
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.product
        production_form.product_qty = 5.0
        production = production_form.save()
        production.action_confirm()
        production.qty_producing = 4.0
        production.action_generate_serial()

        # Check that the Quality Check were created and has correct values
        self.assertEqual(len(production.move_raw_ids[0].move_line_ids.check_ids), 1)
        self.assertEqual(len(production.check_ids), 3)
        self.assertEqual(production.check_ids.filtered(lambda qc: qc.product_id == production.product_id)[0].qty_to_test, 2)

        # Create Production Order of non-tracked product
        production2_form = Form(self.env['mrp.production'])
        production2_form.product_id = product_without_tracking
        production2 = production2_form.save()
        production2.action_confirm()
        production2.qty_producing = 1.0

        # Check that the Quality Check was created
        self.assertEqual(len(production2.check_ids), 1)

    def test_02_quality_check_scrapped(self):
        """
        Test that when scrapping a manufacturing order, no quality check is created for that move
        """
        product = self.env['product.product'].create({'name': 'Time'})
        component = self.env['product.product'].create({'name': 'Money'})

        # Create a quality point for Manufacturing on All Operations (All Operations is set by default)
        qp = self.env['quality.point'].create({'picking_type_ids': [(4, self.picking_type_id)]})
        # Create a Manufacturing order for a product
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mri_form = mo_form.move_raw_ids.new()
        mri_form.product_id = component
        mri_form.product_uom_qty = 1
        mri_form.save()
        mo = mo_form.save()
        mo.action_confirm()
        # Delete the created quality check
        qc = self.env['quality.check'].search([('product_id', '=', product.id), ('point_id', '=', qp.id)])
        qc.unlink()

        # Scrap the Manufacturing Order
        scrap = self.env['stock.scrap'].with_context(active_model='mrp.production', active_id=mo.id).create({
            'product_id': product.id,
            'scrap_qty': 1.0,
            'product_uom_id': product.uom_id.id,
            'production_id': mo.id
        })
        scrap.do_scrap()
        self.assertEqual(len(self.env['quality.check'].search([('product_id', '=', product.id), ('point_id', '=', qp.id)])), 0, "Quality checks should not be created for scrap moves")

    def test_03_quality_check_on_operations(self):
        """ Test Quality Check creation of 'operation' type, meaning only one QC will be created per MO.
        """
        quality_point_operation_type = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'operation',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.env['product.product'].browse(self.product_id)
        production_form.product_qty = 5.0
        production = production_form.save()
        production.action_confirm()

        self.assertEqual(len(production.check_ids), 1)
        self.assertEqual(production.check_ids.point_id, quality_point_operation_type)
        self.assertEqual(production.check_ids.production_id, production)

        # Do the quality checks and create backorder
        production.check_ids.do_pass()
        production.qty_producing = 3.0
        production.lot_producing_id = self.lot_product_27_0
        details_operation_form = Form(production.move_raw_ids[1], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.lot_product_product_drawer_case_0
        details_operation_form.save()
        production.move_raw_ids[1].picked = True
        action = production.button_mark_done()
        consumption_warning = Form(self.env['mrp.consumption.warning'].with_context(**action['context']))
        action = consumption_warning.save().action_confirm()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        production_backorder = production.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(len(production_backorder.check_ids), 1)
        self.assertEqual(production_backorder.check_ids.point_id, quality_point_operation_type)
        self.assertEqual(production_backorder.check_ids.production_id, production_backorder)

    def test_quality_check_serial_backorder(self):
        """Create a MO for a product tracked by serial number.
        Open the smp wizard, generate all but one serial numbers and create a back order.
        """
        # Set up Products
        product_to_build = self.env['product.product'].create({
            'name': 'Young Tom',
            'type': 'product',
            'tracking': 'serial',
        })
        product_to_use_1 = self.env['product.product'].create({
            'name': 'Botox',
            'type': 'product',
        })
        product_to_use_2 = self.env['product.product'].create({
            'name': 'Old Tom',
            'type': 'product',
        })
        bom_1 = self.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_to_use_2.id, 'product_qty': 1}),
                (0, 0, {'product_id': product_to_use_1.id, 'product_qty': 1})
            ]})

        # Create Quality Point for product Laptop Customized with Manufacturing Operation Type.
        self.qality_point_test1 = self.env['quality.point'].create({
            'product_ids': [(4, product_to_build.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
        })

        # Start manufacturing
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_to_build
        mo_form.bom_id = bom_1
        mo_form.product_qty = 5
        mo = mo_form.save()
        mo.action_confirm()

        # Make some stock and reserve
        for product in mo.move_raw_ids.product_id:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 100,
                'location_id': mo.location_src_id.id,
            })._apply_inventory()
        mo.action_assign()
        action = mo.action_serial_mass_produce_wizard()
        wizard = Form(self.env['stock.assign.serial'].with_context(**action['context']))
        wizard.next_serial_number = "sn#1"
        wizard.next_serial_count = mo.product_qty - 1
        action = wizard.save().generate_serial_numbers_production()

        # 'Pass' Quality Checks of production order.
        self.assertEqual(len(mo.check_ids), 1)
        mo.check_ids.do_pass()

        # Reload the wizard to create backorder (applying generated serial numbers)
        wizard = Form(self.env['stock.assign.serial'].browse(action['res_id']))
        wizard.save().create_backorder()

        # Last MO in sequence is the backorder
        bo = mo.procurement_group_id.mrp_production_ids[-1]
        self.assertEqual(len(bo.check_ids), 1)

    def test_production_product_control_point(self):
        """Test quality control point on production order."""

        # Create Quality Point for product with Manufacturing Operation Type.
        self.qality_point_test1 = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'product',
        })

        self.bom.consumption = 'flexible'
        # Create Production Order of 5.0 Unit.
        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.env['product.product'].browse(self.product_id)
        production_form.product_qty = 5.0
        self.mrp_production_qc_test1 = production_form.save()

        # Perform check availability and produce product.
        self.mrp_production_qc_test1.action_confirm()
        self.mrp_production_qc_test1.action_assign()

        mo_form = Form(self.mrp_production_qc_test1)
        mo_form.qty_producing = self.mrp_production_qc_test1.product_qty
        mo_form.lot_producing_id = self.lot_product_27_0
        details_operation_form = Form(self.mrp_production_qc_test1.move_raw_ids[0], view=self.env.ref('stock.view_stock_move_operations'))
        with details_operation_form.move_line_ids.edit(0) as ml:
            ml.lot_id = self.lot_product_product_drawer_drawer_0 if ml.product_id == self.product_product_drawer_drawer else self.lot_product_product_drawer_case_0
        details_operation_form.save()

        self.mrp_production_qc_test1 = mo_form.save()
        self.mrp_production_qc_test1.move_raw_ids[0].picked = True
        # Check Quality Check for Production is created.
        self.assertEqual(len(self.mrp_production_qc_test1.check_ids), 1)

        # 'Pass' Quality Checks of production order.
        self.mrp_production_qc_test1.check_ids.do_pass()

        # Set MO Done.
        self.mrp_production_qc_test1.button_mark_done()

        # Now check that no new quality check are created.
        self.assertEqual(len(self.mrp_production_qc_test1.check_ids), 1)

    def test_failure_location(self):
        """ Ensure that a failing move line gets sent to its prescribed failure location (and
        passing line(s) destinations are not affected).
        """
        qcp = self.env['quality.point'].create({
            'product_ids': [Command.link(self.product.id)],
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            'failure_location_ids': [Command.link(self.failure_location.id)],
            'testing_percentage_within_lot': 100.0,
        })

        with Form(self.env['mrp.production']) as mo_form:
            mo_form.product_id = self.product
            mo_form.product_qty = 2
            with mo_form.move_raw_ids.new() as move_raw:
                move_raw.product_id = self.product_2
                move_raw.product_uom_qty = 2
            mrp_production = mo_form.save()
        mrp_production.action_confirm()

        action = mrp_production.check_ids.action_open_quality_check_wizard()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        wizard.qty_failed = 1
        wizard.failure_location_id = qcp.failure_location_ids.id
        wizard.confirm_fail()

        self.assertEqual(
            set(mrp_production.finished_move_line_ids.location_dest_id.ids),
            {self.failure_location.id, mrp_production.location_dest_id.id},
        )
