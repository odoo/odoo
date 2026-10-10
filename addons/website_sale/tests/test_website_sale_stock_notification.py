from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockNotification(WebsiteSaleCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
    )

    _test_user_name = 'Test Sales & Product Manager'

    def test_send_availability_email_multiple_partners(self):
        self.product.sudo().write({
            "is_storable": True,
            "allow_out_of_stock_order": False,
            "qty_available": 1,
        })

        notifications = self.env["product.stock.notification"].sudo().create([
            {
                "product_id": self.product.id,
                "partner_id": self.partner.id,
                "website_id": self.website.id,
            },
            {
                "product_id": self.product.id,
                "partner_id": self.public_partner.id,
                "website_id": self.website.id,
            },
        ])

        emails_before_cron = self.env["mail.mail"].sudo().search([])
        with patch.object(self.env.registry["ir.cron"], "_commit_progress"):
            self.env["product.product"].sudo()._send_availability_email()

        self.assertFalse(notifications.exists())

        emails = self.env["mail.mail"].sudo().search([
            ("email_to", "in", [
                self.partner.email_formatted,
                self.public_partner.email_formatted,
            ]),
            ("subject", "=", "Test Product is back in stock"),
        ])

        self.assertNotIn(emails, emails_before_cron)
        self.assertEqual(len(emails), 2)
