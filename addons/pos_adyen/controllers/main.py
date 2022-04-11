# coding: utf-8
import logging
import pprint
import json
import re
from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosAdyenController(http.Controller):
    @http.route('/pos_adyen/notification', type='json', methods=['POST'], auth='none', csrf=False)
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
                payment_method.adyen_latest_response = json.dumps(data)

                # Notify the pos ui that the payment status of the last payment request has been received.
                pos_config = self._get_pos_config(data['SaleToPOIResponse']['MessageHeader']['SaleID'])
                if pos_config:
                    message_value = [payment_method.id, payment_method.get_latest_adyen_status(data['SaleToPOIResponse']['MessageHeader']['SaleID'])]
                    pos_config.broadcast_pos_message('adyen-payment-status-received', message_value)
                else:
                    _logger.error("received a message for a terminal that doesn't belong in a pos config: %s", terminal_identifier)

        else:
            _logger.error('received a message for a terminal not registered in Odoo: %s', terminal_identifier)

    def _get_pos_config(self, sale_id: str):
        regex = re.compile(r'ID: (\d*)')
        mo = regex.search(sale_id)
        if mo:
            config_id = int(mo.group(1))
            return request.env['pos.config'].sudo().browse(config_id)
