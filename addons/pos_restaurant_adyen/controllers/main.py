# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request
from odoo.addons.payment_adyen.controllers.main import AdyenController

_logger = logging.getLogger(__name__)


class PosRestaurantAdyenController(AdyenController):

    @http.route()
    def adyen_notification(self, **post):
        if post.get('eventCode') == 'AUTHORISATION_ADJUSTMENT':
            ref = post.get('originalReference')
            payment = request.env['pos.payment'].sudo().search([('transaction_id', '=', ref)], limit=1)
            if payment and post.get('success') == 'true':
                payment._adyen_capture_tip()
            else:
                _logger.warning('Authorisation adjustment for transaction_id %s failed', ref)
        return super(PosRestaurantAdyenController, self).adyen_notification(**post)
