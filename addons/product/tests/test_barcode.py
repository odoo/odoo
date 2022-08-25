# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestProductBarcode(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['product.product'].create([
            {'name': 'BC1', 'barcode': '1'},
            {'name': 'BC2', 'barcode': '2'},
        ])

    def test_blank_barcodes_allowed(self):
        """Makes sure duplicated blank barcodes are allowed."""
        for i in range(2):
            self.env['product.product'].create({'name': f'BC_{i}'})

    def test_false_barcodes_allowed(self):
        """Makes sure duplicated False barcodes are allowed."""
        for i in range(2):
            self.env['product.product'].create({'name': f'BC_{i}', 'barcode': False})

    def test_duplicated_barcode(self):
        """Tests for simple duplication."""
        with self.assertRaises(ValidationError):
            self.env['product.product'].create({'name': 'BC3', 'barcode': '1'})

    def test_duplicated_barcode_in_batch_edit(self):
        """Tests for duplication in batch edits."""
        batch = [
            {'name': 'BC3', 'barcode': '3'},
            {'name': 'BC4', 'barcode': '4'},
        ]
        self.env['product.product'].create(batch)
        batch.append({'name': 'BC5', 'barcode': '1'})
        with self.assertRaises(ValidationError):
            self.env['product.product'].create(batch)

    def test_test_duplicated_barcode_error_msg_content(self):
        """Validates the error message shown when duplicated barcodes are found."""
        batch = [
            {'name': 'BC3', 'barcode': '3'},
            {'name': 'BC4', 'barcode': '3'},
            {'name': 'BC5', 'barcode': '4'},
            {'name': 'BC6', 'barcode': '4'},
            {'name': 'BC7', 'barcode': '1'},
        ]
        try:
            self.env['product.product'].create(batch)
        except ValidationError as exc:
            assert 'Barcode "3" already assigned to product(s): BC3, BC4' in exc.args[0]
            assert 'Barcode "4" already assigned to product(s): BC5, BC6' in exc.args[0]
            assert 'Barcode "1" already assigned to product(s): BC1' in exc.args[0]
