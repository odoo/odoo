# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal.tests.common import PaypalCommon


@tagged('post_install', '-at_install')
class TestPaypalButtons(PaypalCommon, PaymentHttpCommon):

    def test_paypal_buttons_rendered_on_mobile_checkout(self):
        """Check for the presence of the PayPal button on the shop checkout page in mobile."""
        if self.env['ir.module.module']._get('website_sale').state != 'installed':
            self.skipTest("This test requires the website_sale module to be installed.")

        user_admin = self.quick_ref('base.user_admin')
        user_admin.write({
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.quick_ref('base.us'),
            'state_id': self.env['ir.model.data']._xmlid_to_res_id('base.state_us_39'),
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })
        product = self.env['product.product'].create({'name': "$5", 'list_price': 5.0})
        self.env['sale.order'].create({
            'partner_id': user_admin.partner_id.id,
            'order_line': [Command.create({'product_id': product.id})],
            'website_id': self.env['website'].get_current_website().id,
        })

        self.browser_size = '375x667'
        self.touch_enabled = True
        self.start_tour(
            '/shop/payment', 'test_paypal_buttons_rendered_on_mobile_checkout', login='admin',
        )
