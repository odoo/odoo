# -*- coding: utf-8 -*-
import logging
import pprint

from openerp.addons.web import http
from openerp.addons.web.http import request

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _accept_url = '/payment/transfer/feedback'

    @http.route([
        '/payment/transfer/feedback',
    ], type='http', auth='admin', website=True)
    def transfer_form_feedback(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        _logger.info('Beginning form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(cr, uid, post, 'transfer', context)
        return request.redirect(post.pop('return_url', '/'))
