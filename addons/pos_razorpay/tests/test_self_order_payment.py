from hashlib import sha1
from itertools import count
from unittest.mock import patch
from uuid import uuid4

from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_razorpay.models.razorpay_pos_request import RazorpayPosRequest
from odoo.tests.common import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestRazorpaySelfOrderPayment(TestPointOfSaleHttpCommon):
    country_code = 'IN'
    chart_template = 'generic_coa'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.razorpay_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Razorpay',
            'payment_method_type': 'terminal',
            'payment_provider': 'razorpay',
            'razorpay_tid': 'my_tid',
            'razorpay_allowed_payment_modes': 'all',
            'razorpay_username': 'my_username',
            'razorpay_api_key': 'my_token',
            'razorpay_test_mode': True,
            'journal_id': cls.bank_journal.id,
            'type': 'bank',
        })
        cls.main_pos_config.write({
            'use_pricelist': False,
            'payment_method_ids': [Command.link(cls.razorpay_payment_method.id)],
        })

    def setUp(self):
        super().setUp()
        # Fake Razorpay server: like the real API, it authorizes a p2p request with the
        # reference it was requested for, whatever amount was charged.
        transactions = {}
        p2p_request_ids = count(1000)

        def fake_call_razorpay(request, endpoint, payload):
            if endpoint == 'pay':
                p2p_request_id = next(p2p_request_ids)
                transactions[p2p_request_id] = payload['externalRefNumber']
                return {'success': True, 'p2pRequestId': p2p_request_id}
            if endpoint == 'status':
                p2p_request_id = int(payload['origP2pRequestId'])
                return {
                    'success': True,
                    'status': 'AUTHORIZED',
                    'messageCode': 'P2P_DEVICE_TXN_DONE',
                    'p2pRequestId': p2p_request_id,
                    'externalRefNumber': transactions[p2p_request_id],
                }
            raise NotImplementedError(endpoint)

        self.startPatcher(patch.object(RazorpayPosRequest, '_call_razorpay', fake_call_razorpay))

    def _pay_on_terminal(self, order, charged_amount=None):
        """ Pay `order` on the terminal as the kiosk frontend does and return the payment values it sends. """
        amount = order['amount_total']
        reference_id = sha1(
            f"{self.main_pos_config.id}/{order['uuid']}/{self.razorpay_payment_method.id}/INR/{amount}/1".encode()
        ).hexdigest()
        response = self.razorpay_payment_method.razorpay_make_payment_request({
            'amount': charged_amount or amount,
            'referenceId': reference_id,
        })
        return {
            'amount': amount,
            'payment_method_id': self.razorpay_payment_method.id,
            'payment_ref_no': reference_id,
            'razorpay_p2p_request_id': response['p2pRequestId'],
            'razorpay_signature': response['signature'],
        }

    def _is_valid(self, order, payment):
        return self.razorpay_payment_method._is_valid_self_order_payment(self.main_pos_config, order, payment)

    def test_payment_of_the_order_is_valid(self):
        for amount in (100, 99.5):
            order = {'uuid': str(uuid4()), 'amount_total': amount}
            self.assertTrue(self._is_valid(order, self._pay_on_terminal(order)))

    def test_payment_of_another_order_is_rejected(self):
        cheap_order = {'uuid': str(uuid4()), 'amount_total': 1}
        expensive_order = {'uuid': str(uuid4()), 'amount_total': 5000}
        payment = self._pay_on_terminal(cheap_order)
        self.assertFalse(self._is_valid(expensive_order, {**payment, 'amount': 5000}))

    def test_lower_amount_charged_on_terminal_is_rejected(self):
        order = {'uuid': str(uuid4()), 'amount_total': 5000}
        self.assertFalse(self._is_valid(order, self._pay_on_terminal(order, charged_amount=1)))

    def test_missing_or_forged_signature_is_rejected(self):
        order = {'uuid': str(uuid4()), 'amount_total': 100}
        payment = self._pay_on_terminal(order)
        for signature in (None, '', 'forged', 42):
            self.assertFalse(self._is_valid(order, {**payment, 'razorpay_signature': signature}))

    def test_reused_transaction_is_rejected(self):
        order = {'uuid': str(uuid4()), 'amount_total': 100}
        payment = self._pay_on_terminal(order)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        pos_order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'amount_total': 100,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
        })
        pos_order.add_payment({
            'amount': 100,
            'payment_method_id': self.razorpay_payment_method.id,
            'pos_order_id': pos_order.id,
            'razorpay_p2p_request_id': payment['razorpay_p2p_request_id'],
        })
        self.assertFalse(self._is_valid(order, payment))
