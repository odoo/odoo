# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.sale.tests.common import SaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleOrderEmailTemplate(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].create({
            'name': 'Test Website for Email Template',
        })
        cls.sale_order.website_id = cls.website.id

    def test_website_specific_confirmation_template_is_used(self):
        """Ensure _get_confirmation_template returns the website-specific template when set."""
        template = self.env['mail.template'].create({
            'name': "Website Custom Confirmation Template",
            'model_id': self.env.ref('sale.model_sale_order').id,
            'subject': "Website Confirmation",
            'body_html': '<p>Hello</p>',
        })
        self.website.confirmation_email_template_id = template
        with patch.object(self.env.registry['sale.order'], '_send_order_notification_mail') as mock:
            self.sale_order._send_order_confirmation_mail()
            mock.assert_called_once()
            returned_confirmation_template = mock.call_args[0][0]
            self.assertEqual(returned_confirmation_template, template)
