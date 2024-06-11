# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestStockNotificationWishlist(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Warehouse = cls.env['stock.warehouse']
        Product = cls.env['product.product']
        Pricelist = cls.env['product.pricelist']
        Wishlist = cls.env['product.wishlist']
        Partner = cls.env['res.partner']

        warehouse = Warehouse.create({
            'name': 'Wishlist Warehouse',
            'code': 'W_WH'
        })
        current_website = cls.env['website'].get_current_website()
        current_website.warehouse_id = warehouse

        cls.warehouse = warehouse
        cls.current_website = current_website

        cls.product = Product.create({
            'name': 'Macbook Pro',
            'website_published': True,
            'type': 'product',
            'allow_out_of_stock_order': False,

        })
        cls.pricelist = Pricelist.create({
            'name': 'Public Pricelist',
        })
        cls.currency = cls.env.ref("base.USD")
        cls.partner = Partner.search([('id', '=', 3)])
        Wishlist.create({
            'partner_id': cls.partner.id,
            'product_id': cls.product.id,
            'website_id': current_website.id,
            'pricelist_id': cls.pricelist.id
        })

    def test_stock_notification_wishlist(self):
        self.start_tour("/", 'stock_notification_wishlist', login='admin')

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

        ProductProduct._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)])
        self.assertEqual(emails[0].subject, "The product 'Macbook Pro' is now available")
        self.assertFalse(product._has_stock_notification(partner))
