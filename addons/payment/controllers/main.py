# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import route, request, Controller


class PaymentController(Controller):
    @route('/payment/get_provider', type='json', auth='public')
    def get_acquirer_provider(self, acquirer_id, **post):
        acq = request.env['payment.acquirer'].browse(acquirer_id)
        return acq.provider
