# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestProductNameSearch(TransactionCase):

    def _create_product(self, name, code, barcode=None):
        data = {
            'name': name,
            'default_code': code,
        }
        if barcode:
            data['barcode'] = barcode
        self.env['product.product'].create(data)

    def setUp(self):
        super().setUp()
        self._create_product(name='Batman', code='bruce_wayne')
        self._create_product(name='Superman', code='superman', barcode='SUPERMAN')
        self._create_product(name='Superman in black suit', code='superman_in_black', barcode='SUPERMAN_2.0')

    def test_10_search_exact_barcode(self):
        explanation = 'The search must return a single product if there is a perfect math on the barcode.'
        search = self.env['product.product']._name_search('SUPERMAN', operator='ilike')
        search = [id for id, _ in search]
        self.assertEqual(len(search), 1, explanation)
        self.assertEqual(self.env['product.product'].browse(search).default_code, 'superman', explanation)

    def test_20_search_exact_ref_when_limit(self):
        explanation = 'If limited, the search must at least return a product with a perfect match on the reference, if any.'
        search = self.env['product.product']._name_search('superman', limit=1, operator='ilike')
        search = [id for id, _ in search]
        self.assertEqual(len(search), 1, explanation)
        self.assertEqual(self.env['product.product'].browse(search).default_code, 'superman', explanation)

    def test_30_search_not_stopping_exact_ref(self):
        search = self.env['product.product']._name_search('superman', operator='ilike')
        self.assertEqual(len(search), 2,
            'The search should not be stopped if it found a perfect match on the reference.')

    def test_40_search_name_and_ref(self):
        search = self.env['product.product']._name_search('man', operator='ilike')
        self.assertEqual(len(search), 3,
            'The search should be done both on the reference and on the default_code.')
