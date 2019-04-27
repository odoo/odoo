# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayuLatamController(http.Controller):

    @http.route('/payment/payulatam/response', type='http', auth='public', csrf=False)
    def payulatam_response(self, **post):
        """ PayUlatam."""
        _logger.info('PayU Latam: entering form_feedback with post response data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'payulatam')
        return werkzeug.utils.redirect('/payment/process')
