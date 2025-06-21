# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestStockNotificationProduct(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        warehouse = cls.env['stock.warehouse'].create({
            'name': 'Wishlist Warehouse',
            'code': 'W_WH'
        })
        cls.warehouse = warehouse

        cls.website = cls.env['website'].get_current_website()
        cls.website.write({
            'company_id': cls.env.company.id,
            'warehouse_id': cls.warehouse.id,
            'show_line_subtotals_tax_selection': 'tax_excluded',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Macbook Pro',
            'website_published': True,
            'type': 'product',
            'list_price': 100.0,
            'taxes_id': [c['default_tax_sale'].id for c in (cls.company_data, cls.company_data_2)],
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

        ProductProduct._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)])
        self.assertEqual(emails[0].subject, "The product 'Macbook Pro' is now available")
        self.assertFalse(product._has_stock_notification(partner))

    def test_availability_email_price_display(self):
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 10.0,
            'location_id': self.warehouse.lot_stock_id.id,
        }).action_apply_inventory()

        partner = self.env.user.partner_id
        self.product.stock_notification_partner_ids = partner
        self.product._send_availability_email()
        email = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)], limit=1)
        self.assertIn(
            "$ 100.00", email.body_html,
            "Price should be tax-excluded if website displays prices tax-excluded",
        )
        email.sudo().unlink()

        self.product.stock_notification_partner_ids = partner
        self.website.show_line_subtotals_tax_selection = 'tax_included'
        self.product._send_availability_email()
        email = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)], limit=1)
        self.assertIn(
            "$ 115.00", email.body_html,
            "Price should be tax-included if website displays prices tax-included",
        )
