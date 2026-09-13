# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging
from urllib.parse import urlencode

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

ANDROID_RESULT_KEYS = {
    'SERVER_TRANSACTION_ID': 'transaction_id',
    'CLIENT_TRANSACTION_ID': 'client_transaction_id',
    'REQUEST_METADATA': 'state',
    'ERROR_CODE': 'error_code',
    'ERROR_DESCRIPTION': 'error_description',
}


class PosSquareController(http.Controller):

    @http.route('/pos_square/callback', type='http', auth='public', methods=['GET'])
    def square_payment_callback(self, **kwargs):
        """Record the transaction result and send the device back to the PoS."""
        result = self._get_square_result(kwargs)
        # Square only redirects to one registered callback URL, so state carries the uuids.
        order_uuid, __, payment_uuid = (result.get('state') or '').partition('|')

        pos_order_sudo = request.env['pos.order'].sudo().search([('uuid', '=', order_uuid)], limit=1)
        payment_sudo = pos_order_sudo.payment_ids.filtered(lambda p: p.uuid == payment_uuid)
        if not payment_sudo:
            _logger.warning("received a Square callback for an unknown payment line")
            return request.not_found()

        error = result.get('error_description') or result.get('error_code')
        if error:
            _logger.info("received a failed payment callback from Square: %s", error)
            payment_sudo.payment_status = 'error'
        else:
            payment_sudo.write({
                'payment_status': 'done',
                # A payment taken while the device was offline only gets a client-side id.
                'transaction_id': result.get('transaction_id') or result.get('client_transaction_id'),
            })
            if pos_order_sudo.amount_difference == 0 and all(
                payment.payment_status == 'done' for payment in pos_order_sudo.payment_ids
            ):
                pos_order_sudo.state = 'paid'
                return self._redirect_to_pos(pos_order_sudo, 'resume', {'post_validate': 1})

        return self._redirect_to_pos(pos_order_sudo, 'payment', {
            'square_status': 'error' if error else 'success',
            'square_message': error or '',
            'square_payment': payment_uuid,
        })

    def _get_square_result(self, params):
        """Return the transaction result of both platforms as iOS-keyed values."""
        result = json.loads(params.get('data') or '{}')
        for android_key, key in ANDROID_RESULT_KEYS.items():
            if value := params.get(f'com.squareup.pos.{android_key}'):
                # Android namespaces its error codes, the other values never carry the prefix.
                result[key] = value.removeprefix('com.squareup.pos.')
        return result

    def _redirect_to_pos(self, pos_order_sudo, screen, params):
        """Redirect to `screen` of the PoS, reopening the Odoo mobile app if it is installed."""
        base_url = request.env['ir.config_parameter'].sudo().get_str('web.base.url')
        pos_url = (
            f"{base_url}/pos/ui/{pos_order_sudo.config_id.id}/{screen}/{pos_order_sudo.uuid}"
            f"?{urlencode(params)}"
        )
        return request.redirect(f"https://redirect-url.email/?{urlencode({'link': pos_url})}", local=False)
