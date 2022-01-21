# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayuMoneyController(http.Controller):
    @http.route(['/payment/payumoney/return', '/payment/payumoney/cancel', '/payment/payumoney/error'], type='http', auth='public', csrf=False, save_session=False)
    def payu_return(self, **post):
        """ PayUmoney.
        The session cookie created by Odoo has not the attribute SameSite. Most of browsers will force this attribute
        with the value 'Lax'. After the payment, PayUMoney will perform a POST request on this route. For all these reasons,
        the cookie won't be added to the request. As a result, if we want to save the session, the server will create
        a new session cookie. Therefore, the previous session and all related information will be lost, so it will lead
        to undesirable behaviors. This is the reason why `save_session=False` is needed.
        """
        _logger.info(
            'PayUmoney: entering form_feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'payumoney')
        return werkzeug.utils.redirect('/payment/process')
