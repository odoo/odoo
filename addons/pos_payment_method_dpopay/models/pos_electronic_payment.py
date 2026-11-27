import logging
import random
import string
import time

import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError, RequestException

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DPOPAY_DEFAULT_TIMEOUT = 60


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    dpopay_client_id = fields.Char("DPO Pay Client ID", help="The Client ID provided by DPO Pay for authenticating requests.")
    dpopay_client_secret = fields.Char("DPO Pay Client Secret", help="The Client Secret provided by DPO Pay for secure access. Keep it confidential.", groups="pos_payment_method.group_payment_method_admin")
    dpopay_mid = fields.Char("DPO Pay Merchant ID", help="Enter the Merchant ID assigned by DPO Pay (e.g., 123456789012).")
    dpopay_tid = fields.Char("DPO Pay Terminal ID", help="Enter the unique Terminal ID (TID) of your DPO Pay POS terminal (e.g., XXXXXXXX).")
    dpopay_payment_mode = fields.Selection(
        selection=[("card", "Card"), ("momo", "Mobile Money")],
        default="card",
        help="Choose allowed payment mode:\nCard - regular card payments\nMobile Money - M-Pesa / Airtel Mobile Money",
    )
    dpopay_chain_id = fields.Char("DPO Pay Chain-ID", help="Enter the Chain-ID header value(e.g., DPO-DTM-Testing)")
    dpopay_test_mode = fields.Boolean("Enable Test Mode", help="Check this to use DPO Pay's sandbox environment for testing purposes.")
    dpopay_bearer_token = fields.Char(default="Token", help="Bearer token used for authenticating requests. Automatically refreshed when expired.", groups="pos_payment_method.group_payment_method_admin")

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("dpopay", "DPO Pay")]

    def _dpopay_generate_source_id(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=15))

    def _dpopay_get_transaction_type(self):
        if self.dpopay_payment_mode == "momo":
            return "pushPaymentDpoMomoSale"
        return "pushPaymentSale"

    def _dpopay_get_base_url(self, is_token=False):
        host = (self.dpopay_test_mode and "api-dev.network.global") or "api.network.global"

        if is_token:
            return f"https://{host}/v1"
        return f"https://{host}/ngenius-webapi/payments/push/v1/tid:{self.dpopay_tid}/mid:{self.dpopay_mid}"

    def _dpopay_headers(self, token_expired=False):
        token = self._dpopay_refresh_token() if token_expired else self.sudo().dpopay_bearer_token
        return {
            "Authorization": f"Bearer {token}",
            "Chain-ID": self.dpopay_chain_id,
        }

    def _dpopay_refresh_token(self):
        auth = HTTPBasicAuth(self.dpopay_client_id, self.sudo().dpopay_client_secret)
        url = f"{self._dpopay_get_base_url(is_token=True)}/tokenkc/generate"

        _logger.info("Sending request to %s to generate new token", url)
        response = requests.get(url, auth=auth, timeout=DPOPAY_DEFAULT_TIMEOUT)
        response_json = response.json()
        response.raise_for_status()
        access_token = response_json.get("access_token")

        if not access_token:
            raise UserError(self.env._("Unable to retrieve DPO Pay bearer token: check Client ID and Client Secret."))

        # The token is short-lived and refreshed automatically to keep the payment flow working.
        # sudo() is used because POS users only have read access to this model.
        self.sudo().write({"dpopay_bearer_token": access_token})
        return access_token

    def _dpopay_get_payment_result(self, transaction_id: str):
        response = self._dpopay_execute_api_request({"sourceId": transaction_id}, "get-result")
        if "errorMessage" in response:
            return {"status": "failed", "error": response["errorMessage"]}

        data_map = response.get("dataMap", {})
        payment_mode = data_map.get("MNO")
        return {
            "status": "paid",
            "payment_method_issuer_bank": response.get("Acquirer Name"),
            "payment_method_authcode": response.get("authCode"),
            "cardholder_name": response.get("CardHolderName"),
            "card_no": (response.get("panMasked", "") or data_map.get("Phone Number", ""))[-4:],
            "card_brand": response.get("cardType"),
            "payment_method_payment_mode": f"{payment_mode} Mobile Money" if payment_mode else "CARD",
            "payment_ref_no": response.get("rrn") or data_map.get("Transaction Ref"),
        }

    def _dpopay_execute_api_request(self, payload: dict, endpoint: str) -> dict:
        if endpoint not in ("start-transaction", "get-result", "get-status", "cancel-transaction"):
            raise UserError(self.env._("Invalid endpoint"))

        mode = "Test" if self.dpopay_test_mode else "Production"
        url = f"{self._dpopay_get_base_url()}/{endpoint}"
        try:
            def _send_request(token_expired=False):
                headers = self._dpopay_headers(token_expired)
                _logger.info("Sending request to %s | Mode: %s | Headers: %s | Source ID: %s | Transaction Type: %s", url, mode, list(headers.keys()), payload.get("sourceId"), payload.get("transactionType"))
                response = requests.post(url, json=payload, headers=headers, timeout=DPOPAY_DEFAULT_TIMEOUT)
                response_json = response.json()
                return response, response_json

            response, response_json = _send_request()
            errorCode = response_json.get("error_code") or response_json.get("resultCode")
            # Refresh Token and Retry the request if the token is expired (999912) or invalid (999913)
            if response.status_code == 401 and errorCode in ("999912", "999913"):
                _logger.info("Token expired or invalid — regenerating token...")
                response, response_json = _send_request(token_expired=True)

            response.raise_for_status()
            return response_json

        except HTTPError as error:
            _logger.warning("HTTPError: %s | Mode: %s | Source ID: %s | Transaction Type: %s", error, mode, payload.get("sourceId"), payload.get("transactionType"))
            error_json = error.response.json()
            error_code = str(error_json.get("error_code") or error_json.get("errorCode") or error_json.get("resultCode"))
            error_message = error_json.get("errorMessage") or error_json.get("error_description") or error_json.get("resultDescription") or str(error_json)

            if error_code == "403" and error_message == "Terminal not ready":
                error_message = self.env._("Terminal not ready. Please ensure the device is online and confirm that the Merchant ID (MID) and Terminal ID (TID) are correct.")

            if error_code == "999911":
                error_message = self.env._("Invalid Chain ID. Please verify the configuration. %s", error_message)

            return {"errorMessage": error_message}

        except RequestException as error:
            _logger.warning("%s: %s | Mode: %s | Source ID: %s", error.__class__.__name__, error, mode, payload.get("sourceId"))
            return {"errorMessage": str(error)}

    def _start_payment(self, amount: float, currency, extra_args: dict) -> dict:
        if self.payment_provider != "dpopay":
            return super()._start_payment(amount, currency, extra_args)

        status_response = self._dpopay_execute_api_request({}, "get-status")
        if "errorMessage" in status_response:
            return {"error": status_response["errorMessage"]}
        if status_response["displayText"] != "NO TXN / SYSTEM IDLE":
            return {"error": self.env._("Terminal not ready, current status: %s", status_response["displayText"])}

        payment_request = {
            "currency": str(currency.iso_numeric),
            "amount": str(self._convert_amount_to_units(amount, currency)),
            "sourceId": self._dpopay_generate_source_id(),
            "transactionType": self._dpopay_get_transaction_type(),
        }

        payment_response = self._dpopay_execute_api_request(payment_request, "start-transaction")
        if "errorMessage" in payment_response:
            return {"error": payment_response["errorMessage"]}

        return {"transaction_id": payment_request["sourceId"]}

    def _cancel_transaction(self, transaction_id: str) -> dict:
        if self.payment_provider != "dpopay":
            return super()._cancel_transaction(transaction_id)

        cancel_response = self._dpopay_execute_api_request({"sourceId": transaction_id}, "cancel-transaction")
        if "errorMessage" in cancel_response:
            return {"error": cancel_response["errorMessage"]}

        return {}

    def _get_transaction_status(self, transaction_id: str) -> dict:
        if self.payment_provider != "dpopay":
            return super()._get_transaction_status(transaction_id)

        response = self._dpopay_execute_api_request({"sourceId": transaction_id}, "get-status")
        if "errorMessage" in response:
            return {"status": "failed", "error": response["errorMessage"]}

        if response.get("offline"):
            return {"status": "failed", "error": self.env._("DPO Pay terminal is currently offline.")}

        if response.get("declined"):
            return {"status": "failed", "error": self.env._("Payment is declined by DPO Pay.")}

        if not response.get("complete"):
            return {"status": "pending"}

        if not response.get("success"):
            return {"status": "failed", "error": self.env._("Payment is unsuccessful.")}

        # Wait 3 seconds for DPO Pay to finalize the payment result.
        time.sleep(3)

        return self._dpopay_get_payment_result(transaction_id)
