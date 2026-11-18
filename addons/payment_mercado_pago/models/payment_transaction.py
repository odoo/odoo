# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import quote as url_quote

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round
from odoo.tools.urls import urljoin

from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.const import CURRENCY_MINOR_UNITS
from odoo.addons.payment.logging import get_payment_logger
from odoo.addons.payment_mercado_pago import const

_logger = get_payment_logger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    def _get_specific_rendering_values(self, processing_values):
        """Override of `payment` to return Mercado Pago-specific rendering values.

        Note: self.ensure_one() from `_get_rendering_values`.

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        if self.provider_code != "mercado_pago":
            return super()._get_specific_rendering_values(processing_values)

        # Initiate the payment and retrieve the payment link data.
        payload = self._mercado_pago_prepare_preference_request_payload()
        try:
            response_content = self._send_api_request("POST", "/checkout/preferences", json=payload)
        except ValidationError as error:
            self._set_error(str(error))
            return {}

        api_url = response_content["init_point"]
        return {
            "api_url": api_url,
            "http_method": "get",
            "url_params": payment_utils.extract_url_params(api_url),
        }

    def _mercado_pago_prepare_preference_request_payload(self):
        """Create the payload for the preference request based on the transaction values.

        :return: The preference request payload.
        :rtype: dict
        """
        payload = self._mercado_pago_prepare_base_request_payload()

        base_url = self.provider_id.get_base_url()
        return_url = urljoin(base_url, const.PAYMENT_RETURN_ROUTE)
        payload.update({
            "auto_return": "all",
            "back_urls": {"success": return_url, "pending": return_url, "failure": return_url},
            "items": [
                {**item, "currency_id": self.currency_id.name}
                for item in self._mercado_pago_prepare_items_payload()
            ],
            "payer": {
                "name": self.partner_name,
                "email": self.partner_email,
                "phone": {"number": self.partner_phone},
                "address": {"zip_code": self.partner_zip, "street_name": self.partner_address},
            },
        })
        return payload

    def _mercado_pago_prepare_payment_request_payload(self):
        """Create the payload for the direct payment request based on the transaction values.

        :return: The payment request payload.
        :rtype: dict
        """
        payload = self._mercado_pago_prepare_base_request_payload()
        first_name, last_name = payment_utils.split_partner_name(self.partner_name)
        payload.update({
            "additional_info": {"items": self._mercado_pago_prepare_items_payload()},
            "payer": {
                "first_name": first_name,
                "last_name": last_name,
                "email": self.partner_email,
            },
        })
        return payload

    def _mercado_pago_prepare_items_payload(self):
        """Prepare the items of the request payload.

        :return: The Mercado Pago-formatted items payload.
        :rtype: list
        """
        converted_amount = self._mercado_pago_convert_amount()
        # Send a single item covering the whole amount if the items cannot be sent.
        default_items = [{"title": self.reference, "quantity": 1, "unit_price": converted_amount}]
        line_items = self._get_line_items().values()
        if any(line_item["total"] < 0 for line_item in line_items) or any(
            not line_item["name"] for line_item in line_items
        ):
            return default_items

        decimal_places = const.CURRENCY_DECIMALS.get(
            self.currency_id.name,
            CURRENCY_MINOR_UNITS.get(self.currency_id.name, self.currency_id.decimal_places),
        )
        items = []
        total_amount = 0
        for line_item in line_items:
            line_amount = payment_utils.to_minor_currency_units(
                line_item["total"], self.currency_id, arbitrary_decimal_number=decimal_places
            )
            quantity = line_item["quantity"]
            unit_amount = round(line_amount / quantity) if quantity else 0
            if quantity < 1 or quantity != int(quantity) or unit_amount * quantity != line_amount:
                # Force the quantity to 1, priced at the line total, for non-whole quantities
                # or when the rounded unit amount does not add up to the total.
                quantity, unit_amount = 1, line_amount
            total_amount += line_amount
            item = {
                "title": line_item["name"],
                "quantity": int(quantity),
                "unit_price": unit_amount / 10**decimal_places,
            }
            if description := line_item["description"]:
                item["description"] = description
            # Images not served over HTTPS are discarded by Mercado Pago.
            if (image_url := line_item.get("image_url")) and image_url.startswith("https://"):
                item["picture_url"] = image_url
            items.append(item)

        amount = payment_utils.to_minor_currency_units(
            converted_amount, self.currency_id, arbitrary_decimal_number=decimal_places
        )
        if not items or total_amount != amount:  # Partial payment or rounding mismatch.
            return default_items
        return items

    def _mercado_pago_prepare_base_request_payload(self):
        """Create the base payload for requests based on the transaction values.

        :return: The base request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        sanitized_reference = url_quote(self.reference)
        # Append the reference to identify the transaction from the webhook payment data.
        webhook_url = urljoin(base_url, f"{const.WEBHOOK_ROUTE}/{sanitized_reference}")
        return {
            "external_reference": self.reference,
            "notification_url": webhook_url,
            "statement_descriptor": self.company_id.name,
        }

    def _send_payment_request(self):
        """Override of `payment` to send a payment request to Mercado Pago.

        Note: `self.ensure_one()` from :meth:`_charge_with_token`

        :rtype: None
        """
        if self.provider_code != "mercado_pago":
            super()._send_payment_request()
            return

        # A new token has to be generated based on 'card_id' for every payment.
        response_content = self._send_api_request(
            "POST", "/v1/card_tokens", json={"card_id": self.token_id.provider_ref}
        )
        data = self._mercado_pago_prepare_base_request_payload()
        # Send the payment request to Mercado Pago.
        data.update({
            "additional_info": {"items": self._mercado_pago_prepare_items_payload()},
            "transaction_amount": self._mercado_pago_convert_amount(),
            "token": response_content["id"],
            "installments": 1,
            "payer": {"type": "customer", "id": self.token_id.mercado_pago_customer_id},
        })
        response_content = self._send_api_request(
            "POST",
            endpoint="/v1/payments",
            json=data,
            idempotency_key=payment_utils.generate_idempotency_key(self, scope="token_payment"),
        )
        self._record(response_content)

    def _mercado_pago_convert_amount(self):
        """Convert the transaction amount according to Mercado Pago's currency requirements.

        Mercado Pago requires certain currencies (COP, HNL, NIO) to be expressed as integers rather
        than following the standard ISO 4217 decimal places. This method rounds down the amount to
        the appropriate decimal places to ensure API compatibility.

        :return: The transaction amount rounded to Mercado Pago's required decimal precision.
        :rtype: float
        """
        unit_price = self.amount
        decimal_places = const.CURRENCY_DECIMALS.get(
            self.currency_id.name, CURRENCY_MINOR_UNITS.get(self.currency_id.name)
        )
        if decimal_places is not None:
            unit_price = float_round(unit_price, decimal_places, rounding_method="DOWN")
        return unit_price

    @api.model
    def _extract_reference(self, provider_code, payment_data):
        """Override of `payment` to extract the reference from the payment data."""
        if provider_code != "mercado_pago":
            return super()._extract_reference(provider_code, payment_data)
        return payment_data.get("external_reference")

    def _apply_updates(self, payment_data):
        """Override of `payment` to update the transaction based on the payment data."""
        if self.provider_code != "mercado_pago":
            super()._apply_updates(payment_data)
            return

        # Update the provider reference.
        payment_id = payment_data.get("id")
        if not payment_id:
            self._set_error(self.env._("Received data with missing payment id."))
            return
        self.provider_reference = payment_id

        # Update the payment method.
        payment_method_type = payment_data.get("payment_type_id", "")
        for odoo_code, mp_codes in const.PAYMENT_METHODS_MAPPING.items():
            if any(payment_method_type == mp_code for mp_code in mp_codes.split(",")):
                payment_method_type = odoo_code
                break
        if payment_method_type == "card":
            payment_method_code = payment_data.get("payment_method_id")
        else:
            payment_method_code = payment_method_type
        payment_method = self.provider_id._get_pm_from_code(
            payment_method_code, mapping=const.PAYMENT_METHODS_MAPPING
        )
        self.payment_method_id = payment_method or self.payment_method_id

        # Update the payment state.
        payment_status = payment_data.get("status")
        if not payment_status:
            self._set_error(self.env._("Received data with missing status."))
            return

        if payment_status in const.TRANSACTION_STATUS_MAPPING["pending"]:
            self._set_pending()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING["done"]:
            self._set_done()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING["canceled"]:
            self._set_canceled()
        elif payment_status in const.TRANSACTION_STATUS_MAPPING["error"]:
            status_detail = payment_data.get("status_detail")
            _logger.warning(
                "Received data for transaction %s with status %s and error code: %s.",
                self.reference,
                payment_status,
                status_detail,
            )
            error_message = self._mercado_pago_get_error_msg(status_detail)
            self._set_error(error_message)
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction %s with invalid payment status: %s.",
                self.reference,
                payment_status,
            )
            self._set_error(self.env._("Received data with invalid status: %s.", payment_status))

    def _extract_amount_data(self, payment_data):
        """Override of payment to extract the amount and currency from the payment data."""
        if self.provider_code != "mercado_pago":
            return super()._extract_amount_data(payment_data)

        if self.operation in ("online_redirect", "online_direct"):
            items = payment_data.get("additional_info", {}).get("items", [])
            amount = sum(
                float(item.get("unit_price", 0)) * float(item.get("quantity", 1)) for item in items
            )
        else:  # 'online_token', 'offline'
            amount = payment_data.get("transaction_amount")
        currency_code = payment_data.get("currency_id")
        return {
            "amount": float(amount),
            "currency_code": currency_code,
            "precision_digits": const.CURRENCY_DECIMALS.get(currency_code),
        }

    def _extract_token_values(self, payment_data):
        """Override of `payment` to return token data based on payment data."""
        if self.provider_code != "mercado_pago":
            return super()._extract_token_values(payment_data)

        if not payment_data.get("token"):
            return {}

        # Fetch the customer id or create a new one.
        email_data = {"email": payment_data["payer"]["email"]}
        response_content = self._send_api_request("GET", "/v1/customers/search", params=email_data)
        if customers_data := response_content["results"]:
            customer_id = customers_data[0]["id"]
        else:  # No customer found.
            # Create a new customer.
            response_content = self._send_api_request("POST", "/v1/customers", json=email_data)
            customer_id = response_content["id"]

        # Fetch the card data.
        payload = {
            "token": payment_data["token"],
            "issuer_id": int(payment_data["issuer_id"]),
            "payment_method_id": payment_data["payment_method_id"],
        }
        response_content = self._send_api_request(
            "POST", f"/v1/customers/{customer_id}/cards", json=payload
        )
        card_id = response_content["id"]
        last_four_digits = response_content["last_four_digits"]

        return {
            "mercado_pago_customer_id": customer_id,
            "payment_details": last_four_digits,
            "provider_ref": card_id,
        }

    @api.model
    def _mercado_pago_get_error_msg(self, status_detail):
        """Return the error message corresponding to the payment status.

        :param str status_detail: The status details sent by the provider.
        :return: The error message.
        :rtype: str
        """
        return const.ERROR_MESSAGE_MAPPING.get(
            status_detail, const.ERROR_MESSAGE_MAPPING["cc_rejected_other_reason"]
        )
