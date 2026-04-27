# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo import Command, http
from odoo.tests import Form, tagged
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestPickingBarcodeClientAction(TestBarcodeClientAction):
    def test_internal_picking_from_scratch(self):
        """ Opens an empty internal picking and creates following move through the form view:
          - move 2 `self.product1` from shelf1 to shelf2
          - move 1 `self.product2` from shelf1 to shelf3
          - move 1 `self.product2` from shelf1 to shelf2
        Then creates a fourth move by scanning product1 (from shelf1 to shelf3).
        Counts the number of picking's write.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.picking_type_internal.restrict_scan_dest_location = 'mandatory'
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        url = self._get_client_action_url(internal_picking.id)

        # Mock the calls to write and run the phantomjs script.
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        picking_button_validate_orig = odoo.addons.stock.models.stock_picking.Picking.button_validate
        product1 = self.product1
        stock_location = self.stock_location
        shelf1 = self.shelf1
        shelf3 = self.shelf3
        assertEqual = self.assertEqual
        self1 = self
        self1.stop_count_write = False

        def picking_write_mock(self, vals):
            if self1.stop_count_write:
                # Stops to count before `stock.picking` `button_validate` was called because
                # that method and its overrides can call an unpredictable amount of write.
                return picking_write_orig(self, vals)
            self1.call_count += 1
            if self1.call_count == 1:  # Open the edit form view for a line added by scanning its product.
                cmd = vals['move_line_ids'][0]
                write_vals = cmd[2]
                assertEqual(cmd[0], 0)
                assertEqual(cmd[1], 0)
                assertEqual(write_vals['product_id'], product1.id)
                assertEqual(write_vals['picking_id'], internal_picking.id)
                assertEqual(write_vals['location_id'], shelf1.id)
                assertEqual(write_vals['location_dest_id'], stock_location.id)
                assertEqual(write_vals['quantity'], 1)
            elif self1.call_count == 2:  # Write before the validate.
                cmd = vals['move_line_ids'][0]
                write_vals = cmd[2]
                assertEqual(cmd[0], 1)
                assertEqual(write_vals['location_dest_id'], shelf3.id)
            return picking_write_orig(self, vals)

        def picking_button_validate_mock(self):
            self1.stop_count_write = True  # Stops to count write once validate is called.
            return picking_button_validate_orig(self)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock),\
             patch('odoo.addons.stock.models.stock_picking.Picking.button_validate', new=picking_button_validate_mock):
                self.start_tour(url, 'test_internal_picking_from_scratch', login='admin', timeout=180)

        self.assertEqual(self.call_count, 2)
        self.assertRecordValues(internal_picking.move_line_ids, [
            {"product_id": self.product1.id, "quantity": 2, "location_id": self.shelf1.id, "location_dest_id": self.shelf2.id, "picked": True},
            {"product_id": self.product2.id, "quantity": 1, "location_id": self.shelf1.id, "location_dest_id": self.shelf3.id, "picked": True},
            {"product_id": self.product2.id, "quantity": 1, "location_id": self.shelf1.id, "location_dest_id": self.shelf2.id, "picked": True},
            {"product_id": self.product1.id, "quantity": 1, "location_id": self.shelf1.id, "location_dest_id": self.shelf3.id, "picked": True},
        ])

    def test_picking_scan_package_confirmation(self):
        """
        This test ensures that whenever a product is already scanned in a package,
        if we scan the package, a confirmation is asked before adding the content of the package.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        package1 = self.env['stock.quant.package'].create({'name': 'package001'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1, package_id=package1)

        delivery_with_move = self.env['stock.picking'].create({
            'name': "Delivery with Stock Move",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [(0, 0, {
                'name': 'scan_package_confirmation',
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_id': self.product1.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 2
            })],
        })
        delivery_with_move.action_confirm()
        delivery_with_move.action_assign()

        url = f'/odoo/{delivery_with_move.id}/action-stock_barcode.stock_barcode_picking_client_action'
        self.start_tour(url, 'test_picking_scan_package_confirmation', login='admin', timeout=180)

    def test_internal_picking_from_scratch_with_package(self):
        """ Opens an empty internal picking, scans the source (shelf1), then scans
        the products (product1 and product2), scans a existing empty package to
        assign it as the result package, and finally scans the destination (shelf2).
        Checks the dest location is correctly set on the lines.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0), (4, grp_pack.id, 0)]})
        self.picking_type_internal.active = True
        # Creates a new package and add some quants.
        package2 = self.env['stock.quant.package'].create({'name': 'P00002'})
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1, package_id=package2)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 2, package_id=package2)
        self.assertEqual(package2.location_id.id, self.stock_location.id)

        self.start_tour("/odoo/barcode", 'test_internal_picking_from_scratch_with_package', login='admin')

        self.assertEqual(len(self.package.quant_ids), 2)
        self.assertEqual(self.package.location_id.id, self.shelf2.id)
        self.assertRecordValues(self.package.quant_ids, [
            {'product_id': self.product1.id, 'quantity': 1, 'location_id': self.shelf2.id},
            {'product_id': self.product2.id, 'quantity': 1, 'location_id': self.shelf2.id},
        ])

        self.assertEqual(package2.location_id.id, self.shelf2.id)
        self.assertRecordValues(package2.quant_ids, [
            {'product_id': self.product1.id, 'quantity': 1, 'location_id': self.shelf2.id},
            {'product_id': self.product2.id, 'quantity': 2, 'location_id': self.shelf2.id},
        ])

    def test_internal_pack_in_same_package(self):
        """ Ensure we can reuse existing package with content as the result
        package if this package is located in the destination location and
        in another location than the source location."""
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id), Command.link(grp_pack.id)]})
        # Enable 2-steps receiption so the receipt source location and
        # destination location aren't the same.
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.reception_steps = 'two_steps'
        warehouse.int_type_id.active = True
        # Adapt internal picking type to store from WH/Input to WH/Stock by default.
        warehouse.int_type_id.default_location_src_id = warehouse.wh_input_stock_loc_id
        # Create three packages and add quantity in the two first ones.
        pack1, pack2, pack3 = self.env['stock.quant.package'].create([
            {'name': f'pack{i}'} for i in (1, 2, 3)
        ])
        for (product, pack) in ((self.product1, pack1), (self.product2, pack2)):
            self.env['stock.quant']._update_available_quantity(
                product,
                warehouse.wh_input_stock_loc_id,
                1,
                package_id=pack)

        self.start_tour('/odoo/barcode', 'test_internal_pack_in_same_package', login='admin')
        self.assertRecordValues(pack3.quant_ids.sorted(lambda q: q.product_id.id), [
            {'product_id': self.product1.id, 'quantity': 1},
            {'product_id': self.product2.id, 'quantity': 1},
        ])

    def test_internal_picking_reserved_1(self):
        """ Open a reserved internal picking
          - move 1 `self.product1` and 1 `self.product2` from shelf1 to shelf2
          - move 1 `self.product1` from shelf3 to shelf4.
        Before doing the reservation, move 1 `self.product1` from shelf3 to shelf2
        """
        self.clean_access_rights()
        self.picking_type_internal.restrict_scan_dest_location = 'mandatory'
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(internal_picking.id)

        # prepare the picking
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf3, 1)
        move1 = self.env['stock.move'].create({
            'name': 'test_internal_picking_reserved_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_internal_picking_reserved_1_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': internal_picking.id,
        })
        internal_picking.action_confirm()
        internal_picking.action_assign()
        move1.move_line_ids.location_dest_id = self.shelf2.id
        for ml in move2.move_line_ids:
            if ml.location_id.id == self.shelf1.id:
                ml.location_dest_id = self.shelf2.id
            else:
                ml.location_dest_id = self.shelf4.id

        self.start_tour(url, 'test_internal_picking_reserved_1', login='admin', timeout=180)

    def test_receipt_from_scratch_with_lots_1(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        # Create a sibling stock location to check we can scan not only picking's
        # destination and its sublocations for immediate transfers.
        stock_2 = self.env['stock.location'].create({
            'name': "Stock 2",
            'location_id': self.stock_location.location_id.id,
            'barcode': 'WHSTOCK-2',
        })
        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_1', login='admin', timeout=180)
        self.assertRecordValues(receipt_picking.move_line_ids, [
            {'lot_name': 'lot1', 'location_dest_id': self.stock_location.id},
            {'lot_name': 'lot2', 'location_dest_id': self.shelf1.id},
            {'lot_name': 'lot3', 'location_dest_id': stock_2.id},
        ])

    def test_receipt_from_scratch_with_lots_2(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.picking_type_in.write({
            "use_existing_lots": True,
            "use_create_lots": True,
        })

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_2', login='admin', timeout=180)
        self.assertEqual(receipt_picking.move_line_ids.mapped('lot_name'), ['lot1', 'lot2'])
        self.assertEqual(receipt_picking.move_line_ids.mapped('qty_done'), [2, 2])

    def test_receipt_from_scratch_with_lots_3(self):
        """ Scans a non tracked product, then scans a tracked by lots product, then scans a
        production lot twice and checks the tracked product quantity was rightly increased.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_3', login='admin', timeout=180)
        move_lines = receipt_picking.move_line_ids
        self.assertEqual(move_lines[0].product_id.id, self.product1.id)
        self.assertEqual(move_lines[0].qty_done, 2.0)
        self.assertEqual(move_lines[1].product_id.id, self.productlot1.id)
        self.assertEqual(move_lines[1].qty_done, 2.0)
        self.assertEqual(move_lines[1].lot_name, 'lot1')

    def test_receipt_from_scratch_with_lots_4(self):
        """ With picking type options "use_create_lots" and "use existing lots" disabled,
        scan a tracked product 3 times and checks the tracked product quantity was rightly
        increased without the need to enter serial/lot number.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.picking_type_in.use_create_lots = False
        self.picking_type_in.use_existing_lots = False

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_from_scratch_with_lots_4', login='admin', timeout=180)
        move_lines = receipt_picking.move_line_ids
        self.assertEqual(move_lines[0].product_id.id, self.productserial1.id)
        self.assertEqual(move_lines[0].qty_done, 3.0)

    def test_receipt_with_sn_1(self):
        """ With picking type options "use_create_lots" and "use_existing_lots" enabled, scan a
        tracked product and enter a serial number already registered (but not used) in the system.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.picking_type_in.use_create_lots = True
        self.picking_type_in.use_existing_lots = True
        snObj = self.env['stock.lot']
        snObj.create({'name': 'sn1', 'product_id': self.productserial1.id})

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'state': 'draft',
        })

        self.env['stock.move'].create({
            'name': 'test_receipt_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.productserial1.id,
            'product_uom': self.productserial1.uom_id.id,
            'product_uom_qty': 1,
            'picking_id': receipt_picking.id,
            'picking_type_id': self.picking_type_in.id,
        })

        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_with_sn_1', login='admin', timeout=180)
        move_lines = receipt_picking.move_line_ids
        self.assertEqual(move_lines[0].product_id.id, self.productserial1.id)
        self.assertEqual(move_lines[0].lot_id.name, 'sn1')
        self.assertEqual(move_lines[0].quantity, 1.0)

    def test_receipt_reserved_1(self):
        """ Open a receipt. Move four units of `self.product1` and four units of
        unit of `self.product2` into shelf1.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(receipt_picking.id)

        # Create a sibling stock location to check we can only scan picking's
        # destination and its sublocations as move line destination.
        self.env['stock.location'].create({
            'name': "Stock 2",
            'location_id': self.stock_location.location_id.id,
            'barcode': 'WHSTOCK-2',
        })

        move1 = self.env['stock.move'].create({
            'name': 'test_receipt_reserved_1_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipt_picking.id,
        })
        move2 = self.env['stock.move'].create({
            'name': 'test_receipt_reserved_1_2',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipt_picking.id,
        })
        receipt_picking.action_confirm()
        receipt_picking.action_assign()

        # Mock the calls to write and run the phantomjs script.
        assertEqual = self.assertEqual
        ml1 = move1.move_line_ids
        ml2 = move2.move_line_ids
        shelf1 = self.shelf1
        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            if self1.call_count == 1:
                assertEqual(len(vals['move_line_ids']), 2)
                assertEqual(vals['move_line_ids'][0][:2], [1, ml2.id])
                assertEqual(vals['move_line_ids'][1][:2], [1, ml1.id])
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_receipt_reserved_1', login='admin', timeout=180)
            self.assertEqual(self.call_count, 1)
            self.assertEqual(receipt_picking.move_line_ids[0].location_dest_id.id, shelf1.id)
            self.assertEqual(receipt_picking.move_line_ids[1].location_dest_id.id, shelf1.id)

    def test_receipt_reserved_2_partial_put_in_pack(self):
        """ For a planned receipt, check put in pack a uncompleted move line will split it. """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        # Create a receipt and confirm it.
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 3
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 3
        receipt_picking = receipt_form.save()
        receipt_picking.action_confirm()
        receipt_picking.action_assign()
        receipt_picking.name = "receipt_test"

        # Set packages' sequence to 1000 to find it easily during the tour.
        package_sequence = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')], limit=1)
        package_sequence.write({'number_next_actual': 1000})

        # Opens the barcode main menu to be able to open the pickings by scanning their name.
        self.start_tour("/odoo/barcode", "test_receipt_reserved_2_partial_put_in_pack", login="admin", timeout=180)

        package1 = self.env['stock.quant.package'].search([('name', '=', 'PACK0001000')])
        package2 = self.env['stock.quant.package'].search([('name', '=', 'PACK0001001')])
        self.assertRecordValues(receipt_picking.move_ids, [
            {'product_id': self.product1.id, 'product_uom_qty': 3, 'quantity': 3, 'picked': True},
            {'product_id': self.product2.id, 'product_uom_qty': 1, 'quantity': 1, 'picked': True},
        ])
        self.assertRecordValues(receipt_picking.move_line_ids.sorted(), [
            {'product_id': self.product2.id, 'quantity': 1, 'picked': True, 'result_package_id': package2.id},
            {'product_id': self.product1.id, 'quantity': 1, 'picked': True, 'result_package_id': package2.id},
            {'product_id': self.product1.id, 'quantity': 2, 'picked': True, 'result_package_id': package1.id},
        ])
        # Since the receipt wasn't complete, a backorder should be created.
        receipt_backorder = receipt_picking.backorder_ids
        self.assertRecordValues(receipt_backorder.move_ids, [
            {'product_id': self.product2.id, 'product_uom_qty': 2, 'quantity': 2, 'picked': False},
        ])

    def test_receipt_product_not_consecutively(self):
        """ Check that there is no new line created when scanning the same product several times but not consecutively."""
        self.clean_access_rights()

        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'state': 'draft',
        })

        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_receipt_product_not_consecutively', login='admin', timeout=180)

        self.assertEqual(len(receipt_picking.move_line_ids), 2)
        self.assertEqual(receipt_picking.move_line_ids.product_id.mapped('id'), [self.product1.id, self.product2.id])
        self.assertEqual(receipt_picking.move_line_ids.mapped('quantity'), [2, 1])

    def test_delivery_source_location(self):
        """ Ensures a location who isn't the picking's source location or one of its sublocations
        can't be scanned as the source while processing a delivery.
        Ensures also this constraint is not applyable for immediate transfers."""
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        # Creates a new location at the same level than WH/Stock.
        sibling_loc = self.env['stock.location'].create({
            'name': "Second Stock",
            'location_id': self.stock_location.location_id.id,
            'barcode': 'WH-SECOND-STOCK',
        })
        # Adds some quantities in stock and creates a delivery using them.
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        delivery_from_stock = self.env['stock.picking'].create({
            'name': 'delivery_from_stock',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': 'product1 x4 (WH/Stock)',
            'location_id': delivery_from_stock.location_id.id,
            'location_dest_id': delivery_from_stock.location_dest_id.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_from_stock.id,
        })
        delivery_from_stock.action_confirm()
        delivery_from_stock.action_assign()
        # Adds some quantities in 2nd stock and creates a delivery using them.
        self.env['stock.quant']._update_available_quantity(self.product1, sibling_loc, 4)
        delivery_from_stock_2 = self.env['stock.picking'].create({
            'name': 'delivery_from_second_stock',
            'location_id': sibling_loc.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': 'product1 x4 (WH/Second Stock)',
            'location_id': delivery_from_stock_2.location_id.id,
            'location_dest_id': delivery_from_stock_2.location_dest_id.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_from_stock_2.id,
        })
        delivery_from_stock_2.action_confirm()
        delivery_from_stock_2.action_assign()

        url = '/odoo/action-stock_barcode.stock_barcode_action_main_menu'
        self.start_tour(url, 'test_delivery_source_location', login='admin', timeout=180)

    def test_delivery_lot_with_multi_companies(self):
        """ This test ensures that scanning a lot or serial number who exists for
        multiple companies will fetch only the one who belongs to the active company.
        """
        self.clean_access_rights()
        # Creates two companies and assign them to the user.
        company_a = self.env['res.company'].create({'name': 'Company "Ah !" (le meme TMTC)'})
        company_b = self.env['res.company'].create({'name': 'Company Bae 😏😘'})
        self.env.user.write({
            'groups_id': [(4, self.env.ref('stock.group_production_lot').id)],
            'company_ids': [(4, company_a.id), (4, company_b.id)],
            'company_id': company_b.id,
        })
        warehouse_b = self.env['stock.warehouse'].search([('company_id', '=', company_b.id)])
        location_a = self.env['stock.warehouse'].search([('company_id', '=', company_a.id)]).lot_stock_id
        location_b = warehouse_b.lot_stock_id
        picking_type_out_b = warehouse_b.out_type_id
        location_id_by_company = {
            company_a: location_a.id,
            company_b: location_b.id,
        }
        # Creates some serial numbers (some of them being in the two companies.)
        sn_a_1 = self.env['stock.lot'].create({'name': 'tsn-001', 'product_id': self.productserial1.id, 'company_id': company_a.id})
        sn_a_2 = self.env['stock.lot'].create({'name': 'tsn-002', 'product_id': self.productserial1.id, 'company_id': company_a.id})
        sn_b_1 = self.env['stock.lot'].create({'name': 'tsn-001', 'product_id': self.productserial1.id, 'company_id': company_b.id})
        sn_b_2 = self.env['stock.lot'].create({'name': 'tsn-003', 'product_id': self.productserial1.id, 'company_id': company_b.id})
        for sn in [sn_a_1, sn_a_2, sn_b_1, sn_b_2]:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': self.productserial1.id,
                'inventory_quantity': 1,
                'lot_id': sn.id,
                'location_id': location_id_by_company[sn.company_id],
            })
        # Creates a delivery for Company B.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = picking_type_out_b
        delivery = picking_form.save()
        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_delivery_lot_with_multi_companies', login='admin', timeout=180)
        self.assertRecordValues(delivery.move_line_ids.lot_id, [
            {'name': 'tsn-001', 'company_id': company_b.id},
            {'name': 'tsn-003', 'company_id': company_b.id},
        ])

    def test_delivery_lot_with_package(self):
        """ Have a delivery for a product tracked by SN, scan a non-reserved SN
        and checks the new created line has the right SN's package & owner.
        """
        self.clean_access_rights()
        self.picking_type_out.show_reserved_sns = True
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_owner = self.env.ref('stock.group_tracking_owner')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_owner.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        # Creates 4 serial numbers and adds 2 qty. for the reservation.
        snObj = self.env['stock.lot']
        sn1 = snObj.create({'name': 'sn1', 'product_id': self.productserial1.id})
        sn2 = snObj.create({'name': 'sn2', 'product_id': self.productserial1.id})
        sn3 = snObj.create({'name': 'sn3', 'product_id': self.productserial1.id})
        sn4 = snObj.create({'name': 'sn4', 'product_id': self.productserial1.id})
        package1 = self.env['stock.quant.package'].create({'name': 'pack_sn_1'})
        package2 = self.env['stock.quant.package'].create({'name': 'pack_sn_2'})
        partner = self.env['res.partner'].create({'name': 'Particulier'})
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn1.id,
            'location_id': self.stock_location.id,
            'package_id': package1.id,
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn2.id,
            'location_id': self.stock_location.id,
            'package_id': package1.id,
        }).action_apply_inventory()

        # Creates and confirms the delivery.
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': self.productserial1.name,
            'product_id': self.productserial1.id,
            'product_uom_qty': 2,
            'product_uom': self.productserial1.uom_id.id,
            'picking_id': delivery_picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        # Add 2 more qty. after the reservation.
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn3.id,
            'location_id': self.stock_location.id,
            'package_id': package2.id,
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn4.id,
            'location_id': self.stock_location.id,
            'package_id': package2.id,
            'owner_id': partner.id,
        }).action_apply_inventory()

        # Runs the tour.
        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_lot_with_package', login='admin', timeout=180)

        # Checks move lines values after delivery was completed.
        self.assertEqual(delivery_picking.state, "done")
        # ensure that SNs not scanned by validation time are removed
        self.assertEqual(len(delivery_picking.move_line_ids), 2)
        move_line_1 = delivery_picking.move_line_ids[0]
        move_line_2 = delivery_picking.move_line_ids[1]
        self.assertEqual(move_line_1.lot_id, sn3)
        self.assertEqual(move_line_1.package_id, package2)
        self.assertEqual(move_line_1.owner_id.id, False)
        self.assertEqual(move_line_2.lot_id, sn4)
        self.assertEqual(move_line_2.package_id, package2)
        self.assertEqual(move_line_2.owner_id, partner)

    def test_delivery_lot_with_package_delivery_step(self):
        """
        Test that we unpack from the right package in case of having
        multiple packages (or package and no package) for the same lot
        in multi-locations configuration.
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')

        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        sn = self.env['stock.lot'].create({'name': 'sn', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        package1 = self.env['stock.quant.package'].create({'name': 'pack_sn'})
        package2 = self.env['stock.quant.package'].create({'name': 'pack_sn_2'})
        self.env['stock.quant'].create([
            {
                'product_id': self.productlot1.id,
                'inventory_quantity': 1,
                'lot_id': sn.id,
                'location_id': self.shelf1.id,
                'package_id': package1.id,
            }, {
                'product_id': self.productlot1.id,
                'inventory_quantity': 1,
                'lot_id': sn.id,
                'location_id': self.shelf2.id,
            },
            {
                'product_id': self.productlot1.id,
                'inventory_quantity': 1,
                'lot_id': sn.id,
                'location_id': self.shelf2.id,
                'package_id': package2.id,
            }
        ]).action_apply_inventory()

        # Creates and confirms the delivery.
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.shelf2.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        move = self.env['stock.move'].create({
            'name': self.productlot1.name,
            'product_id': self.productlot1.id,
            'product_uom_qty': 1,
            'product_uom': self.productlot1.uom_id.id,
            'picking_id': delivery_picking.id,
            'location_id': self.shelf2.id,
            'location_dest_id': self.customer_location.id,
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        # Runs the tour.
        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_lot_with_package_delivery_step', login='admin', timeout=180)
        self.assertEqual(delivery_picking.state, "done")
        self.assertRecordValues(move.move_line_ids, [
            {'lot_id': sn.id, 'product_id': self.productlot1.id, 'quantity': 1, 'package_id': package2.id, 'result_package_id': False},
        ])

    def test_delivery_pack_from_different_location(self):
        """ Ensures that when lines from different source location are packed,
        their source location is unchanged."""
        self.clean_access_rights()
        group_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        group_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [Command.link(group_multi_loc.id)]})
        self.env.user.write({'groups_id': [Command.link(group_pack.id)]})
        self.picking_type_out.restrict_scan_source_location = 'mandatory'
        # Create an empty package (will be scanned during the tour.)
        self.env['stock.quant.package'].create({
            'name': 'pack-test',
        })
        self.start_tour('/odoo/barcode', 'test_delivery_pack_from_different_location', login='admin')

    def test_delivery_reserved_1(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'note': "A Test Note",
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_1_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self1 = self

        # Mock the calls to write and run the phantomjs script.
        def picking_write_mock(self, vals):
            self1.call_count += 1
            return picking_write_orig(self, vals)
        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_delivery_reserved_1', login='admin', timeout=180)
            self.assertEqual(self.call_count, 1)

    def test_delivery_reserved_2(self):
        self.clean_access_rights()
        self.picking_type_out.restrict_scan_source_location = 'no'
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(delivery_picking.id)

        partner_1 = self.env['res.partner'].create({'name': 'Parter1'})
        partner_2 = self.env['res.partner'].create({'name': 'Partner2'})
        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
            'restrict_partner_id': partner_1.id
        })
        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
            'restrict_partner_id': partner_2.id
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        self.assertEqual(len(delivery_picking.move_ids), 2)

        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_delivery_reserved_2', login='admin', timeout=180)
            self.assertEqual(self.call_count, 0)

    def test_delivery_reserved_3(self):
        self.clean_access_rights()
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        picking_write_orig = odoo.addons.stock.models.stock_picking.Picking.write
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': delivery_picking.id,
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self1 = self

        def picking_write_mock(self, vals):
            self1.call_count += 1
            return picking_write_orig(self, vals)

        with patch('odoo.addons.stock.models.stock_picking.Picking.write', new=picking_write_mock):
            self.start_tour(url, 'test_delivery_reserved_3', login='admin', timeout=180)
            self.assertEqual(self.call_count, 0)

    def test_delivery_reserved_4_backorder(self):
        """ Checks the backorders are correctly created when all quantity isn't processed and the
        confirmation's dialog is shown at the right time with the right informations.
        """
        self.clean_access_rights()
        product3 = self.env['product.product'].create({
            'name': 'product3',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product3',
        })
        # Creates a delivery with three different products.
        delivery = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_out.id,
        })
        common_vals = {
            'location_dest_id': self.stock_location.id,
            'location_id': self.stock_location.id,
            'name': 'test_delivery_reserved_4_backorder',
            'picking_id': delivery.id,
            'product_uom_qty': 4,
        }
        self.env['stock.move'].create(dict(common_vals, product_id=self.product1.id))
        self.env['stock.move'].create(dict(common_vals, product_id=self.product2.id))
        self.env['stock.move'].create(dict(common_vals, product_id=product3.id))
        # Adds quantity on hand for the delivery, but not to fulfill it.
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 2)
        # Confirms and reserves the delivery, then process it.
        delivery.action_confirm()
        delivery.action_assign()
        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_delivery_reserved_4_backorder', login='admin', timeout=180)

        # The delivery should have a backorder with two moves.
        self.assertEqual(len(delivery.backorder_ids), 1)
        backorder = delivery.backorder_ids
        self.assertEqual(len(backorder.move_ids), 2)
        self.assertRecordValues(backorder.move_ids, [
            {'product_uom_qty': 4, 'quantity': 2, 'picked': False, 'product_id': self.product2.id},
            {'product_uom_qty': 4, 'quantity': 0, 'picked': False, 'product_id': product3.id},
        ])

    def test_delivery_reserved_5_dont_show_reserved_sn(self):
        """ Checks reserved serial numbers aren't show until scanned when
        `show_reserved_sns` is set on False."""
        self.clean_access_rights()
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_production_lot').id, 0)]})
        self.picking_type_out.show_reserved_sns = False

        # Creates some SN and adds more than enough quantity on hand for the delivery.
        serial_numbers = self.env['stock.lot'].create([{
            'name': f'sn{n}',
            'product_id': self.productserial1.id,
            'company_id': self.env.company.id,
        } for n in range(1, 6)])
        for sn in serial_numbers:
            self.env['stock.quant']._update_available_quantity(
                self.productserial1, self.stock_location, 1, lot_id=sn)

        # Creates and confirms a delivery.
        delivery_picking = self.env['stock.picking'].create({
            'name': 'test_delivery_reserved_5',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': 'move_test_delivery_reserved_5',
            'location_id': delivery_picking.location_id.id,
            'location_dest_id': delivery_picking.location_dest_id.id,
            'picking_id': delivery_picking.id,
            'product_id': self.productserial1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
        })
        delivery_picking.action_confirm()
        reserved_move_lines = delivery_picking.move_line_ids
        self.assertEqual(len(delivery_picking.move_line_ids), 4)
        self.assertEqual(reserved_move_lines.mapped('quantity'), [1, 1, 1, 1])
        self.assertEqual(reserved_move_lines.lot_id.mapped('name'), ['sn1', 'sn2', 'sn3', 'sn4'])

        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_reserved_5_dont_show_reserved_sn', login='admin', timeout=180)
        self.assertEqual(delivery_picking.move_line_ids.lot_id.mapped('name'), ['sn1', 'sn2', 'sn3', 'sn5'])

    def test_delivery_reserved_6_dont_show_reserved_lots(self):
        """ Uncheck setting to display reserved lots and check they are not show
        in the Barcode app until they are scanned."""
        self.clean_access_rights()
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_production_lot').id, 0)]})
        self.picking_type_out.show_reserved_sns = False

        # Creates some lots and adds more than enough quantity on hand for the delivery.
        lots = self.env['stock.lot'].create([{
            'name': f'lot-00{n}',
            'product_id': self.productlot1.id,
            'company_id': self.env.company.id,
        } for n in range(1, 6)])
        for lot in lots:
            self.env['stock.quant']._update_available_quantity(
                self.productlot1, self.stock_location, 4, lot_id=lot)

        # Creates and confirms a delivery.
        delivery_picking = self.env['stock.picking'].create({
            'name': 'test_delivery_reserved_6',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': 'move_test_delivery_reserved_6',
            'location_id': delivery_picking.location_id.id,
            'location_dest_id': delivery_picking.location_dest_id.id,
            'picking_id': delivery_picking.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 12,
        })
        delivery_picking.action_confirm()
        reserved_move_lines = delivery_picking.move_line_ids
        self.assertEqual(len(delivery_picking.move_line_ids), 3)
        self.assertEqual(reserved_move_lines.mapped('quantity'), [4, 4, 4])
        self.assertEqual(reserved_move_lines.lot_id.mapped('name'), ['lot-001', 'lot-002', 'lot-003'])

        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_reserved_6_dont_show_reserved_lots', login='admin', timeout=180)

    def test_delivery_from_scratch_1(self):
        """ Scan unreserved lots on a delivery order.
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        # Adds lot1 and lot2 for productlot1
        lotObj = self.env['stock.lot']
        lotObj.create({'name': 'lot1', 'product_id': self.productlot1.id})
        lotObj.create({'name': 'lot2', 'product_id': self.productlot1.id})

        # Creates an empty picking.
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        self.start_tour(url, 'test_delivery_from_scratch_with_lots_1', login='admin', timeout=180)

        lines = delivery_picking.move_line_ids
        self.assertEqual(lines[0].lot_id.name, 'lot1')
        self.assertEqual(lines[1].lot_id.name, 'lot2')
        self.assertEqual(lines[0].qty_done, 2)
        self.assertEqual(lines[1].qty_done, 2)

    def test_delivery_from_scratch_with_incompatible_lot(self):
        """
        If a product and a lot have the same barcode, when this barcode is
        scanned, both are found, but to avoid issue, the lot is ignored because
        a lot shouldn't be applied to a line if its product is not the same.
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id)]})

        self.picking_type_out.use_create_lots = False
        self.picking_type_out.use_existing_lots = True

        lot = self.env['stock.lot'].create({
            'name': '0000000001',
            'product_id': self.productlot1.id,
        })

        for product in [self.product1, self.productserial1]:
            product.barcode = lot.name

            delivery_picking = self.env['stock.picking'].create({
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'picking_type_id': self.picking_type_out.id,
                'state': 'draft',
            })
            url = self._get_client_action_url(delivery_picking.id)
            self.start_tour(url, 'test_delivery_from_scratch_with_incompatible_lot', login='admin', timeout=180)

            self.assertRecordValues(delivery_picking.move_line_ids, [
                {'product_id': product.id, 'lot_name': False, 'lot_id': False},
            ])

            product.barcode = False

    def test_delivery_from_scratch_with_common_lots_name(self):
        """
        Suppose:
            - two tracked-by-lot products
            - these products share one lot name
            - an extra product tracked by serial number
        This test ensures that a user can scan the tracked products in a picking
        that does not expect them and updates/creates the right line depending
        of the scanned lot
        """
        self.clean_access_rights()
        group_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, group_lot.id, 0)]})

        (self.product1 + self.product2).tracking = 'lot'

        lot01, lot02, sn = self.env['stock.lot'].create([{
            'name': lot_name,
            'product_id': product.id,
        } for (lot_name, product) in [("LOT01", self.product1), ("LOT01", self.product2), ("SUPERSN", self.productserial1)]])

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2, lot_id=lot01)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 3, lot_id=lot02)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn)

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        delivery = picking_form.save()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_delivery_from_scratch_with_common_lots_name', login='admin', timeout=180)

        self.assertRecordValues(delivery.move_line_ids, [
            # pylint: disable=C0326
            {'product_id': self.product1.id,        'lot_id': lot01.id,     'qty_done': 2},
            {'product_id': self.product2.id,        'lot_id': lot02.id,     'qty_done': 3},
            {'product_id': self.productserial1.id,  'lot_id': sn.id,        'qty_done': 1},
        ])

    def test_delivery_reserved_lots_1(self):
        """ Creates a delivery for product tracked by lots and having some
        quantities in stock. Checks reserved lots are correctly visible in the
        Barcode app and that they can be processed alongside not reserved lots.
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.picking_type_out.show_reserved_sns = True

        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_lots_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_id': delivery_picking.id,
        })

        # Creates lot1, lot2 and lot3 for productlot1.
        lotObj = self.env['stock.lot']
        lot1 = lotObj.create({'name': 'lot1', 'product_id': self.productlot1.id})
        lot2 = lotObj.create({'name': 'lot2', 'product_id': self.productlot1.id})
        lot3 = lotObj.create({'name': 'lot3', 'product_id': self.productlot1.id})

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 2, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 3, lot_id=lot2)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        self.assertEqual(delivery_picking.move_ids.state, 'assigned')
        self.assertEqual(len(delivery_picking.move_ids.move_line_ids), 2)

        self.start_tour(url, 'test_delivery_reserved_lots_1', login='admin', timeout=180)

        self.assertRecordValues(delivery_picking.move_line_ids, [
            {'lot_id': lot1.id, 'quantity': 2, 'picked': True},
            {'lot_id': lot2.id, 'quantity': 2, 'picked': True},
            {'lot_id': lot3.id, 'quantity': 1, 'picked': True},
        ])

    def test_delivery_different_products_with_same_lot_name(self):
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.productlot2 = self.env['product.product'].create({
            'name': 'productlot2',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'productlot2',
            'tracking': 'lot',
        })

        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_different_products_with_same_lot_name_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_delivery_different_products_with_same_lot_name_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
        })

        # Create 2 lots with the same name for productlot1 and productlot2
        lot1 = self.env['stock.lot'].create({'name': 'lot1', 'product_id': self.productlot1.id})
        lot2 = self.env['stock.lot'].create({'name': 'lot1', 'product_id': self.productlot2.id})

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 2, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.productlot2, self.stock_location, 2, lot_id=lot2)

        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self.assertEqual(len(delivery_picking.move_ids), 2)

        self.start_tour(url, 'test_delivery_different_products_with_same_lot_name', login='admin', timeout=180)

        self.env.invalidate_all()
        lines = delivery_picking.move_line_ids
        self.assertEqual(lines[0].lot_id.name, 'lot1')
        self.assertEqual(lines[0].product_id.name, 'productlot1')
        self.assertEqual(lines[0].qty_done, 2)
        self.assertEqual(lines[1].lot_id.name, 'lot1')
        self.assertEqual(lines[1].product_id.name, 'productlot2')
        self.assertEqual(lines[1].qty_done, 2)

    def test_scan_same_lot_different_products(self):
        """
        Checks that the same lot can be scanned for different products and there
        is no conflict when trying to retrieve the lot from the cache.
        """
        products = self.env['product.product'].create([{
            'name': name,
            'barcode': name,
            'tracking': 'lot',
        } for name in ['aaa', 'bbb']])

        self.env["stock.lot"].create([{
            'name': "123",
            'product_id': product.id,
            'company_id': self.env.company.id,
        } for product in products])

        self.picking_type_internal.restrict_scan_product = True
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.shelf1.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        url = self._get_client_action_url(internal_picking.id)

        self.start_tour(url, 'test_scan_same_lot_different_products', login="admin")

    def test_delivery_reserved_with_sn_1(self):
        """ Scan unreserved serial number on a delivery order.
        """

        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        # Add 4 serial numbers productserial1
        snObj = self.env['stock.lot']
        sn1 = snObj.create({'name': 'sn1', 'product_id': self.productserial1.id})
        sn2 = snObj.create({'name': 'sn2', 'product_id': self.productserial1.id})
        sn3 = snObj.create({'name': 'sn3', 'product_id': self.productserial1.id})
        sn4 = snObj.create({'name': 'sn4', 'product_id': self.productserial1.id})

        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn1)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn2)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn3)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn4)

        # empty picking
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_lots_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productserial1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })
        delivery_picking.action_confirm()

        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_reserved_with_sn_1', login='admin', timeout=180)

        lines = delivery_picking.move_line_ids
        self.assertEqual(lines.mapped('lot_id.name'), ['sn1', 'sn2', 'sn3', 'sn4'])
        self.assertEqual(lines.mapped('qty_done'), [1, 1, 1, 1])

    def test_delivery_using_buttons(self):
        """ Creates a delivery with 3 lines, then:
            - Completes first line with "+1" button;
            - Completes second line with "Add reserved quantities" button;
            - Completes last line with "+1" button and scanning barcode.
        Checks also written quantity on buttons is correctly updated and only
        "+1" button is displayed on new line created by user.
        """
        self.clean_access_rights()

        # Creates a new product.
        product3 = self.env['product.product'].create({
            'name': 'product3',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product3',
        })

        # Creates some quants.
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 3)
        self.env['stock.quant']._update_available_quantity(product3, self.stock_location, 4)

        # Create the delivery transfer.
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 2
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 3
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = product3
            move.product_uom_qty = 4

        delivery_picking = delivery_form.save()
        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_delivery_using_buttons', login='admin', timeout=180)

        self.assertEqual(len(delivery_picking.move_line_ids), 4)
        self.assertEqual(delivery_picking.move_line_ids.mapped('qty_done'), [2, 3, 4, 2])

    def test_remaining_decimal_accuracy(self):
        """ Checks if the remaining value of a move is correct
        """
        self.picking_type_out.show_reserved_sns = True
        lot01, lot02 = self.env['stock.lot'].create([{
            'name': lot_name,
            'product_id': self.productlot1.id,
        } for lot_name in ["LOT01", "LOT02"]])

        self.clean_access_rights()
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf1, 2, lot_id=lot01)
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf1, 2, lot_id=lot02)
        # Create the delivery transfer.
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 4

        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 0.12

        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.productlot1
            move.product_uom_qty = 4

        delivery_picking = delivery_form.save()
        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_remaining_decimal_accuracy', login='admin', timeout=90)

    def test_receipt_reserved_lots_multiloc_1(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        receipts_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'user_id': False,
        })

        url = self._get_client_action_url(receipts_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_lots_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': receipts_picking.id,
        })

        # Creates lot1 and lot2 for productlot1.
        lotObj = self.env['stock.lot']
        lotObj.create({'name': 'lot1', 'product_id': self.productlot1.id})
        lotObj.create({'name': 'lot2', 'product_id': self.productlot1.id})

        receipts_picking.action_confirm()
        receipts_picking.action_assign()

        self.assertEqual(receipts_picking.user_id.id, False)
        self.start_tour(url, 'test_receipt_reserved_lots_multiloc_1', login='admin', timeout=180)
        self.assertEqual(receipts_picking.user_id.id, self.env.user.id)
        self.env.invalidate_all()
        lines = receipts_picking.move_line_ids.sorted(lambda ml: (ml.location_id.complete_name, ml.location_dest_id.complete_name, ml.id))
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.mapped('qty_done'), [2, 2])
        self.assertEqual(lines.mapped('location_id.name'), ['Vendors'])
        self.assertEqual(lines[0].location_dest_id.name, 'Section 1')
        self.assertEqual(lines[0].lot_name, 'lot2')
        self.assertEqual(lines[1].location_dest_id.name, 'Section 2')
        self.assertEqual(lines[1].lot_name, 'lot1')

    def test_pack_multiple_scan(self):
        """ Make a reception of two products, put them in pack and validate.
        Then make a delivery, scan the package two times (check the warning) and validate.
        Finally, check that the package is in the customer location.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        # set sequence packages to 1000 to find it easily in the tour
        sequence = self.env['ir.sequence'].search([(
            'code', '=', 'stock.quant.package',
        )], limit=1)
        sequence.write({'number_next_actual': 1000})

        self.start_tour("/odoo/barcode", 'test_pack_multiple_scan', login='admin', timeout=180)

        # Check the new package is well delivered
        package = self.env['stock.quant.package'].search([
            ('name', '=', 'PACK0001000')
        ])
        self.assertEqual(package.location_id, self.customer_location)

    def test_pack_common_content_scan(self):
        """ Simulate a picking where 2 packages have the same products
        inside. It should display one barcode line for each package and
        not a common barcode line for both packages.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        # Create a pack and 2 quants in this pack
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK1',
        })
        pack2 = self.env['stock.quant.package'].create({
            'name': 'PACK2',
        })

        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.stock_location,
            quantity=5,
            package_id=pack1,
        )
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product2,
            location_id=self.stock_location,
            quantity=1,
            package_id=pack1,
        )

        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.stock_location,
            quantity=5,
            package_id=pack2,
        )
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product2,
            location_id=self.stock_location,
            quantity=1,
            package_id=pack2,
        )

        self.start_tour("/odoo/barcode", 'test_pack_common_content_scan', login='admin', timeout=180)

    def test_pack_multiple_location(self):
        """ Create a package in Shelf 1 and makes an internal transfer to move it to Shelf 2.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.picking_type_internal.active = True
        self.picking_type_internal.show_entire_packs = True
        self.picking_type_internal.restrict_scan_dest_location = 'mandatory'
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'

        # Create a pack and 2 quants in this pack
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK0000666',
        })

        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.shelf1,
            quantity=5,
            package_id=pack1,
        )
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product2,
            location_id=self.shelf1,
            quantity=5,
            package_id=pack1,
        )

        self.start_tour("/odoo/barcode", 'test_pack_multiple_location', login='admin', timeout=180)

        # Check the new package is well transfered
        self.assertEqual(pack1.location_id, self.shelf2)

    def test_pack_multiple_location_02(self):
        """ Creates an internal transfer and reserves a package. Then this test will scan the
        location source, the package (already in the barcode view) and the location destination.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        # Creates a package with 1 quant in it.
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK0002020',
        })
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.shelf1,
            quantity=5,
            package_id=pack1,
        )

        # Creates an internal transfer for this package.
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        url = self._get_client_action_url(internal_picking.id)

        self.env['stock.move'].create({
            'name': 'test_delivery_reserved_2_1',
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 5,
            'picking_id': internal_picking.id,
        })
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_pack_multiple_location_02', login='admin', timeout=180)

        # Checks the new package is well transfered.
        self.assertEqual(pack1.location_id, self.shelf2)

    def test_pack_multiple_location_03(self):
        """ Creates a delivery and reserves a package. Then this test will scan
         a different location source, the package should be removed.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0), (4, grp_multi_loc.id, 0)]})

        # Creates a package with a quant in it.
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK000666',
        })
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.shelf1,
            quantity=5,
            package_id=pack1,
        )

        # Creates a delivery transfer for this package.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        picking_form.location_id = self.stock_location
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        delivery_picking = picking_form.save()
        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        url = self._get_client_action_url(delivery_picking.id)

        self.start_tour(url, 'test_pack_multiple_location_03', login='admin', timeout=180)
        self.assertFalse(delivery_picking.move_line_ids.package_id)

    def test_pack_source_location(self):
        """ Put a package in shelf4. Then this test will scan
        this package, the source location of line should be the same location of the package.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_pack.id), Command.link(grp_multi_loc.id)]})
        self.picking_type_internal.active = True
        self.picking_type_internal.show_entire_packs = False
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        # Creates a package with a quant in it.
        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK123666',
        })
        self.env['stock.quant']._update_available_quantity(
            product_id=self.product1,
            location_id=self.shelf4,
            quantity=5,
            package_id=pack1,
        )

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.shelf4, package_id=pack1), 5)
        self.start_tour(url, 'test_pack_source_location', login='admin', timeout=180)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.shelf4, package_id=pack1), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location, package_id=pack1), 5)

    def test_put_in_pack_from_multiple_pages(self):
        """ In an internal picking where prod1 and prod2 are reserved in shelf1 and shelf2, processing
        all these products and then hitting put in pack should move them all in the new pack.
        """
        self.clean_access_rights()
        # Adapts the setting to scan only the source location.
        self.picking_type_internal.restrict_scan_dest_location = 'no'
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf2, 1)

        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_multiple_pages',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': internal_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_multiple_pages',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': internal_picking.id,
        })

        url = self._get_client_action_url(internal_picking.id)
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_put_in_pack_from_multiple_pages', login='admin', timeout=180)

        pack = self.env['stock.quant.package'].search([])[-1]
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(sum(pack.quant_ids.mapped('quantity')), 4)

    def test_put_in_pack_no_freeze(self):
        """ Test that the page doesn't freeze when clicking on put in pack """
        self.clean_access_rights()
        self.env['res.config.settings'].create({'group_stock_tracking_lot': True}).execute()

        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.productlot1
            move.product_uom_qty = 13.5

        receipt = receipt_form.save()
        receipt.action_confirm()
        receipt.action_assign()

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_put_in_pack_no_freeze', login='admin', timeout=180)

    def test_reload_flow(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        self.start_tour("/odoo/barcode", 'test_reload_flow', login='admin', timeout=180)

        move_line1 = self.env['stock.move.line'].search_count([
            ('product_id', '=', self.product1.id),
            ('location_dest_id', '=', self.shelf1.id),
            ('location_id', '=', self.supplier_location.id),
            ('quantity', '=', 2),
            ('picked', '=', True),
        ])
        move_line2 = self.env['stock.move.line'].search_count([
            ('product_id', '=', self.product2.id),
            ('location_dest_id', '=', self.shelf1.id),
            ('location_id', '=', self.supplier_location.id),
            ('quantity', '=', 1),
            ('picked', '=', True),
        ])
        self.assertEqual(move_line1, 1)
        self.assertEqual(move_line2, 1)

    def test_duplicate_serial_number(self):
        """ Simulate a receipt and a delivery with a product tracked by serial
        number. It will try to break the ClientAction by using twice the same
        serial number.
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.start_tour("/odoo/barcode", 'test_receipt_duplicate_serial_number', login='admin', timeout=180)
        self.start_tour("/odoo/barcode", 'test_delivery_duplicate_serial_number', login='admin', timeout=180)

    def test_bypass_source_scan(self):
        """ Scan a lot, package, product without source location scan. """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        # For the purpose of this test, disable the source scan (mandatory for a deliery otherwise).
        self.picking_type_out.restrict_scan_source_location = 'no'

        lot1 = self.env['stock.lot'].create({'name': 'lot1', 'product_id': self.productlot1.id})
        lot2 = self.env['stock.lot'].create({'name': 'serial1', 'product_id': self.productserial1.id})

        pack1 = self.env['stock.quant.package'].create({
            'name': 'THEPACK',
        })

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf1, 2, lot_id=lot1)
        self.env['stock.quant']._update_available_quantity(self.productserial1, self.shelf2, 1, lot_id=lot2)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 4, package_id=pack1)

        # Creates a second pack with some qty in a location the delivery shouldn't have access.
        pack2 = self.env['stock.quant.package'].create({'name': 'SUSPACK'})
        other_loc = self.env['stock.location'].create({
            'name': "Second Stock",
            'location_id': self.stock_location.location_id.id,
            'barcode': 'WH-SECOND-STOCK',
        })
        self.env['stock.quant']._update_available_quantity(self.product1, other_loc, 4, package_id=pack2)

        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        url = self._get_client_action_url(delivery_picking.id)

        self.env['stock.move'].create({
            'name': 'test_bypass_source_scan_1_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productserial1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': delivery_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_bypass_source_scan_1_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_bypass_source_scan_1_3',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4,
            'picking_id': delivery_picking.id,
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()

        self.start_tour(url, 'test_bypass_source_scan', login='admin', timeout=180)

    def test_put_in_pack_from_different_location(self):
        """ Scans two different products from two different locations, then put them in pack and
        scans a destination location. Checks the package is in the right location.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.picking_type_internal.active = True
        self.picking_type_internal.restrict_scan_source_location = 'no'
        self.picking_type_internal.restrict_scan_dest_location = 'optional'
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf3, 1)

        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_different_location',
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_different_location2',
            'location_id': self.shelf3.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })
        # Resets package sequence to be sure we'll have the attended packages name.
        seq = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')])
        seq.number_next_actual = 1

        url = self._get_client_action_url(internal_picking.id)
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_put_in_pack_from_different_location', login='admin', timeout=180)
        pack = internal_picking.move_line_ids.result_package_id
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(pack.location_id, self.shelf2)

    def test_put_in_pack_before_dest(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.picking_type_internal.active = True
        self.picking_type_internal.restrict_scan_dest_location = 'mandatory'
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'

        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf3, 1)

        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_before_dest',
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_before_dest',
            'location_id': self.shelf3.id,
            'location_dest_id': self.shelf4.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking.id,
        })

        url = self._get_client_action_url(internal_picking.id)
        internal_picking.action_confirm()
        internal_picking.action_assign()

        self.start_tour(url, 'test_put_in_pack_before_dest', login='admin', timeout=180)
        pack = self.env['stock.quant.package'].search([])[-1]
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(pack.location_id, self.shelf2)

    def test_put_in_pack_scan_package(self):
        """ Put in pack a product line, then scan the newly created package to
        assign it to another lines.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 1)

        # Resets package sequence to be sure we'll have the attended packages name.
        seq = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')])
        seq.number_next_actual = 1

        # Creates a delivery with three move lines: two from Section 1 and one from Section 2.
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 2
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 1

        delivery = delivery_form.save()
        delivery.action_confirm()
        delivery.action_assign()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_put_in_pack_scan_package', login='admin', timeout=180)

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(len(delivery.move_line_ids), 3)
        for move_line in delivery.move_line_ids:
            self.assertEqual(move_line.result_package_id.name, 'PACK0000001')

    def test_put_in_pack_new_lines(self):
        """
        Receive a product P, put it in a pack PK and validates the receipt.
        Then, do the same a second time with the same package PK
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        receipt01 = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt01.id)
        self.start_tour(url, 'test_put_in_pack_new_lines', login='admin', timeout=180)

        self.assertRecordValues(receipt01.move_line_ids, [
            {'product_id': self.product1.id, 'qty_done': 1, 'result_package_id': self.package.id},
        ])
        self.assertEqual(self.package.quant_ids.available_quantity, 1)

        receipt02 = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        url = self._get_client_action_url(receipt02.id)
        self.start_tour(url, 'test_put_in_pack_new_lines', login='admin', timeout=180)

        self.assertRecordValues(receipt02.move_line_ids, [
            {'product_id': self.product1.id, 'qty_done': 1, 'result_package_id': self.package.id},
        ])
        self.assertEqual(self.package.quant_ids.available_quantity, 2)

    def test_highlight_packs(self):
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        pack1 = self.env['stock.quant.package'].create({
            'name': 'PACK001',
        })
        pack2 = self.env['stock.quant.package'].create({
            'name': 'PACK002',
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4, package_id=pack1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4, package_id=pack1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2, package_id=pack2)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 2, package_id=pack2)

        out_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'state': 'draft',
        })

        self.picking_type_out.show_entire_packs = True

        self.env['stock.package_level'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'package_id': pack1.id,
            'is_done': False,
            'picking_id': out_picking.id,
            'company_id': self.env.company.id,
        })

        url = self._get_client_action_url(out_picking.id)
        out_picking.action_confirm()
        out_picking.action_assign()

        self.start_tour(url, 'test_highlight_packs', login='admin', timeout=180)

    def test_picking_owner_scan_package(self):
        grp_owner = self.env.ref('stock.group_tracking_owner')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_owner.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7, package_id=self.package, owner_id=self.owner)

        self.start_tour("/odoo/barcode", 'test_picking_owner_scan_package', login='admin', timeout=180)

        move_line = self.env['stock.move.line'].search([('product_id', '=', self.product1.id)], limit=1)
        self.assertTrue(move_line)

        line_owner = move_line.owner_id
        self.assertEqual(line_owner.id, self.owner.id)

    def test_picking_type_mandatory_scan_settings(self):
        ''' Makes some operations with different scan's settings.'''
        self.clean_access_rights()

        # Enables packages and multi-locations.
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0), (4, grp_lot.id, 0)]})
        # Creates a product without barcode to check it can always be processed regardless the config.
        product_without_barcode = self.env['product.product'].create({
            'name': 'Barcodeless Product',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        # Adds products' quantities.
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 8)
        self.env['stock.quant']._update_available_quantity(product_without_barcode, self.shelf1, 8)

        # First config: products must be scanned, empty picking can't be immediatly validated,
        # locations can't be scanned, no put in pack.
        self.picking_type_internal.barcode_validation_after_dest_location = False
        self.picking_type_internal.barcode_validation_all_product_packed = False
        self.picking_type_internal.barcode_validation_full = False
        self.picking_type_internal.restrict_scan_product = True
        self.picking_type_internal.restrict_put_in_pack = 'optional'
        self.picking_type_internal.restrict_scan_source_location = 'no'
        self.picking_type_internal.restrict_scan_dest_location = 'no'

        # Creates an internal transfer, from WH/Stock/Shelf 1 to WH/Stock.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_internal
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 4
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_without_barcode
            move.product_uom_qty = 4

        picking_internal_1 = picking_form.save()
        picking_internal_1.action_confirm()
        picking_internal_1.action_assign()

        url = self._get_client_action_url(picking_internal_1.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_settings_pick_int_1', login='admin', timeout=180)
        self.assertEqual(picking_internal_1.state, 'done')

        # Second picking: change the config (same than before but locations MUST be scanned).
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'
        self.picking_type_internal.restrict_scan_dest_location = 'mandatory'
        # Creates an internal transfer, from WH/Stock/Shelf 1 to WH/Stock.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_internal
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 4
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_without_barcode
            move.product_uom_qty = 4

        picking_internal_2 = picking_form.save()
        picking_internal_2.action_confirm()
        picking_internal_2.action_assign()

        url = self._get_client_action_url(picking_internal_2.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_settings_pick_int_2', login='admin', timeout=180)
        self.assertEqual(picking_internal_2.state, 'done')

    def test_receipt_scan_package_and_location_after_group_of_product(self):
        """ This test ensures when a package or a destination is scanned after a group of product,
        if picking type's destination/package destination is on "After group of product" (optional)
        then all and only previously scanned line will be packed/go to this location.
        """
        # Enables packages and multi-locations.
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        # Creates a product without barcode to check it will count even if not
        # scanned but processed through the button.
        product_without_barcode = self.env['product.product'].create({
            'name': 'Barcodeless Product',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        # Create an empty package.
        package = self.env['stock.quant.package'].create({'name': 'pack-128'})

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 4
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_without_barcode
            move.product_uom_qty = 4
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productlot1
            move.product_uom_qty = 6

        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        picking_receipt.action_assign()

        url = self._get_client_action_url(picking_receipt.id)
        self.start_tour(url, 'test_receipt_scan_package_and_location_after_group_of_product', login='admin', timeout=180)
        self.assertEqual(picking_receipt.state, 'done')
        (lot1, lot2, lot3) = self.env['stock.lot'].search([
            ('product_id', '=', self.productlot1.id), ('name', 'in', ['lot-01', 'lot-02', 'lot-03'])
        ])
        move_lines = picking_receipt.move_line_ids.sorted(lambda ml: (ml.product_id.id, ml.location_dest_id.id))
        self.assertRecordValues(move_lines, [
            {'product_id': self.product1.id, 'location_dest_id': self.shelf3.id, 'qty_done': 2, 'lot_id': False, 'result_package_id': package.id},
            {'product_id': self.product1.id, 'location_dest_id': self.shelf1.id, 'qty_done': 2, 'lot_id': False, 'result_package_id': False},
            {'product_id': self.productlot1.id, 'location_dest_id': self.shelf3.id, 'qty_done': 2, 'lot_id': lot3.id, 'result_package_id': package.id},
            {'product_id': self.productlot1.id, 'location_dest_id': self.shelf1.id, 'qty_done': 2, 'lot_id': lot1.id, 'result_package_id': False},
            {'product_id': self.productlot1.id, 'location_dest_id': self.shelf1.id, 'qty_done': 1, 'lot_id': lot2.id, 'result_package_id': False},
            {'product_id': self.productlot1.id, 'location_dest_id': self.shelf2.id, 'qty_done': 1, 'lot_id': lot2.id, 'result_package_id': False},
            {'product_id': product_without_barcode.id, 'location_dest_id': self.shelf1.id, 'qty_done': 4, 'lot_id': False, 'result_package_id': False},
        ])

    def test_receipt_assign_sibling_reservation_no_empty_line(self):
        """ This check ensure that changing the dest location does not create an empty line.
        """
        # Enables multi-locations and lots.
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productlot1
            move.product_uom_qty = 2

        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        picking_receipt.action_assign()

        url = self._get_client_action_url(picking_receipt.id)
        self.start_tour(url, 'test_receipt_assign_sibling_reservation_no_empty_line', login='admin', timeout=180)

        self.assertEqual(picking_receipt.state, 'done')
        (lot1, lot2) = self.env['stock.lot'].search([
            ('product_id', '=', self.productlot1.id), ('name', 'in', ['lot-01', 'lot-02'])
        ])
        move_lines = picking_receipt.move_line_ids.sorted(lambda ml: (ml.product_id.id, ml.lot_id.id))
        self.assertRecordValues(move_lines, [
            {'product_id': self.productlot1.id, 'location_dest_id': self.shelf1.id, 'qty_done': 1, 'lot_id': lot1.id},
            {'product_id': self.productlot1.id, 'location_dest_id': self.shelf1.id, 'qty_done': 1, 'lot_id': lot2.id},
        ])

    def test_picking_type_mandatory_scan_product_packaging(self):
        """ Check a product's packaging can also be scanned when the scan of a product is mandatory.
        """
        self.clean_access_rights()
        group_packaging = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [Command.link(group_packaging.id)]})
        self.picking_type_in.restrict_scan_product = True
        self.env['product.packaging'].create({
            'barcode': 'product1x10',
            'name': "product1 x10",
            'product_id': self.product1.id,
            'qty': 10,
        })
        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'move_ids': [Command.create({
                'name': 'product1 x 10',
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product1.id,
                'product_uom': self.product1.uom_id.id,
                'product_uom_qty': 10,
            })],
        })
        receipt.action_confirm()
        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_product_packaging', login='admin')

    def test_picking_type_mandatory_scan_complete_flux(self):
        """ From the receipt to the delivery, make a complete flux with each
        picking types having their own barcode's settings:
        - Starts by receive multiple products (some of them are tracked);
        - Stores each product in a different location;
        - Makes a picking operation;
        - Then makes a packing operation and put all products in pack;
        - And finally, does the delivery.
        """
        def create_picking(picking_type):
            picking_form = Form(self.env['stock.picking'])
            picking_form.picking_type_id = picking_type
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.product1
                move.product_uom_qty = 2
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.product2
                move.product_uom_qty = 1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = product_without_barcode
                move.product_uom_qty = 1
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.productserial1
                move.product_uom_qty = 3
            with picking_form.move_ids_without_package.new() as move:
                move.product_id = self.productlot1
                move.product_uom_qty = 6
            return picking_form.save()

        self.clean_access_rights()
        # Creates a product without barcode to check it can always be processed regardless the config.
        product_without_barcode = self.env['product.product'].create({
            'name': 'Barcodeless Product',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        # Enables packages, multi-locations and multiple steps routes.
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_production_lot').id, 0)]})
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_tracking_lot').id, 0)]})
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_stock_multi_locations').id, 0)]})
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_adv_location').id, 0)]})
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.reception_steps = 'two_steps'
        warehouse.delivery_steps = 'pick_pack_ship'

        # Creates two cluster packs.
        self.env['stock.quant.package'].create({
            'name': 'cluster-pack-01',
            'package_use': 'reusable',
        })
        self.env['stock.quant.package'].create({
            'name': 'cluster-pack-02',
            'package_use': 'reusable',
        })
        # Resets package sequence to be sure we'll have the attended packages name.
        seq = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')])
        seq.number_next_actual = 1

        # Configures the picking type's scan settings.
        # Receipt: no put in pack, can not be directly validate.
        self.picking_type_in.barcode_validation_full = False
        self.picking_type_in.restrict_put_in_pack = 'no'
        # Quality Control / Storage (internal transfer): no put in pack, scan dest. after each product.
        internal_types = warehouse.qc_type_id | warehouse.store_type_id
        internal_types.barcode_validation_full = False
        internal_types.restrict_put_in_pack = 'no'
        internal_types.restrict_scan_dest_location = 'mandatory'
        internal_types.show_reserved_sns = True
        # Pick: source mandatory, lots reserved only.
        warehouse.pick_type_id.barcode_validation_full = False
        warehouse.pick_type_id.restrict_scan_source_location = 'mandatory'
        warehouse.pick_type_id.restrict_put_in_pack = 'mandatory'  # Will use cluster packs.
        warehouse.pick_type_id.restrict_scan_tracking_number = 'mandatory'
        warehouse.pick_type_id.restrict_scan_dest_location = 'no'
        warehouse.pick_type_id.show_reserved_sns = True
        # Pack: pack after group, all products have to be packed to be validate.
        warehouse.pack_type_id.restrict_put_in_pack = 'optional'
        warehouse.pack_type_id.restrict_scan_tracking_number = 'mandatory'
        warehouse.pack_type_id.barcode_validation_all_product_packed = True
        warehouse.pick_type_id.restrict_scan_dest_location = 'no'
        # Delivery: pack after group, all products have to be packed to be validate.
        self.picking_type_out.restrict_put_in_pack = 'optional'
        self.picking_type_out.restrict_scan_tracking_number = 'mandatory'
        self.picking_type_out.barcode_validation_all_product_packed = True
        self.picking_type_out.show_entire_packs = True

        # Creates and assigns the receipt.
        picking_receipt = create_picking(self.picking_type_in)
        picking_receipt.action_confirm()
        picking_receipt.action_assign()

        # Creates the pick, pack, ship.
        picking_pick = create_picking(warehouse.pick_type_id)

        # Process each picking one by one.
        url = self._get_client_action_url(picking_receipt.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_complete_flux_receipt', login='admin', timeout=180)
        self.assertEqual(picking_receipt.state, 'done')

        # Get the storage operation (created by the receipt).
        picking_internal = picking_receipt.move_ids.move_dest_ids.picking_id
        url = self._get_client_action_url(picking_internal.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_complete_flux_internal', login='admin', timeout=180)
        self.assertEqual(picking_internal.state, 'done')
        picking_pick.action_confirm()
        picking_pick.action_assign()
        url = self._get_client_action_url(picking_pick.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_complete_flux_pick', login='admin', timeout=180)
        self.assertEqual(picking_pick.state, 'done')

        picking_pack = self.env['stock.picking'].search([('location_id', '=', warehouse.pack_type_id.default_location_src_id.id)])
        picking_pack.action_confirm()
        picking_pack.action_assign()
        for move_line in picking_pack.move_line_ids:  # TODO: shouldn't have to do that, reusable packages shouldn't be set in `result_package_id` for the next move.
            move_line.result_package_id = False
        url = self._get_client_action_url(picking_pack.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_complete_flux_pack', login='admin', timeout=180)
        self.assertEqual(picking_pack.state, 'done')

        picking_delivery = self.env['stock.picking'].search([('location_id', '=', warehouse.out_type_id.default_location_src_id.id)])
        picking_delivery.action_confirm()
        picking_delivery.action_assign()
        url = self._get_client_action_url(picking_delivery.id)
        self.start_tour(url, 'test_picking_type_mandatory_scan_complete_flux_delivery', login='admin', timeout=180)
        self.assertEqual(picking_delivery.state, 'done')

    def test_procurement_backorder(self):
        self.clean_access_rights()
        product_a, _product_b = self.env['product.product'].create([{
            'name': p_name,
            'is_storable': True,
            'barcode': p_name,
        } for p_name in ['PA', 'PB']])

        customer = self.env["res.partner"].create({"name": "Customer"})
        proc_group = self.env["procurement.group"].create({"partner_id": customer.id})

        procurement = self.env["procurement.group"].Procurement(
            product_a, 1, product_a.uom_id,
            self.env.ref('stock.stock_location_customers'),
            product_a.name,
            "/",
            self.env.company,
            {
                "warehouse_id": self.env['stock.warehouse'].search([], limit=1),
                "group_id": proc_group,
            }
        )
        self.env["procurement.group"].run([procurement])

        move = self.env['stock.move'].search([('product_id', '=', product_a.id)], limit=1)
        url = self._get_client_action_url(move.picking_id.id)
        self.start_tour(url, 'test_procurement_backorder', login='admin', timeout=99)
        self.assertEqual(len(proc_group.stock_move_ids), 2)

    def test_receipt_delete_button(self):
        """ Scan products that not part of a receipt. Check that products not part of original receipt
        can be deleted, but the products that are part of the original receipt cannot be deleted.
        """
        self.clean_access_rights()
        receipt_picking = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'name': 'test_receipt_1',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.product1.uom_id.id,
            'product_uom_qty': 1,
            'picking_id': receipt_picking.id,
            'picking_type_id': self.picking_type_in.id,
        })
        # extra product to test that deleting works
        self.env['product.product'].create({
            'name': 'product3',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product3',
        })

        url = self._get_client_action_url(receipt_picking.id)
        receipt_picking.action_confirm()
        self.start_tour(url, 'test_receipt_delete_button', login='admin', timeout=180)
        self.assertEqual(len(receipt_picking.move_line_ids), 2, "2 lines expected: product1 + product2")

    def test_scan_aggregate_barcode(self):
        """ Checks the config parameter `stock_barcode.barcode_separator_regex`
        works as expected and it's possible to scan aggregate barcodes if its
        individual barcode encodings are separated by the separator."""
        self.clean_access_rights()
        self.env['ir.config_parameter'].set_param('stock_barcode.barcode_separator_regex', '[,|]')
        url = "/odoo/action-stock_barcode.stock_barcode_action_main_menu"
        self.start_tour(url, "test_scan_aggregate_barcode", login="admin", timeout=180)
        # Check the receipt values.
        domain = [('picking_type_id', '=', self.picking_type_in.id), ('state', '=', 'done')]
        receipt = self.env['stock.picking'].search(domain, limit=1, order="id DESC")
        self.assertRecordValues(receipt.move_ids.sorted(lambda mv: mv.product_id), [
            {'product_id': self.product1.id, 'quantity': 4},
            {'product_id': self.product2.id, 'quantity': 2},
            {'product_id': self.productserial1.id, 'quantity': 10},
        ])
        tracked_move = receipt.move_ids.filtered(lambda mv: mv.product_id == self.productserial1)
        self.assertEqual(
            tracked_move.lot_ids.sorted(lambda sn: sn.name).mapped('name'),
            ['sn01', 'sn02', 'sn03', 'sn04', 'sn05', 'sn06', 'sn07', 'sn08', 'sn09', 'sn10']
        )

    def test_scrap(self):
        """ Checks the scrap button is displayed for when it's possible to scrap
        and the corresponding barcode command follows the same rules."""
        # Creates SN product lots, for digipad testing
        self.env['stock.lot'].create([{
            'name': 'SN0001',
            'product_id': self.productserial1.id,
        }, {
            'name': 'SN0002',
            'product_id': self.productserial1.id,
        }])
        # Creates a receipt and a delivery.
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        # Adds one line with SN product, for digipad testing
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.productserial1
        receipt_picking = receipt_form.save()
        receipt_picking.action_confirm()
        receipt_picking.action_assign()
        receipt_picking.name = "receipt_scrap_test"

        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        delivery_picking = delivery_form.save()
        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        delivery_picking.name = "delivery_scrap_test"
        # Opens the barcode main menu to be able to open the pickings by scanning their name.
        self.start_tour("/odoo/barcode", "test_scrap", login="admin", timeout=180)

    def test_scrap_change_source_location(self):
        self.clean_access_rights()
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        self.product1.tracking = 'lot'
        lot1 = self.env['stock.lot'].create({
            'name': 'Lot1',
            'product_id': self.product1.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 25, lot_id=lot1)
        picking = self.env['stock.picking'].create({
            'name': self.product1.name,
            'location_id': self.stock_location.id,
            'location_dest_id': self.env.ref('stock.stock_location_output').id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': self.product1.name,
            'product_id': self.product1.id,
            'lot_ids': [Command.set([lot1.id])],
            'product_uom_qty': 10.00,
            'quantity': 10.00,
            'picking_id': picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.env.ref('stock.stock_location_output').id,
        })
        picking.action_confirm()
        self.assertEqual(picking.move_ids.lot_ids, lot1)
        url = self._get_client_action_url(picking.id)
        self.start_tour(url, 'test_scrap_change_source_location', login='admin')
        scrap_location = self.env['stock.location'].search([
            ('scrap_location', '=', 'True'),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertRecordValues(
            lot1.quant_ids,
            [
                {'location_id': self.shelf1.id, 'quantity': 0},
                {'location_id': scrap_location.id, 'quantity': 15},
                {'location_id': self.ref('stock.stock_location_output'), 'quantity': 10},
            ]
        )

    def test_show_entire_package(self):
        """ Enables 'Move Entire Packages' for delivery and then creates two deliveries:
          - One where we use package level;
          - One where we use move without package.
        Then, checks it's the right type of line who is shown in the Barcode App."""
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.picking_type_out.show_entire_packs = True
        package1 = self.env['stock.quant.package'].create({'name': 'package001'})
        package2 = self.env['stock.quant.package'].create({'name': 'package002'})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4, package_id=package1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4, package_id=package2)

        delivery_with_package_level = self.env['stock.picking'].create({
            'name': "Delivery with Package Level",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'state': 'draft',
        })
        self.env['stock.package_level'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'package_id': package1.id,
            'is_done': False,
            'picking_id': delivery_with_package_level.id,
            'company_id': self.env.company.id,
        })
        delivery_with_package_level.action_confirm()
        delivery_with_package_level.action_assign()

        delivery_with_move = self.env['stock.picking'].create({
            'name': "Delivery with Stock Move",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'state': 'draft',
        })
        self.env['stock.move'].create({
            'name': 'test_show_entire_package',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_with_move.id,
        })
        delivery_with_move.action_confirm()
        delivery_with_move.action_assign()

        self.assertFalse(delivery_with_package_level.package_level_ids.is_done)
        self.start_tour('/odoo/barcode', 'test_show_entire_package', login='admin', timeout=180)
        self.assertTrue(delivery_with_package_level.package_level_ids.is_done)

    def test_define_the_destination_package(self):
        """
        Suppose a picking that moves a product from a package to another one
        This test ensures that the user can scans the destination package
        """
        self.clean_access_rights()
        group_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, group_pack.id, 0)]})

        pack01, pack02 = self.env['stock.quant.package'].create([{
            'name': name,
        } for name in ('PACK01', 'PACK02')])

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 2, package_id=pack01)

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        delivery = picking_form.save()
        delivery.action_confirm()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_define_the_destination_package', login='admin', timeout=180)

        self.assertRecordValues(delivery.move_line_ids, [
            {'product_id': self.product1.id, 'qty_done': 1, 'result_package_id': pack02.id, 'state': 'done'},
        ])

    def test_avoid_useless_line_creation(self):
        """
        Suppose
            - the option "Create New Lots/Serial Numbers" disabled
            - a tracked product P with an available lot L
        On a delivery, a user scans L (it should add a line)
        Then, the user scans a non-existing lot LX (it should not create any line)
        """
        self.clean_access_rights()
        group_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, group_lot.id, 0)]})

        lot01 = self.env['stock.lot'].create({
            'name': "LOT01",
            'product_id': self.productlot1.id,
        })

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 1, lot_id=lot01)

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        delivery = picking_form.save()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_avoid_useless_line_creation', login='admin', timeout=180)

        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.productlot1.id, 'lot_ids': lot01.ids, 'quantity': 1},
        ])

    def test_setting_barcode_allow_extra_product(self):
        """ This test ensures we can't add non-reserved product when the picking type is set like
        that, but we can still scan any product for a picking created on the fly.
        """
        self.clean_access_rights()
        self.picking_type_out.barcode_allow_extra_product = False
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product1.id,
            'inventory_quantity': 1,
            'location_id': self.stock_location.id,
        }).action_apply_inventory()
        # Create a delivery for product1 only.
        delivery = self.env['stock.picking'].create({
            'name': 'delivery_test',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': 'delivery_test move',
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'product_id': self.product1.id,
            'product_uom_qty': 1,
            'picking_id': delivery.id,
        })
        delivery.action_confirm()
        delivery.action_assign()
        self.start_tour("/odoo/barcode", 'test_setting_barcode_allow_extra_product', login='admin', timeout=180)

    def test_setting_barcode_allow_extra_product_with_packages(self):
        """
        Check that with allow extra products disabled, package scans containing extra
        products are ignored, while scans of valid packages are still processed.

        The test is performed with two deliveries: one in move entire package the other not.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [Command.link(grp_pack.id)]})
        # Disable "Allow Extra Products" setting
        self.picking_type_out.barcode_allow_extra_product = False
        picking_type_out_move_entire_package = self.picking_type_out.copy({'show_entire_packs': True})
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10)
        # PACK01-03: 10 x product1
        # PACK04: 10 x product1 and 5 x product2
        pack01, pack02, pack03, pack04 = self.env['stock.quant.package'].create([
            {'name': f"PACK0{i + 1}"} for i in range(4)
        ])
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10, package_id=pack01)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10, package_id=pack02)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10, package_id=pack03)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10, package_id=pack04)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 5, package_id=pack04)

        deliveries = self.env['stock.picking'].create([
            {
                'name': 'SBAEPWP',
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'picking_type_id': self.picking_type_out.id,
                'move_ids': [
                    Command.create({
                        'name': 'test_move',
                        'location_id': self.stock_location.id,
                        'location_dest_id': self.customer_location.id,
                        'product_id': self.product1.id,
                        'product_uom_qty': 5,
                    }),
                ],
            },
            {
                'name': 'SBAEPWMEP',
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'picking_type_id': picking_type_out_move_entire_package.id,
                'package_level_ids': [
                    Command.create({
                        'location_id': self.stock_location.id,
                        'location_dest_id': self.customer_location.id,
                        'package_id': pack02.id,
                        'company_id': self.env.company.id,
                    }),
                ],
            },
        ])
        deliveries.action_confirm()

        self.start_tour('/odoo/barcode', 'test_setting_barcode_allow_extra_product_with_packages', login='admin')

    def test_split_line_reservation(self):
        """ Tests new lines created when a line is split to take
            from qty in a different location than the reserved
            The following cases:
            - productlot1 available at given location
            - product1 partially available at given location
            - product2 not available
        """
        self.clean_access_rights()
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_production_lot').id, 0)]})
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_tracking_lot').id, 0)]})
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_stock_multi_locations').id, 0)]})
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_adv_location').id, 0)]})
        lot01 = self.env['stock.lot'].create({
            'name': "LOT01",
            'product_id': self.productlot1.id,
        })

        lot02 = self.env['stock.lot'].create({
            'name': "LOT02",
            'product_id': self.productlot1.id,
        })

        lot03 = self.env['stock.lot'].create({
            'name': "LOT03",
            'product_id': self.productlot1.id,
        })
        # all 3 products are available in WHSTOCK
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 5, lot_id=lot01)
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 5, lot_id=lot02)
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 5)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 5)
        # lots are available in shelfs
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf1, 2, lot_id=lot02)
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf2, 2, lot_id=lot03)
        # product 1 has some qty in shelf1
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        # create delivery
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productlot1
            move.product_uom_qty = 5
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 4
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 3

        delivery = picking_form.save()
        delivery.action_confirm()
        delivery.action_assign()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_split_line_reservation', login='admin', timeout=180)
        productlot_mls = delivery.move_ids.filtered(lambda m: m.product_id.id == self.productlot1.id).move_line_ids
        product1_mls = delivery.move_ids.filtered(lambda m: m.product_id.id == self.product1.id).move_line_ids
        product2_mls = delivery.move_ids.filtered(lambda m: m.product_id.id == self.product2.id).move_line_ids

        # Checks the move lines' quantities.
        self.assertRecordValues(productlot_mls, [
            {'quantity': 1, 'picked': True, 'lot_id': lot01.id, 'location_id': self.stock_location.id},
            {'quantity': 1, 'picked': True, 'lot_id': lot02.id, 'location_id': self.stock_location.id},
            {'quantity': 2, 'picked': True, 'lot_id': lot02.id, 'location_id': self.shelf1.id},
            {'quantity': 1, 'picked': True, 'lot_id': lot03.id, 'location_id': self.shelf2.id},
        ])
        self.assertRecordValues(product1_mls, [
            {'quantity': 2, 'picked': True, 'location_id': self.stock_location.id},
            # Only 1 quantity was available for reservation in shelf1
            {'quantity': 2, 'picked': True, 'location_id': self.shelf1.id},
        ])
        self.assertRecordValues(product2_mls, [
            {'quantity': 2, 'picked': True, 'location_id': self.stock_location.id},
            # No qty to reserve in shelf1.
            {'quantity': 1, 'picked': True, 'location_id': self.shelf1.id},
        ])

    def test_split_line_on_destination_scan(self):
        """ Ensures a non-complete line is split when a destination is scanned. """
        self.clean_access_rights()
        self.env.user.write({'groups_id': [(4, self.env.ref('stock.group_stock_multi_locations').id, 0)]})
        self.picking_type_internal.restrict_scan_dest_location = 'mandatory'
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'
        # Creates a receipt for 4x product1 and confirm it.
        receipt = self.env['stock.picking'].create({
            'location_dest_id': self.picking_type_in.default_location_dest_id.id,
            'location_id': self.supplier_location.id,
            'name': "receipt_split_line_on_destination_scan",
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'location_dest_id': receipt.location_dest_id.id,
            'location_id': receipt.location_id.id,
            'name': "product1 x4",
            'picking_id': receipt.id,
            'product_id': self.product1.id,
            'product_uom_qty': 4,
        })
        receipt.action_confirm()
        # Create an internal transfer for 7x product2 (reserved from two different locations.)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 3)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf2, 4)
        internal = self.env['stock.picking'].create({
            'location_dest_id': self.stock_location.id,
            'location_id': self.stock_location.id,
            'name': "internal_split_line_on_destination_scan",
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'location_dest_id': internal.location_dest_id.id,
            'location_id': internal.location_id.id,
            'name': "product2 x7",
            'picking_id': internal.id,
            'product_id': self.product2.id,
            'product_uom_qty': 7,
        })
        internal.action_confirm()
        # Process the receipt and the internal transfer in a tour, then checks its move lines values.
        self.start_tour('/odoo/barcode', 'test_split_line_on_destination_scan', login='admin')
        self.assertRecordValues(receipt.move_line_ids, [
            {'quantity': 2, 'picked': True, 'location_dest_id': receipt.location_dest_id.id},
            {'quantity': 2, 'picked': True, 'location_dest_id': self.shelf1.id},
        ])
        self.assertRecordValues(internal.move_line_ids, [
            {'quantity': 2, 'picked': True, 'location_id': self.shelf1.id, 'location_dest_id': self.shelf3.id},
            {'quantity': 2, 'picked': True, 'location_id': self.shelf2.id, 'location_dest_id': self.shelf2.id},
            {'quantity': 1, 'picked': True, 'location_id': self.shelf1.id, 'location_dest_id': self.stock_location.id},
            {'quantity': 2, 'picked': True, 'location_id': self.shelf2.id, 'location_dest_id': self.shelf1.id},
        ])

    def test_split_line_on_exit_for_delivery(self):
        """ Ensures that exit an unfinished operation will split the uncompleted move lines to have
        one move line with all picked quantity and one move line with the remaining quantity."""
        self.clean_access_rights()
        product3 = self.env['product.product'].create({
            'name': 'product3',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product3',
        })
        # Adds some quantity in stock but not enough to fully complete the delivery.
        self.env['stock.quant'].with_context(inventory_mode=True).create([{
            'product_id': product.id,
            'inventory_quantity': qty,
            'location_id': self.stock_location.id,
        } for product, qty in [
            (self.product1, 4), (self.product2, 4), (product3, 2)]
        ]).action_apply_inventory()

        # Creates a delivery for 4x product1, 4x product2 and 4x product3.
        delivery = self.env['stock.picking'].create({
            'name': "delivery_split_line_on_exit",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create([{
            'location_dest_id': delivery.location_dest_id.id,
            'location_id': delivery.location_id.id,
            'name': f"{product.name} x4",
            'picking_id': delivery.id,
            'product_id': product.id,
            'product_uom_qty': 4,
        } for product in [self.product1, self.product2, product3]])
        delivery.action_confirm()

        self.start_tour("/odoo/barcode", 'test_split_line_on_exit_for_delivery', login='admin')
        # Checks delivery moves values:
        # - product1 line should not be split (completed line)
        # - product2 line should be split in two (2 qty picked, 2 qty left)
        # - product3 line should not be split (not picked at all)
        self.assertRecordValues(delivery.move_ids, [
            {'product_id': self.product1.id, 'quantity': 4, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 4, 'picked': True},
            {'product_id': product3.id, 'quantity': 2, 'picked': False},
        ])
        self.assertRecordValues(delivery.move_line_ids, [
            {'product_id': self.product1.id, 'quantity': 4, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 2, 'picked': True},
            {'product_id': product3.id, 'quantity': 2, 'picked': False},
            {'product_id': self.product2.id, 'quantity': 2, 'picked': False},
        ])

    def test_split_line_on_exit_for_delivery_with_lot(self):
        """ Ensures that the total quantity handled by the splitted moves does
        not exceed the initial demand in case another lot than the initially
        reserved one is scanned from the barcode."""
        self.clean_access_rights()

        group_pack = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, group_pack.id, 0)]})
        lots = self.env['stock.lot'].create([
            {'name': 'LOT001', 'product_id': self.productlot1.id},
            {'name': 'LOT002', 'product_id': self.productlot1.id},
        ])
        for lot in lots:
            self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 5, lot_id=lot)
        # Creates a delivery for 3 x productlot1 initially reserved with LOT001
        delivery = self.env['stock.picking'].create({
            'name': "delivery_split_move_on_exit",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'name': "productlot1 x3",
                'product_id': self.productlot1.id,
                'product_uom_qty': 3,
            })]
        })
        delivery.action_confirm()
        self.assertRecordValues(delivery.move_ids, [
            {'product_uom_qty': 3.0, 'quantity': 3.0, 'picked': False, 'lot_ids': lots[0].ids }
        ])
        self.assertRecordValues(delivery.move_line_ids, [
            {'quantity': 3.0, 'picked': False, 'lot_id': lots[0].id }
        ])

        action = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = f"/web#action={action.id}"
        self.start_tour(url, 'test_split_line_on_exit_for_delivery_with_lot', login='admin')
        # Checks receipt moves values.
        self.assertRecordValues(delivery.move_line_ids.sorted('quantity'), [
            {'quantity': 1, 'picked': True, 'lot_id': lots[0].id},
            {'quantity': 2, 'picked': True, 'lot_id': lots[1].id},
        ])

    def test_split_line_on_exit_for_receipt_with_grouped_lot(self):
        """ Ensures that the total quantity handled by the splitted moves does
        not exceed the initial demand in case the barcode lot lines are grouped.
        """
        self.clean_access_rights()
        grouped_lot_group = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [Command.link(grouped_lot_group.id)]})
        # Creates a receipt for 3 x productlot1
        receipt = self.env['stock.picking'].create({
            'name': "SPLOEFRWGL",
            'location_id': self.stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'picking_type_id': self.picking_type_in.id,
            'move_ids': [Command.create({
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'name': "productlot1 x3",
                'product_id': self.productlot1.id,
                'product_uom_qty': 3,
            })]
        })
        receipt.action_confirm()
        self.assertRecordValues(receipt.move_ids, [
            {'product_uom_qty': 3.0, 'quantity': 3.0, 'picked': False}
        ])
        self.start_tour('/odoo/barcode', 'test_split_line_on_exit_for_receipt_with_grouped_lot', login='admin')
        # Checks receipt moves values.
        self.assertRecordValues(receipt.move_ids, [
            {'product_uom_qty': 3.0, 'quantity': 3.0, 'picked': True},
        ])

    def test_split_line_on_exit_for_receipt(self):
        """ Ensures that exit an unfinished operation will split the uncompleted move lines to have
        one move line with all picked quantity and one move line with the remaining quantity."""
        self.clean_access_rights()
        # Enables package to check the split after a put in pack.
        group_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, group_pack.id, 0)]})
        # Set packages' sequence to 1000 to find it easily during the tour.
        package_sequence = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')], limit=1)
        package_sequence.write({'number_next_actual': 1000})

        # Creates a receipt for 4x product1 and 4x product2.
        receipt = self.env['stock.picking'].create({
            'name': "receipt_split_line_on_exit",
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'location_dest_id': receipt.location_dest_id.id,
            'location_id': receipt.location_id.id,
            'name': "product1 x4",
            'picking_id': receipt.id,
            'product_id': self.product1.id,
            'product_uom_qty': 4,
        })
        self.env['stock.move'].create({
            'location_dest_id': receipt.location_dest_id.id,
            'location_id': receipt.location_id.id,
            'name': "product2 x4",
            'picking_id': receipt.id,
            'product_id': self.product2.id,
            'product_uom_qty': 4,
        })
        receipt.action_confirm()

        self.start_tour("odoo/barcode/", 'test_split_line_on_exit_for_receipt', login='admin')
        # Checks receipt moves values.
        self.assertRecordValues(receipt.move_ids, [
            {'product_id': self.product1.id, 'quantity': 4, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 4, 'picked': True},
        ])
        self.assertRecordValues(receipt.move_ids.move_line_ids, [
            {'product_id': self.product1.id, 'quantity': 2, 'picked': True},
            {'product_id': self.product1.id, 'quantity': 1, 'picked': False},
            {'product_id': self.product1.id, 'quantity': 1, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 1, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 3, 'picked': False},
        ])

    def test_editing_done_picking(self):
        """ Create and validate a picking then try editing it."""
        self.clean_access_rights()
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 69

        receipt = picking_form.save()
        receipt.action_confirm()
        receipt.move_ids.quantity = 69
        receipt.button_validate()

        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_editing_done_picking', login='admin', timeout=180)

    def test_sml_sort_order_by_product_category(self):
        """Test the lines are correctly sorted in the Barcode App regarding
        their product's category.
        """
        self.clean_access_rights()
        # Creates two categories and some products using them.
        product_categoryB = self.env["product.category"].create({"name": "TestB"})
        product_categoryA = self.env["product.category"].create({"name": "TestA"})
        productA = self.env["product.product"].create(
            {"name": "Product A", "categ_id": product_categoryB.id, 'is_storable': True}
        )
        productB = self.env["product.product"].create(
            {"name": "Product B", "categ_id": product_categoryA.id, 'is_storable': True}
        )
        productC = self.env["product.product"].create(
            {"name": "Product C", "categ_id": product_categoryB.id, 'is_storable': True}
        )
        # Creates a receipt with three move lines (one for each product).
        receipt = self.env["stock.picking"].create(
            {
                "location_id": self.stock_location.id,
                "location_dest_id": self.stock_location.id,
                "picking_type_id": self.picking_type_in.id,
            }
        )
        self.env["stock.move.line"].create(
            [
                {
                    "product_id": productA.id,
                    "product_uom_id": productA.uom_id.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.stock_location.id,
                    "qty_done": 1,
                    "picking_id": receipt.id,
                },
                {
                    "product_id": productB.id,
                    "product_uom_id": productB.uom_id.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.stock_location.id,
                    "qty_done": 1,
                    "picking_id": receipt.id,
                },
                {
                    "product_id": productC.id,
                    "product_uom_id": productC.uom_id.id,
                    "location_id": self.stock_location.id,
                    "location_dest_id": self.stock_location.id,
                    "qty_done": 1,
                    "picking_id": receipt.id,
                },
            ]
        )
        url = self._get_client_action_url(receipt.id)
        self.start_tour(
            url, "test_sml_sort_order_by_product_category", login="admin", timeout=180
        )

    def test_create_backorder_after_qty_modified(self):
        """ Adding qty to an SML via the edit buttons updates the barcode cache;
        we should still be shown the confirmation dialog when validating a partially
        complete order, informing the user that a backorder will be created.
        """
        self.clean_access_rights()

        receipt = self.env['stock.picking'].create({
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'name': 'test_create_backorder_after_qty_modified move',
            'picking_id': receipt.id,
            'product_id': self.product1.id,
            'product_uom_qty': 2.0,
            'product_uom': self.product1.uom_id.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
        })
        receipt.action_confirm()

        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_create_backorder_after_qty_modified', login='admin', timeout=180)

        # Original receipt move demand should be modified and the resulting
        # backorder move demand should be for the rest of the original demand.
        backorder = self.env['stock.picking'].search([('backorder_id', '=', receipt.id)])
        self.assertEqual(backorder.move_ids[0].product_uom_qty, 1.0)
        self.assertEqual(receipt.move_ids[0].product_uom_qty, 1.0)

    def test_open_picking_dont_override_assigned_user(self):
        """
        Test that clicking on a picking from the barcode view does not replace
        the current responsible with the current user.
        """
        bob = self.env['res.users'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Bob'}).id,
            'login': 'bob',
        })
        receipt_picking = self.env['stock.picking'].create({
            'name': "test_responsible_receipt",
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'user_id': bob.id,
            'move_ids': [(0, 0, {
                'name': 'some product',
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product1.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 2
            })],
        })
        receipt_picking.action_confirm()
        action = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/odoo/action-stock_barcode.stock_barcode_action_main_menu"
        self.start_tour(url, 'test_open_picking_dont_override_assigned_user', login='admin', timeout=180)
        self.assertEqual(receipt_picking.user_id.id, bob.id, "Picking responsible should be unchanged after click when previously set")

    def test_multi_company_record_access_in_barcode(self):
        """ Test that creating a picking operation wholly in the barcode app will not permit a user
        to find records that don't belong to the operation type's company.
        """
        self.clean_access_rights()
        company2 = self.env['res.company'].create({'name': 'second company'})
        self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', company2.id),
        ], limit=1).barcode = 'company2_receipt'
        self.env.user.company_ids = [(4, company2.id)]

        self.product1.write({
            'company_id': self.env.company.id,
            'barcode': 'company1_product',
        })
        self.product2.write({
            'company_id': company2.id,
            'barcode': 'company2_product',
        })

        cids = '-'.join(str(cid) for cid in self.env.user.company_ids.ids)
        url = f'/odoo/action-stock_barcode.stock_barcode_action_main_menu?cids={cids}'
        self.start_tour(url, 'test_multi_company_record_access_in_barcode', login='admin', timeout=180)

        self.assertTrue(
            self.env['stock.picking'].search([
                ('company_id', '=', company2.id),
                ('product_id', 'in', self.product2.ids),
            ], limit=1)
        )

    def test_no_zero_demand_new_line_from_split(self):
        """ If a split of incomplete barcode lines is triggered when the line quantity == 0, don't
        go through with the split.
        """
        self.clean_access_rights()

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 1)
        picking = self.env['stock.picking'].create({
            'name': 'TNZDNLFS picking',
            'picking_type_id': self.picking_type_internal.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'name': 'TNZDNLFS move',
                'product_id': self.product1.id,
                'product_uom_qty': 1,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        picking.action_confirm()

        url = "/odoo/action-stock_barcode.stock_barcode_action_main_menu"
        self.start_tour(url, 'test_no_zero_demand_new_line_from_split', login='admin', timeout=180)

        self.assertRecordValues(
            picking.move_ids,
            [{'quantity': 1, 'product_uom_qty': 1, 'picked': False}]
        )
        self.assertRecordValues(
            picking.move_line_ids,
            [{'picked': False, 'quantity': 1}]
        )

    def test_barcode_pack_lot(self):
        """
        This test ensures that products of the same lot can be
        packed in different packages.
        """
        self.env.ref('base.group_user').implied_ids += self.env.ref('stock.group_production_lot')
        self.clean_access_rights()
        group_tracking = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [Command.link(group_tracking.id)]})
        warehouse = self.picking_type_out.warehouse_id
        # Enable "Show reserved lots/SN"
        warehouse.out_type_id.write({
            'show_reserved_sns': True,
            'restrict_scan_source_location': 'no',
        })
        # Create a product and its packaging.
        product = self.env['product.product'].create({
            'name': 'Lovely product',
            'is_storable': True,
            'tracking': 'lot',
            'uom_id': self.uom_unit.id,
        })

        lot_1, lot_2 = self.env['stock.lot'].create([
            {'name': 'LOT004', 'product_id': product.id},
            {'name': 'LOT005', 'product_id': product.id},
        ])
        # create 2 lots to test the flow for both reserved and not reserved lots
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 4, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 2, lot_id=lot_2)

        delivery = self.env['stock.picking'].create({
            'name': "Lovely delivery",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'name': 'Lovely move',
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': 4
            })],
        })
        delivery.action_confirm()
        self.assertEqual(delivery.move_line_ids.lot_id, lot_1)
        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_barcode_pack_lot_tour', login='admin', timeout=180)
        self.assertEqual(delivery.state, 'done')
        self.assertRecordValues(delivery.move_line_ids, [
            {'quantity': 1.0, 'lot_id': lot_1.id},
            {'quantity': 1.0, 'lot_id': lot_1.id},
            {'quantity': 1.0, 'lot_id': lot_2.id},
            {'quantity': 1.0, 'lot_id': lot_2.id},
        ])
        self.assertEqual(len(delivery.move_line_ids.result_package_id), 4)

    def test_barcode_picking_return(self):
        """ create a return from a done picking """
        self.clean_access_rights()

        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 5)

        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 5
        delivery = delivery_form.save()
        delivery.action_confirm()
        delivery.action_assign()
        delivery.button_validate()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_barcode_picking_return', login='admin', timeout=180)

    def test_scan_location_destination_for_internal_transfers(self):
        """
        This test ensures that destination location scan is taken into
        account when proposed by the UI.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        self.picking_type_internal.active = True

        # Create a sibling stock location to use a destination
        location_dest = self.env['stock.location'].create({
            'name': "Lovely Location",
            'location_id': self.stock_location.location_id.id,
            'barcode': 'WH-LOVE',
        })
        self.product1.name = "Lovely Product"
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_scan_location_destination_for_internal_transfers', login='admin', timeout=180)
        internal_transfer = self.env['stock.picking'].search([('picking_type_id', '=', self.picking_type_internal.id)], limit=1)
        self.assertRecordValues(internal_transfer.move_ids.move_line_ids, [{
            "product_id": self.product1.id,
            "location_dest_id": location_dest.id,
        }])

    def test_scan_product_when_in_form_view(self):
        """ Ensure nothing happens when in `stock.move.line` for view."""
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        self.picking_type_internal.active = True
        self.start_tour('/odoo/barcode', 'test_scan_product_when_in_form_view', login='admin')

    def test_split_uncomplete_moves_on_exit(self):
        """
        Check that the uncompleted moves are splitted in the backend when you exit
        the barcode, so that the demand of the picking is correctly displayed the
        next time you open the record.

        The flow slightly change with mto moves: both mts and mto procure methods are tested here
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        procurement_group = self.env['procurement.group'].create({
            'name': 'custom procurement',
        })
        warehouse = self.picking_type_out.warehouse_id
        mto_product = self.product1
        self.env['stock.quant']._update_available_quantity(mto_product, warehouse.lot_stock_id, 4)
        warehouse.delivery_steps = 'pick_ship'
        final_destination = self.env.ref('stock.stock_location_customers')
        origin = 'custom origin'
        self.env['procurement.group'].run([
            self.env['procurement.group'].Procurement(mto_product, 4.0, mto_product.uom_id, final_destination, mto_product.name, origin,
                self.picking_type_out.company_id, {'warehouse_id': warehouse, 'group_id': procurement_group})
        ])
        pick = self.env['stock.picking'].search([('group_id', '=', procurement_group.id)], limit=1)
        pick.button_validate()
        ship = self.env['stock.picking'].search([('group_id', '=', procurement_group.id)], limit=2) - pick
        mts_product = self.product2
        self.env['stock.quant']._update_available_quantity(mts_product, ship.location_id, 5)
        self.env['stock.move'].create({
            'name': mts_product.name,
            'product_id': mts_product.id,
            'product_uom_qty': 5,
            'product_uom': mts_product.uom_id.id,
            'picking_id': ship.id,
            'location_id': ship.location_id.id,
            'location_dest_id': ship.location_dest_id.id,
        })
        ship.action_assign()
        self.assertRecordValues(ship.move_ids.sorted('quantity'), [
            {'quantity': 4.0, 'picked': False, 'procure_method': 'make_to_order'},
            {'quantity': 5.0, 'picked': False, 'procure_method': 'make_to_stock'},
            ])
        url = self._get_client_action_url(ship.id)
        self.start_tour(url, 'test_split_uncomplete_moves_on_exit', login='admin', timeout=180)
        self.assertRecordValues(ship.move_ids.sorted('quantity'), [
            {"product_id": mto_product.id, "quantity": 4.0, "picked": True},
            {"product_id": mts_product.id, "quantity": 5.0, "picked": True},
        ])
        self.assertRecordValues(ship.move_line_ids.filtered(lambda m: m.product_id == mto_product).sorted('quantity'), [
            {"quantity": 1.0, "picked": True},
            {"quantity": 3.0, "picked": False},
        ])
        self.assertRecordValues(ship.move_line_ids.filtered(lambda m: m.product_id == mts_product).sorted('quantity'), [
            {"quantity": 1.0, "picked": True},
            {"quantity": 4.0, "picked": False},
        ])

    def test_split_uncomplete_manually_assigned_moves_on_exit(self):
        """
        Check that the uncompleted moves are splitted in the backend when you exit
        the barcode, so that the demand of the picking is correctly displayed the
        next time you open the record.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        # Avoid picking reservation at confirm
        self.picking_type_out.write({
            'reservation_method': 'manual',
            'restrict_scan_source_location': 'no',
        })
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 5)
        delivery = self.env['stock.picking'].create({
            'name': "SUMAMOE",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'name': 'Lovely move',
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_id': self.product1.id,
                'product_uom': self.product1.uom_id.id,
                'product_uom_qty': 3,
            })],
        })
        delivery.action_confirm()
        delivery.action_assign()
        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_split_uncomplete_manually_assigned_moves_on_exit', login='admin')
        self.assertRecordValues(delivery.move_ids, [
            {"quantity": 3.0, "picked": True},
        ])
        self.assertRecordValues(delivery.move_line_ids.sorted('quantity'), [
            {"quantity": 1.0, "picked": True},
            {"quantity": 2.0, "picked": False},
        ])

    def test_split_uncomplete_moves_on_exit_with_neutral_changes(self):
        """
        Check that the post barcode process does change the state of the record if
        neutral actions were performed such as adding and removing products to the
        delivery.
        """

        self.clean_access_rights()
        self.env.user.write({'groups_id': [Command.link(self.ref('stock.group_production_lot'))]})
        self.picking_type_out.show_reserved_sns = True

        lots = self.env['stock.lot'].create([
            {'name': 'LN001', 'product_id': self.productlot1.id},
            {'name': 'LN002', 'product_id': self.productlot1.id},
        ])
        for lot in lots:
            self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 2, lot_id=lot)
        # Creates a delivery for 2 x productlot1 initially reserved with SN001 and SN002
        delivery = self.env['stock.picking'].create({
            'name': "SUMOEWNC",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'name': "productlot1 x2",
                'product_id': self.productlot1.id,
                'product_uom_qty': 4,
            })]
        })
        delivery.action_confirm()
        self.assertRecordValues(delivery.move_ids, [
            {'product_uom_qty': 4.0, 'quantity': 4.0, 'picked': False, 'lot_ids': lots.ids},
        ])
        self.assertRecordValues(delivery.move_line_ids, [
            {'quantity': 2.0, 'picked': False, 'lot_id': lots[0].id},
            {'quantity': 2.0, 'picked': False, 'lot_id': lots[1].id},
        ])

        action = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = f"/web#action={action.id}"
        self.start_tour(url, 'test_split_uncomplete_moves_on_exit_with_neutral_changes', login='admin')
        # Checks the reservation state is equivalent
        self.assertRecordValues(delivery.move_ids, [
            {'product_uom_qty': 4.0, 'quantity': 4.0, 'picked': False, 'lot_ids': lots.ids},
        ])
        self.assertRecordValues(delivery.move_line_ids, [
            {'quantity': 2.0, 'picked': False, 'lot_id': lots[1].id},
            {'quantity': 2.0, 'picked': False, 'lot_id': lots[0].id},
        ])

    def test_barcode_create_serials_in_batch_with_single_scan(self):
        """ Check that it is possible to generate 1000 serial numbers with a signle scan."""
        self.env.ref('base.group_user').implied_ids += self.env.ref('stock.group_production_lot')
        self.clean_access_rights()
        group_tracking = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [Command.link(group_tracking.id)]})
        # Enable "Show reserved lots/SN"
        self.picking_type_out.write({
            'show_reserved_sns': True,
            'restrict_scan_source_location': 'no',
            'use_create_lots': True,
        })

        # Patch controller method to be able to count amount of calls.
        self1 = self
        get_specific_barcode_data_orig = StockBarcodeController.get_specific_barcode_data
        @http.route('/stock_barcode/get_specific_barcode_data', type='json', auth='user')
        def mocked_data_batch_method(self, **kwargs):
            if self1.call_count == 0:
                self1.assertTrue('barcodes_by_model' in kwargs)
                self1.assertFalse('barcodes' in kwargs)
            elif self1.call_count == 1:
                self1.assertFalse('barcodes_by_model' in kwargs)
                self1.assertTrue('barcodes' in kwargs)
            self1.call_count += 1
            return get_specific_barcode_data_orig(self, **kwargs)

        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 1500)
        delivery = self.env['stock.picking'].create({
            'name': "Lovely delivery",
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'name': 'Lovely move',
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_id': self.productlot1.id,
                'product_uom': self.productlot1.uom_id.id,
                'product_uom_qty': 1000,
            })],
        })
        delivery.action_confirm()
        self.assertFalse(delivery.move_line_ids.lot_id)
        url = self._get_client_action_url(delivery.id)
        with patch.object(
            StockBarcodeController,
            'get_specific_barcode_data',
            mocked_data_batch_method
        ):
            self.start_tour(url, 'test_barcode_create_serials_in_batch_with_single_scan', login='admin')
            self.assertEqual(self.call_count, 2)

    def test_barcode_lazy_cache_scan_two_lots(self):
        """ Checks that you can scan 2 lots without the OWL error 'quantsByLocation is not iterable' """
        group_tracking = self.env.ref('stock.group_tracking_owner')
        self.env.user.write({'groups_id': [Command.link(group_tracking.id)]})
        self.picking_type_in.write({'use_existing_lots': True})

        sn1, _ = self.env['stock.lot'].create([
            {'name': 'SN-001', 'product_id': self.productlot1.id},
            {'name': 'SN-002', 'product_id': self.productlot1.id},
        ])
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 1, lot_id=sn1)

        receipt = self.env['stock.picking'].create({
            'name': "Lovely Receipt",
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'move_ids': [Command.create({
                'name': 'Lovely move',
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.productlot1.id,
                'product_uom': self.productlot1.uom_id.id,
                'product_uom_qty': 10,
            })],
        })
        receipt.action_confirm()
        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_barcode_lazy_cache_scan_two_lots', login='admin')

    def test_fetch_archived_records_in_lazy_barcode_cache(self):
        """
        Check that a picking related to archived records can be processed in barcode
        in the same way as it can be in backend.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        warehouse = self.shelf2.warehouse_id
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 10)
        floor_location = self.env['stock.location'].create({
            'name': 'floor1',
            'usage': 'internal',
            'location_id': self.shelf2.id,
        })
        transfer = self.env['stock.picking'].create({
            'name': 'Lovely Transfer',
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'picking_type_id': warehouse.int_type_id.id,
            'move_ids': [Command.create({
                'name': 'Lovely move',
                'location_id': self.shelf1.id,
                'location_dest_id': floor_location.id,
                'product_id': self.product1.id,
                'product_uom_qty': 3,
            })],
        })
        transfer.action_confirm()
        self.shelf2.toggle_active()
        self.assertFalse(self.shelf2.active)
        url = self._get_client_action_url(transfer.id)
        self.start_tour(url, 'test_fetch_archived_records_in_lazy_barcode_cache', login='admin')
        self.assertEqual(transfer.state, 'done')

    def test_validate_uncomplete_return(self):
        """ Ensures we can validate a return created in the Barcode app without any issue.
        """
        self.clean_access_rights()
        self.env['stock.picking'].create({
            'name': 'TEST/IN/0001',
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'move_ids': [Command.create({
                'name': 'test_receipt_1',
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product1.id,
                'product_uom': self.product1.uom_id.id,
                'product_uom_qty': 2,
            })]
        }).action_confirm()
        self.start_tour('/odoo/barcode', 'test_validate_uncomplete_return', login='admin')

    def test_remove_sublines_and_scan_serial_again(self):
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [Command.link(grp_lot.id)]})
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'move_ids': [
                Command.create({
                    'name': '/',
                    'product_id': self.productserial1.id,
                    'product_uom_qty': 3,
                })
            ],
        })
        picking.action_assign()
        url = self._get_client_action_url(picking.id)
        self.start_tour(url, 'test_remove_sublines_and_scan_serial_again', login='admin')

    def test_split_line_preserve_package(self):
        """
        This test ensures that move lines, when assigned a new destination
        while scanning, properly preserve package source info after scanning
        a package destination when the move line moves partial quantity
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_pack.id), Command.link(grp_multi_loc.id)]})
        self.picking_type_out.restrict_scan_source_location = 'no'

        # Create two empty packs
        pack1, pack2 = self.env['stock.quant.package'].create({
            'name': name,
        } for name in ['THEPACK1', 'THEPACK2'])

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, quantity=100, package_id=pack1)
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 50
        delivery_with_move = delivery_form.save()
        delivery_with_move.action_confirm()
        delivery_with_move.action_assign()
        url = self._get_client_action_url(delivery_with_move.id)
        self.start_tour(url, 'test_split_line_preserve_package', login='admin')
        self.assertEqual(delivery_with_move.move_line_ids[0].package_id, pack1)
        self.assertEqual(delivery_with_move.move_line_ids[1].result_package_id, pack2)
        self.assertEqual(delivery_with_move.move_line_ids[1].package_id, pack1)

    # === GS1 TESTS ===#
    def test_gs1_delivery_ambiguous_lot_number(self):
        """
        Have a delivery for a product tracked by lots then scan a lot who exists for
        two different products and check the move line has the right lot.
        Do the same test by scanning a packaging instead of the product.
        """
        self.clean_access_rights()
        group_packaging = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [Command.link(group_packaging.id)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        product_a, product_b = self.env['product.product'].create([{
            'name': name,
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': barcode,
            'tracking': 'lot',
        } for (name, barcode) in [('Product A', '22222220'), ('Product B', '44444440')]])
        # Creates 2 lot numbers (same name but different product.)
        lot_b, lot_a = self.env['stock.lot'].create([
            {'name': '12345', 'product_id': product.id} for product in [product_b, product_a]
        ])
        # Create a product packaging
        self.env['product.packaging'].create({
            'barcode': '10000000240489',
            'name': "Packaging - Product A x1",
            'product_id': product_a.id,
            'qty': 1,
        })
        # For the purpose of the test, lot for product_b has to be created first.
        for [product, lot] in [[product_b, lot_b], [product_a, lot_a]]:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 1,
                'lot_id': lot.id,
                'location_id': self.stock_location.id,
            }).action_apply_inventory()
        # Run the tour.
        self.start_tour('/odoo/barcode', 'test_gs1_delivery_ambiguous_lot_number', login='admin', timeout=180)

    def test_gs1_delivery_ambiguous_serial_number(self):
        """
        Have a delivery for a product tracked by SN then scan a SN who exists for
        two different products and check the move line has the right SN.
        """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        product_a, product_b = self.env['product.product'].create([{
            'name': f'product{i}',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': barcode,
            'tracking': 'serial',
        } for i, barcode in enumerate(['05711544001952', '05711544001969'])])
        # Creates 2 serial numbers (same name different product).
        lot_b, lot_a = self.env['stock.lot'].create([
            {'name': '304', 'product_id': product.id} for product in [product_b, product_a]
        ])
        # For the purpose of the test, lot for product_b has to be created first.
        for [product, lot] in [[product_b, lot_b], [product_a, lot_a]]:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': 1,
                'lot_id': lot.id,
                'location_id': self.stock_location.id,
            }).action_apply_inventory()
        # Creates and confirms the delivery.
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.env['stock.move'].create({
            'name': product_a.name,
            'product_id': product_a.id,
            'product_uom_qty': 1,
            'product_uom': product_a.uom_id.id,
            'picking_id': delivery_picking.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        # Run the tour.
        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_gs1_delivery_ambiguous_serial_number', login='admin', timeout=180)
        self.assertEqual(delivery_picking.move_line_ids.lot_id, lot_a)
        self.assertEqual(delivery_picking.move_line_ids.product_id, product_a)

    def test_gs1_reserved_delivery(self):
        """ Process a delivery by scanning multiple quantity multiple times.
        """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        # Creates a product and adds some quantity.
        product_gtin_8 = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '11011019',  # GTIN-8 format.
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        self.env['stock.quant']._update_available_quantity(product_gtin_8, self.stock_location, 99)

        # Creates and process the delivery.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_8
            move.product_uom_qty = 10

        delivery = picking_form.save()
        delivery.action_confirm()
        delivery.action_assign()

        url = self._get_client_action_url(delivery.id)
        self.start_tour(url, 'test_gs1_reserved_delivery', login='admin', timeout=180)

        self.assertEqual(delivery.state, 'done')
        self.assertEqual(len(delivery.move_ids), 1)
        self.assertEqual(delivery.move_ids.product_uom_qty, 10, "10 units was reserved")
        self.assertEqual(delivery.move_ids.quantity, 14, "14 units was processed")
        self.assertEqual(len(delivery.move_line_ids), 2)
        self.assertEqual(delivery.move_line_ids[0].quantity, 10)
        self.assertEqual(delivery.move_line_ids[1].quantity, 4)

    def test_gs1_receipt_conflicting_barcodes(self):
        """ Creates some receipts for two products but their barcodes mingle
        together once they are adapted for GS1.
        """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product_gtin_8 = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '11011019',  # GTIN-8 format -> Will become 00000011011019.
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        product_gtin_12 = self.env['product.product'].create({
            'name': 'PRO_GTIN_12',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '000011011019',  # GTIN-12 format -> Will also become 00000011011019.
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })

        # Test for product_gtin_8 only.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_8
            move.product_uom_qty = 1

        receipt_1 = picking_form.save()
        receipt_1.action_confirm()
        receipt_1.action_assign()

        url = self._get_client_action_url(receipt_1.id)
        self.start_tour(url, 'test_gs1_receipt_conflicting_barcodes_1', login='admin', timeout=180)

        self.assertEqual(receipt_1.state, 'done')
        self.assertEqual(len(receipt_1.move_line_ids), 1)
        self.assertEqual(receipt_1.move_line_ids.product_id.id, product_gtin_8.id)

        # Test for product_gtin_12 only.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_12
            move.product_uom_qty = 1

        receipt_2 = picking_form.save()
        receipt_2.action_confirm()
        receipt_2.action_assign()

        url = self._get_client_action_url(receipt_2.id)
        self.start_tour(url, 'test_gs1_receipt_conflicting_barcodes_2', login='admin', timeout=180)

        self.assertEqual(receipt_2.state, 'done')
        self.assertEqual(len(receipt_2.move_line_ids), 1)
        self.assertEqual(receipt_2.move_line_ids.product_id.id, product_gtin_12.id)

        # Test for both product_gtin_8 and product_gtin_12.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_8
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gtin_12
            move.product_uom_qty = 1

        receipt_3 = picking_form.save()
        receipt_3.action_confirm()
        receipt_3.action_assign()

        self.assertEqual(len(receipt_3.move_line_ids), 2)
        url = self._get_client_action_url(receipt_3.id)
        self.start_tour(url, 'test_gs1_receipt_conflicting_barcodes_3', login='admin', timeout=180)

        self.assertEqual(receipt_3.state, 'done')
        self.assertEqual(len(receipt_3.move_line_ids), 3)
        self.assertEqual(receipt_3.move_line_ids[0].product_id.id, product_gtin_8.id)
        self.assertEqual(receipt_3.move_line_ids[0].qty_done, 1)
        self.assertEqual(receipt_3.move_line_ids[1].product_id.id, product_gtin_12.id)
        self.assertEqual(receipt_3.move_line_ids[1].qty_done, 1)
        self.assertEqual(receipt_3.move_line_ids[2].product_id.id, product_gtin_8.id)
        self.assertEqual(receipt_3.move_line_ids[2].qty_done, 1)

    def test_gs1_receipt_conflicting_barcodes_mistaken_as_gs1(self):
        """ Checks if a record has a barcode who can be mistaken for a GS1 barcode,
        this record can still be found anyway while using the GS1 nomenclature."""
        self.clean_access_rights()
        group_package = self.env.ref('stock.group_tracking_lot')
        group_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [
            (4, group_package.id, 0),
            (4, group_lot.id, 0),
        ]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        # Creates two products and a package with misleading barcode.
        self.env['product.product'].create({
            'name': "Product AI 21",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '21000000000003',  # Can be read as a serial number (AI 21)
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        self.env['product.product'].create({
            'name': "Product AI 30",
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '3000000015',  # Can be read as a quantity (15 units, AI 30)
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        self.env['stock.quant.package'].create({'name': '21-Chouette-MegaPack'})
        self.start_tour("/odoo/barcode", 'test_gs1_receipt_conflicting_barcodes_mistaken_as_gs1', login='admin', timeout=180)

    def test_gs1_receipt_lot_serial(self):
        """ Creates a receipt for a product tracked by lot, then process it in the Barcode App.
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product_tln_gtn8
            move.product_uom_qty = 40

        receipt = picking_form.save()
        receipt.action_confirm()
        receipt.action_assign()

        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_gs1_receipt_lot_serial', login='admin', timeout=180)

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(len(receipt.move_line_ids), 5)
        self.assertEqual(
            receipt.move_line_ids.lot_id.mapped('name'),
            ['b1-b001', 'b1-b002', 'b1-b003', 'b1-b004', 'b1-b005']
        )
        for move_line in receipt.move_line_ids:
            self.assertEqual(move_line.quantity, 8)
            self.assertTrue(move_line.picked)

    def test_gs1_receipt_quantity_with_uom(self):
        """ Creates a new receipt and scans barcodes with different combinaisons
        of product and quantity expressed with different UoM and checks the
        quantity is taken only if the UoM is compatible with the product's one.
        """
        self.clean_access_rights()
        # Enables the UoM and the GS1 nomenclature.
        grp_uom = self.env.ref('uom.group_uom')
        group_user = self.env.ref('base.group_user')
        group_user.write({'implied_ids': [(4, grp_uom.id)]})
        self.env.user.write({'groups_id': [(4, grp_uom.id)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        # Configures three products using units, kg and g.
        uom_unit = self.env.ref('product.product_category_all')
        uom_g = self.env.ref('uom.product_uom_gram')
        uom_kg = self.env.ref('uom.product_uom_kgm')
        product_by_units = self.env['product.product'].create({
            'name': 'Product by Units',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15264329',
            'uom_id': uom_unit.id,
        })
        product_by_g = self.env['product.product'].create({
            'name': 'Product by g',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15264893',
            'uom_id': uom_g.id,
            'uom_po_id': uom_g.id,
        })
        product_by_kg = self.env['product.product'].create({
            'name': 'Product by kg',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15264879',
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
        })
        # Creates a new receipt.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        receipt = picking_form.save()
        # Runs the tour.
        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_gs1_receipt_quantity_with_uom', login='admin', timeout=180)
        # Checks the moves' quantities and UoM.
        self.assertEqual(len(receipt.move_ids), 3)
        move1, move2, move3 = receipt.move_ids
        self.assertEqual(move1.product_id.id, product_by_units.id)
        self.assertEqual(move1.quantity, 4)
        self.assertTrue(move1.picked)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move2.product_id.id, product_by_kg.id)
        self.assertEqual(move2.quantity, 5)
        self.assertTrue(move2.picked)
        self.assertEqual(move2.product_uom.id, uom_kg.id)
        self.assertEqual(move3.product_id.id, product_by_g.id)
        self.assertEqual(move3.quantity, 1250)
        self.assertTrue(move3.picked)
        self.assertEqual(move3.product_uom.id, uom_g.id)

    def test_gs1_receipt_scan_not_gs1_multi_barcode(self):
        """ This test ensures the user can scan a barcode containing multiple
        non-GS1 barcode when GS1 nomenclature is active."""
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.start_tour('/odoo/barcode', 'test_gs1_receipt_scan_not_gs1_multi_barcode', login='admin')

    def test_gs1_package_receipt_and_delivery(self):
        """ Receives some products and scans a GS1 barcode for a package, then
        creates a delivery and scans the same package.
        """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        # Set package's sequence to 123 to generate always the same package's name in the tour.
        sequence = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')], limit=1)
        sequence.write({'number_next_actual': 123})

        # Creates two products and two package's types.
        product1 = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })
        product2 = self.env['product.product'].create({
            'name': 'PRO_GTIN_12',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '584687955629',  # GTIN-12
            'uom_id': self.env.ref('uom.product_uom_unit').id,
        })
        wooden_chest_package_type = self.env['stock.package.type'].create({
            'name': 'Wooden Chest',
            'barcode': 'WOODC',
        })
        iron_chest_package_type = self.env['stock.package.type'].create({
            'name': 'Iron Chest',
            'barcode': 'IRONC',
        })

        self.start_tour("/odoo/barcode", 'test_gs1_package_receipt', login='admin', timeout=180)
        # Checks the package is in the stock location with the products.
        package = self.env['stock.quant.package'].search([('name', '=', '546879213579461324')])
        package2 = self.env['stock.quant.package'].search([('name', '=', '130406658041178543')])
        package3 = self.env['stock.quant.package'].search([('name', '=', 'PACK0000123')])
        self.assertEqual(len(package), 1)
        self.assertEqual(len(package.quant_ids), 2)
        self.assertEqual(package.package_type_id.id, wooden_chest_package_type.id)
        self.assertEqual(package.quant_ids[0].product_id.id, product1.id)
        self.assertEqual(package.quant_ids[1].product_id.id, product2.id)
        self.assertEqual(package.location_id.id, self.stock_location.id)
        self.assertEqual(package2.package_type_id.id, iron_chest_package_type.id)
        self.assertEqual(package2.quant_ids.product_id.id, product1.id)
        self.assertEqual(package3.package_type_id.id, iron_chest_package_type.id)
        self.assertEqual(package3.quant_ids.product_id.id, product2.id)

        self.start_tour("/odoo/barcode", 'test_gs1_package_delivery', login='admin', timeout=180)
        # Checks the package is in the customer's location.
        self.assertEqual(package.location_id.id, self.customer_location.id)

    def test_gs1_receipt_packaging(self):
        """
        This test ensures that a user can scan a packaging when processing a receipt
        """
        self.clean_access_rights()

        group_packaging = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [(4, group_packaging.id)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product = self.env['product.product'].create({
            'name': 'Bottle',
            'is_storable': True,
            'barcode': '1113',
            'packaging_ids': [(0, 0, {
                'name': '6-bottle pack',
                'qty': 6,
                'barcode': '2226',
            })],
        })

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        receipt = picking_form.save()

        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_gs1_receipt_packaging', login='admin', timeout=180)

        move = receipt.move_ids
        self.assertEqual(move.product_id, product)
        self.assertEqual(move.quantity, 30)
        self.assertEqual(move.picked, True)

    def test_gs1_receipt_packaging_with_uom(self):
        """ This test ensures that packaging quantity is used when a weight is
        scanned but the product uses Units as UoM.
        """
        self.clean_access_rights()
        group_lot = self.env.ref('stock.group_production_lot')
        group_packaging = self.env.ref('product.group_stock_packaging')
        group_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, group_lot.id), (4, group_packaging.id), (4, group_uom.id)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        # Create a product and its packaging.
        self.env['product.product'].create({
            'name': 'Product by Units',
            'is_storable': True,
            'tracking': 'lot',
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
            'barcode': '03287890001332',
            'packaging_ids': [(0, 0, {
                'name': 'PBUx6',
                'qty': 6,
                'barcode': '10347543011337',
            })],
        })
        self.start_tour('/odoo/barcode', 'test_gs1_receipt_packaging_with_uom', login='admin', timeout=180)

    def test_gs1_tracked_packaging(self):
        """ Ensures we can scan a GS1 barcode containing a packaging for a
        tracked product and the lot in one scan.
        """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        group_tracking = self.env.ref('stock.group_production_lot')
        group_packaging = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [(4, group_tracking.id, 0), (4, group_packaging.id, 0)]})

        self.env['product.packaging'].create({
            'name': 'productlot1 6 pack',
            'qty': 6,
            'barcode': '12653256',
            'product_id': self.productlot1.id
        })

        self.start_tour("/odoo/barcode", 'test_gs1_tracked_packaging', login='admin', timeout=180)
        lot = self.env['stock.lot'].search([('name', '=', 'lot-001')])
        move_lines = self.env['stock.move.line'].search([('product_id', '=', self.productlot1.id)])
        self.assertRecordValues(move_lines, [
            {'quantity': 6, 'lot_id': lot.id, 'location_id': self.supplier_location.id, 'location_dest_id': self.stock_location.id},
            {'quantity': 6, 'lot_id': lot.id, 'location_id': self.stock_location.id, 'location_dest_id': self.customer_location.id},
        ])

    def test_gs1_multi_company_setup(self):
        """
        Check that the nomenclature used on the barcode main menu is the nomenclature
        of the contextually selected company rather than the user company.
        """
        self.clean_access_rights()
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        company = self.env['res.company'].create({
            'name': 'Lovely Company',
            'nomenclature_id': self.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature'),
        })
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)])
        warehouse.reception_steps = 'two_steps'
        warehouse.wh_input_stock_loc_id.barcode = '3033710074365'
        self.product1.barcode = '36939282410106'
        self.env['stock.quant'].with_company(company.id)._update_available_quantity(self.product1, warehouse.lot_stock_id, 3.0)
        self.start_tour('/odoo', 'test_gs1_multi_company_setup', login='admin')

    def test_serial_product_packaging(self):
        """ This test ensures that correct packaging lines generated
        for serial product in operations.
        """
        self.clean_access_rights()
        group_lot = self.env.ref('stock.group_production_lot')
        group_packaging = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [(4, group_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, group_packaging.id)]})
        self.env['product.packaging'].create({
            'name': 'Product Serial 1 Packaging',
            'qty': 4,
            'product_id': self.productserial1.id,
            'barcode': 'PCK4',
        })

        self.start_tour('/odoo/barcode', 'test_serial_product_packaging', login='admin', timeout=180)

    def test_split_line_on_scan(self):
        """
        This test ensures that move lines are split correctly
        when a user scans a package on an incomplete move line
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 5)
        # Create two empty packs
        pack1 = self.env['stock.quant.package'].create({
            'name': 'THEPACK1',
        })
        pack2 = self.env['stock.quant.package'].create({
            'name': 'THEPACK2',
        })

        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 5
        delivery_with_move = delivery_form.save()
        delivery_with_move.action_confirm()
        delivery_with_move.action_assign()

        url = self._get_client_action_url(delivery_with_move.id)
        self.start_tour(url, 'test_split_line_on_scan', login='admin', timeout=180)

        self.assertEqual(len(pack1.quant_ids), 1)
        self.assertEqual(len(pack2.quant_ids), 1)
        self.assertEqual(len(delivery_with_move.move_line_ids), 2)

    def test_scan_line_splitting_preserve_destination(self):
        """
        This test ensures that move lines, when assigned a new destination
        while scanning, properly preserve destination info after scanning
        a package
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        # Create two empty packs
        pack1 = self.env['stock.quant.package'].create({
            'name': 'THEPACK1',
        })
        pack2 = self.env['stock.quant.package'].create({
            'name': 'THEPACK2',
        })

        # Create a receipt and confirm it.
        receipt_form = Form(self.env['stock.picking'])
        receipt_form.picking_type_id = self.picking_type_in
        with receipt_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 5
        receipt_picking = receipt_form.save()
        receipt_picking.action_confirm()
        receipt_picking.action_assign()

        url = self._get_client_action_url(receipt_picking.id)
        self.start_tour(url, 'test_scan_line_splitting_preserve_destination', login='admin', timeout=180)

        self.assertEqual(len(pack1.quant_ids), 1)
        self.assertEqual(pack1.location_id.id, self.shelf3.id)
        self.assertRecordValues(pack1.quant_ids, [
            {'product_id': self.product2.id, 'quantity': 2, 'location_id': self.shelf3.id},
        ])

        self.assertEqual(len(pack2.quant_ids), 1)
        self.assertEqual(pack2.location_id.id, self.shelf4.id)
        self.assertRecordValues(pack2.quant_ids, [
            {'product_id': self.product2.id, 'quantity': 3, 'location_id': self.shelf4.id},
        ])

    def test_scan_package_with_decimal(self):
        """This is a test to avoid the rounding issue on javascript when scanning a package
        that has more quantity than the required quantity on line"""
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [Command.link(grp_pack.id)]})
        self.product1.uom_id = self.env.ref('uom.product_uom_kgm')
        self.picking_type_out.restrict_scan_source_location = 'no'
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 275.84, package_id=self.package)
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 3.6
        delivery_picking = delivery_form.save()
        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_scan_package_with_decimal', login='admin', timeout=180)
        self.assertRecordValues(delivery_picking.move_line_ids, [
            {"product_id": self.product1.id, "quantity": 3.6, "location_dest_id": delivery_picking.location_dest_id.id, "picked": True},
            {"product_id": self.product1.id, "quantity": 272.24, "location_dest_id": delivery_picking.location_dest_id.id, "picked": True}
        ])

    def test_barcode_signature_flow(self):
        """
        1. Create two new delivery pickings to test two different signing flows
        2. Assert that delivery does not have a signature assigned to it
        3. After the tour is run, verify that the signature is set
        4. Verify that the two delivery orders have been validated in the end
        """
        self.clean_access_rights()
        group_sign_delivery = self.env.ref('stock.group_stock_sign_delivery')
        self.env.user.write({'groups_id': [(4, group_sign_delivery.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 5)

        partner = self.env['res.partner'].create({'name': 'My partner'})

        def create_delivery_picking(picking_name):
            delivery = self.env['stock.picking'].create({
                'name': picking_name,
                'picking_type_id': self.picking_type_out.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'partner_id': partner.id,
                'user_id': False,
                'move_ids': [(0, 0, {
                    'name': '/',
                    'product_id': self.product1.id,
                    'product_uom': self.product1.uom_id.id,
                    'product_uom_qty': 1,
                    'procure_method': 'make_to_stock',
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                })],
            })
            delivery.action_confirm()
            delivery.action_assign()
            return delivery

        delivery1 = create_delivery_picking('Delivery Order 1')
        delivery2 = create_delivery_picking('Delivery Order 2')

        self.assertFalse(delivery2.signature)

        url = '/odoo/action-stock_barcode.stock_picking_type_action_kanban'
        self.start_tour(url, 'test_barcode_signature_flow', login="admin")

        self.assertTrue(delivery2.signature)
        self.assertEqual(delivery1.state, 'done')
        self.assertEqual(delivery2.state, 'done')

    def test_select_with_same_product_and_lot(self):
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [Command.link(grp_lot.id)]})
        pg = self.env['procurement.group'].create({'name': 'ProcurementGroup'})
        lot_xyz = self.env['stock.lot'].create({'name': 'lot_xyz', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 4, lot_id=lot_xyz)
        self.picking_type_out.show_reserved_sns = True
        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'group_id': pg.id,
        })
        self.env['stock.move'].create({
            'name': 'test_delivery_lot_xyz_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': delivery_picking.id,
            'group_id': pg.id,
        })
        delivery_picking.action_confirm()
        second_move = self.env['stock.move'].create({
            'name': 'test_delivery_lot_xyz_2',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.productlot1.id,
            'product_uom': self.uom_unit.id,
            'quantity': 2,
            'picking_id': delivery_picking.id,
            'group_id': pg.id,
        })
        second_move.move_line_ids.lot_id = lot_xyz
        self.assertEqual(len(delivery_picking.move_ids), 2)
        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_select_with_same_product_and_lot', login='admin', timeout=180)

    def test_description_picking_tour(self):
        """ Test that when creating a receipt or internal transfer using the barcode app, the
        description_picking field of the move_line is not empty
        """
        self.clean_access_rights()
        product = self.env['product.product'].create({
            'name': 'test_product',
            'description_pickingin': 'receipt',
            'barcode': 'test_product',
        })
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_description_picking_tour', login='admin', timeout=180)
        picking = self.env['stock.picking'].search([('move_ids.product_id.id', '=', product.id), ('state', '=', 'done')])

        self.assertEqual(picking.move_ids.description_picking, 'receipt')

    def test_qty_after_uom_update_picking_tour(self):
        """Test that when creating a receipt and updting the uom using the barcode app, the
        quantity demand of the move_line is correctly updated according to the uom.
        """
        self.env.user.groups_id += self.env.ref('uom.group_uom')
        product = self.env['product.product'].create({
            'name': 'test_product_uom_update',
            'barcode': 'test_product_uom_update',
        })
        partner = self.env['res.partner'].create({'name': 'test_product_uom_partner'})
        receipt = self.env['stock.picking'].create({
            'partner_id': partner.id,
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 120,
            'product_uom': product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.customer_location.id,
            'location_dest_id': self.stock_location.id,
        })
        receipt.action_confirm()
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_uom_update_picking_tour', login='admin', timeout=180)

    def test_no_validate_no_dest_package(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0), (4, grp_multi_loc.id, 0)]})
        picking_type = self.env.ref('stock.picking_type_internal')
        picking_type.write({
            'restrict_scan_source_location': 'mandatory',
            'restrict_scan_dest_location': 'mandatory',
            'active': True,
        })
        pack1 = self.env['stock.quant.package'].create({
                'name': 'Pack1',
            })
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 5, package_id=pack1)
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_no_validate_no_dest_package', login='admin')

    def test_scan_package_with_different_uom(self):
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.product1.uom_id = self.env.ref('uom.product_uom_kgm')
        package1 = self.env['stock.quant.package'].create({'name': 'package001'})
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 10, package_id=package1)
        picking = self.env['stock.picking'].create({
            'name': 'test picking',
            'picking_type_id': self.picking_type_internal.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'name': 'test move name',
                'product_id': self.product1.id,
                'product_uom': self.env.ref('uom.product_uom_gram').id,
                'product_uom_qty': 10000,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        url = self._get_client_action_url(picking.id)
        self.start_tour(url, 'test_scan_package_with_different_uom', login='admin', timeout=180)

    def test_stock_quant_ids_computed_by_product_update(self):
        """
        Verify that the computed field `product_stock_quant_ids` on `move_line_ids`
        is correctly updated when product_id is set
        """
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'quantity': 10
        })
        internal_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
            'move_ids': [Command.create({
                'name': 'internal_move',
                'location_id': self.stock_location.id,
                'product_id': self.product1.id,
                'location_dest_id': self.stock_location.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1,
            })]
        })
        internal_picking.action_confirm()
        self.assertEqual(internal_picking.move_ids.move_line_ids.product_stock_quant_ids.quantity, 10.0)

    def test_quantity_distribution_sublines_same_lot(self):
        """Test that when two lines with the same lot are grouped in barcode,
        the quantities are split correctly between the lines when scanning two
        times the lot.
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        lot_1 = self.env['stock.lot'].create({'name': 'lot 1', 'product_id': self.productlot1.id, 'company_id': self.env.company.id})
        self.env['stock.quant'].create([
            {
                'product_id': self.productlot1.id,
                'inventory_quantity': 2,
                'lot_id': lot_1.id,
                'location_id': self.stock_location.id,
            },
        ]).action_apply_inventory()

        delivery_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [Command.create({
                'name':  f"move {i}",
                'product_id': self.productlot1.id,
                'product_uom_qty': 1,
                'price_unit': i,  # Different price unit so moves won't be merged.
                'product_uom': self.productlot1.uom_id.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
            }) for i in (1, 3)],
        })
        delivery_picking.action_confirm()
        delivery_picking.action_assign()
        url = self._get_client_action_url(delivery_picking.id)
        self.start_tour(url, 'test_quantity_distribution_sublines_same_lot', login='admin')
        self.assertEqual(len(delivery_picking.backorder_ids), 0)
        self.assertRecordValues(delivery_picking.move_ids, [
            {'quantity': 1.0, 'product_uom_qty': 1.0, 'lot_ids': [lot_1.id], 'picked': True},
            {'quantity': 1.0, 'product_uom_qty': 1.0, 'lot_ids': [lot_1.id], 'picked': True},
        ])

    def test_rental_partial_reception(self):
        """ Checks that processing a partial receipt for a rental order triggers the backorder dialog.
        """
        if not self.env['ir.module.module'].search([('name', '=', 'sale_stock_renting'), ('state', '=', 'installed')]):
            self.skipTest("sale_stock_renting is not installed, so there is no rental orders to test")

        # Enable rental pickings
        self.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()

        product = self.env['product.product'].create({
            'name': 'Rental',
            'rent_ok': True,
            'is_storable': True,
            'barcode': 'RNT01'
        })
        self.env['stock.quant']._update_available_quantity(product, self.stock_location, 4)
        rental = self.env['sale.order'].with_context(in_rental_app=True).create({
            'partner_id': self.owner.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 4,
            })]
        })
        rental.action_confirm()
        delivery = rental.picking_ids.filtered(lambda p: p.picking_type_id == rental.warehouse_id.out_type_id)
        receipt = rental.picking_ids - delivery
        delivery.button_validate()

        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_rental_partial_reception', login='admin', timeout=180)

        self.assertTrue(receipt.backorder_ids)
        self.assertEqual(receipt.backorder_ids.move_ids.product_uom_qty, 3.0)

    def test_no_validate_multiple_times(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        self.picking_type_internal.action_unarchive()

        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 1)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_no_validate_multiple_times', login='admin')

        quant = self.env['stock.quant'].search([('product_id', '=', self.product2.id), ('location_id', '=', self.shelf1.id)])
        self.assertEqual(quant.quantity, 1)

    def test_gs1_receipt_multiple_extra_items(self):
        """
        This test ensures that when multiple extra items are added during the processing
        of a picking, all the selected items are correctly added to the picking.
        """
        self.product1.barcode = '12345678900005'
        self.product2.barcode = '12345678900012'
        self.productserial1.barcode = '12345678900029'
        self.productlot1.barcode = '12345678900036'

        group_lot = self.env.ref('stock.group_production_lot')
        group_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [Command.link(group_lot.id), Command.link(group_uom.id)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        receipt_with_move = self.env['stock.picking'].create({
            'name': "In Picking for multiple extra items",
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
            'move_ids': [Command.create({
                'name': 'Move for product1',
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product1.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 2
            })],
        })
        receipt_with_move.action_confirm()
        receipt_with_move.action_assign()

        url = self._get_client_action_url(receipt_with_move.id)
        self.start_tour(url, 'test_gs1_receipt_multiple_extra_items', login='admin')

    def test_quantity_updates_on_exit_spam(self):
        """
        Test that spamming the barcode back button multiple times
        triggers the related updates only once.
        """
        self.clean_access_rights()
        delivery = self.env['stock.picking'].create({
            'name': 'Lovely Delivery',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        self.start_tour('/odoo/barcode', 'test_quantity_updates_on_exit_spam', login='admin')
        self.assertRecordValues(delivery.move_line_ids, [{
            'product_id': self.product1.id, 'quantity': 1.0,
        }])
