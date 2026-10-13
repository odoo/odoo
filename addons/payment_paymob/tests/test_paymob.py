# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_paymob.controllers.main import PaymobController
from odoo.addons.payment_paymob.tests.common import PaymobCommon


@tagged("post_install", "-at_install")
class PaymobTest(PaymobCommon, PaymentHttpCommon):
    def test_no_item_missing_from_rendering_values(self):
        """Test that when the redirect flow is triggered, rendering_values contains the API_URL and
        URL_PARAMS corresponding to the response of API request."""
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"intention_order_id": self.order_id, "client_secret": "dummy_secret"},
        ):
            rendering_values = tx.with_context(
                payment_safe_write=True
            )._get_specific_rendering_values(None)
        paymob_url = self.paymob._paymob_get_api_url()
        paymob_pk = self.paymob.paymob_public_key
        self.assertEqual(rendering_values["api_url"], f"{paymob_url}/unifiedcheckout/")
        self.assertEqual(rendering_values["url_params"]["publicKey"], paymob_pk)
        self.assertEqual(rendering_values["url_params"]["clientSecret"], "dummy_secret")

    def test_paymob_return_data(self):
        """Test the processing of the paymob return data."""
        self._disable_process_patcher()
        tx = self._create_transaction("redirect")
        with patch(
            "odoo.addons.payment.models.payment_provider.PaymentProvider._send_api_request",
            return_value={"intention_order_id": self.order_id},
        ):
            tx.with_context(payment_safe_write=True)._get_specific_rendering_values(
                None
            )  # Set provider reference here
            self.assertEqual(tx.provider_reference, self.order_id)
            self.assertEqual(tx.state, "draft")
            tx.with_context(payment_safe_write=True)._process(self.redirection_data)
            self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_paymob.controllers.main")
    def test_compute_signature(self):
        """Test the computation of the signature sent by paymob."""
        computed_hmac = PaymobController._compute_signature(
            self.redirection_data, self.provider.paymob_hmac_key
        )
        self.assertEqual(computed_hmac, self.hmac_signature)

    def test_change_paymob_account_country(self):
        """Test that changing the Paymob account country will change the currency accordingly."""
        self.provider.paymob_account_country_id = self.quick_ref("base.sa")
        self.assertEqual(self.provider.available_currency_ids.name, "SAR")

    def test_visa_payment_rounded_to_supported_decimals_is_accepted(self):
        """Test that a Visa payment rounded down by Paymob to the decimals supported by Visa for the
        currency (e.g., 4.725 OMR charged as 4.720 OMR) doesn't fail the amount validation."""
        self._disable_process_patcher()
        omr = self._enable_currency("OMR")
        tx = self._create_transaction("redirect", amount=4.725, currency_id=omr.id)
        payment_data = dict(self.redirection_data, amount_cents="4720", currency="OMR")
        tx.with_context(payment_safe_write=True)._process(payment_data)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment.models.payment_transaction")
    def test_non_visa_payment_is_validated_with_currency_decimals(self):
        """Test that the amount of a non-Visa payment is still validated with the decimals of the
        currency as per the ISO 4217 norm."""
        self._disable_process_patcher()
        omr = self._enable_currency("OMR")
        tx = self._create_transaction("redirect", amount=4.725, currency_id=omr.id)
        payment_data = dict(
            self.redirection_data,
            amount_cents="4720",
            currency="OMR",
            **{"source_data.sub_type": "MasterCard"},
        )
        tx.with_context(payment_safe_write=True)._process(payment_data)
        self.assertEqual(tx.state, "error")
