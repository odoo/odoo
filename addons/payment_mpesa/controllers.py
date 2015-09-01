# -*- coding: utf-8 -*-
#from openerp import http
import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request

_logger = logging.getLogger(__name__)


class mpesaController(http.Controller):
    _accept_url = '/payment/mpesa/feedback'
    #_logger.info('*******************************88888888888888888888888888888888888888888888*************************88')
    @http.route([
        '/payment/mpesa/feedback',
    ], type='http', auth='none')
    def mpesa_form_feedback(self, **post):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        _logger.info('Beginning form_feedback with post data %s', pprint.pformat(post))
        request.registry['payment.transaction'].form_feedback(cr, uid, post, 'mpesa', context)
        return werkzeug.utils.redirect(post.pop('return_url', '/'))

