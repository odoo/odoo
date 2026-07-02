# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestStockNotificationProduct(WebsiteSaleStockCommon, HttpCase):
    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.macbook = cls._create_product(name="Macbook Pro")

    def test_back_in_stock_notification_product(self):
        self.start_tour(
            self.macbook.website_url, "website_sale_stock.subscribe_to_stock_notification"
        )

        partner = self.env["mail.thread"]._partner_find_from_emails_single(
            ["test@test.test"], no_create=True
        )
        self.assertTrue(self.macbook._has_stock_notification(partner))

        with self.setup_cron_env() as env:
            env["product.product"]._send_availability_email()

        emails = self.env["mail.mail"].search([("email_to", "=", partner.email_formatted)])
        self.assertEqual(len(emails), 0)

        self._add_product_qty_to_wh(self.macbook.id, 10.0, self.warehouse.lot_stock_id.id)

        self.env.ref('base.default_website').company_id.partner_id.email = "test@test.com"
        with self.setup_cron_env() as env:
            env["product.product"]._send_availability_email()

        emails = self.env["mail.mail"].search([("email_to", "=", partner.email_formatted)])
        self.assertEqual(emails[0].subject, "Macbook Pro is back in stock")
        self.assertFalse(self.macbook._has_stock_notification(partner))

    @contextmanager
    def setup_cron_env(self):
        """Set up the `TestCursor` required to execute a cron job and ensures proper handling of the
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
