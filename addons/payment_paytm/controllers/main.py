# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaytmController(http.Controller):
    _callback_url = '/payment/paytm/return/'

    @http.route('/payment/paytm/return', type='http', auth='public', csrf=False)
    def paytm_return(self, **post):
        _logger.info('Beginning Paytm form feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'paytm')
        return werkzeug.utils.redirect('/payment/process')
