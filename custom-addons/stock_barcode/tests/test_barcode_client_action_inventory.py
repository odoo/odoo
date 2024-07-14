# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields
from odoo.tests import tagged, loaded_demo_data
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestInventoryAdjustmentBarcodeClientAction(TestBarcodeClientAction):
    def test_inventory_adjustment(self):
        """ Simulate the following actions:
        - Open the inventory from the barcode app.
        - Scan twice the product 1.
        - Edit the line.
        - Add a product with the form view.
        - Validate
        """

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_adjustment', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', 'in', [self.product1.id, self.product2.id]),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 2)
        self.assertEqual(inventory_moves.mapped('quantity'), [2.0, 2.0])
        self.assertEqual(inventory_moves.mapped('state'), ['done', 'done'])

        quants = self.env['stock.quant'].search([('product_id', 'in', [self.product1.id, self.product2.id]),
                                                 ('location_id.usage', '=', 'internal')])
        self.assertEqual(quants.mapped('quantity'), [2.0, 2.0])
        self.assertEqual(quants.mapped('inventory_quantity'), [0, 0])
        self.assertEqual(quants.mapped('inventory_diff_quantity'), [0, 0])

    def test_inventory_adjustment_dont_update_location(self):
        """ Ensures the existing quants location cannot be update."""
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        # Adds some quants and request a count.
        # Adds quants for the same product in two locations.
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 5)
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf2, 5)
        # Marks them as to count by the user.
        quants = self.env['stock.quant'].search([('product_id', '=', self.product1.id)])
        quants.user_id = self.env.user
        quants.inventory_quantity_set = True
        quants.inventory_date = fields.Date.today()

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_inventory_adjustment_dont_update_location', login='admin', timeout=180)
        quants = self.env['stock.quant'].search([
            ('product_id', '=', self.product1.id),
            ('location_id.usage', '=', 'internal'),
        ])
        self.assertRecordValues(quants, [
            {'location_id': self.stock_location.id, 'quantity': 1},
            {'location_id': self.shelf2.id, 'quantity': 0},
            {'location_id': self.shelf1.id, 'quantity': 1},
        ])

    def test_inventory_adjustment_multi_company(self):
        """ When doing an Inventory Adjustment, ensures only products belonging
        to current company or to no company can be scanned."""
        self.clean_access_rights()
        # Creates two companies and assign them to the user.
        company_a = self.env['res.company'].create({'name': 'Comp A - F2 FTW'})
        company_b = self.env['res.company'].create({'name': 'Comp B - F3 Wee-Wee Pool'})
        self.env.user.write({
            'company_ids': [(4, company_a.id), (4, company_b.id)],
            'company_id': company_a.id,
        })
        # Changes the company of some products.
        self.product1.company_id = company_a
        self.product2.company_id = company_b
        product_no_company = self.env['product.product'].create({
            'name': 'Company-less Product',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product_no_company',
        })
        self.start_tour("/web", 'test_inventory_adjustment_multi_company', login='admin', timeout=180)
        # Checks an inventory adjustment was correctly validated for each company.
        inventory_moves = self.env['stock.move'].search([
            ('is_inventory', '=', True),
            ('product_id', 'in', (self.product1 | self.product2 | product_no_company).ids),
        ])
        self.assertRecordValues(inventory_moves.sorted(lambda mv: (mv.product_id.id, mv.id)), [
            {'product_id': self.product1.id, 'quantity': 1, 'company_id': company_a.id},
            {'product_id': self.product2.id, 'quantity': 1, 'company_id': company_b.id},
            {'product_id': product_no_company.id, 'quantity': 1, 'company_id': company_a.id},
            {'product_id': product_no_company.id, 'quantity': 1, 'company_id': company_b.id},
        ])

    def test_inventory_adjustment_multi_location(self):
        """ Simulate the following actions:
        - Generate those lines with scan:
        WH/stock product1 qty: 2
        WH/stock product2 qty: 1
        WH/stock/shelf1 product2 qty: 1
        WH/stock/shelf2 product1 qty: 1
        - Validate
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_adjustment_multi_location', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', 'in', [self.product1.id, self.product2.id]),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 4)
        self.assertEqual(inventory_moves.mapped('state'), ['done', 'done', 'done', 'done'])
        inventory_move_in_WH_stock = inventory_moves.filtered(lambda l: l.location_dest_id == self.stock_location)
        self.assertEqual(set(inventory_move_in_WH_stock.mapped('product_id')), {self.product1, self.product2})
        self.assertEqual(inventory_move_in_WH_stock.filtered(lambda l: l.product_id == self.product1).quantity, 2.0)
        self.assertEqual(inventory_move_in_WH_stock.filtered(lambda l: l.product_id == self.product2).quantity, 1.0)

        inventory_move_in_shelf1 = inventory_moves.filtered(lambda l: l.location_dest_id == self.shelf1)
        self.assertEqual(len(inventory_move_in_shelf1), 1)
        self.assertEqual(inventory_move_in_shelf1.product_id, self.product2)
        self.assertEqual(inventory_move_in_shelf1.quantity, 1.0)

        inventory_move_in_shelf2 = inventory_moves.filtered(lambda l: l.location_dest_id == self.shelf2)
        self.assertEqual(len(inventory_move_in_shelf2), 1)
        self.assertEqual(inventory_move_in_shelf2.product_id, self.product1)
        self.assertEqual(inventory_move_in_shelf2.quantity, 1.0)

    def test_inventory_adjustment_tracked_product(self):
        """ Simulate the following actions:
        - Generate those lines with scan:
        productlot1 with a lot named lot1 (qty 2)
        productserial1 with serial1 (qty 1)
        productserial1 with serial2 (qty 1)
        productserial1 with serial3 (qty 1)
        productserial1 without serial (qty 1)
        productlot1 with a lot named lot2 (qty 1)
        productlot1 with a lot named lot3 (qty 1)
        - Validate
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_adjustment_tracked_product', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', 'in', [self.productlot1.id, self.productserial1.id]),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 7)
        self.assertTrue(all(s == 'done' for s in inventory_moves.mapped('state')))

        moves_with_lot = inventory_moves.filtered(lambda l: l.product_id == self.productlot1)
        moves_with_sn = inventory_moves.filtered(lambda l: l.product_id == self.productserial1)
        mls_with_lot = moves_with_lot.move_line_ids
        mls_with_sn = moves_with_sn.move_line_ids
        self.assertEqual(len(mls_with_lot), 3)
        self.assertEqual(len(mls_with_sn), 4)
        self.assertEqual(mls_with_lot.mapped('lot_id.name'), ['lot1', 'lot2', 'lot3'])
        self.assertEqual(mls_with_lot.filtered(lambda ml: ml.lot_id.name == 'lot1').qty_done, 3)
        self.assertEqual(mls_with_lot.filtered(lambda ml: ml.lot_id.name == 'lot2').qty_done, 1)
        self.assertEqual(mls_with_lot.filtered(lambda ml: ml.lot_id.name == 'lot3').qty_done, 1)
        self.assertEqual(set(mls_with_sn.mapped('lot_id.name')), {'serial1', 'serial2', 'serial3'})

    def test_inventory_adjustment_tracked_product_multilocation(self):
        """ This test ensures two things:
        - When the user has to count the same lot from multiple locations, the right line will be
        incremented when they scan the lot's barcode, depending of the previous scanned location.
        - When scanning a tracked product, if this product alread has quants, it will retrieve and
        create a barcode line for each quant.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        # Adds some quants for the product tracked by lots in two locations.
        lot_default_values = {'product_id': self.productlot1.id, 'company_id': self.env.company.id}
        lot_1 = self.env['stock.lot'].create(dict(lot_default_values, name="lot1"))
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf1, 3, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.shelf2, 5, lot_id=lot_1)
        # Marks them as to count by the user.
        quants = self.env['stock.quant'].search([('product_id', '=', self.productlot1.id)])
        quants.user_id = self.env.user
        quants.inventory_quantity_set = True
        quants.inventory_date = fields.Date.today()
        quants[0].inventory_quantity = 3
        quants[1].inventory_quantity = 0
        # Adds some quants for the product tracked by serial numbers in two locations.
        serial_default_values = {'product_id': self.productserial1.id, 'company_id': self.env.company.id}
        for location, numbers in [(self.shelf1, [1, 2, 3]), (self.shelf3, [4, 5])]:
            for n in numbers:
                serial_number = self.env['stock.lot'].create(dict(serial_default_values, name=f'sn{n}'))
                self.env['stock.quant']._update_available_quantity(self.productserial1, location, 1, lot_id=serial_number)
        # Opens the inventory adjustement and process it.
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = f"/web#action={action_id.id}"
        self.start_tour(url, "test_inventory_adjustment_tracked_product_multilocation", login="admin", timeout=180)

    def test_inventory_adjustment_tracked_product_permissive_quants(self):
        """Make an inventory adjustment for a product tracked by lot having quants without lot.
           The following actions are made in the barcode app:
            - Scan productlot1
            - Scan lot1 twice
            - Set productlot1 quantity without lot to available
            - Validate
        """
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        self.env["stock.lot"].create({
            'name': 'lot1',
            'product_id': self.productlot1.id,
            'company_id': self.env.company.id
        })
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 5)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_adjustment_tracked_product_permissive_quants', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', '=', self.productlot1.id),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 2)
        self.assertEqual(inventory_moves.mapped('state'), ['done', 'done'])
        self.assertEqual(inventory_moves.mapped('product_id'), self.productlot1)

        self.assertEqual(len(inventory_moves.move_line_ids), 2)
        move_line_1, move_line_2 = inventory_moves.move_line_ids
        self.assertEqual(move_line_1.qty_done, 0)
        self.assertEqual(move_line_2.lot_id.name, 'lot1')
        self.assertEqual(move_line_2.qty_done, 2)

    def test_inventory_create_quant(self):
        """ Creates a quant and checks it will not be deleted until the inventory was validated.
        """
        self.clean_access_rights()
        Quant = self.env['stock.quant']
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_inventory_create_quant', login='admin', timeout=180)

        Quant._unlink_zero_quants()
        product1_quant = Quant.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(product1_quant), 1)
        self.assertEqual(product1_quant.inventory_quantity, 0.0)

        # Validates the inventory, then checks there is no 0 qty quant.
        product1_quant.action_validate()
        Quant.invalidate_model()  # Updates the cache.
        Quant._unlink_zero_quants()
        product1_quant = Quant.search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(product1_quant), 0)

    def test_inventory_nomenclature(self):
        """ Simulate scanning a product and its weight
        thanks to the barcode nomenclature """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes.default_barcode_nomenclature')

        product_weight = self.env['product.product'].create({
            'name': 'product_weight',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '2145631000000',
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_nomenclature', login='admin', timeout=180)
        quantity = self.env['stock.move.line'].search([
            ('product_id', '=', product_weight.id),
            ('state', '=', 'done'),
            ('location_id', '=', product_weight.property_stock_inventory.id),
        ])

        self.assertEqual(quantity.qty_done, 12.35)

    def test_inventory_package(self):
        """ Simulate an adjustment where a package is scanned and edited """
        self.clean_access_rights()
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        pack = self.env['stock.quant.package'].create({
            'name': 'PACK001',
        })

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7, package_id=pack)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 3, package_id=pack)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, "test_inventory_package", login="admin", timeout=180)

        # Check the package is updated after adjustment
        self.assertDictEqual(
            {q.product_id: q.quantity for q in pack.quant_ids},
            {self.product1: 7, self.product2: 21}
        )

    def test_inventory_packaging(self):
        """ Scans a product's packaging and ensures its quantity is correctly
        counted regardless if there is already products in stock or not.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        self.env['product.packaging'].create({
            'name': 'product1 x15',
            'qty': 15,
            'barcode': 'pack007',
            'product_id': self.product1.id
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_inventory_packaging', login='admin', timeout=180)

    def test_inventory_owner_scan_package(self):
        group_owner = self.env.ref('stock.group_tracking_owner')
        group_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, group_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, group_owner.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7, package_id=self.package, owner_id=self.owner)
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_owner_scan_package', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', '=', self.product1.id), ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 1)
        self.assertEqual(inventory_moves.state, 'done')
        self.assertEqual(inventory_moves.move_line_ids.owner_id.id, self.owner.id)

    def test_inventory_using_buttons(self):
        """ Creates an inventory from scratch, then scans products and verifies
        the buttons behavior is right.
        """
        self.clean_access_rights()
        # Adds some quantities for product2.
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 10)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_inventory_using_buttons', login='admin', timeout=180)
        product1_quant = self.env['stock.quant'].search([
            ('product_id', '=', self.product1.id),
            ('quantity', '>', 0)
        ])
        self.assertEqual(len(product1_quant), 1)
        self.assertEqual(product1_quant.quantity, 1.0)
        self.assertEqual(product1_quant.location_id.id, self.stock_location.id)

        productlot1_quant = self.env['stock.quant'].search([
            ('product_id', '=', self.productlot1.id),
            ('quantity', '>', 0)
        ])
        self.assertEqual(len(product1_quant), 1)
        self.assertEqual(productlot1_quant.quantity, 1.0)
        self.assertEqual(productlot1_quant.lot_id.name, 'toto-42')
        self.assertEqual(productlot1_quant.location_id.id, self.stock_location.id)

    def test_gs1_inventory_gtin_8(self):
        """ Simulate scanning a product with his gs1 barcode """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_gs1_inventory_gtin_8', login='admin', timeout=180)

        # Checks the inventory adjustment correclty created a move line.
        move_line = self.env['stock.move.line'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('location_id', '=', product.property_stock_inventory.id),
        ])
        self.assertEqual(move_line.qty_done, 78)

    def test_gs1_inventory_product_units(self):
        """ Scans a product with a GS1 barcode containing multiple quantities."""
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)

        self.start_tour(url, 'test_gs1_inventory_product_units', login='admin', timeout=180)

        quantity = self.env['stock.move.line'].search([
            ('product_id', '=', product.id),
            ('state', '=', 'done'),
            ('location_id', '=', product.property_stock_inventory.id),
        ])

        self.assertEqual(quantity.qty_done, 102)

    def test_gs1_inventory_package(self):
        """ Scans existing packages and checks their products are correclty added
        to the inventory adjustment. Then scans some products, scans a new package
        and checks the package was created and correclty assigned to those products.
        """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_pack.id, 0)]})

        product = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        # Creates a first package in Section 1 and adds some products.
        pack_1 = self.env['stock.quant.package'].create({'name': '987654123487568456'})
        self.env['stock.quant']._update_available_quantity(self.product1, self.shelf1, 8, package_id=pack_1)
        # Creates a second package in Section 2 and adds some other products.
        pack_2 = self.env['stock.quant.package'].create({'name': '487325612456785124'})
        self.env['stock.quant']._update_available_quantity(self.product2, self.shelf2, 6, package_id=pack_2)

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_gs1_inventory_package', login='admin', timeout=180)

        pack_3 = self.env['stock.quant.package'].search([('name', '=', '122333444455555670')])
        self.assertEqual(pack_3.location_id.id, self.shelf2.id)
        self.assertEqual(pack_3.quant_ids.product_id.ids, [product.id])

    def test_gs1_inventory_lot_serial(self):
        """ Checks tracking numbers and quantites are correctly got from GS1
        barcodes for tracked products.
        Also, this test is an opportunity to ensure custom GS1 separators are used clientside."""
        if not loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.env.company.nomenclature_id.gs1_separator_fnc1 = r'(Alt029|#|\x1D|~)'

        product_lot = self.env['product.product'].create({
            'name': 'PRO_GTIN_12_lot',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '111155555717',  # GTIN-12 format
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'tracking': 'lot',
        })

        product_serial = self.env['product.product'].create({
            'name': 'PRO_GTIN_14_serial',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15222222222219',  # GTIN-14 format
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'tracking': 'serial',
        })

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_gs1_inventory_lot_serial', login='admin', timeout=180)

        smls_lot = self.env['stock.move.line'].search([
            ('product_id', '=', product_lot.id),
            ('state', '=', 'done'),
            ('location_id', '=', product_lot.property_stock_inventory.id),
        ])
        self.assertEqual(len(smls_lot), 3)
        self.assertEqual(smls_lot[0].qty_done, 10)
        self.assertEqual(smls_lot[1].qty_done, 15)
        self.assertEqual(smls_lot[2].qty_done, 20)
        self.assertEqual(
            smls_lot.lot_id.mapped('name'),
            ['LOT-AAA', 'LOT-AAB', 'LOT-AAC']
        )

        smls_serial = self.env['stock.move.line'].search([
            ('product_id', '=', product_serial.id),
            ('state', '=', 'done'),
            ('location_id', '=', product_serial.property_stock_inventory.id),
        ])
        self.assertEqual(len(smls_serial), 5)
        self.assertEqual(smls_serial[0].qty_done, 1)
        self.assertEqual(smls_serial[1].qty_done, 1)
        self.assertEqual(smls_serial[2].qty_done, 1)
        self.assertEqual(smls_serial[3].qty_done, 20)
        self.assertEqual(smls_serial[4].qty_done, 1)
        self.assertEqual(
            smls_serial.lot_id.mapped('name'),
            ['Serial1', 'Serial2', 'Serial3', 'Serial4']
        )

    def test_scan_product_lot_with_package(self):
        """
        Check that a lot can be scanned in the inventory Adjustments,
        when the package is set in the quant.
        """
        # Enable the package option
        self.env['res.config.settings'].create({'group_stock_tracking_lot': True}).execute()
        product = self.env['product.product'].create({
            'name': 'Product',
            'type': 'product',
            'tracking': 'lot',
        })
        self.env["stock.quant"].create({
            'product_id': product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 10,
            'package_id': self.env['stock.quant.package'].create({
                'name': 'Package-test',
            }).id,
            'lot_id': self.env['stock.lot'].create({
                'name': 'Lot-test',
                'product_id': product.id,
                'company_id': self.env.company.id,
            }).id,
        })
        self.assertEqual(product.qty_available, 10)
        self.start_tour("/web", 'stock_barcode_package_with_lot', login="admin")
