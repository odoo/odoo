from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import HttpCase, tagged

import json


@tagged('-at_install', 'post_install')
class TestPurchaseProductCatalog(AccountTestInvoicingCommon, HttpCase):

    def test_catalog_price(self):
        """
        Products having a SupplierInfo record in a foreign currency should have their price
        converted in the product catalog
        When it's the same currency, the price shouldn't be changed
        """
        self.authenticate(self.env.user.login, self.env.user.login)
        company_currency = self.env.company.currency_id
        other_currency = self.setup_other_currency('HRK')

        self.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'rate': 0.5,
            'currency_id': company_currency.id,
            'company_id': self.env.company.id,
        })

        other_product_price = 100
        company_converted_product_price = other_currency._convert(other_product_price, company_currency, date=fields.Date.today())

        company_product_price = 150

        other_product = self.env['product.product'].create({
            'name': 'Product',
            'seller_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'min_qty': 1,
                    'price': other_product_price,
                    'currency_id': other_currency.id,
                }),
            ]
        })
        company_product = self.env['product.product'].create({
            'name': 'Product',
            'seller_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'min_qty': 1,
                    'price': company_product_price,
                    'currency_id': company_currency.id,
                }),
            ]
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': company_currency.id,
        })
        self.assertNotEqual(other_product.seller_ids[0].currency_id.id, purchase_order.currency_id.id)

        resp = self.url_open(
            url='/product/catalog/order_lines_info',
            data=json.dumps({
                'params': {
                    'child_field': 'order_line',
                    'order_id': purchase_order.id,
                    'product_ids': other_product.ids + company_product.ids,
                    'res_model': 'purchase.order'
                }
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        catalog_price_eur = resp.json()['result'][str(other_product.id)]['price']
        self.assertEqual(catalog_price_eur, company_converted_product_price)
        catalog_price_usd = resp.json()['result'][str(company_product.id)]['price']
        self.assertEqual(catalog_price_usd, company_product_price)

        # The prices are recalculated on product order line update
        resp = self.url_open(
            url='/product/catalog/update_order_line_info',
            data=json.dumps({
                'params': {
                    'child_field': 'order_line',
                    'order_id': purchase_order.id,
                    'product_id': other_product.id,
                    'quantity': 1,
                    'res_model': 'purchase.order'
                }
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], company_converted_product_price)

        resp = self.url_open(
            url='/product/catalog/update_order_line_info',
            data=json.dumps({
                'params': {
                    'child_field': 'order_line',
                    'order_id': purchase_order.id,
                    'product_id': company_product.id,
                    'quantity': 1,
                    'res_model': 'purchase.order'
                }
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], company_product_price)
