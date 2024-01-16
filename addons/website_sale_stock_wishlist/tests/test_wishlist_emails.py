# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale_stock.tests.test_website_sale_stock_product_warehouse import TestWebsiteSaleStockProductWarehouse
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWishlistEmail(TestWebsiteSaleStockProductWarehouse):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'John',
            'email': 'john@doe.com'
        })

        # Create the warehouse
        warehouse = cls.env['stock.warehouse'].create({
            'name': 'Wishlist Warehouse',
            'code': 'W_WH'
        })
        current_website = cls.env['website'].get_current_website()
        current_website.warehouse_id = warehouse

        cls.warehouse = warehouse
        cls.current_website = current_website

        # Create two stockable products
        cls.product_1 = cls.env['product.product'].create({
            'name': 'Product A',
            'allow_out_of_stock_order': False,
            'type': 'product',
            'default_code': 'E-COM1',
        })
        cls.product_2 = cls.env['product.product'].create({
            'name': 'Product B',
            'allow_out_of_stock_order': False,
            'type': 'product',
            'default_code': 'E-COM2',
        })

        # Pricelist and currency
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Public Pricelist',
        })
        cls.currency = cls.env.ref("base.USD")

    def test_send_availability_email(self):
        """
            For two products in a users wishlist, test that an email is sent
            when one is replenished
        """
        # Update quantity of Product A
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_1.id,
            'inventory_quantity': 10.0,
            'location_id': self.warehouse.lot_stock_id.id,
        })
        quants.action_apply_inventory()

        # Only sold out product B wishlist should be registered for
        # email notifications
        Wishlist = self.env['product.wishlist']

        wish_1 = Wishlist._add_to_wishlist(product_id=self.product_1.id, partner_id=self.partner.id, website_id=self.current_website.id, currency_id=self.currency.id, pricelist_id=self.pricelist.id, price=self.product_1.price)
        self.assertEqual(wish_1.stock_notification, False)
        wish_2 = Wishlist._add_to_wishlist(product_id=self.product_2.id, partner_id=self.partner.id, website_id=self.current_website.id, currency_id=self.currency.id, pricelist_id=self.pricelist.id, price=self.product_2.price)
        self.assertEqual(wish_2.stock_notification, True)

        # No email should be sent
        Wishlist._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', self.partner.email)])
        self.assertEqual(len(emails), 0)

        # Replenish Product B
        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_2.id,
            'inventory_quantity': 10.0,
            'location_id': self.warehouse.lot_stock_id.id,
        })
        quants.action_apply_inventory()

        # An email should be sent for Product B
        Wishlist._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', self.partner.email_formatted)])
        self.assertEqual(emails[0].subject, "The product 'Product B' is now available")
        self.assertEqual(wish_2.stock_notification, False)
