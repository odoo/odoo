import json
import logging
from urllib.parse import quote, unquote

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosSquareController(http.Controller):
    @http.route('/pos_square/callback', type='http', auth='none', csrf=False, readonly=False)
    def notification(self, **kwargs):
        payload = kwargs.get('payload')
        returned_data = kwargs.get('data', '{}')
        redirect_url = fallback_url = ''

        # Redirecting to Square from the POS Payment Screen
        if payload:
            if kwargs.get('is_ios') == 'true':
                redirect_url = f'square-commerce-v1://payment/create?data={quote(payload)}'
                fallback_url = "https://apps.apple.com/us/app/square-point-of-sale-pos/id335393788"
            else:
                redirect_url = f'intent:#Intent;{payload};end'
                fallback_url = "https://play.google.com/store/apps/details?id=com.squareup"

        returned_data = json.loads(returned_data)

        # Payload returned from square after payment via Android
        if any('com.squareup.pos.' in key for key in kwargs):
            # Translate android keys to match iOS keys
            translation_map = {
                    "SERVER_TRANSACTION_ID": "transaction_id",
                    "CLIENT_TRANSACTION_ID": "client_transaction_id",
                    "ERROR_CODE": "error_code",
                    "REQUEST_METADATA": "state",
                    "ERROR_DESCRIPTION": "error_description",
            }
            for key, ios_key in translation_map.items():
                value = kwargs.get(f"com.squareup.pos.{key}")
                if value:
                    returned_data[ios_key] = value.removeprefix("com.squareup.pos.")

        # Payload returned from square after payment via iOS
        if returned_data:
            state = unquote(returned_data.get('state'))
            session_id, _, payment_method_id, line_id = state.split('|')
            square_pm_sudo = request.env['pos.payment.method'].sudo().browse(int(payment_method_id))
            pos_session_sudo = request.env['pos.session'].sudo().browse(int(session_id))
            square_pm_sudo.square_latest_response = json.dumps(returned_data)
            pos_session_sudo.config_id._notify("SQUARE_LATEST_RESPONSE", {
                'response': returned_data,
                'line_uuid': line_id,
            })

        return request.render('pos_square.direct_display', {
            'redirect_url': redirect_url,
            'fallback_url': fallback_url,
        })
