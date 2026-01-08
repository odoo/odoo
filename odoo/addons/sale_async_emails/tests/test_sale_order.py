# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.async_emails_cron = cls.env.ref('sale_async_emails.cron')
        cls.confirmation_email_template = cls.sale_order._get_confirmation_template()

    def test_order_status_email_is_sent_asynchronously(self):
        """ Test that the order status email is sent asynchronously when configured. """
        self.env['ir.config_parameter'].set_param('sale.async_emails', 'True')

        with patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._send_order_notification_mail'
        ) as sync_email_send_mock:
            self.sale_order._send_order_notification_mail(self.confirmation_email_template)
            self.assertTrue(
                self.sale_order.pending_email_template_id,
                msg="The email template should be saved on the sales order.",
            )
            self.assertTrue(
                self.env['ir.cron.trigger'].search_count(
                    [('cron_id', '=', self.async_emails_cron.id)]
                ),
                msg="The asynchronous email sending cron should be triggered.",
            )
            self.assertEqual(
                sync_email_send_mock.call_count,
                0,
                msg="The email should not also be sent synchronously.",
            )

    def test_order_status_email_is_sent_synchronously_if_not_configured(self):
        """ Test that the order status email is sent synchronously when nothing is configured. """
        self.env['ir.config_parameter'].set_param('sale.async_emails', 'False')

        with patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._send_order_notification_mail'
        ) as sync_email_send_mock:
            self.sale_order._send_order_notification_mail(self.confirmation_email_template)
            self.assertEqual(
                sync_email_send_mock.call_count,
                1,
                msg="The email should be sent synchronously when the system parameter is not set.",
            )

    def test_async_emails_cron_does_not_trigger_itself(self):
        """ Test that the asynchronous email sending cron does not enter an infinite loop. """
        self.env['ir.config_parameter'].set_param('sale.async_emails', 'True')
        self.sale_order.pending_email_template_id = self.confirmation_email_template

        with patch(
            'odoo.addons.sale.models.sale_order.SaleOrder._send_order_notification_mail'
        ) as sync_email_send_mock:
            self.env['sale.order']._cron_send_pending_emails(auto_commit=False)
            self.assertFalse(
                self.sale_order.pending_email_template_id,
                msg="The email template should be removed from the sales order.",
            )
            self.assertEqual(
                sync_email_send_mock.call_count,
                1,
                msg="The email should be sent synchronously when requested by the cron.",
            )
