# coding: utf-8
import logging
import pprint
import json
from urllib.parse import parse_qs
from odoo import fields, http
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
        terminal_identifier = data['SaleToPOIResponse']['MessageHeader']['POIID']
        payment_method = request.env['pos.payment.method'].sudo().search([('adyen_terminal_identifier', '=', terminal_identifier)], limit=1)

        if payment_method:
            # These are only used to see if the terminal is reachable,
            # store the most recent ID we received.
            if data['SaleToPOIResponse'].get('DiagnosisResponse'):
                payment_method.adyen_latest_diagnosis = data['SaleToPOIResponse']['MessageHeader']['ServiceID']
            else:
                try:
                    adyen_additional_response = data['SaleToPOIResponse']['PaymentResponse']['Response']['AdditionalResponse']
                    parsed_adyen_additional_response = parse_qs(adyen_additional_response)
                    pos_hmac_metadata = parsed_adyen_additional_response.get('metadata.pos_hmac')
                    pos_hmac = pos_hmac_metadata[0] if pos_hmac_metadata and len(pos_hmac_metadata) == 1 else None

                    msg_header = data['SaleToPOIResponse']['MessageHeader']
                    if not pos_hmac or not consteq(pos_hmac, payment_method._get_hmac(msg_header['SaleID'], msg_header['ServiceID'], msg_header['POIID'], data['SaleToPOIResponse']['PaymentResponse']['SaleData']['SaleTransactionID']['TransactionID'])):
                        _logger.warning('Received an invalid Adyen event notification (invalid hmac): \n%s', pprint.pformat(data))
                        return

                    # The HMAC is removed to prevent anyone from using it in place of Adyen.
                    pos_hmac_metadata_raw = 'metadata.pos_hmac='+pos_hmac
                    safe_additional_response = adyen_additional_response.replace('&'+pos_hmac_metadata_raw, '').replace(pos_hmac_metadata_raw, '')
                    data['SaleToPOIResponse']['PaymentResponse']['Response']['AdditionalResponse'] = safe_additional_response
                except (KeyError, AttributeError):
                    _logger.warning('Received an invalid Adyen event notification: \n%s', pprint.pformat(data))
                    return
                payment_method.adyen_latest_response = json.dumps(data)
        else:
            _logger.error('received a message for a terminal not registered in Odoo: %s', terminal_identifier)
