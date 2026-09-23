import json
import logging
import pprint
from urllib.parse import parse_qs

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosAdyenController(http.Controller):
    @http.route(
        "/pos_adyen/notification",
        type="jsonrpc",
        methods=["POST"],
        auth="receiver",
        receiver="pos.payment.method:_receiver_for_adyen_terminal",
        receiver_event="adyen_terminal",
        save_session=False,
        typed=True,
    )
    def notification(self):
        adyen_pm_sudo = request.admission.subject
        data = request.admission.extra["data"]
        _logger.info("notification received from adyen:\n%s", pprint.pformat(data))
        # The HMAC is removed to prevent anyone from using it in place of Adyen.
        adyen_additional_response = data["SaleToPOIResponse"]["PaymentResponse"][
            "Response"
        ]["AdditionalResponse"]
        pos_hmac = PosAdyenController._get_additional_data_from_unparsed(
            adyen_additional_response, "metadata.pos_hmac"
        )
        pos_hmac_metadata_raw = "metadata.pos_hmac=" + pos_hmac
        data["SaleToPOIResponse"]["PaymentResponse"]["Response"][
            "AdditionalResponse"
        ] = adyen_additional_response.replace("&" + pos_hmac_metadata_raw, "").replace(
            pos_hmac_metadata_raw, ""
        )
        return self._process_payment_response(data, adyen_pm_sudo)

    @staticmethod
    def _get_additional_data_from_unparsed(adyen_additional_response, data_key):
        parsed_adyen_additional_response = parse_qs(adyen_additional_response)
        return PosAdyenController._get_additional_data_from_parsed(
            parsed_adyen_additional_response, data_key
        )

    @staticmethod
    def _get_additional_data_from_parsed(parsed_adyen_additional_response, data_key):
        data_value = parsed_adyen_additional_response.get(data_key)
        return data_value[0] if data_value and len(data_value) == 1 else None

    def _process_payment_response(self, data, adyen_pm_sudo):
        transaction_id = data["SaleToPOIResponse"]["PaymentResponse"]["SaleData"][
            "SaleTransactionID"
        ]["TransactionID"]
        if not transaction_id:
            return None
        transaction_id_parts = transaction_id.split("--")
        if len(transaction_id_parts) != 2:
            return None
        pos_session_id = int(transaction_id_parts[1])
        pos_session_sudo = request.env["pos.session"].sudo().browse(pos_session_id)
        adyen_pm_sudo.adyen_latest_response = json.dumps(data)
        pos_session_sudo.config_id._notify(
            "ADYEN_LATEST_RESPONSE", pos_session_sudo.config_id.id
        )
        return request.prepare_json_response(
            "[accepted]"
        )  # https://docs.adyen.com/point-of-sale/design-your-integration/choose-your-architecture/cloud/#guarantee
