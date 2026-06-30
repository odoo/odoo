# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_redsys.tests.common import RedsysCommon

from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPaymentTransaction(RedsysCommon):

    def test_reference_uses_only_alphanumeric_chars(self):
        """The computed reference must be made of alphanumeric characters."""
        reference = self.env['payment.transaction']._compute_reference(provider_code='redsys')
        self.assertTrue(reference.isalnum())

    def test_reference_length_is_between_9_and_12_chars(self):
        """The computed reference must be between 9 and 12 characters."""
        reference = self.env['payment.transaction']._compute_reference(provider_code='redsys')
        self.assertTrue(9 <= len(reference) <= 12)

    def test_no_item_missing_from_merchant_parameters(self):
        """Test that all important items are present in the merchant parameters."""
        tx = self._create_transaction(flow='redirect')
        merchant_parameters = tx._redsys_prepare_merchant_parameters()
        converted_amount = payment_utils.to_minor_currency_units(tx.amount, tx.currency_id)
        self.assertEqual(merchant_parameters['DS_MERCHANT_AMOUNT'], str(converted_amount))
        self.assertEqual(merchant_parameters['DS_MERCHANT_CURRENCY'], tx.currency_id.iso_numeric)
        self.assertEqual(merchant_parameters['DS_MERCHANT_ORDER'], tx.reference)
        self.assertEqual(merchant_parameters['DS_MERCHANT_PAYMETHODS'], 'C')  # credit card
        self.assertTrue('DS_MERCHANT_EMV3DS' in merchant_parameters)

    def test_search_by_reference_returns_tx(self):
        """Test that the transaction is returned from the payment data."""
        tx = self._create_transaction('redirect')
        self.assertEqual(tx, self.env['payment.transaction']._search_by_reference(
            'redsys', self.merchant_parameters
        ))

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction('redirect')
        amount_data = tx._extract_amount_data(self.merchant_parameters)
        self.assertDictEqual(amount_data, {
            'amount': self.amount,
            'currency_code': self.currency_euro.name,
        })

    def test_apply_updates_sets_payment_method(self):
        """Test that the payment method is updated according to the brand."""
        tx = self._create_transaction('redirect')
        tx._apply_updates(self.merchant_parameters)
        self.assertEqual(tx.payment_method_id, self.env.ref('payment.payment_method_visa'))

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction('redirect')
        tx._apply_updates(self.merchant_parameters)
        self.assertEqual(tx.state, 'done')
