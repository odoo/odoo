# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

from odoo.tests import tagged
from odoo.tests.common import HttpCase, new_test_user


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

        partner_ids = self.env['res.partner']._mail_find_partner_from_emails(['test@test.test'])
        partner = partner_ids[0]
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

    def test_multi_email_user_form_prefilled_with_first_address(self):
        """A contact may hold several addresses in its email field, but the client-side check of
        the back-in-stock form only accepts a single one."""
        user = new_test_user(
            self.env,
            login='multi_email',
            groups='base.group_portal',
            email='buyer@example.com,orders@example.com',
        )
        self.authenticate(user.login, user.login)
        response = self.url_open(self.product.website_url)
        user_email = html.fromstring(response.content).get_element_by_id('wsale_user_email').get('value')
        self.assertEqual(user_email, 'buyer@example.com')
