# -*- coding: utf-8 -*-
import json
import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

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
    ], type='http', auth='none', csrf=False)
    def buckaroo_return(self, **post):
        """ Buckaroo."""
        _logger.info('Buckaroo: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, 'buckaroo', context=request.context)
        post = dict((key.upper(), value) for key, value in post.items())
        return_url = post.get('ADD_RETURNDATA') or '/'
        return werkzeug.utils.redirect(return_url)
