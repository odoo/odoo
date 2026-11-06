# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import http
from odoo.http import request
from odoo.tools import verify_hash_signed

_logger = logging.getLogger(__name__)


class PosWorldline(http.Controller):
    @http.route('/pos_worldline/webhook', methods=['POST'], auth='public', type='http', save_session=False, csrf=False)
    def worldline_webhook(self, payload=None):
        data = request.get_json_data()
        _logger.debug("Received Worldline webhook notification: %s", data)

        sale_to_poi_response = (data.get('data') or {}).get('SaleToPOIServiceResponse', {})
        header = sale_to_poi_response.get('Header', {})

        # Ignore webhook polluting notifications like /status endpoint ones
        if header.get('MessageFunction') not in ('SaleFinancialServiceResponse', 'Abort'):
            return request.make_json_response({})

        # The payload is signed by us and used to identify payment method / pos session and payment line
        exchange_id = header.get('ExchangeIdentification')
        try:
            decoded_payload = verify_hash_signed(request.env(su=True), 'pos_worldline', payload) if payload else None
        except ValueError:
            decoded_payload = None
        if not decoded_payload or not exchange_id or decoded_payload.get('exchange_id') != exchange_id:
            _logger.warning("Received a Worldline webhook with an invalid payload for ExchangeIdentification: %s", exchange_id)
            return request.make_json_response({})

        if not decoded_payload.get('payment_uuid'):
            return request.make_json_response({})

        service_response = sale_to_poi_response.get('ServiceResponse', {})
        response = service_response.get('Response', {})

        payment_method_sudo = request.env['pos.payment.method'].sudo().browse(decoded_payload['payment_method_id']).exists()
        if not payment_method_sudo:
            _logger.warning("No payment method found matching Worldline webhook, ignoring")
            return request.make_json_response({})
        pos_session_sudo = request.env['pos.session'].sudo().browse(decoded_payload['pos_session_id']).exists()
        if not pos_session_sudo:
            _logger.warning("No POS session found matching Worldline webhook, ignoring")
            return request.make_json_response({})

        payment_response = service_response.get('PaymentResponse', {})
        message = {
            'payment_uuid': decoded_payload['payment_uuid'],
            'exchange_id': exchange_id,
            'pos_session_id': pos_session_sudo.id,
            **payment_method_sudo._worldline_get_payment_result(response, payment_response, service_response.get('Environment', {})),
        }
        pos_session_sudo.config_id._notify('WORLDLINE_API_PAYMENT_STATUS', message)
        return request.make_json_response({})
