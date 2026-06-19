# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestStockNotificationProduct(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        warehouse = cls.env['stock.warehouse'].create({
            'name': 'Wishlist Warehouse',
            'code': 'W_WH'
        })
        current_website = cls.env['website'].get_current_website()
        current_website.warehouse_id = warehouse

        cls.warehouse = warehouse
        cls.current_website = current_website

        cls.product = cls.env['product.product'].create({
            'name': 'Macbook Pro',
            'website_published': True,
            'is_storable': True,
            'allow_out_of_stock_order': False,

        })
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Public Pricelist',
        })
        cls.currency = cls.env.ref("base.USD")

    def test_back_in_stock_notification_product(self):
        self.start_tour("/", 'back_in_stock_notification_product')

        partner = self.env['mail.thread']._partner_find_from_emails_single(['test@test.test'], no_create=True)
        ProductProduct = self.env['product.product']
        product = ProductProduct.browse(self.product.id)
        self.assertTrue(product._has_stock_notification(partner))

        # No email should be sent
        ProductProduct._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)])
        self.assertEqual(len(emails), 0)

        # Replenish Product
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 10.0,
            'location_id': self.warehouse.lot_stock_id.id,
        })
        quants.action_apply_inventory()

        website = self.env['website'].get_current_website()
        website.company_id.partner_id.email = "test@test.com"

        ProductProduct._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)])
        self.assertEqual(emails[0].subject, "The product 'Macbook Pro' is now available")
        self.assertEqual(emails[0].email_from, website.company_id.partner_id.email_formatted)
        self.assertFalse(product._has_stock_notification(partner))

    def _call_stock_notification(self, email, product_id):
        """Helper to make a proper JSON-RPC request to the endpoint."""
        payload = {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': {
                'email': email,
                'product_id': product_id,
            },
            'id': 1,
        }
        return self.url_open(
            '/shop/add/stock_notification',
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )

    def test_01_public_user_rate_limit(self):
        """Test public user cannot subscribe to more than 5 unique products per session."""
        products = self.env['product.product']
        for i in range(6):
            prod = self.env['product.product'].create({
                'name': f'Test rate limit {i}',
                'website_published': True,
                'list_price': 10.0,
                'is_storable': True,
            })
            products |= prod

        for i in range(5):
            self._call_stock_notification(f'rate{i}@test.com', products[i].id)
            
        for i in range(5):
            self.assertEqual(len(products[i].stock_notification_partner_ids), 1, 
                             f"Product {i} should have 1 notification partner")

        # 6th request should fail due to rate limit
        response = self._call_stock_notification('rate5@test.com', products[5].id)
        json_resp = response.json()
        
        self.assertEqual(len(products[5].stock_notification_partner_ids), 0, 
                         "6th product should not have any notification partners")
        
        # assert for expected error
        self.assertIn('error', json_resp, "6th request should fail with an error")
        self.assertIn('maximum number', json_resp['error']['data']['message'].lower())

    def test_02_duplicate_subscription_blocked(self):
        """Test public user cannot subscribe twice to the same product in the same session."""
        product = self.env['product.product'].create({
            'name': 'Test duplicate',
            'website_published': True,
            'list_price': 10.0,
            'is_storable': True,
        })

        self._call_stock_notification('dup@test.com', product.id)

        self.assertEqual(len(product.stock_notification_partner_ids), 1)

        # Second subscription to the same product fails
        response2 = self._call_stock_notification('dup@test.com', product.id)
        json_resp = response2.json()
        
        self.assertEqual(len(product.stock_notification_partner_ids), 1, 
                         "Duplicate subscription should not create a second partner link")

        self.assertIn('error', json_resp, "Duplicate subscription should be blocked")
        self.assertIn('already subscribed', json_resp['error']['data']['message'].lower())