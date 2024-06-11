# coding: utf-8
import logging
import pprint
import json
from urllib.parse import parse_qs
from odoo import http
from odoo.http import request
from odoo.tools import consteq

_logger = logging.getLogger(__name__)


class PosAdyenController(http.Controller):

    @http.route('/pos_adyen/notification', type='json', methods=['POST'], auth='public', csrf=False, save_session=False)
    def notification(self):
        data = json.loads(request.httprequest.data)

        # ignore if it's not a response to a sales request
        if not data.get('SaleToPOIResponse'):
            return

        _logger.info('notification received from adyen:\n%s', pprint.pformat(data))

        msg_header = data['SaleToPOIResponse'].get('MessageHeader')
        if not msg_header \
            or msg_header.get('ProtocolVersion') != '3.0' \
            or msg_header.get('MessageClass') != 'Service' \
            or msg_header.get('MessageType') != 'Response' \
            or msg_header.get('MessageCategory') != 'Payment' \
            or not msg_header.get('POIID'):
            _logger.warning('Received an unexpected Adyen notification')
            return

        terminal_identifier = msg_header['POIID']
        adyen_pm_sudo = request.env['pos.payment.method'].sudo().search([('adyen_terminal_identifier', '=', terminal_identifier)], limit=1)
        if not adyen_pm_sudo:
            _logger.warning('Received an Adyen event notification for a terminal not registered in Odoo: %s', terminal_identifier)
            return

        try:
            adyen_additional_response = data['SaleToPOIResponse']['PaymentResponse']['Response']['AdditionalResponse']
            pos_hmac = PosAdyenController._get_additional_data_from_unparsed(adyen_additional_response, 'metadata.pos_hmac')

            if not pos_hmac or not consteq(pos_hmac, adyen_pm_sudo._get_hmac(msg_header['SaleID'], msg_header['ServiceID'], msg_header['POIID'], data['SaleToPOIResponse']['PaymentResponse']['SaleData']['SaleTransactionID']['TransactionID'])):
                _logger.warning('Received an invalid Adyen event notification (invalid hmac): \n%s', pprint.pformat(data))
                return

            # The HMAC is removed to prevent anyone from using it in place of Adyen.
            pos_hmac_metadata_raw = 'metadata.pos_hmac='+pos_hmac
            safe_additional_response = adyen_additional_response.replace('&'+pos_hmac_metadata_raw, '').replace(pos_hmac_metadata_raw, '')
            data['SaleToPOIResponse']['PaymentResponse']['Response']['AdditionalResponse'] = safe_additional_response
        except (KeyError, AttributeError):
            _logger.warning('Received an invalid Adyen event notification: \n%s', pprint.pformat(data))
            return

        return self._process_payment_response(data, adyen_pm_sudo)

    @staticmethod
    def _get_additional_data_from_unparsed(adyen_additional_response, data_key):
        parsed_adyen_additional_response = parse_qs(adyen_additional_response)
        return PosAdyenController._get_additional_data_from_parsed(parsed_adyen_additional_response, data_key)

    @staticmethod
    def _get_additional_data_from_parsed(parsed_adyen_additional_response, data_key):
        data_value = parsed_adyen_additional_response.get(data_key)
        return data_value[0] if data_value and len(data_value) == 1 else None

    def _process_payment_response(self, data, adyen_pm_sudo):
        transaction_id = data['SaleToPOIResponse']['PaymentResponse']['SaleData']['SaleTransactionID']['TransactionID']
        if not transaction_id:
            return
        transaction_id_parts = transaction_id.split("--")
        if len(transaction_id_parts) != 2:
            return
        pos_session_id = int(transaction_id_parts[1])
        pos_session_sudo = request.env["pos.session"].sudo().browse(pos_session_id)
        adyen_pm_sudo.adyen_latest_response = json.dumps(data)
        request.env['bus.bus'].sudo()._sendone(pos_session_sudo._get_bus_channel_name(), 'ADYEN_LATEST_RESPONSE', pos_session_sudo.config_id.id)
        return request.make_json_response('[accepted]') # https://docs.adyen.com/point-of-sale/design-your-integration/choose-your-architecture/cloud/#guarantee
