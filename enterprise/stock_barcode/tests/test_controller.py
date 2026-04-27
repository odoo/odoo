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
                        'domains_by_model': {'all': [['company_id', 'in', [False, company.id]]]},
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

    def test_search_barcode_for_package_type(self):
        self.authenticate('admin', 'admin')
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
            'params': {
                "barcodes_by_model": {
                    "stock.package.type": ["00000012345678"]
                },
                    "domains_by_model": {}
            }
        })
        response = self.url_open(
            '/stock_barcode/get_specific_barcode_data',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        self.assertNotIn("AttributeError", response.text)

    def test_barcode_with_uri_without_gs1_nomenclature(self):
        self.authenticate('admin', 'admin')
        barcode_value = "urn:epc:tag:sgtin-96 : 3.0614141.038656.0"
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
            'params': {
                "barcode": barcode_value,
            }
        })
        response = self.url_open(
            '/stock_barcode/scan_from_main_menu',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        result = response.json()
        self.assertIn("result", result)

    def test_barcode_with_uri_with_gs1_nomenclature(self):
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.authenticate('admin', 'admin')
        barcode_value = "urn:epc:tag:sgtin-96 : 3.0614141.038656.0"
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
            'params': {
                "barcode": barcode_value,
            }
        })
        response = self.url_open(
            '/stock_barcode/scan_from_main_menu',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        result = response.json()
        self.assertIn("result", result)

    def test_main_menu_returns_product_location_action(self):
        """Test that calling main_menu with a product barcode that does not respect
        the GS1 nomenclature does not block the flow. The GS1 parsing error is
        ignored and the standard main menu resolution logic continues, resulting
        in an action opening the product location view.
        """
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'barcode': '15099590483921',
        })
        self.env.company.nomenclature_id = self.env.ref('barcodes_gs1_nomenclature.default_gs1_nomenclature')
        self.authenticate('admin', 'admin')
        barcode_value = "15099590483921"
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
            'params': {
                "barcode": barcode_value,
            }
        })
        response = self.url_open(
            '/stock_barcode/scan_from_main_menu',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        result = response.json()['result']
        self.assertEqual(result['action']['res_model'], 'stock.quant')
        self.assertIn(['product_id', '=', product.id], result['action']['domain'])

    def test_barcode_with_weight_default_nomenclature(self):
        self.env.company.nomenclature_id = self.env.ref('barcodes.default_barcode_nomenclature')
        self.authenticate('admin', 'admin')
        product = self.env['product.product'].create({
            'name': 'Super product',
            'barcode': '2155555000000',
        })
        payload = json.dumps({
            'jsonrpc': '2.0',
            'method': 'call',
            'id': 0,
            'params': {
                "barcode": '2155555050005',
            }
        })
        response = self.url_open(
            '/stock_barcode/scan_from_main_menu',
            data=payload,
            headers={'Content-Type': 'application/json'},
        )
        result = response.json()['result']
        self.assertEqual(result['action']['res_model'], 'stock.quant')
        self.assertIn(['product_id', '=', product.id], result['action']['domain'])
