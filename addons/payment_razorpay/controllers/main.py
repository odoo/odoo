# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class RazorpayController(http.Controller):

    @http.route(['/payment/razorpay/capture'], type='http', auth='public', csrf=False)
    def razorpay_capture(self, **kwargs):
        payment_id = kwargs.get('payment_id')
        if payment_id:
            response = request.env['payment.transaction'].sudo()._create_razorpay_capture(kwargs)
            if response.get('id'):
                _logger.info('Razorpay: entering form_feedback with post data %s', pprint.pformat(response))
                request.env['payment.transaction'].sudo().form_feedback(response, 'razorpay')
        return '/payment/process'
