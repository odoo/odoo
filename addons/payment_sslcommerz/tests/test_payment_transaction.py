# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import urls

from odoo.addons.payment_sslcommerz import const
from odoo.addons.payment_sslcommerz.tests.common import SSLCommerzCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(SSLCommerzCommon):
    def test_no_item_missing_from_prepared_payload(self):
        """Test that no expected item is missing from the payload sent to SSLCOMMERZ."""
        payment_method = self.env.ref("payment_sslcommerz.payment_method_card")
        tx = self._create_transaction("redirect", payment_method_id=payment_method.id)
        base_url = tx.provider_id.get_base_url()
        return_url = urls.urljoin(base_url, const.PAYMENT_RETURN_ROUTE)
        expected_payload = {
            "store_id": tx.provider_id.sslcommerz_store_id,
            "store_passwd": tx.provider_id.sslcommerz_store_passwd,
            "total_amount": tx.amount,
            "currency": tx.currency_id.name,
            "tran_id": tx.reference,
            "success_url": return_url,
            "fail_url": return_url,
            "cancel_url": return_url,
            "ipn_url": urls.urljoin(base_url, const.IPN_ROUTE),
            "cus_name": tx.partner_name,
            "cus_email": tx.partner_email,
            "product_name": "Online Payment",
            "product_category": "general",
            "product_profile": "non-physical-goods",
            "multi_card_name": const.PAYMENT_METHODS_MAPPING[tx.payment_method_code],
        }
        self.assertDictEqual(tx._sslcommerz_prepare_session_payload(), expected_payload)

    def test_extract_reference_finds_reference(self):
        """Test that the transaction reference is found in the payment data."""
        tx = self._create_transaction("redirect")
        reference = self.env["payment.transaction"]._extract_reference(
            "sslcommerz", self.payment_data
        )
        self.assertEqual(tx.reference, reference)

    def test_extract_amount_data_returns_amount_and_currency(self):
        """Test that the amount and currency are returned from the payment data."""
        tx = self._create_transaction("redirect")
        amount_data = tx._extract_amount_data(self.payment_data)
        self.assertDictEqual(
            amount_data, {"amount": tx.amount, "currency_code": tx.currency_id.name}
        )

    def test_apply_updates_sets_provider_reference(self):
        """Test that the provider reference is set when processing the payment data."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.provider_reference, self.payment_data["bank_tran_id"])

    def test_apply_updates_sets_mastercard_payment_method(self):
        """Test that the card payment method brand is updated from the payment data."""
        self.payment_data.update({"card_brand": "Mastercard"})
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.payment_method_id.code, "mastercard")

    def test_apply_updates_sets_wallet_payment_method(self):
        """Test that the specific wallet payment method is updated from the payment data."""
        self.payment_data.update({"card_brand": "MOBILEBANKING", "card_type": "BKASH-BKash"})
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.payment_method_id.code, "bkash")

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.payment_data)
        self.assertEqual(tx.state, "done")

    def test_apply_updates_cancels_transaction(self):
        """Test that the transaction state is set to 'cancel' when the payment data indicate a
        canceled payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates({"status": "CANCELLED"})
        self.assertEqual(tx.state, "cancel")

    def test_apply_updates_errors_transaction(self):
        """Test that the transaction state is set to 'error' when the payment data indicate a
        failed payment."""
        tx = self._create_transaction("redirect")
        tx.with_context(payment_safe_write=True)._apply_updates({"status": "FAILED"})
        self.assertEqual(tx.state, "error")
