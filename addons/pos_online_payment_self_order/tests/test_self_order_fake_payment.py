import odoo.tests
from odoo import Command
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.pos_online_payment_self_order.tests.test_self_order_mobile import (
    TestSelfOrderMobile,
)


class SelfOrderFakePaymentCommon:

    def _create_draft_online_order(self, source, **order_values):
        if source == 'mobile':
            self.pos_config.write({
                'self_ordering_mode': 'mobile',
                'self_ordering_pay_after': 'each',
                'self_ordering_service_mode': 'table',
                'self_order_online_payment_method_id': self.online_payment_method.id,
            })
        else:
            self.pos_config.write({
                'self_ordering_mode': 'kiosk',
                'self_ordering_service_mode': 'counter',
                'payment_method_ids': [Command.set(self.online_payment_method.ids)],
            })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        return self.process_self_order(
            [{'product': self.cola}], preset=self.out_preset, **order_values,
        )


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFakePayment(SelfOrderFakePaymentCommon, TestSelfOrderMobile):

    _test_user_groups = None  # FIXME list needed groups

    def test_online_payment_mobile(self):
        order = self._create_draft_online_order('mobile')
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
        self.assertEqual(order.state, 'paid')

    def test_online_payment_mobile_no_confirmation_page(self):
        self._disable_post_process_patcher()
        order = self._create_draft_online_order('mobile')
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=False)
        self.assertEqual(order.state, 'paid')

    def test_online_payment_kiosk(self):
        order = self._create_draft_online_order('kiosk')
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=True)
        self.assertEqual(order.state, 'paid')

    def test_online_payment_kiosk_no_confirmation_page(self):
        self._disable_post_process_patcher()
        order = self._create_draft_online_order('kiosk')
        self.assertEqual(order.state, 'draft')

        self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/", confirmation_page=False)
        self.assertEqual(order.state, 'paid')


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFakePaymentMail(SelfOrderFakePaymentCommon, MailCase, TestSelfOrderMobile):
    _test_user_groups = None  # FIXME list needed groups

    def test_online_payment_mobile_sends_mail_after_payment(self):
        self.out_preset.mail_template_id = self.env.ref('pos_self_order.takeout_email_template')
        order = self._create_draft_online_order('mobile', email='after.payment.self.order@test.com')

        with self.mock_mail_gateway():
            self.assertEqual(len(self._new_mails), 0)
            self._fake_online_payment(
                order.id,
                order.access_token,
                self.payment_provider.id,
                exit_route="/",
                confirmation_page=True,
            )
            order = self.env['pos.order'].browse(order.id)

        self.assertEqual(order.state, 'paid')
        self.assertEqual(len(self._new_mails), 1)
        self.assertEqual(self._new_mails.email_to, order.email)
        self.assertIn('receipt', (self._new_mails.subject or '').lower())
