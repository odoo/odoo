# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.http import root
from odoo.tests import new_test_user, tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paypal.tests.common import PaypalCommon
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class PaypalMobileUITest(PaypalCommon, PaymentHttpCommon, WebsiteSaleCommon):
    browser_size = '375x667'
    touch_enabled = True
    allow_inherited_tests_method = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(cls.env, login="portalDude", groups="base.group_portal")
        cls.portal_user.write(cls.dummy_partner_address_values)

    def test_available_paypal_button(self):
        product = self.env['product.product'].create({'name': "$5", 'list_price': 5.0})
        so = self.env['sale.order'].create({
            'partner_id': self.portal_user.partner_id.id,
            'order_line': [Command.create({'product_id': product.id})],
            'website_id': self.env['website'].get_current_website().id,
        })

        portal_login = self.portal_user.login
        session = self.authenticate(portal_login, self.portal_user.password)
        session['sale_order_id'] = so.id
        root.session_store.save(session)

        self.start_tour('/shop/payment', 'test_paypal_mobile_available_button', login=portal_login)
