# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
from random import randint

from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentTestController(http.Controller):

    @http.route('/payment/test/payments', type='json', auth='public')
    def process_payment(
            self, acquirer_id, reference, amount, currency_id, partner_id, cc_number, cc_cvc, cc_name, cc_expiry
    ):
        """ Simulate the result of a payment request and handle the response.

        :param int acquirer_id: The acquirer handling the transaction, as a `payment.acquirer` id
        :param str reference: The reference of the transaction
        :param int amount: The amount of the transaction in minor units of the currency
        :param int currency_id: The currency of the transaction, as a `res.currency` id
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        # :return: The JSON-formatted content of the response
        :rtype: dict
        """
        # In the future, we could generate fail or uncertain payment
        data = {
            'reference': reference,
            'amount': amount,
            'acquirer_id': acquirer_id,
            'currency_id': currency_id,
            'partner_id': partner_id,
            'fake_api_response': {
                'status': 'success',
                '3d_secure': False,
                'verified': True,
                'acquirer_reference': randint(1, 10000),
                'cc_number': 'X'*13 + cc_number[-3:],
                'cc_cvc': 'XXX',
                'cc_expiry': cc_expiry
            }
        }

        # Handle the payment request response
        _logger.info(f"payment Test request response:\n{pprint.pformat(data['fake_api_response'])}")
        request.env['payment.transaction'].sudo()._handle_feedback_data(
            'test', data,  # Match the transaction
        )
        return data['fake_api_response']

