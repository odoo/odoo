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
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')])
        eur_currency = self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'EUR')])

        self.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'rate': 0.5,
            'currency_id': usd_currency.id,
            'company_id': self.env.company.id,
        })

        eur_product_price = 100
        usd_converted_product_price = eur_currency._convert(eur_product_price, usd_currency, date=fields.Date.today())

        usd_product_price = 150

        eur_product = self.env['product.product'].create({
            'name': 'Product',
            'seller_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'min_qty': 1,
                    'price': eur_product_price,
                    'currency_id': eur_currency.id,
                }),
            ]
        })
        usd_product = self.env['product.product'].create({
            'name': 'Product',
            'seller_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'min_qty': 1,
                    'price': usd_product_price,
                    'currency_id': usd_currency.id,
                }),
            ]
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'currency_id': usd_currency.id,
        })
        self.assertNotEqual(eur_product.seller_ids[0].currency_id.id, purchase_order.currency_id.id)

        resp = self.url_open(
            url='/product/catalog/order_lines_info',
            data=json.dumps({
                'params': {
                    'child_field': 'order_line',
                    'order_id': purchase_order.id,
                    'product_ids': eur_product.ids + usd_product.ids,
                    'res_model': 'purchase.order'
                }
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        catalog_price_eur = resp.json()['result'][str(eur_product.id)]['price']
        self.assertEqual(catalog_price_eur, usd_converted_product_price)
        catalog_price_usd = resp.json()['result'][str(usd_product.id)]['price']
        self.assertEqual(catalog_price_usd, usd_product_price)

        # The prices are recalculated on product order line update
        resp = self.url_open(
            url='/product/catalog/update_order_line_info',
            data=json.dumps({
                'params': {
                    'child_field': 'order_line',
                    'order_id': purchase_order.id,
                    'product_id': eur_product.id,
                    'quantity': 1,
                    'res_model': 'purchase.order'
                }
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], usd_converted_product_price)

        resp = self.url_open(
            url='/product/catalog/update_order_line_info',
            data=json.dumps({
                'params': {
                    'child_field': 'order_line',
                    'order_id': purchase_order.id,
                    'product_id': usd_product.id,
                    'quantity': 1,
                    'res_model': 'purchase.order'
                }
            }),
            headers={'Content-Type': 'application/json'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['result'], usd_product_price)
