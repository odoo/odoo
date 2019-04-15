# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.payment_adyen.controllers.main import AdyenController

_logger = logging.getLogger(__name__)


class PosAdyenTippingController(AdyenController):
    @http.route()
    def adyen_notification(self, **post):
        if post.get('eventCode') == 'CAPTURE':
            _logger.info('received capture:\n%s', pprint.pformat(post))
            ref = post.get('originalReference')
            payment = request.env['pos.payment'].sudo().search([('transaction_id', '=', ref)], limit=1)
            if payment and post.get('success') == 'true':
                payment.captured = True
                _logger.info('successfully captured transaction_id %s (pos.payment ID: %s)', ref, payment.id)
            else:
                _logger.warning('couldn\'t find transaction_id %s', ref)
        return super(PosAdyenTippingController, self).adyen_notification(**post)
