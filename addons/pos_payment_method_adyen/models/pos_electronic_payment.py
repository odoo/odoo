import logging
import pprint
import random
import string
import time
import uuid
from urllib.parse import parse_qs, urlencode

import requests

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.tools import hmac

_logger = logging.getLogger(__name__)


REQUEST_TIMEOUT = 10


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    adyen_api_key = fields.Char(string="Adyen API key", help="Used when connecting to Adyen: https://docs.adyen.com/user-management/how-to-get-the-api-key/#description", copy=False, groups="pos_payment_method.group_payment_method_admin")
    adyen_terminal_identifier = fields.Char(help="[Terminal model]-[Serial number], for example: P400Plus-123456789", copy=False)
    adyen_merchant_account = fields.Char(help="The POS merchant account code used in Adyen")
    adyen_test_mode = fields.Boolean(help="Run transactions in the test environment.")
    adyen_event_url = fields.Char(
        string="Event URL",
        help="This URL needs to be pasted on Adyen's portal terminal settings.",
        readonly=True,
        store=False,
        default=lambda self: f"{self.get_base_url()}/pos_adyen/notification",
    )
    adyen_ask_customer_for_tip = fields.Boolean("Ask Customers For Tip")

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("adyen", "Adyen")]

    def _parse_adyen_additional_response(self, response: dict) -> dict[str, str]:
        if "AdditionalResponse" not in response:
            return {}
        result_with_lists = parse_qs(response["AdditionalResponse"])
        return {key: values[0] for key, values in result_with_lists.items()}

    def _call_adyen(self, path: str, data: dict, use_checkout_api: bool = False):
        self.ensure_one()

        _logger.info("Request to Adyen by user #%d:\n%s", self.env.uid, pprint.pformat(data))

        environment = "test" if self.adyen_test_mode else "live"
        if use_checkout_api:
            endpoint = f"https://checkout-{environment}.adyen.com/v72{path}"
        else:
            endpoint = f"https://terminal-api-{environment}.adyen.com{path}"
        headers = {
            "x-api-key": self.sudo().adyen_api_key,
        }
        response = requests.post(endpoint, json=data, headers=headers, timeout=REQUEST_TIMEOUT)

        if not response.ok:
            raise ValidationError(response.text)

        if response.text == "ok":
            return {}

        return response.json()

    def _generate_adyen_service_id(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=10))

    def _generate_adyen_hmac(self, service_id: str):
        return hmac(self.sudo().env, "pos_adyen", (self.id, self.adyen_terminal_identifier, service_id))

    def _wait_until_adyen_payment_ready_to_adjust(self, payment_authorized_timestamp: float):
        # The Adyen docs say to wait at least 5 seconds before capturing/adjusting an authorised payment.
        # If we don't do this it can fail.
        time_elapsed_since_authorization = time.monotonic() - payment_authorized_timestamp
        if time_elapsed_since_authorization < 5:
            time.sleep(5 - time_elapsed_since_authorization)

    def _make_adyen_header(self, message_category: str, service_id: str | None = None):
        return {
            "ProtocolVersion": "3.0",
            "MessageClass": "Service",
            "MessageType": "Request",
            "SaleID": f"Odoo Payment Method: {self.name} (ID={self.id})",
            "ServiceID": service_id or self._generate_adyen_service_id(),
            "POIID": self.adyen_terminal_identifier,
            "MessageCategory": message_category,
        }

    def _make_adyen_sale_data(self, service_id: str, data: dict[str, str] | None = None):
        acquirer_data = {
            **(data or {}),
            "metadata.payment_method_id": self.id,
            "metadata.pos_hmac": self._generate_adyen_hmac(service_id),
        }
        return {
            "SaleTransactionID": {
                "TransactionID": uuid.uuid4().hex,
                "TimeStamp": fields.Datetime.now().isoformat(),
            },
            "SaleToAcquirerData": urlencode(acquirer_data),
        }

    def _process_adyen_transaction_result(self, result: dict):
        transaction_result = result.get("PaymentResponse") or result.get("ReversalResponse")
        additional_response = self._parse_adyen_additional_response(transaction_result["Response"])

        if transaction_result["Response"]["Result"] == "Success":
            payment_result = transaction_result.get("PaymentResult")
            return {
                "status": "paid",
                "final_transaction_id": transaction_result["POIData"]["POITransactionID"]["TransactionID"],
                "card_type": additional_response.get("cardType"),
                "cardholder_name": additional_response.get("cardHolderName"),
                "tip_amount": payment_result["AmountsResp"].get("TipAmount") if payment_result else None,
                "metadata": {
                    "can_be_adjusted": "adjustAuthorisationData" in additional_response,
                    "adjust_authorisation_data": additional_response.get("adjustAuthorisationData"),
                    "payment_authorized_timestamp": time.monotonic(),
                },
            }

        return {"status": "failed", "error": self.env._("Error from Adyen: %s", additional_response["message"])}

    def _start_payment(self, amount: float, currency, extra_args: dict):
        if self.payment_provider != "adyen":
            return super()._start_payment(amount, currency, extra_args)

        service_id = self._generate_adyen_service_id()
        if extra_args.get("allow_adjustments"):
            sale_data_options = {"authorisationType": "PreAuth", "manualCapture": "true"}
        else:
            sale_data_options = {"authorisationType": "FinalAuth", "manualCapture": "false"}
        if extra_args.get("allow_tips") and self.adyen_ask_customer_for_tip:
            sale_data_options |= {"tenderOption": "AskGratuity"}
        data = {
            "SaleToPOIRequest": {
                "MessageHeader": self._make_adyen_header("Payment", service_id),
                "PaymentRequest": {
                    "SaleData": self._make_adyen_sale_data(service_id, sale_data_options),
                    "PaymentTransaction": {
                        "AmountsReq": {
                            "Currency": currency.name,
                            "RequestedAmount": amount,
                        },
                    },
                },
            },
        }

        self._call_adyen("/async", data)
        return {"transaction_id": f"Payment/{service_id}"}

    def _start_reversal(self, amount: float, currency, original_transaction_id: str, extra_args: dict):
        if self.payment_provider != "adyen":
            return super()._start_reversal(amount, currency, original_transaction_id, extra_args)

        service_id = self._generate_adyen_service_id()
        data = {
            "SaleToPOIRequest": {
                "MessageHeader": self._make_adyen_header("Reversal", service_id),
                "ReversalRequest": {
                    "SaleData": self._make_adyen_sale_data(service_id, {"currency": currency.name}),
                    "ReversalReason": "MerchantCancel",
                    "ReversedAmount": amount,
                    "OriginalPOITransaction": {
                        "POITransactionID": {
                            "TransactionID": original_transaction_id,
                            "TimeStamp": extra_args.get("original_payment_timestamp", fields.Datetime.now().isoformat()),
                        },
                    },
                },
            },
        }

        self._call_adyen("/async", data)
        return {"transaction_id": f"Reversal/{service_id}"}

    def _adjust_payment(self, amount: float, currency, transaction_id: str, extra_args: dict):
        if self.payment_provider != "adyen":
            return super()._adjust_payment(amount, currency, transaction_id, extra_args)

        if "." in transaction_id:
            transaction_id = transaction_id.split(".")[1]
        data = {
            "amount": {
                "value": self._convert_amount_to_units(amount, currency),
                "currency": currency.name,
            },
            "merchantAccount": self.adyen_merchant_account,
            "reference": uuid.uuid4().hex,
            "adjustAuthorisationData": extra_args["metadata"]["adjust_authorisation_data"],
        }

        self._wait_until_adyen_payment_ready_to_adjust(extra_args["metadata"]["payment_authorized_timestamp"])
        response = self._call_adyen(f"/payments/{transaction_id}/amountUpdates", data, use_checkout_api=True)

        return {
            "transaction_id": transaction_id,
            "status": "paid",
            "metadata": {
                **extra_args["metadata"],
                "adjust_authorisation_data": response["adjustAuthorisationData"],
            },
        }

    def _capture_payment(self, amount: float, currency, transaction_id: str, extra_args: dict):
        if self.payment_provider != "adyen":
            return super()._capture_payment(amount, currency, transaction_id, extra_args)

        if "." in transaction_id:
            transaction_id = transaction_id.split(".")[1]
        data = {
            "amount": {
                "value": self._convert_amount_to_units(amount, currency),
                "currency": currency.name,
            },
            "merchantAccount": self.adyen_merchant_account,
            "reference": uuid.uuid4().hex,
        }

        self._wait_until_adyen_payment_ready_to_adjust(extra_args["metadata"]["payment_authorized_timestamp"])
        self._call_adyen(f"/payments/{transaction_id}/captures", data, use_checkout_api=True)
        return {
            "transaction_id": transaction_id,
            "status": "paid",
        }

    def _cancel_transaction(self, transaction_id: str):
        if self.payment_provider != "adyen":
            return super()._cancel_transaction(transaction_id)

        category, service_id = transaction_id.split("/")
        data = {
            "SaleToPOIRequest": {
                "MessageHeader": self._make_adyen_header("Abort"),
                "AbortRequest": {
                    "AbortReason": "MerchantAbort",
                    "MessageReference": {
                        "MessageCategory": category,
                        "ServiceID": service_id,
                    },
                },
            },
        }

        return self._call_adyen("/sync", data)

    def _get_transaction_status(self, transaction_id: str):
        if self.payment_provider != "adyen":
            return super()._get_transaction_status(transaction_id)

        category, service_id = transaction_id.split("/")
        data = {
            "SaleToPOIRequest": {
                "MessageHeader": self._make_adyen_header("TransactionStatus"),
                "TransactionStatusRequest": {
                    "MessageReference": {
                        "ServiceID": service_id,
                        "MessageCategory": category,
                    },
                },
            },
        }

        response = self._call_adyen("/sync", data)
        transaction_status = response["SaleToPOIResponse"]["TransactionStatusResponse"]["Response"]

        if transaction_status.get("ErrorCondition") == "InProgress":
            return {"status": "pending"}
        if transaction_status.get("Result") == "Failure":
            additional_response = self._parse_adyen_additional_response(transaction_status)
            message = additional_response.get("message") or transaction_status["ErrorCondition"]
            return {"status": "failed", "error": self.env._("Error from Adyen: %s", message)}

        repeated_message_body = response["SaleToPOIResponse"]["TransactionStatusResponse"]["RepeatedMessageResponse"]["RepeatedResponseMessageBody"]
        return self._process_adyen_transaction_result(repeated_message_body)
