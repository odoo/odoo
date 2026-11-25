import logging

from odoo import fields, models

from .worldline_api_request import WorldlineApiRequest

_logger = logging.getLogger(__name__)


class PosElectronicPayment(models.Model):
    _inherit = "pos.electronic.payment"

    worldline_merchant_id = fields.Char("Worldline Merchant ID")
    worldline_terminal_id = fields.Char("Worldline Terminal ID")
    worldline_api_key = fields.Char("Worldline API Key", groups="pos_payment_method.group_payment_method_admin")
    worldline_test_mode = fields.Boolean("Worldline Test Mode")
    worldline_webhook_url = fields.Char("Worldline Webhook URL", compute="_compute_worldline_webhook_url")

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [("worldline", "Worldline")]

    def _compute_worldline_webhook_url(self):
        for record in self:
            record.worldline_webhook_url = f"{record.get_base_url()}/pos_worldline/webhook"

    def _worldline_get_authorisation_result(self, payment_response: dict):
        return payment_response.get("RetailerPaymentResult", {}).get("TransactionResponse", {}).get("AuthorisationResult", {})

    def _worldline_is_approved(self, response: dict, payment_response: dict):
        """Check the response to see if the transaction was approved by the terminal.

        :param response: The "Response" block of the transaction
        :param payment_response: The "PaymentResponse" (or "RepeatedPaymentResponse") block
        """
        authorisation_result = self._worldline_get_authorisation_result(payment_response)
        return response.get("Response") == "Successful" and authorisation_result.get("ResponseToAuthorisation", {}).get("Response") == "Approved"

    def _worldline_get_error_message(self, response: dict):
        """Adapt user error depending on the error message in the "response" of the API request.

        :param response:
            {"Response": "Failed", "ResponseReason": "...", "AdditionalResponseInformation": "WPI_ERR_COND_BUSY:..."}

        :return: The error message, or "None" when the response carries no error reason
        """
        if not response.get("ResponseReason"):
            return None
        error_messages = {
            "WPI_ERR_COND_ABORTED:Payment aborted!": None,  # Cancelled from POS, no need for error message
            "WPI_ERR_COND_USER_TIMEOUT:EFT_E_CARDHOLDER_TIMEOUT": self.env._("Transaction timed out on the terminal. Please try again."),
            "WPI_ERR_COND_USER_CANCEL:EFT_E_CARDHOLDER_ABORT": self.env._("Transaction was cancelled on the terminal. Please try again."),
            "WPI_ERR_COND_GENERIC:CECR_ERROR_TRX_D_CARD_UNKNOWN": self.env._("Transaction failed on the terminal. Please try again."),
            "WPI_ERR_COND_BUSY:Busy, another request already running": self.env._("The terminal is currently busy with a different transaction. Please try again later."),
            "WPI_ERR_COND_INVALID_CURRENCY:EP2_E_CURR_NOT_INITIALIZED": self.env._("This currency is not supported by the terminal. Contact Worldline to activate it."),
            "WPI_ERR_COND_INVALID_AMOUNT:EFT_E_INPUT_INVALID_AMOUNT": self.env._("The transaction was initiated with a wrong amount. Please try again."),
            "WPI_ERR_COND_TRANSACTION_TIMEOUT:Operation timed out": self.env._("The transaction did not start on the terminal in time. Please make sure the terminal is turned on and connected to the internet, then try again."),
        }
        worldline_error_code = response.get("AdditionalResponseInformation", "")
        return error_messages.get(worldline_error_code, self.env._("An error has occured during transaction handling, please try again."))

    def _worldline_get_payment_result(self, response, payment_response, environment):
        """Build the transaction outcome notified to the POS, shared by the webhook and the status polling.

        :param response: The "Response" block, carrying the error reason of a failed transaction
        :param payment_response: The "PaymentResponse" (or "RepeatedPaymentResponse") block
        :param environment: The "Environment" block, carrying the card used
        """
        if self._worldline_is_approved(response, payment_response):
            card = environment.get("Card", {})
            authorisation_result = self._worldline_get_authorisation_result(payment_response)
            return {
                "status": "paid",
                "final_transaction_id": payment_response.get("POITransactionIdentification", {}).get("TransactionReference"),
                "card_brand": card.get("CardBrand"),
                "card_no": card.get("MaskedPAN"),
                "payment_method_authcode": authorisation_result.get("AuthorisationCode"),
            }
        return {
            "status": "failed",
            "error": self._worldline_get_error_message(response),
        }

    def _start_payment(self, amount: float, currency, extra_args: dict) -> dict:
        if self.payment_provider != "worldline":
            return super()._start_payment(amount, currency, extra_args)

        result = WorldlineApiRequest(self, currency).create_transaction("CardPayment", amount)
        if "error" in result:
            return {"status": "failed", "error": result["error"]}
        return {"transaction_id": result["exchange_id"]}

    def _start_refund(self, amount: float, currency, extra_args: dict) -> dict:
        if self.payment_provider != "worldline":
            return super()._start_refund(amount, currency, extra_args)

        result = WorldlineApiRequest(self, currency).create_transaction("Refund", amount)
        if "error" in result:
            return {"status": "failed", "error": result["error"]}
        return {"transaction_id": result["exchange_id"]}

    def _cancel_transaction(self, transaction_id: str) -> dict:
        if self.payment_provider != "worldline":
            return super()._cancel_transaction(transaction_id)

        result = WorldlineApiRequest(self).cancel_transaction(transaction_id)
        if "error" in result:
            return {"error": result["error"]}
        return {}

    def _get_transaction_status(self, transaction_id: str) -> dict:
        if self.payment_provider != "worldline":
            return super()._get_transaction_status(transaction_id)

        result = WorldlineApiRequest(self).get_transaction_status(transaction_id)
        _logger.debug("Worldline status request for transaction with exchange_id %s returned: %s", transaction_id, result)

        if "error" in result:
            _logger.info("Worldline status request for %s failed: %s", transaction_id, result["error"])
            return {"error": result["error"]}

        status_response = result.get("data", {}).get("SaleToPOIMessageStatusResponse", {}).get("StatusResponse", {})
        status_data = status_response.get("MessageStatusResponseData", {})
        repeated_payment_response = status_data.get("RepeatedPaymentResponse") or {}
        # The outcome of the original transaction (e.g. cancelled on the terminal) is in TransactionResponse.
        transaction_response = status_data.get("TransactionResponse", {})
        if not repeated_payment_response:
            # Without a RepeatedPaymentResponse the transaction is still running on the terminal
            return {"status": "pending"}
        return self._worldline_get_payment_result(transaction_response, repeated_payment_response, status_response.get("Environment", {}))
