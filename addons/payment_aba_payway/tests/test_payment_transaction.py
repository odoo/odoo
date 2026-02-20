from odoo.addons.payment_aba_payway.tests.common import AbaPaywayCommon

from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPaymentTransaction(AbaPaywayCommon):
    def test_reference_length_is_atmost_20_chars(self):
        """The computed reference must be atmost 20 characters."""
        reference = self.env['payment.transaction']._compute_reference(provider_code='aba_payway')
        self.assertTrue(len(reference) <= 20)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction('direct')
        amount_data = tx._extract_amount_data(self.enriched_payment_result_data)
        self.assertDictEqual(amount_data, {
            'amount': self.amount,
            'currency_code': self.currency_khr.name,
            'precision_digits': 0
        })

    def test_apply_updates_sets_payment_values(self):
        """ Test that the transaction state is set to 'done' and tran_id updated
        according to the payment data on successful payment. """
        tx = self._create_transaction('direct')
        tx._apply_updates(self.enriched_payment_result_data)
        self.assertEqual(tx.state, 'done')
        self.assertEqual(tx.provider_reference, self.payment_result_data['apv'])
