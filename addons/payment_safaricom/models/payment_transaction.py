# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import hash_sign
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_safaricom import const

_logger = get_payment_logger(__name__, const.SENSITIVE_KEYS)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    # === LIFECYCLE METHODS - CREATION === #

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator="-", **kwargs):
        """Override of `payment` to ensure that Safaricom requirement for references is satisfied.

        Safaricom requires for the M-PESA AccountReference to be at most 12 characters long.

        :param str provider_code: The code of the provider handling the transaction.
        :param str prefix: The custom prefix used to compute the full reference.
        :param str separator: The custom separator used to separate the prefix from the suffix.
        :return: The unique reference for the transaction.
        :rtype: str
        """
        reference = super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )
        if provider_code != "safaricom":
            return reference

        if len(reference) <= 12:  # M-PESA AccountReference is limited to 12 chars
            return reference

        return super()._compute_reference(
            provider_code, prefix=reference[:9], separator=separator, **kwargs
        )

    # === LIFECYCLE METHODS - PAYMENT FORM === #

    def _get_specific_processing_values(self, processing_values):
        """Override of `payment` to return an access token authenticating the STK Push request.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        if self.provider_code != "safaricom":
            return super()._get_specific_processing_values(processing_values)
        return {"access_token": payment_utils.generate_access_token(self.reference, env=self.env)}

    # === LIFECYCLE METHODS - OUTBOUND REQUESTS === #

    def _safaricom_send_stk_push(self, phone):
        """Send an STK Push request prompting the customer to confirm the payment on their phone.

        The initiation response is recorded for deferred processing; if the request fails, the
        transaction is immediately set in error.

        Note: `self.ensure_one()`

        :param str phone: The phone number to send the payment prompt to.
        :return: None
        """
        self.ensure_one()

        # Validate the phone before any API work: a bad number must not error the transaction,
        # or the draft-state guard would block the customer from retrying
        phone = self._safaricom_format_phone_number(phone)

        provider = self.provider_id
        party_b = (
            provider.safaricom_shortcode
            if provider.safaricom_transaction_type == "CustomerPayBillOnline"
            else provider.safaricom_till_number
        )
        timestamp = fields.Datetime.now().strftime("%Y%m%d%H%M%S")
        payload = {
            "BusinessShortCode": provider.safaricom_shortcode,
            "Password": provider._safaricom_get_password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": provider.safaricom_transaction_type,
            "Amount": int(self.amount),
            "PartyA": phone,
            "PartyB": party_b,
            "PhoneNumber": phone,
            "CallBackURL": self._safaricom_get_callback_url(),
            "AccountReference": self.reference[:12],  # Max 12 chars - Shown in the USSD prompt
            "TransactionDesc": self.reference[:13],  # Max 13 chars - Optional description
        }
        response_data = self._send_api_request(
            "POST", "/mpesa/stkpush/v1/processrequest", json=payload
        )
        self._record(response_data)

    def _safaricom_get_callback_url(self):
        """Return the webhook URL carrying the signed reference that authenticates callbacks.

        Note: `self.ensure_one()`

        :return: The callback URL to request the STK Push with.
        :rtype: str
        """
        self.ensure_one()
        signed_reference = hash_sign(
            self.env(su=True),
            "payment_safaricom",
            {"reference": self.reference},
            expiration_hours=1,
        )
        return f"{urljoin(self.get_base_url(), const.WEBHOOK_URL)}?reference={signed_reference}"

    def _safaricom_format_phone_number(self, phone):
        """Format and validate phone numbers to the 254XXXXXXXXX format required by M-PESA."""
        kenya = self.env.ref("base.ke")
        phone = self._phone_format(number=phone, country=kenya, force_format="E164")
        if not phone:
            raise ValidationError(self.env._("Invalid phone number format."))
        return phone.removeprefix("+")  # M-PESA expects E.164 without the plus sign

    # === LIFECYCLE METHODS - PAYLOAD RECEPTION === #

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "safaricom":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("reference")

    # === LIFECYCLE METHODS - PROCESSING === #

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "safaricom":
            return super()._apply_updates(payment_data)

        if payment_data.get("canceled_by_customer"):  # Canceled from the payment status page
            self._set_canceled(state_message=self.env._("The payment was canceled on the website."))
        elif "Body" in payment_data:  # Webhook callback
            stk_callback = payment_data["Body"]["stkCallback"]
            result_code = str(stk_callback["ResultCode"])
            result_desc = stk_callback["ResultDesc"]
            if result_code in const.PAYMENT_STATUS_MAPPING["done"]:
                self._set_done()
            elif result_code in const.PAYMENT_STATUS_MAPPING["cancel"]:
                self._set_canceled(state_message=result_desc)
            elif result_code in const.PAYMENT_STATUS_MAPPING["unreachable"]:
                self._set_error(self.env._("User cannot be reached."))
            else:
                self._set_error(self.env._("Transaction failed with status: %s", result_desc))
        elif str(payment_data.get("ResponseCode")) == "0":  # STK Push accepted
            self.provider_reference = payment_data["CheckoutRequestID"]
            self._set_pending(
                state_message=self.env._("Waiting for customer to confirm transaction.")
            )
        else:
            self._set_error(
                self.env._(
                    "Transaction failed with status: %s",
                    payment_data.get("errorMessage", "Failed to initiate STK Push"),
                )
            )

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount from the payment data."""
        if self.provider_code != "safaricom":
            return super()._extract_amount_data(payment_data)

        if "Body" not in payment_data:
            return None  # No amount to validate for the STK Push initiation response

        stk_callback = payment_data["Body"]["stkCallback"]
        # CallbackMetadata is returned only for successful transactions, a successful transaction
        # should contain an amount, if not, then something wrong has happened, and 0.0 should be
        # returned so that the amount validation isn't skipped and fails down the line
        metadata_items = stk_callback.get("CallbackMetadata", {}).get("Item", [])
        amount = next(
            (float(item["Value"]) for item in metadata_items if item.get("Name") == "Amount"), 0.0
        )
        return {"amount": amount, "currency_code": self.currency_id.name}
