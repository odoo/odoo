# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class CCAvenueController(http.Controller):
    _return_url = '/payment/ccavenue/return/'
    _cancel_url = '/payment/ccavenue/cancel/'

    @http.route(['/payment/ccavenue/return', '/payment/ccavenue/cancel'], type='http', auth='public', csrf=False)
    def ccavenue_return(self, **post):
        _logger.info('CCAvenue: Entering form_feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'ccavenue')
        return werkzeug.utils.redirect('/payment/process')
