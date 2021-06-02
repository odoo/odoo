# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayuMoneyController(http.Controller):
    @http.route(['/payment/payumoney/return', '/payment/payumoney/cancel', '/payment/payumoney/error'], type='http', auth='public', csrf=False)
    def payu_return(self, **post):
        """ PayUmoney."""
        _logger.info(
            'PayUmoney: entering form_feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'payumoney')
        return werkzeug.utils.redirect('/payment/process')
