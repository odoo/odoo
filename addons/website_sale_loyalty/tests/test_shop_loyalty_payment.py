# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged('post_install', '-at_install')
class TestShopLoyaltyTransaction(PaymentHttpCommon, TestSaleCouponCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website = cls.env.company.website_id
        if not cls.website:
            cls.website = cls.env.ref('website.default_website')
            cls.website.company_id = cls.env.company

    @mute_logger('odoo.http')
    def test_expired_reward_validation(self):
        """Ensure payments don't process if any applied reward is no longer valid."""
        order = self.empty_order
        program = self.program_gift_card

        program.date_to = date.today()  # set program to expire after today
        self.product_a.type = 'service'  # prevent need for delivery method

        self.env['loyalty.generate.wizard'].with_context(active_id=program.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()

        order.write({
            'partner_id': self.portal_partner.id,
            'website_id': self.website.id,
            'message_partner_ids': self.portal_partner.ids,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
            })],
        })
        self._apply_promo_code(order, program.coupon_ids.code)

        with freeze_time(program.date_to + timedelta(days=1)):
            self.authenticate(self.portal_user.login, self.portal_user.login)
            tx_response = self._make_json_rpc_request(
                self._build_url(f'/shop/payment/transaction/{order.id}'),
                {
                    'order_id': order.id,
                    'access_token': None,
                    'amount': order.amount_total,
                    'currency_id': order.currency_id.id,
                    'payment_option_id': self.provider.id,
                    'flow': 'direct',
                    'tokenization_requested': False,
                    'landing_route': order.get_portal_url(),
                },
            ).json()

        self.assertIn(
            'error',
            tx_response,
            "Attempting to initate payment with an expired reward should raise an error.",
        )
        self.assertEqual(
            tx_response['error']['data']['message'],
            "Cannot process payment: applied reward was changed or has expired.",
        )
