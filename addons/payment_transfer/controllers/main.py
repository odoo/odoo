# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TransferController(http.Controller):
    _accept_url = '/payment/transfer/feedback'

    @http.route([
        '/payment/transfer/feedback',
    ], type='http', auth='public', csrf=False)
    def transfer_form_feedback(self, **post):
        _logger.info('Beginning _handle_feedback_data with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo()._handle_feedback_data(data=post, provider='transfer')
        return werkzeug.utils.redirect('/payment/status')
