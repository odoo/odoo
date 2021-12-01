# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import hmac

import werkzeug.exceptions

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayuLatamController(http.Controller):
    _return_url = '/payment/payulatam/return'
    _webhook_url = '/payment/payulatam/webhook'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def payulatam_return(self, **data):
        _logger.info("handling redirection from PayU Latam with data:\n%s", pprint.pformat(data))
        self._verify_signature(data)
        request.env['payment.transaction'].sudo()._handle_notification_data('payulatam', data)
        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def payulatam_webhook(self, **data):
        _logger.info("handling confirmation from PayU Latam with data:\n%s", pprint.pformat(data))
        state_pol = data.get('state_pol')
        if state_pol == '4':
            lapTransactionState = 'APPROVED'
        elif state_pol == '6':
            lapTransactionState = 'DECLINED'
        elif state_pol == '5':
            lapTransactionState = 'EXPIRED'
        else:
            lapTransactionState = f'INVALID state_pol {state_pol}'

        data = {
            'signature': data.get('sign'),
            'TX_VALUE': data.get('value'),
            'currency': data.get('currency'),
            'referenceCode': data.get('reference_sale'),
            'transactionId': data.get('transaction_id'),
            'transactionState': data.get('state_pol'),
            'message': data.get('response_message_pol'),
            'lapTransactionState': lapTransactionState,
        }

        self._verify_signature(data)

        try:
            request.env['payment.transaction'].sudo()._handle_notification_data('payulatam', data)
        except ValidationError:
            _logger.warning(
                'An error occurred while handling the confirmation from PayU with data:\n%s',
                pprint.pformat(data))
        return http.Response(status=200)

    def _verify_signature(self, data):
        sign = data.get('signature')
        reference = data.get('referenceCode')
        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', reference), ('provider', '=', 'payulatam')])
        sign_check = tx.acquirer_id._payulatam_generate_sign(data, incoming=True)
        if not hmac.compare_digest(sign_check, sign):
            _logger.warning('Invalid signature %s', sign)
            raise werkzeug.exceptions.Forbidden
