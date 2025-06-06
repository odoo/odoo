from odoo import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestProductLabelLayout(ProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create additional UoM.
        cls.uom_pack_of_6, cls.uom_pack_of_24 = cls.env['uom.uom'].create([
            {
                'name': "Pack of 6",
                'relative_factor': 6,
                'relative_uom_id': cls.uom_unit.id,
            }, {
                'name': "Pack of 24",
                'relative_factor': 2,
                'relative_uom_id': cls.uom_dozen.id,
            },
        ])
        # Set a barcode for the product and create multiple
        cls.product.barcode = 'barcode_test_prod'
        cls.product_pack_of_6, cls.product_dozen = cls.env['product.uom'].create([
            {
                'barcode': 'barcode_test_prod_x6',
                'product_id': cls.product.id,
                'uom_id': cls.uom_pack_of_6.id,
            }, {
                'barcode': 'barcode_test_prod_x12',
                'product_id': cls.product.id,
                'uom_id': cls.uom_dozen.id,
            },
        ])
        cls.product.uom_ids = [
            Command.link(cls.uom_pack_of_6.id),
            Command.link(cls.uom_dozen.id),
        ]

    def _get_report_labels_data(self, products, report_data):
        # Convert the products ID into string, also in report data.
        str_product_ids = [str(id) for id in products.ids]
        data_by_product_id = report_data['data_by_product_id']
        data_by_product_str_id = {}
        for id, data in data_by_product_id.items():
            data_by_product_str_id[str(id)] = data
        report_data['data_by_product_id'] = data_by_product_str_id
        return self.env['report.product.report_producttemplatelabel2x7']._get_report_values(
            str_product_ids, report_data
        )

    def test_product_label_data(self):
        """ Ensure the data used by the product label reports are correctly computed."""
        wizard = self.env['product.label.layout'].create({
            'product_ids': [self.product.id],
            'custom_quantity': 4,
        })
        self.assertTrue(wizard.product_uom_ids == self.product.uom_ids == (self.uom_pack_of_6 | self.uom_dozen))

        # Check report data.
        _xml_id, report_data = wizard._prepare_report_data()
        product_data = report_data['data_by_product_id'].get(self.product.id)
        self.assertEqual(len(product_data), 1)
        self.assertDictEqual(product_data[0], {
            'barcode': self.product.barcode,
            'quantity': 4,
        })

        # Check report data when using an UoM.
        wizard.uom_id = self.uom_pack_of_6
        _xml_id, report_data = wizard._prepare_report_data()
        product_data = report_data['data_by_product_id'].get(self.product.id)
        self.assertEqual(len(product_data), 1)
        self.assertDictEqual(product_data[0], {
            'barcode': self.product_pack_of_6.barcode,
            'quantity': 4,
            'uom_id': self.uom_pack_of_6.id,
            'packaging_id': self.product_pack_of_6.id,
        })

        # Check that when selecting an UoM with no barcode for the product,
        # the result is the same than if no UoM was selected.
        wizard.uom_id = self.uom_pack_of_24
        _xml_id, report_data = wizard._prepare_report_data()
        product_data = report_data['data_by_product_id'].get(self.product.id)
        self.assertEqual(len(product_data), 1)
        self.assertDictEqual(product_data[0], {
            'barcode': self.product.barcode,
            'quantity': 4,
        })
        report_labels_data = self._get_report_labels_data(self.product, report_data)
        self.assertEqual(report_labels_data['page_numbers'], 1)
        self.assertEqual(len(report_labels_data['labels']), 1)
        self.assertEqual(len(report_labels_data['labels'][self.product]), 1)
        self.assertDictEqual(report_labels_data['labels'][self.product][0], {
            'barcode': self.product.barcode,
            'quantity': 4,
        })

    def test_product_label_data_for_multiple_products(self):
        """ Ensure the data used by the product label reports are correctly computed."""
        # Create a new product.
        product2 = self.env['product.product'].create({
            'name': "Test Product 2",
            'barcode': 'barcode_product2',
        })
        product2_dozen, product2_pack_of_24 = self.env['product.uom'].create([
            {
                'barcode': 'barcode_product2_x12',
                'product_id': product2.id,
                'uom_id': self.uom_dozen.id,
            }, {
                'barcode': 'barcode_product2_x24',
                'product_id': product2.id,
                'uom_id': self.uom_pack_of_24.id,
            },
        ])
        product2.uom_ids = [
            Command.link(self.uom_dozen.id),
            Command.link(self.uom_pack_of_24.id),
        ]

        # Check report data with UoM used by both products.
        wizard = self.env['product.label.layout'].create({
            'product_ids': [self.product.id, product2.id],
            'custom_quantity': 3,
            'uom_id': self.uom_dozen.id,
        })
        # Check all products' packaging related UoM are valid option for the wizard.
        self.assertTrue(wizard.product_uom_ids == (self.uom_pack_of_6 | self.uom_dozen | self.uom_pack_of_24))
        _xml_id, report_data = wizard._prepare_report_data()
        product1_data = report_data['data_by_product_id'].get(self.product.id)
        product2_data = report_data['data_by_product_id'].get(product2.id)
        self.assertEqual(len(product1_data), 1)
        self.assertDictEqual(product1_data[0], {
            'barcode': self.product_dozen.barcode,
            'quantity': 3,
            'uom_id': self.uom_dozen.id,
            'packaging_id': self.product_dozen.id,
        })
        self.assertEqual(len(product2_data), 1)
        self.assertDictEqual(product2_data[0], {
            'barcode': product2_dozen.barcode,
            'quantity': 3,
            'uom_id': self.uom_dozen.id,
            'packaging_id': product2_dozen.id,
        })
        report_labels_data = self._get_report_labels_data((self.product | product2), report_data)
        labels = report_labels_data['labels']
        self.assertEqual(report_labels_data['page_numbers'], 1)
        self.assertEqual(len(labels), 2)
        self.assertEqual(len(labels[self.product]), 1)
        self.assertDictEqual(labels[self.product][0], {
            'barcode': self.product_dozen.barcode,
            'quantity': 3,
            'uom': self.uom_dozen,
            'packaging': self.product_dozen,
        })
        self.assertEqual(len(labels[product2]), 1)
        self.assertDictEqual(labels[product2][0], {
            'barcode': product2_dozen.barcode,
            'quantity': 3,
            'uom': self.uom_dozen,
            'packaging': product2_dozen,
        })

        # Check report data with UoM used by one of the products but not by the other.
        wizard.uom_id = self.uom_pack_of_24
        _xml_id, report_data = wizard._prepare_report_data()
        product1_data = report_data['data_by_product_id'].get(self.product.id)
        product2_data = report_data['data_by_product_id'].get(product2.id)
        self.assertEqual(len(product1_data), 1)
        # No barcode for this product UoM -> Use the product's barcode instead.
        self.assertDictEqual(product1_data[0], {
            'barcode': self.product.barcode,
            'quantity': 3,
        })
        self.assertEqual(len(product2_data), 1)
        self.assertDictEqual(product2_data[0], {
            'barcode': product2_pack_of_24.barcode,
            'quantity': 3,
            'uom_id': self.uom_pack_of_24.id,
            'packaging_id': product2_pack_of_24.id,
        })
