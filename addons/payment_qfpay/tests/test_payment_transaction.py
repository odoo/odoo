# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.payment_qfpay.tests.common import QFPayCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(QFPayCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mock payload from QFPay
        cls.payment_result_data = {
            'out_trade_no': cls.reference,
            'txamt': str(int(cls.amount * 100)),
            'txcurrcd': cls.currency.name,
            'respcd': '0000',
            'respmsg': 'Success',
        }

    def test_reference_uses_only_alphanumeric_chars(self):
        """The computed reference must be made of alphanumeric characters and '-' or '_'."""
        reference = self.env['payment.transaction']._compute_reference('qfpay')
        self.assertRegex(reference, r'^[a-zA-Z0-9_-]+$')

    def test_reference_length_is_between_6_and_64_chars(self):
        """The computed reference must be between 6 and 64 characters."""
        reference = self.env['payment.transaction']._compute_reference('qfpay')
        self.assertTrue(6 <= len(reference) <= 64)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction('direct')
        reference = self.env['payment.transaction']._extract_reference(
            'qfpay', self.payment_result_data
        )
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are correctly extracted and converted."""
        tx = self._create_transaction('direct')
        amount_data = tx._extract_amount_data(self.payment_result_data)
        self.assertDictEqual(
            amount_data,
            {'amount': self.amount, 'currency_code': self.currency.name}
        )

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' for successful payment."""
        tx = self._create_transaction('direct')
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.state, 'done')
