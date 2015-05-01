# -*- coding: utf-8 -*-

import logging
import pprint
import werkzeug

from openerp import http
from openerp.http import request

_logger = logging.getLogger(__name__)


class PayuMoneyController(http.Controller):
    _return_url = '/payment/payumoney/return'
    _cancel_url = '/payment/payumoney/cancel'
    _exception_url = '/payment/payumoney/error'

    @http.route([_return_url, _cancel_url, _exception_url], type='http', auth='public')
    def payu_return(self, **post):
        """ Payu Money."""
        _logger.info(
            'Payu: entering form_feedback with post data %s', pprint.pformat(post))
        return_url = '/'
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'payumoney')
            return_url = post.get('udf1')
        return werkzeug.utils.redirect(return_url)
