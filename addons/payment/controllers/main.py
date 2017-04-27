# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class Payment(http.Controller):

    @http.route(['/invoice/payment/<int:payment_request_id>'], type='http', auth="user", website=True)
    def invoice_pay_user(self, *args, **kwargs):
        return self.invoice_pay(*args, **kwargs)
