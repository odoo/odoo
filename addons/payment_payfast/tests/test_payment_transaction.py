# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_payfast.tests.common import PayfastCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(PayfastCommon, PaymentHttpCommon):
    def test_no_item_missing_from_rendering_values(self):
        """Test that the rendered values are conform to the transaction fields."""
        tx = self._create_transaction(flow="redirect")
        partner_first_name, partner_last_name = payment_utils.split_partner_name(tx.partner_name)
        with patch(
            "odoo.addons.payment_payfast.models.payment_provider.PaymentProvider"
            "._payfast_generate_signature",
            return_value="dummy_signature",
        ):
            rendering_values = tx._get_specific_rendering_values(None)
        self.assertDictEqual(
            rendering_values,
            {
                "api_url": f"{self.payfast._payfast_get_api_url()}/eng/process",
                "http_method": "post",
                "url_params": {
                    "merchant_id": self.payfast.payfast_merchant_id,
                    "merchant_key": self.payfast.payfast_merchant_key,
                    "return_url": self._build_url("/payment/payfast/return"),
                    "cancel_url": self._build_url("/payment/payfast/cancel"),
                    "notify_url": self._build_url("/payment/payfast/notify"),
                    "name_first": partner_first_name or partner_last_name or "",
                    "name_last": partner_last_name or "",
                    "email_address": tx.partner_email or "",
                    "cell_number": tx.partner_phone or "",
                    "m_payment_id": tx.reference,
                    "amount": f"{tx.amount:.2f}",
                    "item_name": tx.reference,
                    "signature": "dummy_signature",
                },
            },
        )

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_no_input_missing_from_redirect_form(self):
        """Test that no key is omitted from the rendering values."""
        tx = self._create_transaction(flow="redirect")
        expected_input_keys = [
            "merchant_id",
            "merchant_key",
            "return_url",
            "cancel_url",
            "notify_url",
            "name_first",
            "name_last",
            "email_address",
            "cell_number",
            "m_payment_id",
            "amount",
            "item_name",
            "signature",
        ]
        processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values["redirect_form_html"])
        self.assertEqual(form_info["action"], f"{self.payfast._payfast_get_api_url()}/eng/process")
        self.assertEqual(form_info["method"], "post")
        self.assertListEqual(list(form_info["inputs"].keys()), expected_input_keys)

    def test_tokenize_without_passphrase_raises(self):
        """Test that requesting tokenization without a passphrase set is rejected, since
        Payfast's tokenized-charge API requires it."""
        self.payfast.payfast_passphrase = False
        tx = self._create_transaction(flow="redirect", tokenize=True)
        with self.assertRaises(ValidationError):
            tx._get_specific_rendering_values(None)

    def test_extract_reference_returns_m_payment_id(self):
        reference = self.env["payment.transaction"]._extract_reference(
            "payfast", self.notification_data
        )
        self.assertEqual(reference, self.reference)

    def test_apply_updates_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the payment data indicate a
        successful payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates(self.notification_data)
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, self.notification_data["pf_payment_id"])

    def test_apply_updates_cancels_transaction(self):
        """Test that the transaction state is set to 'cancel' when the payment data indicate a
        cancelled payment."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates({
            **self.notification_data,
            "payment_status": "CANCELLED",
        })
        self.assertEqual(tx.state, "cancel")

    @mute_logger("odoo.addons.payment_payfast.models.payment_transaction")
    def test_apply_updates_errors_on_unsupported_status(self):
        """Test that the transaction is put in error for any status other than the two Payfast
        statuses that Odoo understands."""
        tx = self._create_transaction(flow="redirect")
        tx.with_context(payment_safe_write=True)._apply_updates({
            **self.notification_data,
            "payment_status": "PENDING",
        })
        self.assertEqual(tx.state, "error")

    def test_extract_amount_data_forces_zar_currency(self):
        """Test that the currency is always ZAR, since Payfast doesn't send it back in the
        notification and only ever operates in ZAR."""
        tx = self._create_transaction(flow="redirect")
        amount_data = tx._extract_amount_data(self.notification_data)
        self.assertEqual(amount_data["currency_code"], "ZAR")
        self.assertEqual(amount_data["amount"], tx.amount)

    def test_extract_token_values_maps_token(self):
        tx = self._create_transaction(flow="redirect", tokenize=True)
        token_values = tx._extract_token_values({**self.notification_data, "token": "dummy_token"})
        self.assertEqual(token_values["provider_ref"], "dummy_token")

    def test_send_payment_request_charges_the_token(self):
        """Test that charging a token sends a request to the right endpoint with the amount
        expressed in cents, and immediately records the payment as complete."""
        tx = self._create_transaction(flow="redirect")
        token = self._create_token(provider_ref="dummy_token")
        self._update_transaction(tx, token_id=token.id)
        with (
            patch(
                "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
                return_value={"data": {"pf_payment_id": "1324567"}},
            ) as send_request_mock,
            patch(
                "odoo.addons.payment.models.payment_transaction.PaymentTransaction._record"
            ) as record_mock,
        ):
            tx._send_payment_request()

        send_request_mock.assert_called_once_with(
            "POST",
            "subscriptions/dummy_token/adhoc",
            json={
                "amount": payment_utils.to_minor_currency_units(tx.amount, tx.currency_id),
                "item_name": tx.reference,
            },
        )
        record_mock.assert_called_once_with({
            "payment_status": "COMPLETE",
            "amount_gross": f"{tx.amount:.2f}",
            "pf_payment_id": "1324567",
        })
