# coding: utf-8
import logging
import pprint
import json
from odoo import http
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
        payment_method_sudo = request.env['pos.payment.method'].sudo().search([('adyen_terminal_identifier', '=', terminal_identifier)], limit=1)
        pos_session_id = int(data["SaleToPOIResponse"]["PaymentResponse"]["SaleData"]["SaleTransactionID"]["TransactionID"].split("-")[1])
        pos_session_sudo = request.env["pos.session"].sudo().browse(pos_session_id)

        if payment_method_sudo:
            # These are only used to see if the terminal is reachable,
            # store the most recent ID we received.
            if data['SaleToPOIResponse'].get('DiagnosisResponse'):
                payment_method_sudo.adyen_latest_diagnosis = data['SaleToPOIResponse']['MessageHeader']['ServiceID']
            else:
                payment_method_sudo.adyen_latest_response = json.dumps(data)
                request.env["bus.bus"].sudo()._sendone(pos_session_sudo._get_bus_channel_name(), "ADYEN_LATEST_RESPONSE", pos_session_sudo.config_id.id)
        else:
            _logger.error('received a message for a terminal not registered in Odoo: %s', terminal_identifier)
