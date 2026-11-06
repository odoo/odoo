# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Worldline API Documentation: https://docs.terminal.worldline-solutions.com/api-reference
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

from odoo.tools import hash_sign

_logger = logging.getLogger(__name__)

TEST_BASE_URL = "https://api.terminal.iacc.global.worldline-solutions.com"
PROD_BASE_URL = "https://api.terminal.global.worldline-solutions.com"

PROTOCOL_VERSION = "5.1-WL2.1.1"  # Worldline API version used
INTEGRATOR_ID = "175d97a0-2a88-4413-b920-e90037b582ac"  # Odoo integrator id
SALE_SOFTWARE_VERSION = "Odoo Point Of Sale 1.0.2"
NUMBER_OF_RETRIES = 3  # must be between 0 and 3. Number of requests (re)sent if the webhook is unavailable or returns an error
TIMEOUT = 10


class WorldlineApiRequest:
    def __init__(self, payment_method):
        sudo_payment_method = payment_method.sudo()
        self.env = sudo_payment_method.env
        self.base_url = TEST_BASE_URL if sudo_payment_method.worldline_test_mode else PROD_BASE_URL
        self.api_key = sudo_payment_method.worldline_api_key
        self.merchant_id = sudo_payment_method.worldline_merchant_id
        self.terminal_id = sudo_payment_method.worldline_terminal_id
        self.webhook_url = sudo_payment_method.worldline_webhook_url
        self.currency = sudo_payment_method._get_worldline_currency()
        self.payment_method = sudo_payment_method

    def _get_current_time(self):
        """Return the current UTC time formatted as "2026-08-18T09:11:08.497+00:00"."""
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

    def _get_webhook_payload(self, exchange_id, payment_uuid=None, pos_session_id=None):
        """Sign the payload added to the WebhookUrl, proving the notification answers a request we sent.

        Kept out of the model so it cannot be called from server actions to forge webhook notifications.
        """
        payload = {
            "exchange_id": exchange_id,
            "payment_uuid": payment_uuid,
            "payment_method_id": self.payment_method.id,
            "pos_session_id": pos_session_id,
        }
        return hash_sign(self.env, 'pos_worldline', payload)

    def _get_poi_environment(self):
        """Generate the Environment block identifying the terminal, shared by every Worldline request."""
        return {
            "POI": {
                "Identification": {
                    "Identification": self.terminal_id,
                },
            },
        }

    def _get_header(self, message_function, exchange_id, now, payment_uuid=None, pos_session_id=None):
        """Generate the Header block shared by every Worldline request.

        :param message_function: "SaleFinancialServiceRequest", "Abort", "MessageStatusRequest" or "DeviceRequest"
        :param exchange_id: UUID identifying each request sent (Worldline accepts v4 or v7)
        :param now: The creation datetime of the request, formatted as "2026-08-18T09:11:08.497+00:00"
        :param payment_uuid: The identifier of the payment, only for transaction requests
        :param pos_session_id: The identifier of the POS session, only for transaction requests
        """
        webhook_payload = self._get_webhook_payload(exchange_id, payment_uuid, pos_session_id)
        return {
            "MessageFunction": message_function,
            "ProtocolVersion": PROTOCOL_VERSION,
            "ExchangeIdentification": exchange_id,  # Unique identifier for each request sent
            "CreationDateTime": now,
            "InitiatingParty": {
                "Identification": "Odoo Point Of Sale",
                "Type": "Merchant",
            },
            "SalesSystemInfo": {
                "IntegratorId": INTEGRATOR_ID,
                "SaleSoftware": [
                    {
                        "Type": "ECR",
                        "Status": {
                            "VersionNumber": SALE_SOFTWARE_VERSION,
                        },
                    },
                ],
            },
            # WebhookURL and NumberOfRetries are required for the async endpoints, ignored for sync "status" requests
            # The signed payload proves the notification answers a request we sent and identifies its payment line
            "WebhookUrl": f"{self.webhook_url}?{urlencode({'payload': webhook_payload})}",
            "NumberOfRetries": NUMBER_OF_RETRIES,
        }

    def _send_request(self, json_body, endpoint="payments"):
        url = f"{self.base_url}/api/v2/merchants/{self.merchant_id}/terminals/{self.terminal_id}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        _logger.debug("Sending json to Worldline endpoint %s: %s", endpoint, json_body)
        try:
            resp = requests.post(url, json=json_body, headers=headers, timeout=TIMEOUT)
        except requests.exceptions.Timeout:
            _logger.warning("Request to Worldline endpoint %s timed out", endpoint)
            return {"error": self.env._("Worldline request to terminal %s timed out. Please make sure the terminal is connected to internet and try again.", self.terminal_id)}
        except requests.exceptions.RequestException as e:
            _logger.warning("Failed to call Worldline %s endpoint", endpoint)
            return {"error": str(e)}

        if resp.status_code in (200, 202):
            return resp.json()
        _logger.warning("Worldline API request to %s error response: %s: %s", url, resp.status_code, resp.text)
        try:
            return {"error": resp.json().get("message")}
        except ValueError:
            return {"error": resp.text}

    def _get_transaction_json(self, transaction_type, amount, payment_uuid, pos_session_id, exchange_id):
        """Generate the JSON payload for a Worldline transaction request.

        :param transaction_type: The type of the transaction (Ex: "CardPayment" or "Refund")
        :param amount: The amount of the transaction (Ex: 104.11)
        :param payment_uuid: The identifier of the payment
        :param pos_session_id: The identifier of the POS session
        :param exchange_id: The UUID identifying this request, recovered by the webhook notification or status request

        :return: A dictionary representing the JSON payload for the Worldline transaction request
        """
        now = self._get_current_time()
        # Despite what's noted in the documentation adding "OriginalTransaction" rejects the referenced refunds with EFT_E_INVALID_ARGUMENT
        # Without it it works as an unreferenced refund (card must be presented)
        payment_transaction = {
            "TransactionType": transaction_type,  # CardPayment or Refund
            "TransactionIdentification": {
                "TransactionDateTime": now,
                "TransactionReference": payment_uuid,
            },
            "TransactionDetails": {
                "Currency": self.currency.name,  # "EUR"
                "TotalAmount": amount,  # 104.11
            },
        }
        return {
            "SaleToPOIServiceRequest": {
                "Header": self._get_header("SaleFinancialServiceRequest", exchange_id, now, payment_uuid, pos_session_id),
                "ServiceRequest": {
                    "Environment": self._get_poi_environment(),
                    "ServiceContent": "FinancialPaymentRequest",
                    "PaymentRequest": {
                        "PaymentTransaction": payment_transaction,
                    },
                },
            },
        }

    def _get_cancel_json(self, exchange_id_to_abort, payment_uuid, pos_session_id):
        """Generate the JSON payload for a Worldline transaction cancellation request.

        :param exchange_id_to_abort: The ExchangeIdentification of the ongoing request to abort
        :param payment_uuid: The identifier of the payment being cancelled
        :param pos_session_id: The identifier of the POS session

        :return: A dictionary representing the JSON payload for the Worldline cancellation request
        """
        return {
            "SaleToPOIAbort": {
                "Header": self._get_header("Abort", str(uuid.uuid4()), self._get_current_time(), payment_uuid, pos_session_id),
                "Abort": {
                    "Environment": self._get_poi_environment(),
                    "SystemAbort": {
                        "ExchangeIdentification": exchange_id_to_abort,
                        "AbortReason": "Cancelled from the Point of Sale",
                    },
                },
            },
        }

    def _get_status_json(self, exchange_id_to_check):
        """Generate the JSON payload for a Worldline message status request.

        :param exchange_id_to_check: The ExchangeIdentification of the request whose outcome is requested

        :return: A dictionary representing the JSON payload for the Worldline status request
        """
        header = self._get_header("MessageStatusRequest", str(uuid.uuid4()), self._get_current_time())
        return {
            "SaleToPOIMessageStatusRequest": {
                "Header": header,
                "StatusRequest": {
                    "Environment": self._get_poi_environment(),
                    "MessageStatusRequestData": {
                        "ExchangeIdentification": exchange_id_to_check,
                        "InitiatingParty": header["InitiatingParty"],
                    },
                },
            },
        }

    def _get_image_screen_json(self, image_base64):
        """Generate the JSON payload for a Worldline device request displaying an image.

        :param image_base64: The base64 encoded image to display on the terminal

        :return: A dictionary representing the JSON payload for the Worldline device request
        """
        return {
            "SaleToPOIDeviceRequest": {
                "Header": self._get_header("DeviceRequest", str(uuid.uuid4()), self._get_current_time()),
                "DeviceRequest": {
                    "InputRequest": {
                        "DisplayOutput": {
                            "MessageContent": {
                                "ImageScreen": {
                                    "ShowLogo": False,  # Hide the Worldline logo at the top of the screen
                                    "ImageBase64": image_base64,
                                    "PrimaryButton": {
                                        "ButtonId": "close",
                                        "ButtonContent": "OK",
                                    },
                                },
                            },
                        },
                        "InputData": {
                            "MaximumInputTime": 0,  # No limit: the image stays on screen until the "OK" button is pressed
                        },
                    },
                },
            },
        }

    def create_transaction(self, transaction_type, amount, payment_uuid, pos_session_id):
        """Start a payment or refund on the terminal.

        :return: Worldline's response (Ex: 202 { "requestId": "..." }) with the "exchange_id" of the request,
            used to poll its status, or {"error": "..."} otherwise
        """
        exchange_id = str(uuid.uuid4())  # Unique for each request sent: a retry of the same payment line is a new request
        json_body = self._get_transaction_json(transaction_type, amount, payment_uuid, pos_session_id, exchange_id)
        result = self._send_request(json_body)
        if "error" not in result:
            result["exchange_id"] = exchange_id
        return result

    def cancel_transaction(self, exchange_id, payment_uuid, pos_session_id):
        """Cancel the ongoing transaction identified by "exchange_id" on the terminal.

        Worldline answers with code 200 once the cancel signal is delivered to the terminal.
        If no transaction is in progress, the terminal ignores the request.
        """
        return self._send_request(self._get_cancel_json(exchange_id, payment_uuid, pos_session_id), endpoint="payments/abort")

    def get_transaction_status(self, exchange_id):
        """Ask the terminal for the raw status of the request identified by "exchange_id".
        Cannot be used to identify cancelled payments (through our own "Abort" request) as Worldline answers the same
        for an ongoing and aborted transaction"""
        return self._send_request(self._get_status_json(exchange_id), endpoint="status/sync")

    def display_image(self, image_base64):
        """Display pos_worldline/static/img/pos_logo_connected.png image on the terminal screen."""
        return self._send_request(self._get_image_screen_json(image_base64), endpoint="device")
