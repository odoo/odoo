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
        other_currency = self.setup_other_currency('HRK', rates=[(fields.Date.today(), 0.5)])

        other_product_price = 100
        company_product_price = 150
        other_product_price_converted = other_product_price / 0.5

        other_product = self.env['product.product'].create({
            'name': 'Other Product',
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
            'name': 'Company Product',
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
        catalog_price_other_cur = resp.json()['result'][str(other_product.id)]['price']
        self.assertEqual(catalog_price_other_cur, other_product_price_converted)
        catalog_price_company_cur = resp.json()['result'][str(company_product.id)]['price']
        self.assertEqual(catalog_price_company_cur, company_product_price)

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
        self.assertEqual(resp.json()['result'], other_product_price_converted)

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

    # === TOUR TESTS ===#
    def test_catalog_vendor_uom(self):
        """Check the product's UoM matches the one set on the vendor line."""
        # Enable units of measure and create two partners using different UoM.
        self._enable_uom()
        uom_liter = self.env.ref('uom.product_uom_litre')
        vendor_by_liter, vendor_by_unit = self.env['res.partner'].create([
            {'name': 'Vendor A (l)'},
            {'name': 'Vendor B (unit)'},
        ])
        # Create a product and configure some vendor's prices.
        self.env['product.template'].create({
            'name': "Crab Juice",
            'seller_ids': [
                Command.create({
                    'partner_id': vendor_by_liter.id,
                    'product_uom_id': uom_liter.id,
                    'price': 2,
                    'discount': 22.5
                }),
                Command.create({
                    'partner_id': vendor_by_unit.id,
                    'product_uom_id': self.uom_unit.id,
                    'price': 2.5,
                }),
                Command.create({
                    'partner_id': vendor_by_unit.id,
                    'product_uom_id': self.uom_unit.id,
                    'min_qty': 6,
                    'price': 2.45,
                }),
                Command.create({
                    'partner_id': vendor_by_unit.id,
                    'product_uom_id': self.uom_unit.id,
                    'min_qty': 12,
                    'price': 2.45,
                    'discount': 10.2,
                }),
            ],
        })
        # Create two PO and rename them to find them easily in the tour.
        purchase_orders = self.env['purchase.order'].create([{
            'partner_id': vendor.id
        } for vendor in (vendor_by_liter, vendor_by_unit)])
        purchase_orders[0].name = "PO/TEST/00001"
        purchase_orders[1].name = "PO/TEST/00002"
        self.start_tour('/odoo/purchase', 'test_catalog_vendor_uom', login='accountman')
