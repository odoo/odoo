# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from odoo import Command, fields, http
from odoo.tests import patch, tagged
from odoo.tools.misc import file_open
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestInventoryAdjustmentBarcodeClientAction(TestBarcodeClientAction):
    # === HELPER METHODS ===#
    def create_serial_numbers(self, product, start_index, quantity=1, prefix='sn'):
        return self.env['stock.lot'].create([{
            'name': f'{prefix}{start_index + n}',
            'product_id': product.id,
            'company_id': self.env.company.id,
        } for n in range(quantity)])

    # === TESTS ===#
    def test_inventory_adjustment(self):
        """ Simulate the following actions:
        - Open the inventory from the barcode app.
        - Scan twice the product 1.
        - Edit the line.
        - Add a product with the form view.
        - Validate
        """
        self.start_tour("/odoo/barcode", 'test_inventory_adjustment', login='admin', timeout=180)

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

        self.start_tour("/odoo/barcode", 'test_inventory_adjustment_dont_update_location', login='admin', timeout=180)
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
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product_no_company',
        })
        self.start_tour("/odoo", 'test_inventory_adjustment_multi_company', login='admin', timeout=180)
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

        self.start_tour("/odoo/barcode", 'test_inventory_adjustment_multi_location', login='admin', timeout=180)

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

        self.start_tour("/odoo/barcode", 'test_inventory_adjustment_tracked_product', login='admin', timeout=180)

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
        self.assertFalse(moves_with_sn.lot_ids.company_id)

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
        lot_1 = self.env['stock.lot'].create({'product_id': self.productlot1.id, 'name': "lot1"})
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
        for location, numbers in [(self.shelf1, [1, 2, 3]), (self.shelf3, [4, 5])]:
            for n in numbers:
                serial_number = self.env['stock.lot'].create({'product_id': self.productserial1.id, 'name': f'sn{n}'})
                self.env['stock.quant']._update_available_quantity(self.productserial1, location, 1, lot_id=serial_number)
        # Opens the inventory adjustement and process it.
        self.start_tour("/odoo/barcode", "test_inventory_adjustment_tracked_product_multilocation", login="admin", timeout=180)

    def test_inventory_adjustment_tracked_product_permissive_quants(self):
        """Make an inventory adjustment for a product tracked by lot having quants without lot.
           The following actions are made in the barcode app:
            - Scan productlot1
            - Scan lot1 twice
            - Set productlot1 quantity without lot to available
            - Validate
        """
        self.env.ref('base.group_user').implied_ids += self.env.ref('stock.group_production_lot')
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})

        lot1 = self.env["stock.lot"].create({
            'name': 'lot1',
            'product_id': self.productlot1.id,
        })
        self.env['stock.quant']._update_available_quantity(self.productlot1, self.stock_location, 5)
        self.start_tour("/odoo/barcode", 'test_inventory_adjustment_tracked_product_permissive_quants', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', '=', self.productlot1.id),
                                                         ('is_inventory', '=', True)])
        inventory_location = self.productlot1.property_stock_inventory
        self.assertEqual(len(inventory_moves), 2)
        self.assertEqual(inventory_moves.mapped('state'), ['done', 'done'])
        self.assertEqual(inventory_moves.product_id, self.productlot1)

        self.assertEqual(len(inventory_moves.move_line_ids), 2)
        self.assertRecordValues(inventory_moves.move_line_ids, [
            {'quantity': 5, 'location_id': self.stock_location.id, 'location_dest_id': inventory_location.id, 'lot_id': False},
            {'quantity': 2, 'location_id': inventory_location.id, 'location_dest_id': self.stock_location.id, 'lot_id': lot1.id},
        ])

    def test_inventory_create_quant(self):
        """ Creates a quant and checks it will not be deleted until the inventory was validated.
        """
        self.clean_access_rights()
        Quant = self.env['stock.quant']
        self.start_tour("/odoo/barcode", 'test_inventory_create_quant', login='admin', timeout=180)

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

    def test_inventory_dialog_not_counted_serial_numbers(self):
        """ This test ensures when some SN were counted in a location, if there
        is uncounted SN in this location, a dialog asks the user if they want to
        count them as missing when the inventory adjustment is applied.
        """
        self.env['ir.config_parameter'].set_param('stock_barcode.barcode_separator_regex', '[,;]')
        self.clean_access_rights()
        group_lot = self.env.ref('stock.group_production_lot')
        group_location = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.groups_id = [Command.link(group_lot.id)]
        self.env.user.groups_id = [Command.link(group_location.id)]
        Quant = self.env['stock.quant']
        # Creates some serial numbers and adds them in the stock.
        productserial2 = self.env['product.product'].create({
            'name': 'productserial2',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'productserial2',
            'tracking': 'serial',
        })
        serial1_sns = self.create_serial_numbers(self.productserial1, 1, 6)
        serial2_sns = self.create_serial_numbers(productserial2, 1, 3)
        # Adds 3 SNs in Shelf 1 and adds 6 SNs in Shelf 2.
        for sn in serial1_sns[:3]:
            Quant._update_available_quantity(sn.product_id, self.shelf1, 1, lot_id=sn)
        for sn in (serial1_sns[3:] | serial2_sns):
            Quant._update_available_quantity(sn.product_id, self.shelf2, 1, lot_id=sn)
        # Marks created quants as to count.
        quants = Quant.search([('product_id', 'in', [self.productserial1.id, productserial2.id])])
        wizard_request_count = self.env['stock.request.count'].create({
            'user_id': self.env.user.id,
            'quant_ids': quants.ids,
            'set_count': 'empty',
        })
        wizard_request_count.action_request_count()
        self.start_tour("/odoo/barcode?debug=assets", 'test_inventory_dialog_not_counted_serial_numbers', login='admin')
        self.assertRecordValues(quants, [
            {'product_id': self.productserial1.id, 'lot_id': serial1_sns[0].id, 'quantity': 1, 'location_id': self.shelf1.id},
            {'product_id': self.productserial1.id, 'lot_id': serial1_sns[1].id, 'quantity': 1, 'location_id': self.shelf1.id},
            {'product_id': self.productserial1.id, 'lot_id': serial1_sns[2].id, 'quantity': 0, 'location_id': self.shelf1.id},
            {'product_id': self.productserial1.id, 'lot_id': serial1_sns[3].id, 'quantity': 1, 'location_id': self.shelf2.id},
            {'product_id': self.productserial1.id, 'lot_id': serial1_sns[4].id, 'quantity': 1, 'location_id': self.shelf2.id},
            {'product_id': self.productserial1.id, 'lot_id': serial1_sns[5].id, 'quantity': 1, 'location_id': self.shelf2.id},
            {'product_id': productserial2.id, 'lot_id': serial2_sns[0].id, 'quantity': 1, 'location_id': self.shelf2.id},
            {'product_id': productserial2.id, 'lot_id': serial2_sns[1].id, 'quantity': 1, 'location_id': self.shelf2.id},
            {'product_id': productserial2.id, 'lot_id': serial2_sns[2].id, 'quantity': 1, 'location_id': self.shelf2.id},
        ])

    def test_inventory_image_visible_for_quant(self):
        """ Ensure the product's image is visible in the Barcode quant form view."""
        # Load an image and use it for a product.
        img_url = 'stock_barcode/static/img/barcode.png'
        img_content = base64.b64encode(file_open(img_url, "rb").read())
        self.product1.image_1920 = img_content
        # Creates two quants to count.
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 4)
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 4)
        quants = self.env['stock.quant'].search([('product_id', 'in', [self.product1.id, self.product2.id])])
        wizard_request_count = self.env['stock.request.count'].create({
            'user_id': self.env.user.id,
            'quant_ids': quants.ids,
            'set_count': 'empty',
        })
        wizard_request_count.action_request_count()
        self.start_tour("/odoo/barcode/", 'test_inventory_image_visible_for_quant', login='admin', timeout=180)

    def test_inventory_nomenclature(self):
        """ Simulate scanning a product and its weight
        thanks to the barcode nomenclature """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes.default_barcode_nomenclature')

        product_weight = self.env['product.product'].create({
            'name': 'product_weight',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '2145631000000',
        })

        self.start_tour("/odoo/barcode", 'test_inventory_nomenclature', login='admin', timeout=180)
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

        self.start_tour("/odoo/barcode", "test_inventory_package", login="admin", timeout=180)

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
        self.start_tour("/odoo/barcode", 'test_inventory_packaging', login='admin', timeout=180)

    def test_inventory_serial_product_packaging(self):
        """ This test ensures that correct packaging lines generated
        for serial product in inventory adjustments.
        """
        self.clean_access_rights()
        group_lot = self.env.ref('stock.group_production_lot')
        group_packaging = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [(4, group_lot.id, 0)]})
        self.env.user.write({'groups_id': [(4, group_packaging.id)]})
        self.env['product.packaging'].create({
            'name': 'Product Serial 1 Packaging',
            'qty': 3,
            'product_id': self.productserial1.id,
            'barcode': 'PCK3',
        })

        self.start_tour('/odoo/barcode', 'test_inventory_serial_product_packaging', login='admin', timeout=180)

    def test_inventory_packaging_button(self):
        """
        Check that the product packaging button are correctly dipslayed on the
        digipad when creating an invetory adjustment.
        """
        self.clean_access_rights()
        grp_pack = self.env.ref('product.group_stock_packaging')
        self.env.user.write({'groups_id': [Command.link(grp_pack.id)]})

        self.product1.name = "Lovely Product"
        self.env['product.packaging'].create({
            'name': 'LP x15',
            'qty': 15,
            'product_id': self.product1.id
        })
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_inventory_packaging_button', login='admin', timeout=180)
        quant = self.env['stock.quant'].search([("product_id", "=", self.product1.id)], limit=1)
        self.assertEqual(quant.inventory_quantity, 15.0)

    def test_inventory_owner_scan_package(self):
        group_owner = self.env.ref('stock.group_tracking_owner')
        group_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(4, group_pack.id, 0)]})
        self.env.user.write({'groups_id': [(4, group_owner.id, 0)]})

        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7, package_id=self.package, owner_id=self.owner)

        self.start_tour("/odoo/barcode", 'test_inventory_owner_scan_package', login='admin', timeout=180)

        inventory_moves = self.env['stock.move'].search([('product_id', '=', self.product1.id), ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 1)
        self.assertEqual(inventory_moves.state, 'done')
        self.assertEqual(inventory_moves.move_line_ids.owner_id.id, self.owner.id)

    def test_inventory_setting_count_entire_locations_on(self):
        """
        Check the scenario when the "Count Entire Locations" setting is enabled,
        considering both tracked and untracked products and the usage of multiple locations.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        Quant = self.env['stock.quant']

        # Create lots and serial numbers.
        lots = self.env['stock.lot'].create([{
            'name': f'lot{i}',
            'product_id': self.productlot1.id,
        } for i in range(1, 5)])
        shelf1_serial_numbers = self.create_serial_numbers(self.productserial1, 1, 3)
        shelf2_serial_numbers = self.create_serial_numbers(self.productserial1, 4, 3)

        # Adds quantity in WH/Stock/Shelf1.
        Quant._update_available_quantity(self.product1, self.shelf1, 10)
        Quant._update_available_quantity(self.product2, self.shelf1, 20)
        Quant._update_available_quantity(self.productlot1, self.shelf1, 3, lot_id=lots[0])
        Quant._update_available_quantity(self.productlot1, self.shelf1, 4, lot_id=lots[1])
        for sn in shelf1_serial_numbers:
            Quant._update_available_quantity(self.productserial1, self.shelf1, 1, lot_id=sn)
        # Adds quantity in WH/Stock/Shelf2.
        Quant._update_available_quantity(self.product1, self.shelf2, 30)
        Quant._update_available_quantity(self.productlot1, self.shelf2, 5, lot_id=lots[2])
        Quant._update_available_quantity(self.productlot1, self.shelf2, 2, lot_id=lots[3])
        for sn in shelf2_serial_numbers:
            Quant._update_available_quantity(self.productserial1, self.shelf2, 1, lot_id=sn)

        # Mark quant for product1 in shelf 1 as to count.
        quants = Quant.search([('product_id', '=', self.product1.id), ('location_id', '=', self.shelf1.id)])
        wizard_request_count = self.env['stock.request.count'].create({
            'user_id': self.env.user.id,
            'quant_ids': quants.ids,
            'set_count': 'set',
        })
        wizard_request_count.action_request_count()
        # Set "Count Entire Locations" setting on after the count request, otherwise all quants for
        # this quant's location will be already marked as to count.
        grp_barcode_count_entire_location = self.env.ref('stock_barcode.group_barcode_count_entire_location')
        self.env.user.write({'groups_id': [(4, grp_barcode_count_entire_location.id, 0)]})
        self.start_tour("/odoo/barcode", 'test_inventory_setting_count_entire_locations_on', login='admin', timeout=180)

    def test_inventory_setting_count_entire_locations_off(self):
        """
        Check the scenario when the "Count Entire Locations" setting is disabled,
        considering both tracked and untracked products and the usage of multiple locations.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        Quant = self.env['stock.quant']

        # Adds quantity in WH/Stock/Shelf1.
        Quant._update_available_quantity(self.product1, self.shelf1, 10)
        Quant._update_available_quantity(self.product2, self.shelf1, 20)
        # Adds quantity in WH/Stock/Shelf2.
        Quant._update_available_quantity(self.product1, self.shelf2, 30)

        # Mark quant for product1 in shelf 1 as to count.
        quants = Quant.search([('product_id', '=', self.product1.id), ('location_id', '=', self.shelf1.id)])
        wizard_request_count = self.env['stock.request.count'].create({
            'user_id': self.env.user.id,
            'quant_ids': quants.ids,
            'set_count': 'set',
        })
        wizard_request_count.action_request_count()
        self.start_tour('/odoo/barcode', 'test_inventory_setting_count_entire_locations_off', login='admin', timeout=180)

    def test_inventory_setting_show_quantity_to_count(self):
        """
        Check the scenario when "Show Quantity to Count" setting is enabled or
        disabled, considering both tracked and untracked products.
        """
        self.clean_access_rights()
        # Enables multilocations and tracking.
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0)]})
        Quant = self.env['stock.quant']

        # Creates some lots and serial numbers.
        serial_numbers = self.create_serial_numbers(self.productserial1, 1, 3)
        lots = self.env['stock.lot'].create([{
            'name': lot_name,
            'product_id': self.productlot1.id,
        } for lot_name in ['lot1', 'lot2']])

        # Adds quantity in stock for the products.
        for sn in serial_numbers:
            Quant._update_available_quantity(self.productserial1, self.stock_location, 1, lot_id=sn)
        Quant._update_available_quantity(self.productlot1, self.stock_location, 3, lot_id=lots[0])
        Quant._update_available_quantity(self.productlot1, self.stock_location, 4, lot_id=lots[1])
        Quant._update_available_quantity(self.product1, self.stock_location, 5)

        # Mark added quants as to count.
        quants = Quant.search([('product_id', 'in', [self.product1.id, self.productlot1.id, self.productserial1.id])])
        wizard_request_count = self.env['stock.request.count'].create({
            'user_id': self.env.user.id,
            'quant_ids': quants.ids,
            'set_count': 'empty',
        })
        wizard_request_count.action_request_count()

        self.start_tour("/odoo/barcode", 'test_inventory_setting_show_quantity_to_count_on', login='admin', timeout=180)
        # Disable the "Show Quantity to Count" setting and launch second tour.
        grp_show_quantity_count = self.env.ref('stock_barcode.group_barcode_show_quantity_count')
        group_user = self.env.ref('base.group_user')
        group_user.write({'implied_ids': [(3, grp_show_quantity_count.id)]})
        self.env.user.write({'groups_id': [(3, grp_show_quantity_count.id)]})
        self.start_tour("/odoo/barcode", 'test_inventory_setting_show_quantity_to_count_off', login='admin', timeout=180)

    def test_inventory_using_buttons(self):
        """ Creates an inventory from scratch, then scans products and verifies
        the buttons behavior is right.
        """
        self.clean_access_rights()
        # Adds some quantities for product2.
        self.env['stock.quant']._update_available_quantity(self.product2, self.stock_location, 10)

        self.start_tour("/odoo/barcode", 'test_inventory_using_buttons', login='admin', timeout=180)
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

    def test_inventory_adjustment_with_no_internal_location_quant(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        
        # Simulate moving 1 unit of product1 from Customer Location to Inventory Adjustment Location
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.env.ref('stock.stock_location_customers').id,
            'quantity': -1,
        })

        # Create a quant in Inventory adjustment location
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.product1.property_stock_inventory.id,
            'quantity': 1,
        })

        self.start_tour("/odoo/barcode", 'test_inventory_adjustment_with_no_internal_location_quant', login='admin')

        inventory_moves = self.env['stock.move'].search([('product_id', '=', self.product1.id),
                                                         ('is_inventory', '=', True)])
        self.assertEqual(len(inventory_moves), 1)
        self.assertEqual(inventory_moves.quantity, 1.0)
        self.assertEqual(inventory_moves.state, 'done')
        self.assertEqual(inventory_moves.location_id.name, 'Inventory adjustment')
        self.assertEqual(inventory_moves.location_dest_id.name, 'Stock')

        quants = self.env['stock.quant'].search([('product_id', '=', self.product1.id),
                                                 ('location_id.usage', '=', 'internal')])
        self.assertEqual(quants.quantity, 1.0)
        self.assertEqual(quants.inventory_quantity, 0)
        self.assertEqual(quants.inventory_diff_quantity, 0)

    # === RFID TESTS ===#
    def test_rfid_inventory_scan_sgtin(self):
        """ Checks multiple products can be scanned at once for an Inventory
        Adjustment using RFID."""
        self.clean_access_rights()
        group_lot = self.env.ref('stock.group_production_lot')
        self.env.user.write({'groups_id': [Command.link(group_lot.id)]})
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        # Create a bunch of products with EAN13.
        product_common_vals = {
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'uom_id': self.env.ref('uom.product_uom_unit').id
        }
        products = self.env['product.product'].create([{
            **product_common_vals,
            'name': product_name,
            'barcode': barcode,
        } for (product_name, barcode) in [
            ('Lunch box', '2300001000015'),
            ('French wine', '2300001000084'),
            ('Japanese wine', '2300001000121'),
            ('Large plate', '5468123001239'),
            ('Inox knife', '5468123002465'),
        ]])
        # Create a few products tracked by SN with EAN13.
        tracked_products = self.env['product.product'].create([{
            **product_common_vals,
            'name': product_name,
            'tracking': 'serial',
            'barcode': barcode,
        } for (product_name, barcode) in [
            ('Handmade argyle plate', '8765432100002'),
            ('Chief suit', '8765432300044'),
        ]])
        # Create serial numbers for those products.
        p1_serial_numbers = self.env['stock.lot'].create([{
            'name': str(i).rjust(5, '0'),
            'product_id': tracked_products[0].id,
        } for i in range(128, 134)])
        p2_serial_numbers = self.env['stock.lot'].create([{
            'name': str(i),
            'product_id': tracked_products[1].id,
        } for i in [12, 10, 15, 16, 9]])
        # Add some quantity in stock.
        self.env['stock.quant']._update_available_quantity(products[0], self.stock_location, 12)
        self.env['stock.quant']._update_available_quantity(products[3], self.stock_location, 35)
        self.env['stock.quant']._update_available_quantity(products[4], self.stock_location, 11)
        for serial_number in (p1_serial_numbers | p2_serial_numbers):
            self.env['stock.quant']._update_available_quantity(
                serial_number.product_id,
                self.stock_location,
                1,
                lot_id=serial_number)

        # Mock the calls to the route to count the call amount.
        self1 = self
        get_specific_barcode_data_orig = StockBarcodeController.get_specific_barcode_data

        @http.route('/stock_barcode/get_specific_barcode_data', type='json', auth='user')
        def mocked_data_batch_method(self, **kwargs):
            if self1.call_count == 0:
                # First call: product and serial numbers.
                self1.assertEqual(list(kwargs['barcodes_by_model'].keys()), ['product.product', 'stock.lot'])
            elif self1.call_count == 1:
                # First call: serial numbers only (no new product's barcode scanned).
                self1.assertEqual(list(kwargs['barcodes_by_model'].keys()), ['stock.lot'])
            self1.call_count += 1
            return get_specific_barcode_data_orig(self, **kwargs)

        with patch.object(
            StockBarcodeController,
            'get_specific_barcode_data',
            mocked_data_batch_method
        ):
            self.start_tour('/odoo/barcode', 'test_rfid_inventory_scan_sgtin', login='admin', timeout=180)
            self.assertEqual(self.call_count, 2)

    def test_inventory_count_with_line_deletion(self):
        """
        Check that the quant data of the barcode cache is not
        corrupted by line deletions.
        """
        self.clean_access_rights()
        # Put 5 units of prodcut1 in stock and start an inventory count
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 5)
        self.start_tour("/odoo/barcode", 'test_inventory_count_with_line_deletion', login='admin')

    # === GS1 TESTS ===#
    def test_gs1_inventory_gtin_8(self):
        """ Simulate scanning a product with his gs1 barcode """
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')

        product = self.env['product.product'].create({
            'name': 'PRO_GTIN_8',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        self.start_tour("/odoo/barcode", 'test_gs1_inventory_gtin_8', login='admin', timeout=180)

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
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '82655853',  # GTIN-8 format
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        self.start_tour("/odoo/barcode", 'test_gs1_inventory_product_units', login='admin', timeout=180)

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
            'is_storable': True,
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

        self.start_tour("/odoo/barcode", 'test_gs1_inventory_package', login='admin', timeout=180)

        pack_3 = self.env['stock.quant.package'].search([('name', '=', '122333444455555670')])
        self.assertEqual(pack_3.location_id.id, self.shelf2.id)
        self.assertEqual(pack_3.quant_ids.product_id.ids, [product.id])

    def test_gs1_inventory_lot_serial(self):
        """ Checks tracking numbers and quantites are correctly got from GS1
        barcodes for tracked products.
        Also, this test is an opportunity to ensure custom GS1 separators are used clientside."""
        self.env.ref('base.group_user').implied_ids += self.env.ref('stock.group_production_lot')
        self.clean_access_rights()
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.env.company.nomenclature_id.gs1_separator_fnc1 = r'(Alt029|#|\x1D|~)'

        product_lot = self.env['product.product'].create({
            'name': 'PRO_GTIN_12_lot',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '111155555717',  # GTIN-12 format
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'tracking': 'lot',
        })

        product_serial = self.env['product.product'].create({
            'name': 'PRO_GTIN_14_serial',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '15222222222219',  # GTIN-14 format
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'tracking': 'serial',
        })

        self.start_tour("/odoo/barcode", 'test_gs1_inventory_lot_serial', login='admin', timeout=180)

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
            'is_storable': True,
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
            }).id,
        })
        self.assertEqual(product.qty_available, 10)
        self.start_tour("/odoo", 'stock_barcode_package_with_lot', login="admin")

    def test_inventory_count_lot_split_in_packages(self):
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_barcode_count_entire_location = self.env.ref('stock_barcode.group_barcode_count_entire_location')
        self.env.user.write({'groups_id': [(4, grp_barcode_count_entire_location.id, 0), (4, grp_pack.id, 0), (4, grp_multi_loc.id, 0), (4, grp_lot.id, 0)]})
        shelf1 = self.env['stock.location'].create({
            'name': 'Shelf 11',
            'barcode': 'Shelf11',
            'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
        })
        product = self.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
            'tracking': 'lot',
        })
        lot = self.env['stock.lot'].create({
            'name': 'Lot-test',
            'product_id': product.id,
            })
        pack1 = self.env['stock.quant.package'].create({
                'name': 'Pack1',
            })
        pack2 = self.env['stock.quant.package'].create({
                'name': 'Pack2',
            })
        self.env['stock.quant']._update_available_quantity(product, shelf1, 5, lot_id=lot, package_id=pack1)
        self.env['stock.quant']._update_available_quantity(product, shelf1, 5, lot_id=lot, package_id=pack2)
        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_correct_inventory_with_packages', login="admin")
