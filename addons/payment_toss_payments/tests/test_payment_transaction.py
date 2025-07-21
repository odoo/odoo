from odoo.tests import tagged

from odoo.addons.payment_toss_payments.tests.common import TossPaymentsCommon


@tagged('post_install', '-at_install')
class TestPaymentTransaction(TossPaymentsCommon):
    def test_reference_uses_only_alphanumeric_chars(self):
        """The computed reference must be made of alphanumeric and symbols '-' and '_'."""
        reference = self.env['payment.transaction']._compute_reference('toss_payments')
        self.assertRegex(reference, r'^[a-zA-Z0-9_-]+$')

    def test_reference_length_is_between_6_and_64_chars(self):
        """The computed reference must be between 6 and 64 characters, both numbers inclusive."""
        reference = self.env['payment.transaction']._compute_reference('toss_payments')
        self.assertTrue(6 <= len(reference) <= 64)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction('direct')
        reference = self.env['payment.transaction']._extract_reference(
            'toss_payments', self.payment_result_data
        )
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction('direct')
        amount_data = tx._extract_amount_data(self.payment_result_data)
        self.assertDictEqual(
            amount_data, {'amount': self.amount, 'currency_code': self.currency_krw.name}
        )

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is set when processing the payment data."""
        tx = self._create_transaction('direct')
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.provider_reference, self.payment_result_data['paymentKey'])

    def test_apply_updates_sets_payment_secret(self):
        """Test that the payment secret is set when processing the payment data."""
        tx = self._create_transaction('direct')
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.toss_payments_payment_secret, self.payment_result_data['secret'])

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction('direct')
        tx._apply_updates(self.payment_result_data)
        self.assertEqual(tx.state, 'done')
