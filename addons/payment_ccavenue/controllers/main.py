# -*- coding: utf-8 -*-

import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class CCAvenueController(http.Controller):
    _return_url = '/payment/ccavenue/return'
    _cancel_url = '/payment/ccavenue/cancel'
    _exception_url = '/payment/ccavenue/error'
    _reject_url = '/payment/ccavenue/reject'

    @http.route([
        '/payment/ccavenue/return',
        '/payment/ccavenue/cancel',
        '/payment/ccavenue/error',
        '/payment/ccavenue/reject',
    ], type='http', auth='none')
    def ccavenue_return(self, **post):
        """ CCAvenue."""
        _logger.info('CCAvenue: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(request.cr, SUPERUSER_ID, post, 'ccavenue', context=request.context)
        return_url = post.pop('return_url', '')
        return werkzeug.utils.redirect(return_url)
