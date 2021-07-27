# -*- coding: utf-8 -*-
import json
import logging

from odoo.http import request

from odoo import http

_logger = logging.getLogger(__name__)


class StripeController(http.Controller):

    @http.route('/payment/stripe/webhook', type='json', auth='public', csrf=False)
    def stripe_webhook(self, **kwargs):
        data = json.loads(request.httprequest.data)
        request.env['payment.acquirer'].sudo()._handle_stripe_webhook(data)
        return 'OK'
