# -*- coding: utf-8 -*-

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website

try:
    import simplejson as json
except ImportError:
    import json
import logging
import pprint

_logger = logging.getLogger(__name__)


class AdyenController(http.Controller):
    _return_url = '/payment/adyen/return/'

    @website.route([
        '/payment/adyen/return/',
    ], type='http', auth='public')
    def adyen_return(self, **post):
        """ Paypal IPN. """
        _logger.info('Beginning Adyen form_feedback with post data %s', pprint.pformat(post))  # debug
        request.registry['payment.transaction'].form_feedback(request.cr, request.uid, post, 'adyen', context=request.context)
        return_url = post.pop('return_url', '')
        if not return_url:
            custom = json.loads(post.pop('merchantReturnData', '{}'))
            return_url = custom.pop('return_url', '/')
        return request.redirect(return_url)
