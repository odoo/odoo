# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayuLatamController(http.Controller):

    @http.route('/payment/payulatam/response', type='http', auth='public', csrf=False)
    def payulatam_response(self, **post):
        """ PayUlatam."""
        _logger.info('PayU Latam: entering form_feedback with post response data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'payulatam')
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/payulatam/webhook', type='http', auth='public', methods=['POST'], csrf=False)
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
            'merchantId': data.get('merchant_id'),
        }

        try:
            request.env['payment.transaction'].sudo().form_feedback(data, 'payulatam')
        except ValidationError:
            _logger.warning(
                'An error occurred while handling the confirmation from PayU with data:\n%s',
                pprint.pformat(data))
        return http.Response(status=200)
