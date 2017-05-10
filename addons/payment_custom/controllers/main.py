# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from odoo.http import Controller, request, route

_logger = logging.getLogger(__name__)


class CustomProviderController(Controller):

    @route('/payment/custom/feedback', type='http', auth='none', csrf=False)
    def custom_form_feedback(self, **post):
        _logger.info('Beginning form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'custom')
        return werkzeug.utils.redirect(post.pop('return_url', '/'))
