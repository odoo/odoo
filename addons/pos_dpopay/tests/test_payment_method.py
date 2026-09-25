# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import Mock, patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestPosDpoPayPaymentMethod(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        common_field = {
            'use_payment_terminal': 'dpopay',
            'dpopay_test_mode': True,
            'dpopay_mid': '123456789012',
            'dpopay_tid': 'TESTTID',
        }
        cls.payment_methods = cls.env['pos.payment.method'].create([
            {
                'name': 'DPO Pay Card',
                'dpopay_payment_mode': 'card',
                **common_field,
            },
            {
                'name': 'DPO Pay Mobile Money',
                'dpopay_payment_mode': 'momo',
                **common_field,
            },
        ])

    def _mock_post(self, url, json=None, **kwargs):
        self.payload = json
        response = Mock()
        response.json.return_value = {'resultCode': '0'}
        return response

    def test_send_dpopay_request_sets_transaction_type(self):
        with patch('odoo.addons.pos_dpopay.models.pos_payment_method.requests.post', self._mock_post):
            for payment_method, transaction_type in zip(self.payment_methods, ('pushPaymentSale', 'pushPaymentDpoMomoSale')):
                payment_method.send_dpopay_request({'amount': 100}, 'start-transaction')
                self.assertEqual(self.payload['transactionType'], transaction_type)
