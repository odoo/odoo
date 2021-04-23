# -*- coding: utf-8 -*-
import logging

from odoo.http import request

from odoo import http

_logger = logging.getLogger(__name__)


class StripeController(http.Controller):

    @http.route('/payment/stripe/webhook', type='json', auth='public', csrf=False)
    def stripe_webhook(self, **kwargs):
        request.env['payment.acquirer'].sudo()._handle_stripe_webhook(request.jsonrequest)
        return 'OK'
