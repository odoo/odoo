# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestStockBarcodeController(HttpCase):

    def test_search_by_barcode_with_multiple_companies(self):
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Test Company'})
        self.env.ref('base.user_admin').company_ids = [(4, company_b.id)]

        products = [
            {'name': 'A1', 'barcode': 'abc1', 'company_id': False},
            {'name': 'A2', 'barcode': 'abc2', 'company_id': False},
            {'name': 'A3', 'barcode': 'abc3', 'company_id': company_a.id},
            {'name': 'A4', 'barcode': 'abc3', 'company_id': company_b.id},
        ]

        for product in products:
            self.env['product.product'].create(product)

        expected_responses = {
            company_a: [
                ('abc1', 'A1'),
                ('abc2', 'A2'),
                ('abc3', 'A3'),
            ],
            company_b: [
                ('abc1', 'A1'),
                ('abc2', 'A2'),
                ('abc3', 'A4'),
            ],
        }

        self.authenticate('admin', 'admin')
        for company, responses in expected_responses.items():
            for barcode, expected_display_name in responses:
                payload = json.dumps({
                    'jsonrpc': '2.0',
                    'method': 'call',
                    'id': 0,
                    'params': {
                        'barcode': barcode,
                        'domains_by_model': {},
                        'model_name': False,
                    },
                })
                self.env.ref('base.user_admin').company_id = company
                response = self.url_open(
                    '/stock_barcode/get_specific_barcode_data',
                    data=payload,
                    headers={'Content-Type': 'application/json'},
                )
                received_barcode = response.json()['result']['product.product'][0]['barcode']
                display_name = response.json()['result']['product.product'][0]['display_name']

                self.assertEqual(
                    barcode, received_barcode,
                    f"Expected barcode '{barcode}' for company '{company.name}' "
                    f"(id: {company.id}), but got '{received_barcode}' instead."
                )
                self.assertEqual(
                    display_name, expected_display_name,
                    f"Expected product '{expected_display_name}' for company '{company.name}' "
                    f"(id: {company.id}), but got '{display_name}' instead."
                )
