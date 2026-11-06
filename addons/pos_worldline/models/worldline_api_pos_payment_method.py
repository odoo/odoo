import base64
import logging

from odoo import _, fields, models
from odoo.tools import file_open
from odoo.exceptions import AccessError

from .worldline_api_request import WorldlineApiRequest

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [("worldline_api", "Worldline API")]

    worldline_merchant_id = fields.Char("Worldline Merchant ID")
    worldline_terminal_id = fields.Char("Worldline Terminal ID")
    worldline_api_key = fields.Char("Worldline API Key", groups="point_of_sale.group_pos_manager")
    worldline_test_mode = fields.Boolean("Worldline Test Mode")
    worldline_webhook_url = fields.Char("Worldline Webhook URL", compute="_compute_worldline_webhook_url")

    def _compute_worldline_webhook_url(self):
        for record in self:
            record.worldline_webhook_url = f"{record.get_base_url()}/pos_worldline/webhook"

    def _worldline_check_access(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Only 'group_pos_user' are allowed to send a Worldline API payment request"))

    def _get_worldline_currency(self):
        return self.journal_id.currency_id or self.company_id.currency_id

    def worldline_create_transaction(self, transaction_type, amount, payment_uuid, pos_session_id):
        self.ensure_one()
        self._worldline_check_access()
        return WorldlineApiRequest(self).create_transaction(transaction_type, amount, payment_uuid, pos_session_id)

    def worldline_cancel_transaction(self, exchange_id, payment_uuid, pos_session_id):
        """Cancel the ongoing transaction identified by "exchange_id" on the terminal.

        Worldline answers synchronously (with 200) once the cancel signal is delivered to the terminal.
        If no transaction is in progress, the terminal ignores the request.
        The abort is confirmed only by a webhook notification answering the abort request.
        : exchange_id: The ExchangeIdentification of the ongoing request to cancel
        : payment_uuid: The identifier of the payment being cancelled
        : pos_session_id: The identifier of the POS session
        """
        self.ensure_one()
        self._worldline_check_access()
        return WorldlineApiRequest(self).cancel_transaction(exchange_id, payment_uuid, pos_session_id)

    def worldline_get_transaction_status(self, exchange_id):
        """Ask the terminal for the outcome of the transaction identified by "exchange_id".
        Called repeatedly until transaction/cancellation is complete as a fallback for webhook notifications
        :return: ``{"status": "pending"}`` while in progress, otherwise {"status": "done", ...}
            with the same keys as the webhook notification.
        """
        self.ensure_one()
        self._worldline_check_access()
        result = WorldlineApiRequest(self).get_transaction_status(exchange_id)
        _logger.debug("Worldline status request for transaction with exchange_id %s returned: %s", exchange_id, result)
        if "error" in result:
            _logger.info("Worldline status request for %s failed: %s", exchange_id, result["error"])
            return {"status": "pending", "error": result["error"]}
        status_response = (result.get("data") or {}).get("SaleToPOIMessageStatusResponse", {}).get("StatusResponse", {})
        status_data = status_response.get("MessageStatusResponseData", {})
        repeated_payment_response = status_data.get("RepeatedPaymentResponse") or {}
        # The outcome of the original transaction (e.g. cancelled on the terminal) is in TransactionResponse.
        transaction_response = status_data.get("TransactionResponse", {})
        if not repeated_payment_response:
            # Without a RepeatedPaymentResponse the transaction is still running on the terminal
            return {"status": "pending"}
        return {
            "status": "done",
            "exchange_id": exchange_id,
            **self._worldline_get_payment_result(transaction_response, repeated_payment_response, status_response.get("Environment", {})),
        }

    def _worldline_get_error_message(self, response):
        """Adapt user error depending on the error message in the "response" of the API request.

        :param response:
            {"Response": "Failed", "ResponseReason": "...", "AdditionalResponseInformation": "WPI_ERR_COND_BUSY:..."}

        :return: The error message, or "False" when the response carries no error reason
        """
        self.ensure_one()
        if not response.get("ResponseReason"):
            return False
        currency = self._get_worldline_currency()
        error_messages = {
            "WPI_ERR_COND_USER_TIMEOUT:EFT_E_CARDHOLDER_TIMEOUT": _("Transaction timed out on the terminal. Please try again."),
            "WPI_ERR_COND_USER_CANCEL:EFT_E_CARDHOLDER_ABORT": _("Transaction was cancelled on the terminal. Please try again."),
            "WPI_ERR_COND_GENERIC:CECR_ERROR_TRX_D_CARD_UNKNOWN": _("Transaction failed on the terminal. Please try again."),
            "WPI_ERR_COND_BUSY:Busy, another request already running": _("The terminal is currently busy with a different transaction. Please try again later."),
            "WPI_ERR_COND_INVALID_CURRENCY:EP2_E_CURR_NOT_INITIALIZED": _("The currency %s is not supported by the terminal. Contact Worldline to activate it.", currency.name),
            "WPI_ERR_COND_INVALID_AMOUNT:EFT_E_INPUT_INVALID_AMOUNT": _("The transaction was initiated with a wrong amount. Please try again."),
            "WPI_ERR_COND_TRANSACTION_TIMEOUT:Operation timed out": _("The transaction did not start on the terminal in time. Please make sure the terminal is turned on and connected to the internet, then try again."),
        }
        return error_messages.get(
            response.get("AdditionalResponseInformation"),
            _("An error has occured during transaction handling, please try again."),
        )

    def _worldline_get_authorisation_result(self, payment_response):
        return payment_response.get("RetailerPaymentResult", {}).get("TransactionResponse", {}).get("AuthorisationResult", {})

    def _worldline_is_approved(self, response, payment_response):
        """Check the response to see if the transaction was approved by the terminal.

        :param response: The "Response" block of the transaction
        :param payment_response: The "PaymentResponse" (or "RepeatedPaymentResponse") block
        """
        authorisation_result = self._worldline_get_authorisation_result(payment_response)
        return response.get("Response") == "Successful" and authorisation_result.get("ResponseToAuthorisation", {}).get("Response") == "Approved"

    def _worldline_get_payment_result(self, response, payment_response, environment):
        """Build the transaction outcome notified to the POS, shared by the webhook and the status polling.

        :param response: The "Response" block, carrying the error reason of a failed transaction
        :param payment_response: The "PaymentResponse" (or "RepeatedPaymentResponse") block
        :param environment: The "Environment" block, carrying the card used
        """
        self.ensure_one()
        success = self._worldline_is_approved(response, payment_response)
        result = {
            "transaction_id": payment_response.get("POITransactionIdentification", {}).get("TransactionReference"),
            "success": success,
        }
        if success:
            card = environment.get("Card", {})
            authorisation_result = self._worldline_get_authorisation_result(payment_response)
            result.update({
                "card_brand": card.get("CardBrand"),
                "card_no": (card.get("MaskedPAN") or "")[-4:] or False,
                "payment_method_authcode": authorisation_result.get("AuthorisationCode"),
            })
        elif error := self._worldline_get_error_message(response):
            result["error"] = error
        return result

    def _display_notification(self, level, message):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": level,
                "message": message,
            },
        }

    def action_worldline_test(self):
        """Test the credentials by showing a 'Connected to Odoo Point Of Sale' image on the terminal"""
        self.ensure_one()
        self._worldline_check_access()
        with file_open("pos_worldline/static/img/pos_logo_connected.png", "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()
        result = WorldlineApiRequest(self).display_image(image_base64)
        if "error" in result:
            return self._display_notification("danger", _("Worldline request failed: %s", result["error"]))
        return self._display_notification("success", _("Worldline request sent successfully. Check the terminal to see if the image is displayed."))
