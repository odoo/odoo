# Copyright 2019 VentorTech OU
# Part of Ventor modules. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestMerpProductBarcodeMulti(TransactionCase):

    def setUp(self):
        super(TestMerpProductBarcodeMulti, self).setUp()
        self.product_1 = self.env['product.template'].create({
            'name': 'product_1',
            'barcode': 'test003',
            'barcode_ids': [(0, 0, {'name': 'test001'})]
        })
        self.product_2 = self.env['product.template'].create({
            'name': 'product_2',
            'barcode_ids': [(0, 0, {'name': 'test002'})]
        })
        self.product_3 = self.env['product.product'].create({
            'name': 'product_2',
            'barcode_ids': [(0, 0, {'name': 'test004'})]
        })

        ctx = self.env.context.copy()
        ctx.update({
            'active_model': 'product.product',
            'active_id': self.product_3.id,
        })
        self.env.context = ctx

    def test_search_by_barcode_multi_product_1(self):
        results = self.env['product.product']._name_search('test001')
        for res in results:
            self.assertEqual(res[1], 'product_1')

    def test_search_by_barcode_product_1(self):
        results = self.env['product.product']._name_search('test003')
        for res in results:
            self.assertEqual(res[1], 'product_1')

    def test_search_by_barcode_multi_product_2(self):
        results = self.env['product.product']._name_search('test002')
        for res in results:
            self.assertEqual(res[1], 'product_2')

    def test_update_barcode_wizard(self):
        product = self.product_3

        old_barcode = product.barcode
        new_barcode = 'test007'

        self.env['multiply.barcode.wizard'].create({
            'name': new_barcode,
            'remember_previous_barcode': True,
        }).update_barcode()

        self.assertNotEqual(old_barcode, product.barcode)
        self.assertEqual(new_barcode, product.barcode)
