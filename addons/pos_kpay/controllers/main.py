# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import logging
import pprint
import json
from odoo import http
from odoo.http import request
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

_logger = logging.getLogger(__name__)


PAYMENT_METHODS_MAPPING = {
    1: 'Visa',
    2: 'Mastercard',
    3: '中國銀聯',
    4: '微信',
    5: '支付寶',
    6: 'American Express',
    7: 'Diners Club',
    8: 'JCB',
    9: '銀聯雲閃付',
    11: '八達通',
    12: 'Payme',
}


class PosKpayController(http.Controller):

    @http.route('/pos_kpay/<string:kpay_unique_id>/notification', type='json', methods=['POST'], cors='*', auth='public', save_session=False)
    def notification(self, kpay_unique_id):
        data = json.loads(request.httprequest.data)

        _logger.info('notification received from kpay:\n%s', pprint.pformat(data))

        if '-' in kpay_unique_id:
            kpay_app_id, kpay_payment_type = kpay_unique_id.split('-')
        else:
            kpay_app_id = kpay_unique_id
            kpay_payment_type = False

        kpay_pm_sudo = request.env['pos.payment.method'].sudo().search([('kpay_app_id', '=', kpay_app_id), ('kpay_payment_type', '=', kpay_payment_type)], limit=1)
        if not kpay_pm_sudo:
            _logger.warning('Received an KPay event notification for a terminal not registered in Odoo: %s', kpay_app_id)
            return

        try:
            method = request.httprequest.method
            path = request.httprequest.path
            signature = request.httprequest.headers.get('signature', '')
            timestamp = request.httprequest.headers.get('timestamp', '')
            nonce_str = request.httprequest.headers.get('nonceStr', '')

            signaturePayload = f"{method}\n{path}\n{timestamp}\n{nonce_str}\n{request.httprequest.data.decode()}\n"
            public_key = load_pem_public_key(kpay_pm_sudo.kpay_public_key.encode(), backend=default_backend())
            if isinstance(public_key, RSAPublicKey):
                public_key.verify(signature=base64.b64decode(signature), data=signaturePayload.encode(), padding=padding.PKCS1v15(), algorithm=hashes.SHA256())
            else:
                _logger.error('Unsupported public key type')
                return
        except InvalidSignature:
            _logger.error('Invalid signature received from KPay')
            return

        return self._process_payment_response(data, kpay_pm_sudo)

    def _process_payment_response(self, data, kpay_pm_sudo):
        if data.get('transactionType') == 6:
            return self._process_refund_response(data, kpay_pm_sudo)

        transaction_id = data.get('outTradeNO')
        if not transaction_id:
            return
        transaction_id = transaction_id.split("Order")[-1].strip() if "Order" in transaction_id else transaction_id
        transaction_id_parts = transaction_id.split("-")
        if len(transaction_id_parts) != 4:
            return
        pos_session_id = int(transaction_id_parts[0])
        pos_session_sudo = request.env["pos.session"].sudo().browse(pos_session_id)
        kpay_pm_sudo.kpay_latest_response = json.dumps(data)
        pos_session_sudo.config_id._notify("KPAY_LATEST_RESPONSE", pos_session_sudo.config_id.id)
        return request.make_json_response({'code': 10000})

    def _process_refund_response(self, data, kpay_pm_sudo):
        if data.get("payResult") != 2:
            return
        payment_transaction_id = data.get('refNo') or data.get('transactionNo')
        pos_payment_sudo = request.env['pos.payment'].sudo().search([('transaction_id', '=', payment_transaction_id)], limit=1)
        pos_order_sudo = pos_payment_sudo.pos_order_id
        if not pos_order_sudo:
            return
        refund_order = pos_order_sudo._refund()
        refund_order.add_payment({
            'pos_order_id': refund_order.id,
            'amount': -float(data.get('payAmount')) * refund_order.currency_id.rounding,
            'payment_method_id': kpay_pm_sudo.id,
            'payment_method_payment_mode': PAYMENT_METHODS_MAPPING.get(data.get('payMethod')),
        })
        if refund_order.state == 'draft' and refund_order._is_pos_order_paid():
            refund_order._process_saved_order(False)
            if refund_order.state in {'paid', 'done', 'invoiced'}:
                refund_order._send_order()
        return request.make_json_response({'code': 10000})
