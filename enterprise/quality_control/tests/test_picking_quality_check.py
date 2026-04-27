# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.exceptions import UserError
from .test_common import TestQualityCommon
from odoo.tests import Form, tagged


@tagged('-at_install', 'post_install')
class TestQualityCheck(TestQualityCommon):

    def test_00_picking_quality_check(self):

        """Test quality check on incoming shipment."""

        # Create Quality Point for incoming shipment.
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
        })

        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "First Quality Point not created for Laptop Customized.")

        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Confirm incoming shipment.
        self.picking_in.action_confirm()

        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # 'Pass' Quality Checks of incoming shipment.
        self.picking_in.check_ids.do_pass()

        # Validate incoming shipment.
        self.picking_in.button_validate()

        # Now check state of quality check.
        self.assertEqual(self.picking_in.check_ids.quality_state, 'pass')

    def test_01_picking_quality_check_type_text(self):

        """ Test a Quality Check on a picking with 'Instruction'
        as test type.
        """
        # Create Quality Point for incoming shipment with 'Instructions' as test type
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality.test_type_instructions').id
        })

        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "Quality Point not created")

        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Confirm incoming shipment.
        self.picking_in.action_confirm()

        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # Check that the Quality Check on the picking has 'instruction' as test_type
        self.assertEqual(self.picking_in.check_ids[0].test_type, 'instructions')

    def test_02_picking_quality_check_type_picture(self):

        """ Test a Quality Check on a picking with 'Take Picture'
        as test type.
        """
        # Create Quality Point for incoming shipment with 'Take Picture' as test type
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality.test_type_picture').id
        })
        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "Quality Point not created")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # Check that the Quality Check on the picking has 'picture' as test_type
        self.assertEqual(self.picking_in.check_ids[0].test_type, 'picture')

    def test_03_lot_quality_check(self):
        """ Test a Quality Check at the lot level.
        """
        product_tracked_by_lot = self.env['product.product'].create({
            'name': 'Product tracked by lot',
            'tracking': 'lot',
        })

        product = self.env['product.product'].create({
            'name': 'Product',
            'tracking': 'none',
        })

        # Create Quality Point for incoming shipment on lots with 'Measure' as test type
        self.quality_point_test1 = self.env['quality.point'].create({
            'product_ids': [product_tracked_by_lot.id],
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'testing_percentage_within_lot': 10.02,
            'measure_on': 'move_line',
            'norm': 5.,
            'tolerance_min': 4.,
            'tolerance_max': 6.,
        })

        # Create Quality Point for incoming shipment on lots for all products
        self.quality_point_test2 = self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })

        # Create Quality Point for product without tracking
        self.quality_point_test3 = self.env['quality.point'].create({
            'product_ids': [product.id],
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })

        # Check that the quality points are created
        self.assertTrue(self.quality_point_test1, "Quality Point not created")
        self.assertTrue(self.quality_point_test2, "Quality Point not created")
        self.assertTrue(self.quality_point_test3, "Quality Point not created")

        # Create incoming shipment
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })

        move = self.env['stock.move'].create({
            'name': product_tracked_by_lot.name,
            'product_id': product_tracked_by_lot.id,
            'product_uom_qty': 11,
            'product_uom': product_tracked_by_lot.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Creating move lines with the serial number widget
        move._generate_serial_numbers("1", next_serial_count=10)
        self.assertTrue(len(move.move_line_ids) == 10, "Not all move lines are created with _generate_serial_number")

        # Check that quality checks were created
        self.assertTrue(len(move.move_line_ids.check_ids) == 20, "Wrong number of Quality Checks created on the move lines")

        # Create move line without qty_done and setting it after
        move_line_vals = move._prepare_move_line_vals()
        move_line = self.env['stock.move.line'].create(move_line_vals)
        move_line.quantity = 1.
        self.assertTrue(len(move.move_line_ids.check_ids) == 22, "Wrong number of Quality Checks created on the move lines")

        # Updating quantity of one move line
        move.move_line_ids[0].quantity = 2
        check_line1 = move.move_line_ids[0].check_ids[0]
        check_line2 = move.move_line_ids[1].check_ids[0]

        # Check that the percentage of the lot to check is correct
        self.assertTrue(check_line1.qty_to_test == 0.21, "Quantity to test within lot not well calculated (check rounding)")
        self.assertTrue(check_line2.qty_to_test == 0.11, "Quantity to test within lot not well calculated (check rounding)")

        # Check that tests are failing and succeeding properly
        check_line1.measure = 3.
        check_line2.measure = 4.5
        check_line1.do_measure()
        check_line2.do_measure()
        self.assertTrue(check_line1.quality_state == 'fail', "Quality Check of type 'measure' not failing on move line")
        self.assertTrue(check_line2.quality_state == 'pass', "Quality Check of type 'measure' not passing on move line")

        # Create move with a product without tracking with done quantity
        move_without_tracking1 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'quantity': 1,
            'product_uom': product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        self.assertTrue(len(move_without_tracking1.move_line_ids.check_ids) == 2, "Wrong number of Quality Checks created on the move lines")

        # Create move with a product without tracking without done quantity and changing done quantity after
        move_without_tracking2 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'quantity': 0,
            'product_uom': product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        move_without_tracking2.quantity = 1
        self.assertTrue(len(move_without_tracking2.move_line_ids.check_ids) == 2, "Wrong number of Quality Checks created on the move lines")

    def test_04_picking_quality_check_creation_no_products_no_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with no products and no product_categories set
        """
        # Create Quality Point for incoming shipment with no product or product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that Quality Check for incoming shipment has been created.
        self.assertEqual(len(self.picking_in.check_ids), 1)

    def test_05_picking_quality_check_creation_with_product_no_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with products and no product_categories set
        """
        # Create Quality Point for incoming shipment with only a product set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product.
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that only one Quality Check for incoming shipment has been created for the right product.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 0)

    def test_06_picking_quality_check_creation_no_product_with_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with no products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with product having right category (child of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with product having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that only one Quality Check for incoming shipment has been created for the right category.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 0)

    def test_07_picking_quality_check_creation_with_product_and_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with both products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product_2.id), (4, self.product_4.id)],
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product but having right category (child of Quality Point set category.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product but having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product and having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product having right category
        self.env['stock.move'].create({
            'name': self.product_4.name,
            'product_id': self.product_4.id,
            'product_uom_qty': 2,
            'product_uom': self.product_4.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that Quality Check for incoming shipment have been created only for the right product / category.
        self.assertEqual(len(self.picking_in.check_ids), 3)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_3.id)), 0)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_4.id)), 1)

    def test_08_on_product_creation_with_product_and_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with both products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product_2.id), (4, self.product_4.id)],
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product but having right category (child of Quality Point set category.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product but having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product and having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product having right category
        self.env['stock.move'].create({
            'name': self.product_4.name,
            'product_id': self.product_4.id,
            'product_uom_qty': 2,
            'product_uom': self.product_4.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        self.picking_in.move_ids.picked = True

        # Check that Quality Check for incoming shipment have been created for all the good move lines
        self.assertEqual(len(self.picking_in.check_ids), 3)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_3.id)), 0)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_4.id)), 1)

    def test_09_quality_check_on_operations(self):

        """ Test Quality Check creation of 'operation' type, meaning only one QC will be created per picking.
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        quality_point_operation_type = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'operation',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create([{
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        } for product in (self.product, self.product_2)])
        receipt.action_confirm()
        receipt.with_context(default_picking_id=receipt.id).write({
            'move_ids': [Command.create({
                'name': self.product_3.name,
                'product_id': self.product_3.id,
                'product_uom_qty': 1,
                'location_id': self.location_id,
                'location_dest_id': self.location_dest_id,
            })],
        })
        self.assertEqual(len(receipt.check_ids), 1)
        self.assertEqual(receipt.check_ids.point_id, quality_point_operation_type)
        self.assertEqual(receipt.check_ids.picking_id, receipt)

        with self.assertRaises(UserError):
            receipt._action_done()

        receipt.check_ids.do_pass()
        receipt._action_done()

    def test_check_no_serial(self):
        """
        The tracked product without set lot should not open a quality check unless
        the picking type does not need lot.
        """
        self.product.write({
            'tracking': 'serial',
            'is_storable': True,
        })
        picking_type_without_lot = self.env['stock.picking.type'].browse(self.picking_type_id).copy({
            'use_create_lots': False,
            'use_existing_lots': False,
        })
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id), Command.link(picking_type_without_lot.id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        receipts = self.env['stock.picking'].create([
            {
                'picking_type_id': picking_type,
                'location_id': self.location_id,
                'location_dest_id': self.location_dest_id,
                'move_ids': [Command.create({
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 5,
                    'product_uom': self.product.uom_id.id,
                    'location_id': self.location_id,
                    'location_dest_id': self.location_dest_id,
                })],
            } for picking_type in (self.picking_type_id, picking_type_without_lot.id)
        ])
        receipts.action_confirm()
        receipt, receipt_wihtout_lot = receipts

        # Use case 1: lot is necessary
        move = receipt.move_ids
        self.assertFalse(move.move_line_ids.lot_id)
        self.assertEqual(move.move_line_ids.mapped('lot_name'), [False] * 5)
        self.assertFalse(receipt.quality_check_todo)
        move.move_line_ids[0].lot_name = "test_sn1"
        receipt.invalidate_recordset()
        self.assertTrue(receipt.quality_check_todo)

        qc_wizard = Form.from_action(self.env, receipt.check_quality())
        # no quality check created yet
        quality_check = qc_wizard.save()
        # there is only one check created for the picking
        self.assertTrue(quality_check.is_last_check)

        # Use case 2: lot is not necessary
        self.assertRecordValues(receipt_wihtout_lot.move_line_ids, [
            {'lot_id': False, 'lot_name': False},
        ])
        self.assertTrue(receipt_wihtout_lot.quality_check_todo)

        qc_wizard = Form.from_action(self.env, receipt_wihtout_lot.check_quality())
        # no quality check created yet
        quality_check = qc_wizard.save()
        # there is only one check created for the picking
        self.assertTrue(quality_check.is_last_check)

    def test_checks_removal_on_SM_cancellation(self):
        """
        Configuration:
            - 2 storable products P1 and P2
            - Receipt in 2 steps
            - QCP for internal pickings
        Process a first receipt with P1 and P2 (an internal picking and two
        quality checks are created)
        Process a second receipt with P1. The SM input->stock should be merged
        into the existing one and the quality checks should still exist
        """
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        warehouse.reception_steps = 'two_steps'

        p01, p02 = self.env['product.product'].create([{
            'name': name,
            'is_storable': True,
        } for name in ('SuperProduct01', 'SuperProduct02')])

        self.env['quality.point'].create([{
            'product_ids': [(4, product.id)],
            'picking_type_ids': [(4, warehouse.store_type_id.id)],
        } for product in (p01, p02)])

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        self.env['stock.move'].create([{
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        } for product in (p01, p02)])
        receipt.action_confirm()
        receipt.move_ids.quantity = 1
        receipt.button_validate()

        storage_transfer = self.env['stock.picking'].search(
            [('location_id', '=', warehouse.wh_input_stock_loc_id.id), ('picking_type_id', '=', warehouse.store_type_id.id)],
            order='id desc', limit=1)
        self.assertEqual(storage_transfer.check_ids.product_id, p01 + p02)

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        self.env['stock.move'].create({
            'name': p01.name,
            'product_id': p01.id,
            'product_uom_qty': 1,
            'product_uom': p01.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        receipt.action_confirm()
        receipt.move_ids.quantity = 1
        receipt.button_validate()

        self.assertRecordValues(storage_transfer.move_ids, [
            {'product_id': p01.id, 'product_uom_qty': 2},
            {'product_id': p02.id, 'product_uom_qty': 1},
        ])
        self.assertEqual(storage_transfer.check_ids.product_id, p01 + p02)

    def test_propagate_sml_lot_name(self):
        self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        self.product.write({
            'is_storable': True,
            'tracking': 'serial',
        })

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': receipt.location_id.id,
            'location_dest_id': receipt.location_dest_id.id,
        })
        receipt.action_confirm()
        ml = move.move_line_ids

        ml.write({
            'quantity': 1,
            'lot_name': '1457',
        })
        self.assertEqual(ml.check_ids.lot_name, '1457')

        ml.lot_name = '1458'
        self.assertEqual(ml.check_ids.lot_name, '1458')
        # after validation check if lot_id is also propagated
        ml.check_ids.do_pass()
        receipt.button_validate()
        self.assertEqual(ml.check_ids.lot_line_id, ml.lot_id)
        self.assertEqual(ml.check_ids.lot_id, ml.lot_id)

        # Get lot from lot name
        self.assertEqual(ml.check_ids._get_check_action_name(), 'Quality Check : Office Chair - 1.0 Units - 1458')
        ml.lot_name = False
        # Get lot from lot id
        self.assertEqual(ml.check_ids._get_check_action_name(), 'Quality Check : Office Chair - 1.0 Units - 1458')

    def test_update_sml_done_qty(self):
        """
        When changing the done quantity of a SML, the related QC should be
        updated too
        """
        self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        })

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        picking.action_confirm()

        move.quantity = 1.0
        self.assertEqual(picking.check_ids.qty_line, 1)

        move.quantity = 0.0
        self.assertEqual(picking.check_ids.qty_line, 0)

        move.quantity = 2.0
        self.assertEqual(picking.check_ids.qty_line, 2)

    def test_quality_check_with_backorder(self):
        """Test that a user without quality manager access rights can create a backorder"""
        # Create a user wtih stock and quality user rights
        user = self.env['res.users'].create({
            'name': 'Inventory Manager',
            'login': 'test',
            'email': 'test@test.com',
            'groups_id': [(6, 0, [self.env.ref('stock.group_stock_user').id, self.env.ref('quality.group_quality_user').id])]
        })

        self.env['quality.point'].create([{
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'operation',
        }, {
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        }])

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        picking.action_confirm()
        move.quantity = 1.0
        self.assertEqual(len(picking.check_ids), 2)
        # 'Pass' Quality Checks of shipment.
        for check in picking.check_ids:
            check.do_pass()
        # Validate the picking and create a backorder
        Form.from_action(self.env, picking.button_validate()).save()\
            .with_user(user).process()

        # Check that the backorder is created and in assigned state
        self.assertEqual(picking.state, 'done')
        backorder = picking.backorder_ids
        self.assertEqual(backorder.state, 'assigned')
        self.assertEqual(len(backorder.check_ids), 2)
        # 'Pass' Quality Checks of backorder.
        for check in backorder.check_ids:
            check.do_pass()
        # Validate the backorder
        backorder.move_ids.quantity = 1.0
        backorder.with_user(user).button_validate()
        self.assertEqual(backorder.state, 'done')

    def test_failure_location_move(self):
        """ Quality point per quantity with failure locations list, a picking with 2 products / moves,
            fail one move with qty less than total move qty, a new move with the failing quantity is created,
            moving it to the failure location chosen
        """
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            'failure_location_ids': [Command.link(self.failure_location.id)],
        })

        (self.product | self.product_2).write({
            'is_storable': True,
        })

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })

        product_move, product2_move = self.env['stock.move'].create([
            {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'picking_id': receipt.id,
                'location_id': receipt.location_id.id,
                'location_dest_id': receipt.location_dest_id.id,
            },
            {
                'name': self.product_2.name,
                'product_id': self.product_2.id,
                'product_uom_qty': 2,
                'picking_id': receipt.id,
                'location_id': receipt.location_id.id,
                'location_dest_id': receipt.location_dest_id.id,
            }
        ])
        receipt.action_confirm()
        self.assertEqual(len(receipt.check_ids), 2)
        # open the wizard to do the checks
        action = receipt.check_ids.action_open_quality_check_wizard()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        self.assertEqual(len(wizard.check_ids), 2)
        self.assertEqual(wizard.current_check_id.move_line_id, product_move.move_line_ids)
        # pass the first quantity
        action = wizard.do_pass()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        self.assertEqual(wizard.current_check_id.move_line_id, product2_move.move_line_ids)
        action = wizard.do_fail()
        wizard = self.env[action['res_model']].with_context(action['context']).browse(action['res_id'])

        self.assertEqual(wizard.qty_failed, 2)
        # only fail one qty of the two
        wizard.qty_failed = 1
        wizard.failure_location_id = self.failure_location.id
        wizard.confirm_fail()
        # there should be 3 moves and 3 checks
        self.assertEqual(len(receipt.move_ids), 3)
        self.assertRecordValues(receipt.check_ids, [
            {'quality_state': 'pass', 'product_id': self.product.id, 'qty_line': 2, 'failure_location_id': False},
            {'quality_state': 'fail', 'product_id': self.product_2.id, 'qty_line': 1, 'failure_location_id': self.failure_location.id},
            {'quality_state': 'pass', 'product_id': self.product_2.id, 'qty_line': 1, 'failure_location_id': False},
        ])

    def test_failure_location_lot(self):
        """ Quality point per quantity with failure locations list, a picking with 2 products / moves,
            fail one move with qty less than total move qty, a new move with the failing quantity is created,
            moving it to the chosen failure location.
        """
        product_lot = self.env['product.product'].create({
            'name': 'product lot',
            'is_storable': True,
            'tracking': 'lot',
        })
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'move_line',
            'product_ids': [Command.link(product_lot.id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            'failure_location_ids': [Command.link(self.failure_location.id)],
        })
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': product_lot.name,
            'product_id': product_lot.id,
            'product_uom_qty': 4,
            'picking_id': receipt.id,
            'location_id': receipt.location_id.id,
            'location_dest_id': receipt.location_dest_id.id,
        })

        receipt.action_confirm()
        self.assertEqual(len(receipt.check_ids), 1)
        move.quantity = 0
        move.with_context(auto_conso=True).move_line_ids = [Command.create({
            'product_id': product_lot.id,
            'product_uom_id': product_lot.uom_id.id,
            'quantity': 2,
            'picking_id': receipt.id,
            'lot_name': 'lot1',
        }), Command.create({
            'product_id': product_lot.id,
            'product_uom_id': product_lot.uom_id.id,
            'quantity': 2,
            'picking_id': receipt.id,
            'lot_name': 'lot2',
        })]

        # open the wizard to do the checks
        self.assertEqual(len(receipt.check_ids), 2)
        action = receipt.check_ids.action_open_quality_check_wizard()
        wizard = Form.from_action(self.env, receipt.check_ids.action_open_quality_check_wizard()).save()
        self.assertEqual(len(wizard.check_ids), 2)
        self.assertEqual(wizard.current_check_id.move_line_id, move.move_line_ids[0])
        # pass the first quantity
        action = wizard.do_pass()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        self.assertEqual(wizard.current_check_id.move_line_id, move.move_line_ids[1])
        action = wizard.do_fail()
        wizard = self.env[action['res_model']].with_context(action['context']).browse(action['res_id'])

        self.assertEqual(wizard.qty_failed, 2)
        wizard.failure_location_id = self.failure_location.id
        wizard.confirm_fail()
        self.assertEqual(len(receipt.check_ids), 2)
        # there should be a move for the passed quantity and a move for the failed quantity
        self.assertEqual(len(receipt.move_ids), 2)
        self.assertRecordValues(receipt.move_ids, [
            {'product_id': product_lot.id, 'product_uom_qty': 2, 'quantity': 2, 'location_dest_id': receipt.location_dest_id.id},
            {'product_id': product_lot.id, 'product_uom_qty': 2, 'quantity': 2, 'location_dest_id': self.failure_location.id},
        ])
        self.assertRecordValues(receipt.check_ids, [
            {'quality_state': 'pass', 'product_id': product_lot.id, 'qty_line': 2, 'failure_location_id': False},
            {'quality_state': 'fail', 'product_id': product_lot.id, 'qty_line': 2, 'failure_location_id': self.failure_location.id},
        ])
        receipt.button_validate()
        self.assertEqual(receipt.state, 'done')
        self.assertEqual(receipt.move_ids.mapped('state'), ['done', 'done'])

    def test_qp_with_product_ctg(self):
        """
        Test that the quality check is created based on the product category of product and quality point.
        """
        product_cat_2 = self.product_category_base.copy({'name': 'cat2'})
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'categ_id': product_cat_2.id,
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'categ_id': self.product_category_base.id,
        })
        self.env['quality.point'].create({
            'title': 'QP1',
            'product_category_ids': [(4, product_cat_2.id), (4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        })
        self.env['quality.point'].create({
            'title': 'QP2',
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': product_a.id,
            'product_uom_qty': 1,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': product_b.id,
            'product_uom_qty': 1,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        picking.action_confirm()
        self.assertEqual(len(picking.check_ids), 3)

    def test_qc_with_partial_reception(self):
        """
        Test that the quality check is required only for move lines with quantity set.
        """
        self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })
        (self.product_2 | self.product_3 | self.product_4).is_storable = True
        (self.product_2 | self.product_4).tracking = 'serial'
        # Create incoming shipment.
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move_tracked_product_a = self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 1,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        move_untracked = self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 1,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        move_tracked_product_b = self.env['stock.move'].create({
            'name': self.product_4.name,
            'product_id': self.product_4.id,
            'product_uom_qty': 2,
            'product_uom': self.product_4.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check Quality Check for incoming shipment is created
        self.assertEqual(len(picking_in.check_ids), 4)
        self.assertTrue(picking_in.quality_check_todo)
        # Set the quantity for the untracked product and complete its quality check.
        move_untracked.quantity = 1
        move_untracked.picked = True
        untracked_check_ids = picking_in.check_ids.filtered(lambda qc: qc.product_id == self.product_3)
        untracked_check_ids.do_pass()
        self.assertEqual(untracked_check_ids.quality_state, 'pass')
        # Register a quantity of 2 units for your product_b and none for product_a
        move_tracked_product_a.quantity = 0
        move_tracked_product_b.quantity = 2
        move_tracked_product_b._generate_serial_numbers("1", next_serial_count=2)
        tracked_check_ids_to_do = picking_in.check_ids.filtered(lambda qc: qc.product_id == self.product_4)
        self.env.invalidate_all()
        # Check that clicking on the Quality Check button shows you the QC's related to product_b
        qc_wizard = Form.from_action(self.env, picking_in.check_quality()).save()
        self.assertEqual(qc_wizard.check_ids, tracked_check_ids_to_do)
        # process one of the 2 QC's and keep the second one for validation
        tracked_check_ids_to_do[0].do_pass()
        self.assertEqual(tracked_check_ids_to_do[0].quality_state, 'pass')
        tracked_check_ids_to_do = tracked_check_ids_to_do.filtered(lambda qc: qc.quality_state == 'none')
        qc_wizard = Form.from_action(self.env, picking_in.check_quality()).save()
        self.assertEqual(qc_wizard.check_ids, tracked_check_ids_to_do)

        # Set a quantity on the product_a but check only product_b
        # Clicking on the Quality check button one should see both QC's
        # -> At validation only the QC's for picked move should be seen
        move_tracked_product_b.picked = True
        move_tracked_product_a.quantity = 1
        move_tracked_product_a._generate_serial_numbers("1", next_serial_count=1)
        self.assertFalse(move_tracked_product_a.picked)
        qc_wizard = Form.from_action(self.env, picking_in.check_quality()).save()
        self.assertEqual(qc_wizard.check_ids, picking_in.check_ids.filtered(lambda qc: qc.quality_state == 'none'))

        # Validate incoming shipment.
        wizard = Form.from_action(self.env, picking_in.button_validate()).save()
        qc_wizard = Form.from_action(self.env, wizard.process()).save()
        self.assertEqual(qc_wizard.check_ids, tracked_check_ids_to_do)
        qc_wizard.do_pass()
        backorder = picking_in.backorder_ids
        self.assertEqual(picking_in.state, 'done')
        self.assertEqual(len(backorder.check_ids), 1)
        backorder.check_ids.do_pass()
        self.assertTrue(backorder.check_ids.quality_state, 'pass')

    def test_quality_check_with_scrapped_moves(self):
        """
        Test that a quality check is not created for scrapped moves.
        """
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'operation',
        })
        self.product_3.is_storable = True
        # Create incoming shipment.
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check Quality Check for incoming shipment is created
        self.assertEqual(len(picking_in.check_ids), 1)
        # open the wizard to do the checks
        action = picking_in.check_ids.action_open_quality_check_wizard()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        self.assertEqual(len(wizard.check_ids), 1)
        wizard.do_fail()
        self.assertEqual(picking_in.check_ids.quality_state, 'fail')

        scrap = self.env['stock.scrap'].create({
            'picking_id': picking_in.id,
            'product_id': self.product_3.id,
            'product_uom_id': self.product_3.uom_id.id,
            'scrap_qty': 5.0,
        })
        scrap.do_scrap()
        self.assertEqual(len(picking_in.move_ids), 2)
        self.assertEqual(len(picking_in.check_ids), 1)

    def test_qc_by_product_with_partial_reception(self):
        """
        Test that a new quality check is created for the backorder.
        If splitting before validating, test that the old QC remains.
        """
        self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'product',
        })
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 10,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        picking_in.action_confirm()
        self.assertEqual(len(picking_in.check_ids), 1)
        self.assertTrue(picking_in.quality_check_todo)
        move.quantity = 5
        move.picked = True
        # validate the incoming picking and create a backorder
        action_quality_check = Form.from_action(self.env, picking_in.button_validate()).save().process()
        # Confirm the quality check wizard
        Form.from_action(self.env, action_quality_check).save().do_pass()
        # Check that the first quality check is still linked to the first picking
        self.assertEqual(len(picking_in.check_ids), 1)
        self.assertEqual(picking_in.check_ids.quality_state, 'pass')
        # Make sure that the backorder is correctly created and that it has a quality check
        backorder = picking_in.backorder_ids
        self.assertEqual(len(backorder.check_ids), 1)
        # Check that splitting the backorder doesn't remove the check
        backorder.move_ids.quantity = 3
        backorder.move_ids.picked = True
        backorder.action_split_transfer()
        self.assertEqual(len(backorder.check_ids), 1)
        backorder.check_ids.do_pass()
        self.assertEqual(backorder.check_ids.quality_state, 'pass')
        # Check that the new-new backorder has its own quality check
        backorder_2 = backorder.backorder_ids
        self.assertEqual(len(backorder_2.check_ids), 1)
        self.assertNotIn(backorder_2.check_ids, (picking_in + backorder).check_ids)

    def test_quality_check_on_receipt_with_additional_move_lines(self):
        """
        Check that adding a move line for a new product to an already
        assigned receipt will generate the associated quality check.
        """
        # Create Quality Point for incoming shipments.
        self.env['quality.point'].create([
            {
                'title': "Check product 2",
                'measure_on': "operation",
                'product_ids': [Command.link(self.product_2.id)],
                'picking_type_ids': [Command.link(self.picking_type_id)],
            },
        ])

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
            'move_ids': [Command.create({
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'product_uom': self.product.uom_id.id,
                'location_id': self.location_id,
                'location_dest_id': self.location_dest_id,
            })],
        })
        receipt.action_confirm()
        self.assertRecordValues(receipt,[{
            'state': 'assigned', 'quality_check_todo': False,
        }] )
        # create a move line as you would from the detailed operation
        self.env['stock.move.line'].create({
            'product_id': self.product_2.id,
            'picking_id': receipt.id,
            'quantity': 3,
        })
        # try to validate the receipt to be warned that you still need to process some quality checks
        self.assertRecordValues(receipt.move_ids.sorted('quantity'), [
            {'product_id': self.product.id, 'quantity': 2.0, 'state': 'assigned'},
            {'product_id': self.product_2.id, 'quantity': 3.0, 'state': 'assigned'},
        ])
        receipt.invalidate_recordset()
        self.assertRecordValues(receipt,[{
            'state': 'assigned', 'quality_check_todo': True,
        }])
        self.assertEqual(len(receipt.check_ids), 1)
        receipt.check_ids.do_pass()
        receipt.button_validate()
        self.assertEqual(len(receipt.check_ids), 1)

    def test_quality_check_on_delivery_with_additional_move_lines(self):
        """
        Check that adding a move line for a new product to an already
        assigned delivery will generate the associated quality check.
        """
        out_type_id = self.env.ref('stock.warehouse0').out_type_id
        # Create Quality Point for outgoing shipments.
        self.env['quality.point'].create([
            {
                'title': "Check product 2",
                'measure_on': "operation",
                'product_ids': [Command.link(self.product_2.id)],
                'picking_type_ids': [Command.link(out_type_id.id)],
            },
        ])

        delivery = self.env['stock.picking'].create({
            'picking_type_id': out_type_id.id,
            'location_id': self.location_dest_id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_ids': [Command.create({
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'product_uom': self.product.uom_id.id,
                'location_id': self.location_dest_id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })
        delivery.action_confirm()
        self.assertRecordValues(delivery,[{
            'state': 'assigned', 'quality_check_todo': False,
        }] )
        # create a move line as you would from the detailed operation
        self.env['stock.move.line'].create({
            'product_id': self.product_2.id,
            'picking_id': delivery.id,
            'quantity': 3,
        })
        # try to validate the delivery to be warned that you still need to process some quality checks
        self.assertRecordValues(delivery.move_ids.sorted('quantity'), [
            {'product_id': self.product.id, 'quantity': 2.0, 'state': 'assigned'},
            {'product_id': self.product_2.id, 'quantity': 3.0, 'state': 'assigned'},
        ])
        delivery.invalidate_recordset()
        self.assertRecordValues(delivery,[{
            'state': 'assigned', 'quality_check_todo': True,
        }])
        self.assertEqual(len(delivery.check_ids), 1)
        delivery.check_ids.do_pass()
        delivery.button_validate()
        self.assertEqual(len(delivery.check_ids), 1)

    def test_quality_check_creation_multi_company(self):
        """
        Test confirming a new delivery when the picking and environment company
        differ. Test that the quality check can be created by using the
        picking's company.
        """
        out_picking_type = self.env['stock.picking.type'].search([('company_id', '=', self.env.company.id), ('code', '=', 'outgoing')], limit=1)
        self.env['quality.point'].create([
            {
                'title': "Delivery QCP",
                'picking_type_ids': out_picking_type.ids,
            },
            {
                'measure_on': 'move_line',
                'title': "Delivery QCP",
                'picking_type_ids': out_picking_type.ids,
            },
        ])
        customer_location = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
        picking_out = self.env['stock.picking'].create({
            'picking_type_id': out_picking_type.id,
            'partner_id': self.partner_id,
            'location_id': out_picking_type.default_location_src_id.id,
            'location_dest_id': customer_location.id,
            'move_ids': [Command.create({
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'product_uom': self.product.uom_id.id,
                'location_id': out_picking_type.default_location_src_id.id,
                'location_dest_id': customer_location.id,
            })],
        })
        # Force env.company to be different from the picking's company
        new_company = self.env['res.company'].create({
            'name': "New Company",
        })
        picking_out.with_company(new_company).action_confirm()
        self.assertRecordValues(picking_out, [{
            'state': 'assigned', 'quality_check_todo': True,
        }])
        self.assertTrue(picking_out.check_ids)

    def test_receipt_validation_triggers_serial_number_label_print(self):
        """
        Ensure that the 'do_multi_print' action is trigger after quality check wizard validation
        when the operation's auto_print_lot_labels is activate and Serial Number is set on the product
        """
        self.env.user.groups_id |= self.env.ref('stock.group_production_lot')
        picking_type = self.env['stock.picking.type'].browse(self.picking_type_id)
        picking_type.auto_print_lot_labels = True
        self.product.write({
            'is_storable': True,
            'tracking': 'serial',
        })
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(picking_type.id)],
            'product_ids': [Command.link(self.product.id)],
            'measure_on': 'product',
            'test_type_id': self.ref('quality_control.test_type_passfail')
        })
        receipts = self.env['stock.picking'].create([{
            'picking_type_id': picking_type.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
            'move_ids': [Command.create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': product.uom_id.id,
            })]
        } for product in [self.product, self.product_2]])
        receipts[0].action_confirm()

        ml = receipts[0].move_ids.move_line_ids
        ml.write({
            'quantity': 1,
            'lot_name': '1457',
        })
        self.assertEqual(ml.lot_name, '1457')

        action_quality_check = Form.from_action(self.env, receipts.button_validate()).save()
        validate_res = action_quality_check.do_pass()

        self.assertEqual(validate_res.get('type'), 'ir.actions.client')
        self.assertEqual(validate_res.get('tag', False), 'do_multi_print')

        self.assertRecordValues(receipts, [
            {'state': 'done'},
            {'state': 'done'}
        ])

    def test_product_quality_point_smart_button_count(self):
        """
        Archived QCP should not be included in the product smart button count
        """
        quality_point = self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id)],
        })

        self.assertEqual(self.product.quality_control_point_qty, 1)

        quality_point.active = False
        self.product.invalidate_recordset(fnames=['quality_control_point_qty'])
        self.assertEqual(self.product.quality_control_point_qty, 0)

    def test_partial_quantity_failure_split(self):
        """Test quantity failure splits move quantities correctly.
        CASE-1: With total qty = 5 and failed qty = 3:
        - Passed move: product_uom_qty = 2, move_line quantity = 2
        - Failed move: product_uom_qty = 3, move_line quantity = 3
        CASE-2: Failed qty > total qty (failed = 6):
        - Passed move: product_uom_qty = 0, move_line quantity = 0
        - Failed move: product_uom_qty = 5, move_line quantity = 6
        """
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'move_line',
            'failure_location_ids': [Command.link(self.failure_location.id)],
        })
        self.product.is_storable = True
        receipt1, receipt2 = self.env['stock.picking'].create([
            {
                'picking_type_id': self.picking_type_id,
                'location_id': self.location_id,
                'location_dest_id': self.location_dest_id,
                'move_ids': [Command.create({
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_uom_qty': 5,
                    'location_id': self.location_id,
                    'location_dest_id': self.location_dest_id,
                })],
            }
            for _ in range(2)
        ])
        for picking, failed_qty in [(receipt1, 3), (receipt2, 6)]:
            picking.action_confirm()
            wizard_action = picking.check_ids.action_open_quality_check_wizard()
            wizard = self.env[wizard_action['res_model']].with_context(wizard_action['context']).create({})
            fail_action = wizard.do_fail()
            fail_wizard = self.env[fail_action['res_model']].with_context(fail_action['context']).browse(fail_action['res_id'])
            fail_wizard.qty_failed = failed_qty
            fail_wizard.confirm_fail()
        self.assertRecordValues(receipt1.move_ids, [
            {'product_id': self.product.id, 'product_uom_qty': 2, 'quantity': 2},
            {'product_id': self.product.id, 'product_uom_qty': 3, 'quantity': 3},
        ])
        self.assertRecordValues(receipt2.move_ids, [
            {'product_id': self.product.id, 'product_uom_qty': 0, 'quantity': 0},
            {'product_id': self.product.id, 'product_uom_qty': 5, 'quantity': 6},
        ])
