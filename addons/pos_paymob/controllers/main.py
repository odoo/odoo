# Part of Odoo. See LICENSE file for full copyright and licensing details.
import hashlib
import hmac
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# Exact field order Paymob concatenates for the callback HMAC ("parent.child" = nested).
PAYMOB_HMAC_FIELDS = [
    'amount_cents',
    'created_at',
    'currency',
    'error_occured',
    'has_parent_transaction',
    'id',
    'integration_id',
    'is_3d_secure',
    'is_auth',
    'is_capture',
    'is_refunded',
    'is_standalone_payment',
    'is_voided',
    'order.id',
    'owner',
    'pending',
    'source_data.pan',
    'source_data.sub_type',
    'source_data.type',
    'success',
]


class PosPaymobController(http.Controller):

    @http.route('/pos_paymob/notification', type='http', methods=['POST'], auth='public', csrf=False, save_session=False)
    def notification(self, **query):
        """ Authenticate Paymob's callback and relay the result to the POS over the bus. """
        payload = request.httprequest.get_json(silent=True)
        obj = payload.get('obj') if isinstance(payload, dict) else None
        if not obj:
            _logger.warning("Paymob callback received with no transaction object")
            return http.Response(status=400)

        # merchant_order_id = "<session>_<pm>_<order_uuid>_<ts>"; uuid has no "_", so parts[2].
        merchant_order_id = (obj.get('order') or {}).get('merchant_order_id') or ''
        parts = merchant_order_id.split('_')
        if len(parts) < 3:
            _logger.warning("Paymob callback with malformed merchant_order_id: %s", merchant_order_id)
            return http.Response(status=400)
        session_id, payment_method_id, order_uuid = parts[0], parts[1], parts[2]

        pos_session_sudo = request.env['pos.session'].sudo().browse(int(session_id)).exists()
        if not pos_session_sudo or pos_session_sudo.state != 'opened':
            _logger.warning("Paymob callback for an invalid/closed session: %s", session_id)
            # Not Paymob's fault; acknowledge so it is not retried.
            return http.Response('OK', status=200)

        payment_method_sudo = pos_session_sudo.config_id.payment_method_ids.filtered(
            lambda p: p.id == int(payment_method_id) and p.use_payment_terminal == 'paymob')
        if not payment_method_sudo:
            _logger.warning("Paymob callback for an invalid payment method: %s", payment_method_id)
            return http.Response('OK', status=200)

        # Skip HMAC verification for test mode refunds/voids.
        if not (payment_method_sudo.paymob_test_mode and (obj.get('is_refunded') or obj.get('is_voided'))):
            secret = payment_method_sudo.paymob_hmac_secret
            received_hmac = query.get('hmac')
            if not secret or not received_hmac or not self._verify_hmac(obj, received_hmac, secret):
                _logger.error("Paymob callback rejected: HMAC secret missing or signature invalid")
                return http.Response(status=401)

        source_data = obj.get('source_data') or {}
        data = obj.get('data') or {}
        extra_detail = data.get('extra_detail') or {}
        payment_method_sudo.paymob_latest_response = json.dumps({
            'order_uuid': order_uuid,
            'transaction_id': obj.get('id'),
            'success': bool(obj.get('success')) and not obj.get('pending') and not obj.get('error_occured'),
            'is_refunded': bool(obj.get('is_refunded')),
            'is_voided': bool(obj.get('is_voided')),
            'amount_cents': obj.get('amount_cents'),
            'message': data.get('message'),
            'card_no': source_data.get('pan'),
            'card_brand': source_data.get('sub_type'),
            'card_type': extra_detail.get('application_name'),
            'cardholder_name': extra_detail.get('card_holder_name'),
            'payment_ref_no': extra_detail.get('reference_number'),
            'payment_method_authcode': data.get('auth_code') or extra_detail.get('auth_code'),
            'payment_method_payment_mode': source_data.get('type'),
        })
        pos_session_sudo.config_id._notify('PAYMOB_LATEST_RESPONSE', {
            'config_id': pos_session_sudo.config_id.id,
        })
        return http.Response('OK', status=200)

    @staticmethod
    def _verify_hmac(obj, received_hmac, secret):
        if not secret:
            return False
        concatenated = ''.join(
            PosPaymobController._hmac_value(obj, field) for field in PAYMOB_HMAC_FIELDS
        )
        computed_hmac = hmac.new(secret.encode(), concatenated.encode(), hashlib.sha512).hexdigest()
        return hmac.compare_digest(computed_hmac, received_hmac)

    @staticmethod
    def _hmac_value(obj, field):
        """ Read a (nested) field and render it the way Paymob serializes it for the HMAC. """
        value = obj
        for key in field.split('.'):
            value = (value or {}).get(key)
        if isinstance(value, bool):
            return 'true' if value else 'false'
        if value is None:
            return 'false'
        return str(value)
