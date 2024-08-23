# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import logging
import re

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PosMercadoPagoWebhook(http.Controller):
    @http.route('/pos_mercado_pago/notification', methods=['POST'], type="http", auth="none", csrf=False)
    def notification(self):
        """ Process the notification sent by Mercado Pago

        Notification format is always json
        """
        _logger.debug('POST message received on the end point')

        # Check for mandatory keys in header
        x_request_id = request.httprequest.headers.get('X-Request-Id')
        if not x_request_id:
            _logger.debug('POST message received with no X-Request-Id in header')
            return http.Response(status=400)

        x_signature = request.httprequest.headers.get('X-Signature')
        if not x_signature:
            _logger.debug('POST message received with no X-Signature in header')
            return http.Response(status=400)

        ts_m = re.search(r"ts=(\d+)", x_signature)
        v1_m = re.search(r"v1=([a-f0-9]+)", x_signature)
        ts = ts_m.group(1) if ts_m else None
        v1 = v1_m.group(1) if v1_m else None
        if not ts or not v1:
            _logger.debug('Webhook bad X-Signature, ts: %s, v1: %s', ts, v1)
            return http.Response(status=400)

        # Check for payload
        data = request.httprequest.get_json(silent=True)
        if not data:
            _logger.debug('POST message received with no data')
            return http.Response(status=400)

        # If and only if this webhook is related with a payment intend (see payment_mercado_pago.js)
        # then the field data['additional_info']['external_reference'] contains a string
        # formated like "XXX_YYY_ZZZ" where "XXX" is the session_id, "YYY" is the payment_method_id,
        # and ZZZ is the pos_reference/uid for customer identification (Format ZZZZ-ZZZZ-ZZZZ)
        external_reference = data.get('additional_info', {}).get('external_reference')

        if not external_reference or not re.fullmatch(r'\d+_\d+[_\d-]*', external_reference):
            _logger.debug('POST message received with no or malformed "external_reference" key')
            return http.Response(status=400)

        session_id, payment_method_id, _ = external_reference.split('_')

        pos_session_sudo = request.env['pos.session'].sudo().browse(int(session_id))
        if not pos_session_sudo or pos_session_sudo.state != 'opened':
            _logger.error("Invalid session id: %s", session_id)
            # This error is not related with Mercado Pago, simply acknowledge Mercado Pago message
            return http.Response('OK', status=200)

        payment_method_sudo = pos_session_sudo.config_id.payment_method_ids.filtered(lambda p: p.id == int(payment_method_id))
        if not payment_method_sudo or payment_method_sudo.use_payment_terminal != 'mercado_pago':
            _logger.error("Invalid payment method id: %s", payment_method_id)
            # This error is not related with Mercado Pago, simply acknowledge Mercado Pago message
            return http.Response('OK', status=200)

        # We have to check if this comes from Mercado Pago with the secret key
        secret_key = payment_method_sudo.mp_webhook_secret_key
        signed_template = f"id:{data['id']};request-id:{x_request_id};ts:{ts};"
        cyphed_signature = hmac.new(secret_key.encode(), signed_template.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(cyphed_signature, v1):
            _logger.error('Webhook authenticating failure, ts: %s, v1: %s', ts, v1)
            return http.Response(status=401)

        _logger.debug('Webhook authenticated, POST message: %s', data)

        # Notify the frontend that we received a message from Mercado Pago
        pos_session_sudo.config_id._notify('MERCADO_PAGO_LATEST_MESSAGE', {
            'config_id': pos_session_sudo.config_id.id
        })

        # Acknowledge Mercado Pago message
        return http.Response('OK', status=200)
