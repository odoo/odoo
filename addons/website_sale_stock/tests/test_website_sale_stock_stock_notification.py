# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager

from lxml import html

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestStockNotificationProduct(WebsiteSaleStockCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.macbook = cls._create_product(name="Macbook Pro")

    def test_back_in_stock_notification_product(self):
        self.start_tour(self.macbook.website_url, 'website_sale_stock.subscribe_to_stock_notification')

        partner = self.env['mail.thread']._partner_find_from_emails_single(['test@test.test'], no_create=True)
        self.assertTrue(self.macbook._has_stock_notification(partner))

        with self.setup_cron_env() as env:
            env['product.product']._send_availability_email()

        emails = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)])
        self.assertEqual(len(emails), 0)

        self._add_product_qty_to_wh(self.macbook.id, 10.0, self.warehouse.lot_stock_id.id)

        website = self.env['website'].get_current_website()
        website.company_id.partner_id.email = "test@test.com"
        with self.setup_cron_env() as env:
            env['product.product']._send_availability_email()

        emails = self.env['mail.mail'].search([('email_to', '=', partner.email_formatted)])
        self.assertEqual(emails[0].subject, "Macbook Pro is back in stock")
        self.assertFalse(self.macbook._has_stock_notification(partner))

    def test_back_in_stock_notification_price_tax_included(self):
        self.macbook.stock_notification_partner_ids += self.partner
        self._add_product_qty_to_wh(self.macbook.id, 10.0, self.warehouse.lot_stock_id.id)
        website = self.env['website'].get_current_website()
        website.company_id.partner_id.email = "test@test.com"
        website.show_line_subtotals_tax_selection = "tax_included"
        with self.setup_cron_env() as env:
            env['product.product']._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', self.partner.email_formatted)])
        email_tree = html.fromstring(emails[0].body_html)
        price_span = email_tree.find('.//span[@class="oe_currency_value"]')
        self.assertEqual(price_span.text.strip(), "115.00")

    def test_back_in_stock_notification_variant_price(self):
        """The price shown in the back-in-stock email must be the price of the variant, extra price
        of its attribute values included."""
        size = self.env['product.attribute'].create({
            'name': "Size",
            'value_ids': [Command.create({'name': "S"}), Command.create({'name': "XL"})],
        })
        template = self.env['product.template'].create({
            'name': "Shirt",
            'list_price': 100.0,
            'taxes_id': False,
            'is_storable': True,
            'allow_out_of_stock_order': False,
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': size.id,
                    'value_ids': [Command.set(size.value_ids.ids)],
                }),
            ],
        })
        xl_ptav = template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.name == "XL",
        )
        xl_ptav.price_extra = 20.0
        xl_variant = template._get_variant_for_combination(xl_ptav)
        xl_variant.stock_notification_partner_ids += self.partner
        self._add_product_qty_to_wh(xl_variant.id, 10.0, self.warehouse.lot_stock_id.id)
        website = self.env['website'].get_current_website()
        website.company_id.partner_id.email = "test@test.com"
        with self.setup_cron_env() as env:
            env['product.product']._send_availability_email()
        emails = self.env['mail.mail'].search([('email_to', '=', self.partner.email_formatted)])
        email_tree = html.fromstring(emails[0].body_html)
        price_span = email_tree.find('.//span[@class="oe_currency_value"]')
        self.assertEqual(price_span.text.strip(), "120.00")

    @contextmanager
    def setup_cron_env(self):
        """Setup the `TestCursor` required to execute a cron job and ensures proper handling of the
        environment before and after the operation.

        Note: In `HttpCase`, `TransactionCase.enter_registry_test_mode` is enabled by default.
        """
        env = self.env
        env.flush_all()
        try:
            with self.registry.cursor() as cr:  # Creates a temporary `TestCursor`
                yield env(cr=cr)
        finally:
            env.invalidate_all()

    def test_partner_email_confirmation(self):
        """Partner receives email confirmation for a delivery if the setting is enabled."""
        self.company.stock_move_email_validation = True
        self.partner.email = 'test@example.com'
        new_so = self._create_so()
        new_so._validate_order()
        new_so.picking_ids.button_validate()
        self.assertTrue(
            any(partner.email == self.partner.email
            for partner in new_so.picking_ids.message_ids.notified_partner_ids
        ))
