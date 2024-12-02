import hashlib
import hmac
import json
import logging
import pprint

import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaymobController(http.Controller):

    @http.route(
        "/payment/paymob/return",
        type="json",
        auth="public",
        csrf=False,
        methods=["POST"],
    )
    def paymob_return(self, **kwargs):
        raw_data = request.httprequest.get_data()

        try:
            json_data = json.loads(raw_data)
        except json.JSONDecodeError:
            _logger.error("Invalid JSON data received.")
            return {"error": "Invalid JSON data"}, 400

        _logger.info("Paymob Parsed JSON data: %s", pprint.pformat(json_data))
        event_type = json_data.get("type")
        if event_type == "TOKEN":
            return self._handle_token(json_data)

        elif event_type == "TRANSACTION":
            return self._handle_transaction(json_data)

        else:
            _logger.error(
                "Received paymob callback with invalid event type.", event_type
            )
            return {"error": "Invalid event type"}, 400

    def _handle_transaction(self, json_data):
        received_hmac = request.httprequest.args.get("hmac")
        hmac_secret = (
            request.env["payment.provider"]
            .sudo()
            .search([("code", "=", "paymob")])
            .paymob_hmac
        )

        calculated_hmac = self._calculate_hmac(hmac_secret, json_data)

        if received_hmac != calculated_hmac:
            _logger.error("HMAC verification failed.")
            return "HMAC verification failed", 400

        transaction = (
            request.env["payment.transaction"]
            .sudo()
            ._get_tx_from_notification_data("paymob", json_data)
        )
        if not transaction:
            _logger.error("Transaction not found.")
            return "Transaction not found", 404

        transaction._handle_notification_data("paymob", json_data)

        return request.redirect("/payment/status")

    def _handle_token(self, json_data):
        token_data = json_data.get("obj")
        if not token_data:
            _logger.error("No token data found.")
            return {"error": "No token data found"}, 400

        try:
            # Get the payment provider
            paymob_provider = (
                request.env["payment.provider"]
                .sudo()
                .search([("code", "=", "paymob")], limit=1)
            )
            if not paymob_provider:
                _logger.error("Paymob provider not found.")
                return {"error": "Paymob provider not found"}, 404

            base_url = paymob_provider._paymob_get_api_url()

            # Get authentication token
            auth_url = f"{base_url}/api/auth/tokens"
            auth_response = requests.post(
                auth_url, json={"api_key": paymob_provider.paymob_api_key}
            )

            auth_token = auth_response.json().get("token")
            if not auth_token:
                _logger.error("Authentication token not found in response.")
                return {"error": "Token retrieval failed"}, 500

            # Transaction inquiry
            inquiry_url = f"{base_url}/api/ecommerce/orders/transaction_inquiry"
            headers = {"Authorization": f"Bearer {auth_token}"}
            payload = {"order_id": token_data["order_id"]}
            inquiry_response = requests.post(inquiry_url, json=payload, headers=headers)
            if inquiry_response.status_code != 200:
                _logger.error("Transaction inquiry failed.")
                return {"error": "Transaction inquiry failed"}, 500

            transaction_id = inquiry_response.json().get("id")

            # Get or create payment transaction
            payment_transaction = (
                request.env["payment.transaction"]
                .sudo()
                .search(
                    [
                        ("provider_reference", "=", transaction_id),
                        ("provider_code", "=", "paymob"),
                    ],
                    limit=1,
                )
            )
            clear_old_tokens = False
            payment_method = None

            if payment_transaction:
                payment_method = payment_transaction.payment_method_id.id
                clear_old_tokens = True

            if not payment_method:
                payment_method = (
                    request.env["payment.method"]
                    .sudo()
                    .search([("integration_id", ">", 0)], limit=1)
                    .id
                )

            # Create payment token
            partner = (
                request.env["res.partner"]
                .sudo()
                .search([("email", "=", token_data["email"])], limit=1)
            )
            if not partner:
                _logger.error("Partner not found for email: %s", token_data["email"])
                return {"error": "Partner not found"}, 404

            token_values = {
                "provider_id": paymob_provider.id,
                "partner_id": partner.id,
                "payment_method_id": payment_method,
                "payment_details": f"{token_data['card_subtype']} {token_data['masked_pan']}",
                "provider_ref": token_data["id"],
                "paymob_reference": token_data["token"],
                "active": True,
                "create_date": token_data["created_at"],
                "paymob_order_id": token_data["order_id"],
            }

            payment_token = request.env["payment.token"].sudo().create(token_values)
            _logger.info("Payment token created with ID: %s", payment_token.id)

            # Deactivate old tokens
            if clear_old_tokens:
                tokens = (
                    request.env["payment.token"]
                    .sudo()
                    .search(
                        [
                            ("payment_method_id", "=", payment_method),
                            ("partner_id", "=", partner.id),
                            ("payment_details", "=", token_values["payment_details"]),
                            ("active", "=", True),
                        ],
                        order="create_date desc",
                    )
                )
                if len(tokens) > 1:
                    tokens[1:].write({"active": False})

                payment_transaction.write({"token_id": payment_token.id})

            return {"status": "Token processed successfully"}, 200

        except Exception as e:
            _logger.error("Error processing token: %s", e)
            return {"error": f"Error processing token: {str(e)}"}, 500

    def _calculate_hmac(self, key, json_data):
        try:
            data = json_data["obj"].copy()
            data["order"] = data["order"]["id"]

            data["is_3d_secure"] = "true" if data["is_3d_secure"] else "false"
            data["is_auth"] = "true" if data["is_auth"] else "false"
            data["is_capture"] = "true" if data["is_capture"] else "false"
            data["is_refunded"] = "true" if data["is_refunded"] else "false"
            data["is_standalone_payment"] = (
                "true" if data["is_standalone_payment"] else "false"
            )
            data["is_voided"] = "true" if data["is_voided"] else "false"
            data["success"] = "true" if data["success"] else "false"
            data["error_occured"] = "true" if data["error_occured"] else "false"
            data["has_parent_transaction"] = (
                "true" if data["has_parent_transaction"] else "false"
            )
            data["pending"] = "true" if data["pending"] else "false"
            data["source_data_pan"] = data["source_data"]["pan"]
            data["source_data_type"] = data["source_data"]["type"]
            data["source_data_sub_type"] = data["source_data"]["sub_type"]

            concatenated_string = (
                str(data["amount_cents"])
                + str(data["created_at"])
                + str(data["currency"])
                + str(data["error_occured"])
                + str(data["has_parent_transaction"])
                + str(data["id"])
                + str(data["integration_id"])
                + str(data["is_3d_secure"])
                + str(data["is_auth"])
                + str(data["is_capture"])
                + str(data["is_refunded"])
                + str(data["is_standalone_payment"])
                + str(data["is_voided"])
                + str(data["order"])
                + str(data["owner"])
                + str(data["pending"])
                + str(data["source_data_pan"])
                + str(data["source_data_sub_type"])
                + str(data["source_data_type"])
                + str(data["success"])
            )

            calculated_hmac = hmac.new(
                key.encode("utf-8"), concatenated_string.encode("utf-8"), hashlib.sha512
            ).hexdigest()

            return calculated_hmac
        except Exception as e:
            _logger.error("Error calculating HMAC: %s", e)
            return None
