# -*- coding: utf-8 -*-
import logging
import pprint

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _accept_url = '/payment/transfer/feedback'

    @website.route([
        '/payment/transfer/feedback',
    ], type='http', auth='admin')
    def transfer_form_feedback(self, **post):
        _logger.info('entering form_feedback with post data %s', pprint.pformat(post))  # debug
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['payment.transaction'].form_feedback(cr, uid, post, 'transfer', context)
        return request.redirect(post.pop('return_url', '/'))
