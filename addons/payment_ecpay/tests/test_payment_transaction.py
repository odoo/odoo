from odoo.tests import tagged

from odoo.addons.payment_ecpay.tests.common import EcpayCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(EcpayCommon):
    def test_reference_uses_only_alphanumeric_chars(self):
        """The computed reference must be alphanumeric."""
        reference = self.env['payment.transaction']._compute_reference(provider_code='ecpay')
        self.assertTrue(reference)
        pattern = r'^[a-zA-Z0-9]+$'
        self.assertRegex(reference, pattern)

    def test_reference_length_is_atmost_20_chars(self):
        """The computed reference must be atmost 20 characters."""
        reference = self.env['payment.transaction']._compute_reference(provider_code='ecpay')
        self.assertTrue(len(reference) <= 20)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction('redirect')
        amount_data = tx._extract_amount_data(self.payment_result_data)
        self.assertDictEqual(
            amount_data, {'amount': self.amount, 'currency_code': self.currency_twd.name}
        )

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction('redirect', reference="S0000220251104095811")
        reference = self.env['payment.transaction']._extract_reference(
            'ecpay', self.payment_result_data
        )
        self.assertEqual(tx.reference, reference)

    def test_apply_updates_sets_payment_values(self):
        """Test that the transaction state is set to 'done' and TradeNo updated
        according to the payment data on successful payment."""
        tx = self._create_transaction('redirect')
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, self.payment_result_data['TradeNo'])
