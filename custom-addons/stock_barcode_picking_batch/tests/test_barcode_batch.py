# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestBarcodeBatchClientAction(TestBarcodeClientAction):
    def setUp(self):
        super().setUp()

        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        # Create some products
        self.product3 = self.env['product.product'].create({
            'name': 'product3',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product3',
        })
        self.product4 = self.env['product.product'].create({
            'name': 'product4',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product4',
        })
        self.product5 = self.env['product.product'].create({
            'name': 'product5',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product5',
        })

        # Create locations dedicated to package
        self.shelf5 = self.env['stock.location'].create({
            'name': 'Section 5',
            'location_id': self.stock_location.id,
            'barcode': 'shelf5',
        })

        # Create some packages
        self.package1 = self.env['stock.quant.package'].create({'name': 'p5pack01'})
        self.package2 = self.env['stock.quant.package'].create({'name': 'p5pack02'})

        # Create some quants (for deliveries)
        Quant = self.env['stock.quant']
        quants = Quant.with_context(inventory_mode=True).create({
            'product_id': self.product1.id,
            'location_id': self.shelf1.id,
            'inventory_quantity': 2
        })
        quants |= Quant.with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'location_id': self.shelf2.id,
            'inventory_quantity': 1
        })
        quants |= Quant.with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'location_id': self.shelf3.id,
            'inventory_quantity': 1
        })
        quants |= Quant.with_context(inventory_mode=True).create({
            'product_id': self.product3.id,
            'location_id': self.shelf3.id,
            'inventory_quantity': 2
        })
        quants |= Quant.with_context(inventory_mode=True).create({
            'product_id': self.product4.id,
            'location_id': self.shelf1.id,
            'inventory_quantity': 1
        })
        quants |= Quant.with_context(inventory_mode=True).create({
            'product_id': self.product4.id,
            'location_id': self.shelf4.id,
            'inventory_quantity': 1
        })
        quants |= Quant.with_context(inventory_mode=True).create({
            'product_id': self.product5.id,
            'location_id': self.shelf5.id,
            'package_id': self.package1.id,
            'inventory_quantity': 4,
        })
        quants |= Quant.with_context(inventory_mode=True).create({
            'product_id': self.product5.id,
            'location_id': self.shelf5.id,
            'inventory_quantity': 4,
        })
        quants.action_apply_inventory()

        # Create a first receipt for 2 products.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productserial1
            move.product_uom_qty = 2
        self.picking_receipt_1 = picking_form.save()
        self.picking_receipt_1.action_confirm()

        # Create a second receipt for 2 products.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 3
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productlot1
            move.product_uom_qty = 8
        self.picking_receipt_2 = picking_form.save()
        self.picking_receipt_2.action_confirm()

        # Changes name of pickings to be able to track them on the tour
        self.picking_receipt_1.name = 'picking_receipt_1'
        self.picking_receipt_2.name = 'picking_receipt_2'

        # Create a first delivery for 2 products.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 2
        self.picking_delivery_1 = picking_form.save()
        self.picking_delivery_1.action_confirm()
        self.picking_delivery_1.action_assign()

        # Create a second delivery for 3 products.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product3
            move.product_uom_qty = 2
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product4
            move.product_uom_qty = 2
        self.picking_delivery_2 = picking_form.save()
        self.picking_delivery_2.action_confirm()
        self.picking_delivery_2.action_assign()

        # Create a delivery dedicated to package testing.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product5
            move.product_uom_qty = 8
        self.picking_delivery_package = picking_form.save()
        self.picking_delivery_package.action_confirm()
        self.picking_delivery_package.action_assign()

        # Create another quant with package after reservation to test scan
        # unexpected package in the Barcode App.
        Quant.with_context(inventory_mode=True).create({
            'product_id': self.product5.id,
            'location_id': self.shelf5.id,
            'package_id': self.package2.id,
            'inventory_quantity': 4,
        }).action_apply_inventory()

        # Changes name of pickings to be able to track them on the tour
        self.picking_delivery_1.name = 'picking_delivery_1'
        self.picking_delivery_2.name = 'picking_delivery_2'
        self.picking_delivery_package.name = 'picking_delivery_package'

    def _get_batch_client_action_url(self, batch_id):
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode_picking_batch.stock_barcode_picking_batch_client_action")
        return '/web#action=%s&active_id=%s' % (action['id'], batch_id)

    def test_barcode_batch_receipt_1(self):
        """ Create a batch picking with 3 receipts, then open the batch in
        barcode app and scan each product, SN or LN one by one.
        """
        # Creates an additional receipt for the product tracked by lots.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_in
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productlot1
            move.product_uom_qty = 4
        picking_receipt_3 = picking_form.save()
        picking_receipt_3.action_confirm()
        picking_receipt_3.name = 'picking_receipt_3'
        picking_receipt_3.user_id = False

        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_ids.add(self.picking_receipt_1)
        batch_form.picking_ids.add(self.picking_receipt_2)
        batch_form.picking_ids.add(picking_receipt_3)
        batch_receipt = batch_form.save()
        self.assertEqual(
            batch_receipt.picking_type_id.id,
            self.picking_receipt_1.picking_type_id.id,
            "Batch picking must take the picking type of its sub-pickings"
        )
        batch_receipt.action_confirm()
        self.assertEqual(len(batch_receipt.move_ids), 5)
        self.assertEqual(len(batch_receipt.move_line_ids), 6)
        self.assertEqual(batch_receipt.user_id.id, False)
        self.assertEqual(picking_receipt_3.user_id.id, False)

        url = self._get_batch_client_action_url(batch_receipt.id)
        self.start_tour(url, 'test_barcode_batch_receipt_1', login='admin', timeout=180)
        # Checks user was assign on the batch and its pickings.
        self.assertEqual(batch_receipt.user_id.id, self.env.user.id)
        self.assertEqual(picking_receipt_3.user_id.id, self.env.user.id)

    def test_barcode_batch_delivery_1(self):
        """ Create a batch picking with 2 deliveries (split into 3 locations),
        then open the batch in barcode app and scan each product.
        Change the location when all products of the page has been scanned.
        """
        batch_form = Form(self.env['stock.picking.batch'])
        # Adds two quantities for product tracked by SN.
        sn1 = self.env['stock.lot'].create({'name': 'sn1', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        sn2 = self.env['stock.lot'].create({'name': 'sn2', 'product_id': self.productserial1.id, 'company_id': self.env.company.id})
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn1.id,
            'location_id': self.shelf1.id,
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.productserial1.id,
            'inventory_quantity': 1,
            'lot_id': sn2.id,
            'location_id': self.shelf1.id,
        }).action_apply_inventory()

        # Creates a delivery for a product tracked by SN, the purpose is to
        # reserve sn1 and scan sn2 instead.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.productserial1
            move.product_uom_qty = 1
        picking_delivery_sn = picking_form.save()
        picking_delivery_sn.name = 'picking_delivery_sn'
        picking_delivery_sn.action_confirm()
        picking_delivery_sn.action_assign()

        batch_form.picking_ids.add(self.picking_delivery_1)
        batch_form.picking_ids.add(self.picking_delivery_2)
        batch_form.picking_ids.add(self.picking_delivery_package)
        batch_form.picking_ids.add(picking_delivery_sn)
        batch_delivery = batch_form.save()
        self.assertEqual(
            batch_delivery.picking_type_id.id,
            self.picking_delivery_1.picking_type_id.id,
            "Batch picking must take the picking type of its sub-pickings"
        )
        batch_delivery.action_confirm()
        self.assertEqual(len(batch_delivery.move_ids), 7)
        self.assertEqual(len(batch_delivery.move_line_ids), 10)
        packaged_move_lines = batch_delivery.move_line_ids.filtered(lambda ml: ml.product_id.id == self.product5.id)
        self.assertEqual(len(packaged_move_lines), 2)
        self.assertEqual(packaged_move_lines.package_id.id, self.package1.id)

        url = self._get_batch_client_action_url(batch_delivery.id)
        self.start_tour(url, 'test_barcode_batch_delivery_1', login='admin', timeout=180)

    def test_barcode_batch_delivery_2_move_entire_package(self):
        """ Creates a batch picking with 2 deliveries while the delivery picking type use the "move
        entire package" setting and check lines are correctly displayed as package line when moving
        the entire package, or as usual barcode line in other cases.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.picking_type_out.show_entire_packs = True

        # Creates two packages and adds some quantities on hand.
        pack1 = self.env['stock.quant.package'].create({'name': 'pack1'})
        pack2 = self.env['stock.quant.package'].create({'name': 'pack2'})
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product1.id,
            'inventory_quantity': 10,
            'package_id': pack1.id,
            'location_id': self.stock_location.id,
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'inventory_quantity': 10,
            'package_id': pack2.id,
            'location_id': self.stock_location.id,
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product3.id,
            'inventory_quantity': 10,
            'package_id': pack1.id,
            'location_id': self.stock_location.id,
        }).action_apply_inventory()

        # Creates two deliveries.
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 10
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 5
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product3
            move.product_uom_qty = 10
        delivery_1 = picking_form.save()
        delivery_1.action_confirm()
        delivery_1.action_assign()

        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 5
        delivery_2 = picking_form.save()
        delivery_2.action_confirm()
        delivery_2.action_assign()

        # Changes name of pickings to be able to track them on the tour.
        delivery_1.name = 'delivery_1'
        delivery_2.name = 'delivery_2'

        # Creates and confirms the batch.
        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_ids.add(delivery_1)
        batch_form.picking_ids.add(delivery_2)
        batch_delivery = batch_form.save()
        batch_delivery.action_confirm()

        url = self._get_batch_client_action_url(batch_delivery.id)
        self.start_tour(url, 'test_barcode_batch_delivery_2_move_entire_package', login='admin', timeout=180)

    def test_put_in_pack_from_multiple_pages(self):
        """ A batch picking of 2 internal pickings where prod1 and prod2 are reserved in shelf1 and shelf2,
        processing all these products and then hitting put in pack should move them all in the new pack.

        This is a copy of the stock_barcode `test_put_in_pack_from_multiple_pages` test with exception that
        there are 2 internal pickings containing the 2 products. We expect the same UI and behavior with the
        batch's `put_in_pack` button as we do with a single internal transfer so we re-use the same exact tour.
        Note that batch `put_in_pack` logic is not the same as it is for pickings.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 1)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 1)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf2, 1)

        # Adapts the setting to scan only the source location.
        self.picking_type_internal.restrict_scan_dest_location = 'no'
        self.picking_type_internal.restrict_scan_source_location = 'mandatory'

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
        internal_picking2 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_from_multiple_pages',
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 2,
            'picking_id': internal_picking2.id,
        })

        internal_picking.action_confirm()
        internal_picking.action_assign()
        internal_picking2.action_confirm()
        internal_picking2.action_assign()

        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_ids.add(internal_picking)
        batch_form.picking_ids.add(internal_picking2)
        batch_internal = batch_form.save()

        batch_internal.action_confirm()
        self.assertEqual(len(batch_internal.move_ids), 2)

        url = self._get_batch_client_action_url(batch_internal.id)

        self.start_tour(url, 'test_put_in_pack_from_multiple_pages', login='admin', timeout=180)

        pack = self.env['stock.quant.package'].search([('location_id', '=', self.stock_location.id)], limit=1)
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(sum(pack.quant_ids.mapped('quantity')), 4)

    def test_put_in_pack_before_dest(self):
        """ A batch picking of 2 internal pickings where prod1 and prod2 are reserved in shelf1 and shelf3,
        and have different move destinations. Processing the products and then put in pack should open a choose
        destination wizard which will help make sure the package ends up where its expected.

        This is a copy of the stock_barcode `test_put_in_pack_before_dest` test with exception that
        there are 2 internal pickings containing the 2 products. We expect the same UI and behavior with the
        batch's `put_in_pack` button as we do with a single internal transfer so we re-use the same exact tour.
        For some reason the order of the move lines in the destination wizard is different, so we swap the expected
        destination in this test (since it doesn't matter).
        """
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
        internal_picking2 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'name': 'test_put_in_pack_before_dest',
            'location_id': self.shelf3.id,
            'location_dest_id': self.shelf4.id,
            'product_id': self.product2.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1,
            'picking_id': internal_picking2.id,
        })

        internal_picking.action_confirm()
        internal_picking.action_assign()
        internal_picking2.action_confirm()
        internal_picking2.action_assign()

        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_ids.add(internal_picking)
        batch_form.picking_ids.add(internal_picking2)
        batch_internal = batch_form.save()

        batch_internal.action_confirm()
        self.assertEqual(len(batch_internal.move_ids), 2)

        url = self._get_batch_client_action_url(batch_internal.id)

        self.start_tour(url, 'test_put_in_pack_before_dest', login='admin', timeout=180)
        pack = self.env['stock.quant.package'].search([('location_id', '=', self.shelf2.id)], limit=1)
        self.assertEqual(len(pack.quant_ids), 2)
        self.assertEqual(pack.location_id, self.shelf2)

    def test_put_in_pack_scan_suggested_package(self):
        """ Create two deliveries with a line from two different locations each.
        Then, group them in a batch and process the batch in barcode.
        Put first picking line in a package and the second one in another package,
        then change the location page and scan the suggested packaged for each picking lines.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})
        self.picking_type_out.barcode_validation_all_product_packed = True

        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 2)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf2, 2)
        self.env['stock.quant']._update_available_quantity(self.product3, self.shelf1, 1)

        # Creates a first delivery with 2 move lines: one from Section 1 and one from Section 2.
        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 1
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product3
            move.product_uom_qty = 1
        delivery_1 = delivery_form.save()
        delivery_1.action_confirm()
        delivery_1.action_assign()

        # Creates a second delivery (same idea than the first one).

        delivery_form = Form(self.env['stock.picking'])
        delivery_form.picking_type_id = self.picking_type_out
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product1
            move.product_uom_qty = 1
        with delivery_form.move_ids_without_package.new() as move:
            move.product_id = self.product2
            move.product_uom_qty = 1
        delivery_2 = delivery_form.save()
        delivery_2.action_confirm()
        delivery_2.action_assign()

        # Changes name of pickings to be able to track them on the tour
        delivery_1.name = 'test_delivery_1'
        delivery_2.name = 'test_delivery_2'

        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_ids.add(delivery_1)
        batch_form.picking_ids.add(delivery_2)
        batch_delivery = batch_form.save()
        batch_delivery.action_confirm()
        self.assertEqual(len(batch_delivery.move_ids), 5)
        self.assertEqual(len(batch_delivery.move_line_ids), 5)

        # Resets package sequence to be sure we'll have the attended packages name.
        seq = self.env['ir.sequence'].search([('code', '=', 'stock.quant.package')])
        seq.number_next_actual = 1

        url = self._get_batch_client_action_url(batch_delivery.id)
        self.start_tour(url, 'test_put_in_pack_scan_suggested_package', login='admin', timeout=180)

        self.assertEqual(batch_delivery.state, 'done')
        self.assertEqual(len(batch_delivery.move_line_ids), 5)
        for move_line in delivery_1.move_line_ids:
            self.assertEqual(move_line.result_package_id.name, 'PACK0000001')
        for move_line in delivery_2.move_line_ids:
            self.assertEqual(move_line.result_package_id.name, 'PACK0000002')

    def test_batch_create(self):
        """ Create a batch picking via barcode app from scratch """

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_batch_create', login='admin', timeout=180)
        self.assertEqual(self.picking_delivery_1.batch_id, self.picking_delivery_2.batch_id)
        batch_delivery = self.picking_delivery_1.batch_id
        self.assertEqual(len(batch_delivery.move_ids), 5)
        self.assertEqual(len(batch_delivery.move_line_ids), 7)

    def test_pack_and_same_product_several_sml(self):
        """
        A batch with two transfers, source and destination are the same. The
        first picking contains 3 x P1 and 25 x P2, the second one 7 x P1 and
        30 x P2. The 10 P1 are in a package PK1. The situation is more
        complicated for the second product: there are 100 P2 in a package PK2.
        When processing the batch, if the user scans the package PK1, it should
        update all move lines related to P1. Then, when scanning PK2, it should
        also update the move lines related to P2 and a new line should be
        created for the surplus (45 x P2).
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id)]})

        package02 = self.package.copy({'name': 'P00002'})
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 10, package_id=self.package)
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf1, 100, package_id=package02)

        # Two pickings,
        #   one with 3 x P1 and 25 x P2
        #   one with 7 x P1 and 30 x P2
        pickings = self.env['stock.picking'].create([{
            'location_id': self.shelf1.id,
            'location_dest_id': self.shelf2.id,
            'picking_type_id': self.picking_type_internal.id,
            'move_ids': [(0, 0, {
                'name': 'test_put_in_pack_from_multiple_pages',
                'location_id': self.shelf1.id,
                'location_dest_id': self.shelf2.id,
                'product_id': product.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': qty,
            }) for product, qty in picking_lines]
        } for picking_lines in [
            [(self.product1, 3), (self.product2, 25)],
            [(self.product1, 7), (self.product2, 30)],
        ]])
        pickings.action_confirm()
        pickings.action_assign()

        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_ids.add(pickings[0])
        batch_form.picking_ids.add(pickings[1])
        batch = batch_form.save()
        batch.action_confirm()

        url = self._get_batch_client_action_url(batch.id)
        self.start_tour(url, 'test_pack_and_same_product_several_sml', login='admin', timeout=180)

        self.assertRecordValues(pickings.move_ids, [
            {'picking_id': pickings[0].id, 'product_id': self.product1.id, 'state': 'done', 'quantity': 3, 'picked': True},
            {'picking_id': pickings[0].id, 'product_id': self.product2.id, 'state': 'done', 'quantity': 70, 'picked': True},
            {'picking_id': pickings[1].id, 'product_id': self.product1.id, 'state': 'done', 'quantity': 7, 'picked': True},
            {'picking_id': pickings[1].id, 'product_id': self.product2.id, 'state': 'done', 'quantity': 30, 'picked': True},
        ])

    def test_delete_from_batch(self):
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_delete_from_batch', login='admin', timeout=180)

    def test_split_line_on_exit_for_batch(self):
        """ Ensures that exit an unfinished batch will split the uncompleted move lines to have one
        move line with all picked quantity and one move line with the remaining quantity."""
        self.clean_access_rights()

        # Creates a new batch.
        batch_receipts = self.env['stock.picking.batch'].create({
            'name': 'batch_split_line_on_exit',
            'picking_type_id': self.picking_type_in.id,
        })

        # Creates two receipts (one for 4x product1, one for 4x product2) and add them to the batch.
        # Creates a receipt for 4x product1 and a second receipt for 4x product2.
        receipt1 = self.env['stock.picking'].create({
            'batch_id': batch_receipts.id,
            'name': "receipt1",
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'location_dest_id': receipt1.location_dest_id.id,
            'location_id': receipt1.location_id.id,
            'name': "product1 x4",
            'picking_id': receipt1.id,
            'product_id': self.product1.id,
            'product_uom_qty': 4,
        })
        receipt2 = self.env['stock.picking'].create({
            'batch_id': batch_receipts.id,
            'name': "receipt2",
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_in.id,
        })
        self.env['stock.move'].create({
            'location_dest_id': receipt2.location_dest_id.id,
            'location_id': receipt2.location_id.id,
            'name': "product2 x4",
            'picking_id': receipt2.id,
            'product_id': self.product2.id,
            'product_uom_qty': 4,
        })
        batch_receipts.action_confirm()

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = f"/web#action={action_id.id}"
        self.start_tour(url, 'test_split_line_on_exit_for_batch', login='admin')
        # Checks the receipts moves values.
        self.assertRecordValues(receipt1.move_ids, [
            {'product_id': self.product1.id, 'quantity': 2, 'picked': True},
            {'product_id': self.product1.id, 'quantity': 2, 'picked': False},
        ])
        self.assertRecordValues(receipt2.move_ids, [
            {'product_id': self.product2.id, 'quantity': 1, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 3, 'picked': False},
        ])

    def test_scan_can_change_destination_location(self):
        """ When we have multiple pickings in a batch for the same product, we should be able to change
        the destination location of each of them by scanning only once the destination.
        """
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, quantity=2)
        self.picking_type_internal.write({
            'restrict_scan_source_location': 'mandatory',
            'restrict_scan_product': True,
            'restrict_scan_dest_location': 'mandatory',
        })

        internal_picking_1 = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.stock_location.id,
            'picking_type_id': self.picking_type_internal.id,
        })
        self.env['stock.move'].create({
            'location_dest_id': internal_picking_1.location_dest_id.id,
            'location_id': internal_picking_1.location_id.id,
            'name': 'product1 x1',
            'picking_id': internal_picking_1.id,
            'product_id': self.product1.id,
            'product_uom_qty': 1,
        })
        internal_picking_2 = internal_picking_1.copy()

        internal_picking_1.name = 'test_int_picking_1'
        internal_picking_2.name = 'test_int_picking_2'

        batch_form = Form(self.env['stock.picking.batch'])
        batch_form.picking_type_id = self.picking_type_internal
        batch_form.picking_ids.add(internal_picking_1)
        batch_form.picking_ids.add(internal_picking_2)
        batch = batch_form.save()
        batch.action_confirm()

        url = self._get_batch_client_action_url(batch.id)
        self.start_tour(url, 'test_scan_can_change_destination_location', login='admin')

        # validate that SML destination locations changed
        move_lines = internal_picking_1.move_line_ids + internal_picking_2.move_line_ids
        self.assertEqual(move_lines.mapped('location_dest_id'), self.shelf3)
