# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo import Command

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
        for move in self.mrp_production_qc_test1.move_raw_ids:
            details_operation_form = Form(move, view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.lot_id = self.lot_product_product_drawer_drawer_0 if ml.product_id == self.product_product_drawer_drawer else self.lot_product_product_drawer_case_0
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
        for move in production.move_raw_ids:
            details_operation_form = Form(move, view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.lot_id = self.lot_product_product_drawer_drawer_0 if ml.product_id == self.product_product_drawer_drawer else self.lot_product_product_drawer_case_0
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

    def test_04_quality_check_on_quantity(self):
        """ Test Quality Check creation of 'move_line' type.
        Check that quality checks are created for the final product.
        Check that quality checks are not created for the components.
        """
        self.env['product.product'].browse(self.product_id).tracking = 'serial'
        quality_point_operation_type, _ = self.env['quality.point'].create([
            {
                'picking_type_ids': [Command.link(self.picking_type_id)],
                'measure_on': 'move_line',
                'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            },
            {
                'picking_type_ids': [Command.link(self.picking_type_id)],
                'measure_on': 'move_line',
                'product_ids': [Command.link(self.bom.bom_line_ids[0].product_id.id)],
                'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            },
        ])

        production_form = Form(self.env['mrp.production'])
        production_form.product_id = self.env['product.product'].browse(self.product_id)
        production_form.product_qty = 5.0
        production = production_form.save()
        production.action_confirm()

        self.assertEqual(len(production.check_ids), 1)
        self.assertEqual(production.check_ids.point_id, quality_point_operation_type)
        self.assertEqual(production.check_ids.production_id, production)
        production.qty_producing = 1

        # Do the quality checks and create backorder
        action = production.check_quality()
        quality_wizard = Form(self.env[(action.get('res_model'))].browse(action.get('res_id')).with_context(action['context']))
        action = quality_wizard.save().do_fail()
        production.action_generate_serial()
        for move in production.move_raw_ids:
            details_operation_form = Form(move, view=self.env.ref('stock.view_stock_move_operations'))
            with details_operation_form.move_line_ids.edit(0) as ml:
                ml.lot_id = self.lot_product_product_drawer_drawer_0 if ml.product_id == self.product_product_drawer_drawer else self.lot_product_product_drawer_case_0
                ml.quantity = 1
            details_operation_form.save()
        production.move_raw_ids.picked = True
        backorder_action = production.button_mark_done()
        backorder_form = Form(self.env['mrp.production.backorder'].with_context(**backorder_action['context']))
        backorder_form.save().action_close_mo()
        self.assertEqual(production.state, 'done')

    def test_quality_check_serial_backorder(self):
        """Create a MO for a product tracked by serial number.
        Open the smp wizard, generate all but one serial numbers and create a back order.
        """
        # Set up Products
        product_to_build = self.env['product.product'].create({
            'name': 'Young Tom',
            'is_storable': True,
            'tracking': 'serial',
        })
        product_to_use_1 = self.env['product.product'].create({
            'name': 'Botox',
            'is_storable': True,
        })
        product_to_use_2 = self.env['product.product'].create({
            'name': 'Old Tom',
            'is_storable': True,
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
        # 'Pass' Quality Checks of production order.
        self.assertEqual(len(mo.check_ids), 1)
        mo.check_ids.do_pass()

        action = mo.action_mass_produce()
        wizard = Form(self.env['mrp.batch.produce'].with_context(**action['context']))
        wizard.lot_name = "sn#1"
        wizard.lot_qty = mo.product_qty - 1
        wizard = wizard.save()
        wizard.action_generate_production_text()
        wizard.action_prepare()
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
        for move in self.mrp_production_qc_test1.move_raw_ids:
            details_operation_form = Form(move, view=self.env.ref('stock.view_stock_move_operations'))
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

    def test_manufacture_picking_type_with_product_categ_in_qp(self):
        """Create a quality point of type measure on'operation' with the manufacturing
        picking type and product category set, and verify that the quality check
        is correctly created.
        """
        qp = self.env['quality.point'].create({
            'product_category_ids': [Command.link(self.bom.product_tmpl_id.categ_id.id)],
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'operation',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
        })
        production = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 20,
            'move_raw_ids': [
                Command.create({
                    'product_id': self.product_3.id,
                    'product_uom_qty': 10,
                })
            ],
        })
        production.action_confirm()
        self.assertEqual(production.state, 'confirmed')
        self.assertEqual(len(production.check_ids), 1)
        self.assertEqual(production.check_ids.point_id, qp)
        production.check_ids.do_pass()
        self.assertEqual(production.check_ids.quality_state, 'pass')

    def test_failing_sn_product(self):
        """Test that a manufacturing order with a serial-numbered product
        in multiple quantity can fail and be sent to the failure location.
        """
        self.product.tracking = 'serial'
        self.product.bom_ids.bom_line_ids.product_id.tracking = 'none'
        self.env['quality.point'].create({
            'product_ids': [Command.link(self.product.id)],
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            'failure_location_ids': [Command.link(self.failure_location.id)],
        })
        mo = self.env['mrp.production'].create({
            'product_id': self.product.id,
            'product_qty': 2.0,
        })
        mo.action_confirm()
        mo.action_generate_serial()
        self.assertEqual(len(mo.check_ids), 1)
        action = mo.check_ids.action_open_quality_check_wizard()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        action = wizard.do_fail()
        wizard = self.env[action['res_model']].with_context(action['context']).browse(action['res_id'])
        wizard.failure_location_id = self.failure_location.id
        wizard.confirm_fail()
        self.assertEqual(mo.check_ids.quality_state, 'fail')
        mo.move_raw_ids.picked = True
        # validate the MO and create a backorder
        action = mo.button_mark_done()
        backorder_form = Form(self.env[action['res_model']].with_context(**action['context']))
        backorder = backorder_form.save().action_backorder()
        self.assertEqual(mo.state, 'done')
        # validate the backorder and pass the QC
        backorder = mo.procurement_group_id.mrp_production_ids[1]
        backorder.action_generate_serial()
        self.assertEqual(len(backorder.check_ids), 1)
        backorder.check_ids.do_pass()
        self.assertEqual(backorder.check_ids.quality_state, 'pass')
        backorder.move_raw_ids.picked = True
        backorder.button_mark_done()
        self.assertEqual(backorder.state, 'done')

    def test_procure_method_with_mto_and_failure_location(self):
        """Create a delivery picking with an MTO product and a quality point that has a failure location.
        Ensure that the move is switched to 'make_to_stock' when the quality check fails,
        as the destination location differs from the failure location.
        """
        # Set the product's routes to MTO and Manufacture.
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        manufacture_route = self.env['stock.route'].search([('name', '=', 'Manufacture')])
        product = self.bom.product_tmpl_id.product_variant_ids[0]
        product.route_ids = [Command.set([mto_route.id, manufacture_route.id])]
        (product | self.bom.bom_line_ids.product_id).tracking = 'none'
        # Create a quality point for the product with a failure location.
        qcp = self.env['quality.point'].create({
            'product_ids': [Command.link(product.id)],
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            'failure_location_ids': [Command.link(self.failure_location.id)],
        })
        # Create a delivery picking with the MTO product.
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        picking_type_out = self.env.ref('stock.picking_type_out')
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type_out.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'move_ids': [Command.create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 10.0,
                'product_uom': product.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
                'procure_method': 'make_to_order',
            })],
        })
        picking.action_confirm()
        # The move should be in 'waiting' state and have the procurement method set to 'make_to_order'
        self.assertEqual(picking.move_ids.state, 'waiting')
        self.assertEqual(picking.move_ids.procure_method, 'make_to_order')
        # Search for the manufacturing order created from the picking
        mo = self.env['mrp.production'].search([('product_id', '=', product.id)], limit=1)
        self.assertTrue(mo, "No manufacturing order created for the MTO product.")
        mo.qty_producing = 10
        # Fail 10 units from the MO
        action = mo.check_ids.action_open_quality_check_wizard()
        wizard = self.env[action['res_model']].with_context(action['context']).create({
            'qty_failed': 10,
            'failure_location_id': qcp.failure_location_ids.id,
        })
        wizard.confirm_fail()
        # validate the MO
        mo.move_raw_ids.picked = True
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        # Check that the move is switched to 'make_to_stock' and the picking state is 'confirmed'.
        self.assertEqual(mo.finished_move_line_ids.location_dest_id.ids, qcp.failure_location_ids.ids)
        self.assertEqual(picking.move_ids.procure_method, 'make_to_stock')
        self.assertEqual(picking.state, 'confirmed')

        # Test with partial fail
        picking_2 = self.env['stock.picking'].create({
            'picking_type_id': picking_type_out.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'move_ids': [Command.create({
                'name': 'Partial Fail Product',
                'product_id': product.id,
                'product_uom_qty': 10.0,
                'product_uom': product.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
                'procure_method': 'make_to_order',
            })],
        })
        picking_2.action_confirm()
        # Search for the manufacturing order created from the picking
        mo_2 = self.env['mrp.production'].search([('product_id', '=', product.id)], limit=1)
        self.assertTrue(mo_2, "No manufacturing order created for the MTO product.")
        mo_2.qty_producing = 10
        # Fail only 5 units from the MO
        action = mo_2.check_ids.action_open_quality_check_wizard()
        wizard = self.env[action['res_model']].with_context(action['context']).create({
            'qty_failed': 5,
            'failure_location_id': qcp.failure_location_ids.id,
        })
        wizard.confirm_fail()
        # validate the MO
        mo_2.move_raw_ids.picked = True
        mo_2.button_mark_done()
        self.assertEqual(mo_2.state, 'done')
        # Check that the move is not switched to 'make_to_stock'
        self.assertEqual(mo_2.finished_move_line_ids.location_dest_id.ids, qcp.failure_location_ids.ids)
        self.assertEqual(picking_2.move_ids.procure_method, 'make_to_order')
