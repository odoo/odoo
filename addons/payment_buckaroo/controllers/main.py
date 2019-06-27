# -*- coding: utf-8 -*-

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BuckarooController(http.Controller):
    _return_url = '/payment/buckaroo/return'
    _cancel_url = '/payment/buckaroo/cancel'
    _exception_url = '/payment/buckaroo/error'
    _reject_url = '/payment/buckaroo/reject'

    @http.route([
        '/payment/buckaroo/return',
        '/payment/buckaroo/cancel',
        '/payment/buckaroo/error',
        '/payment/buckaroo/reject',
    ], type='http', auth='public', csrf=False)
    def buckaroo_return(self, **post):
        """ Buckaroo."""
        _logger.info('Buckaroo: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'buckaroo')
        post = {key.upper(): value for key, value in post.items()}
        return_url = post.get('ADD_RETURNDATA') or '/'
        return werkzeug.utils.redirect('/payment/process')
