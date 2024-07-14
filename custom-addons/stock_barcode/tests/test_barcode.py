# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestBarcodeClientAction(HttpCase):
    def test_filter_picking_by_product_gs1(self):
        """ Checks if a product is searched with a complete GS1 barcode, the
        product data is correctly retrieved and the search operates only on the
        product's part of the GS1 barcode. Also, checks a product can still be
        searched by its raw barcode even if GS1 nomenclature is used.
        """
        Product = self.env['product.product']
        product_category_all = self.env.ref('product.product_category_all')
        # Creates three products.
        product1 = Product.create({
            'name': 'product1',
            'barcode': '01304510',
            'categ_id': product_category_all.id,
            'type': 'product',
        })
        product2 = Product.create({
            'name': 'product2',
            'barcode': '73411048',
            'categ_id': product_category_all.id,
            'type': 'product',
        })
        product3 = Product.create({
            'name': 'product3',
            'barcode': '00000073411048',  # Ambiguous with the product2 barcode.
            'categ_id': product_category_all.id,
            'type': 'product',
        })

        # Searches while using the default barcode nomenclature.
        product = Product.search([('barcode', '=', '01304510')])
        self.assertEqual(len(product), 1, "Product should be found when searching by its barcode")
        self.assertEqual(product.id, product1.id)
        product = Product.search([('barcode', '=', '0100000001304510')])
        self.assertEqual(len(product), 0, "Product shouldn't be found with GS1 barcode if GS1 nomenclature is inactive")

        # Searches while using the GS1 barcode nomenclature.
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        for operator in ['=', 'ilike']:
            product = Product.search([('barcode', operator, '01304510')])
            self.assertEqual(len(product), 1, "Product should still be found when searching by its raw barcode even if GS1 nomenclature is active")
            self.assertEqual(product.id, product1.id)
            product = Product.search([('barcode', operator, '300005\x1D0100000001304510')])
            self.assertEqual(len(product), 1, "Product should be found when scanning a GS1 barcode containing its data")
            self.assertEqual(product.id, product1.id)
            product = Product.search([('barcode', operator, '0100000001304510\x1Dt00.d4r|<')])
            self.assertEqual(len(product), 0, "No products should be found because of invalid GS1 barcode")
            product = Product.search([('barcode', operator, '0100000073411048')])
            self.assertEqual(len(product), 2, "Should found two products because of the ambiguity")
            self.assertEqual(product.ids, [product2.id, product3.id])

        # Checks search for all products except one from a GS1 barcode is workking as expected.
        for operator in ['!=', 'not ilike']:
            products = Product.search([('barcode', operator, '01304510')])
            self.assertFalse(product1 in products)
            self.assertTrue(product2 in products and product3 in products)
            products = Product.search([('barcode', operator, '300005\x1D0100000001304510')])
            self.assertFalse(product1 in products)
            self.assertTrue(product2 in products and product3 in products)
            products = Product.search([('barcode', operator, '00000073411048')])
            self.assertTrue(product1 in products)
            self.assertFalse(product2 in products, "product2 shouldn't be found due to unpadding of the barcode implied in the search")
            self.assertFalse(product3 in products)
            products = Product.search([('barcode', operator, '0100000073411048300005')])
            self.assertTrue(product1 in products)
            self.assertFalse(product2 in products or product3 in products)

    def test_filter_picking_by_package_gs1(self):
        grp_pack = self.env.ref('stock.group_tracking_lot')
        self.env.user.write({'groups_id': [(3, grp_pack.id)]})

        Package = self.env['stock.quant.package']
        # Creates three packages.
        package1 = Package.create({
            'name': '1234560000000018',
        })
        package2 = Package.create({
            'name': '7189085627231896',
        })
        package3 = Package.create({
            'name': '007189085627231896',  # Ambiguous with the package2 barcode.
        })

        # Searches while using the default barcode nomenclature.
        self.env.company.nomenclature_id = self.env.ref('barcodes.default_barcode_nomenclature')
        package = Package.search([('name', '=', '1234560000000018')])
        self.assertEqual(len(package), 1, "Package should be found when searching by its barcode")
        self.assertEqual(package.id, package1.id)
        package = Package.search([('name', '=', '00007189085627231896')])
        self.assertFalse(package, "Package shouldn't be found with GS1 barcode if GS1 nomenclature is inactive")

        # Searches while using the GS1 barcode nomenclature.
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        for operator in ['=', 'ilike']:
            package = Package.search([('name', operator, '1234560000000018')])
            self.assertEqual(len(package), 1, "Package should still be found when searching by its raw barcode even if GS1 nomenclature is active")
            self.assertEqual(package.id, package1.id)
            package = Package.search([('name', operator, '300005\x1D00001234560000000018')])
            self.assertEqual(len(package), 1, "Package should be found when scanning a GS1 barcode containing its data")
            self.assertEqual(package.id, package1.id)
            package = Package.search([('name', operator, '00007189085627231896\x1Dt00.d4r|<')])
            self.assertEqual(len(package), 0, "No package should be found because of invalid GS1 barcode")
            package = Package.search([('name', operator, '00007189085627231896')])
            self.assertEqual(len(package), 2, "Should found two packages because of the ambiguity")
            self.assertTrue(package.ids, (package2 | package3).ids)

        # Checks search for all packages except one from a GS1 barcode is workking as expected.
        for operator in ['!=', 'not ilike']:
            packages = Package.search([('name', operator, '1234560000000018')])
            self.assertFalse(package1 in packages)
            self.assertTrue(packages.ids, (package2 | package3).ids)
            packages = Package.search([('name', operator, '300005\x1D00001234560000000018')])
            self.assertFalse(package1 in packages)
            self.assertTrue(packages.ids, (package2 | package3).ids)
            packages = Package.search([('name', operator, '007189085627231896')])
            self.assertTrue(package1 in packages)
            self.assertFalse(package2 in packages, "package2 shouldn't be found due to unpadding of the barcode implied in the search")
            self.assertFalse(package3 in packages)
            package = Package.search([('name', operator, '00007189085627231896')])
            self.assertTrue(package1 in packages)
            self.assertFalse(package2 in packages or package3 in packages)

    def test_filter_picking_by_location_gs1(self):
        Location = self.env['stock.location']
        # Creates three locations.
        location1 = Location.create({
            'name': 'loc1',
            'barcode': '5055218716187',
        })
        location2 = Location.create({
            'name': 'loc2',
            'barcode': '614141000531',
        })
        location3 = Location.create({
            'name': 'loc3',
            'barcode': '0614141000531',  # Ambiguous with the package2 barcode.
        })

        # Searches while using the default barcode nomenclature.
        self.env.company.nomenclature_id = self.env.ref('barcodes.default_barcode_nomenclature')
        location = Location.search([('barcode', '=', '5055218716187')])
        self.assertEqual(len(location), 1, "Location should be found when searching by its barcode")
        self.assertEqual(location.id, location1.id)
        package = Location.search([('name', '=', '4100614141000531')])
        self.assertFalse(package, "Package shouldn't be found with GS1 barcode if GS1 nomenclature is inactive")

        # Searches while using the GS1 barcode nomenclature.
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        for operator in ['=', 'ilike']:
            location = Location.search([('barcode', operator, '5055218716187')])
            self.assertEqual(len(location), 1, "Location should still be found when searching by its raw barcode even if GS1 nomenclature is active")
            self.assertEqual(location.id, location1.id)
            location = Location.search([('barcode', operator, '300005\x1D4145055218716187')])
            self.assertEqual(len(location), 1, "Location should be found when scanning a GS1 barcode containing its data")
            self.assertEqual(location.id, location1.id)
            location = Location.search([('barcode', operator, '4100614141000531\x1Dt00.d4r|<')])
            self.assertEqual(len(location), 0, "No location should be found because of invalid GS1 barcode")
            location = Location.search([('barcode', operator, '4100614141000531')])
            self.assertEqual(len(location), 2, "Should found two locations because of the ambiguity")
            self.assertTrue(location.ids, (location2 | location3).ids)

        # Checks search for all locations except one from a GS1 barcode is workking as expected.
        for operator in ['!=', 'not ilike']:
            locations = Location.search([('barcode', operator, '5055218716187')])
            self.assertFalse(location1 in locations)
            self.assertTrue(location2.id in locations.ids and location3.id in locations.ids)
            locations = Location.search([('barcode', operator, '300005\x1D4145055218716187')])
            self.assertFalse(location1 in locations)
            self.assertTrue(location2.id in locations.ids and location3.id in locations.ids)
            locations = Location.search([('barcode', operator, '0614141000531')])
            self.assertTrue(location1 in locations)
            self.assertFalse(location2 in locations, "location2 shouldn't be found due to unpadding of the barcode implied in the search")
            self.assertFalse(location3 in locations)
            locations = Location.search([('barcode', operator, '4100614141000531')])
            self.assertTrue(location1 in locations)
            self.assertFalse(location2 in locations or location3 in locations)

    def test_searching_lot_gs1(self):
        """ Checks if a lot is searched with a complete GS1 barcode, the
        lot data is correctly retrieved and the search operates only on the
        lot's part of the GS1 barcode. Also, checks a lot can still be
        searched by its raw barcode even if GS1 nomenclature is used.
        """
        product = self.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'tracking': 'lot',
        })
        # create 2 lots
        lot1 = self.env['stock.lot'].create({
            'name': 'lot1',
            'product_id': product.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': 'lot2',
            'product_id': product.id,
            'company_id': self.env.company.id,
        })
        lot3 = self.env['stock.lot'].create({
            'name': '0000lot2',
            'product_id': product.id,
            'company_id': self.env.company.id,
        })


        # Searches while using the default barcode nomenclature.
        lot = self.env['stock.lot'].search([('name', '=', 'lot1')])
        self.assertEqual(len(lot), 1, "Lot should be found when searching by its barcode")
        self.assertEqual(lot.id, lot1.id)
        lot = self.env['stock.lot'].search([('name', '=', '01lot1')])
        self.assertEqual(len(lot), 0, "Lot shouldn't be found with GS1 barcode if GS1 nomenclature is inactive")

        # Searches while using the GS1 barcode nomenclature.
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        for operator in ['=', 'ilike']:
            lot = self.env['stock.lot'].search([('name', operator, '10lot1')])
            self.assertEqual(len(lot), 1, "Lot should still be found when searching by its raw barcode even if GS1 nomenclature is active")
            self.assertEqual(lot.id, lot1.id)
            lot = self.env['stock.lot'].search([('name', operator, '300005\x1D10lot1')])
            self.assertEqual(len(lot), 1, "Lot should be found when scanning a GS1 barcode containing its data")
            self.assertEqual(lot.id, lot1.id)
            lot = self.env['stock.lot'].search([('name', operator, '1000000010304510\x1Dt00.d4r|<')])
            self.assertEqual(len(lot), 0, "No lots should be found because of invalid GS1 barcode")
            lot = self.env['stock.lot'].search([('name', operator, '100000lot2')])
            self.assertEqual(len(lot), 1, "Should found only one lot because of the ambiguity")
            self.assertEqual(lot.ids, [lot3.id])

        # Checks search for all lots except one from a GS1 barcode is working as expected.
        for operator in ['!=', 'not ilike']:
            lots = self.env['stock.lot'].search([('name', operator, '10lot1')])
            self.assertFalse(lot1 in lots)
            self.assertTrue(lot2 in lots and lot3 in lots)
            lots = self.env['stock.lot'].search([('name', operator, '300005\x1D10000000lot1')])
            self.assertTrue(lot1 in lots and lot2 in lots and lot3 in lots, "Should found all lots because lot are not trimmed")
            lots = self.env['stock.lot'].search([('name', operator, 'lot2')])
            self.assertTrue(lot1 in lots)
            self.assertFalse(lot2 in lots, "lot2 shouldn't be found due to unpadding of the barcode implied in the search")
            lots = self.env['stock.lot'].search([('name', operator, '10lot2300005')])
            self.assertTrue(lot1 in lots and lot2 in lots, "Lot lenght is variable so we can't trim it")
