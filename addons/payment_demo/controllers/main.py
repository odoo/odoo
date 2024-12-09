# Part of Odoo. See LICENSE file for full copyright and licensing details.

from math import trunc

from odoo import http
from odoo.http import request

from odoo.addons.payment.controllers.portal import PaymentPortal


class PaymentDemoController(PaymentPortal):
    _simulation_url = '/payment/demo/simulate_payment'

    @http.route(_simulation_url, type='json', auth='public')
    def demo_simulate_payment(self, **data):
        """ Simulate the response of a payment request.

        :param dict data: The simulated notification data.
        :return: None
        """
        __import__('ipdb').set_trace()
        request.env['payment.transaction'].sudo()._handle_notification_data('demo', data)

    def _create_transaction(self, amount, **kwargs):
        res = super()._create_transaction(amount=float(trunc(amount)), **kwargs)
        __import__('ipdb').set_trace()
        return res
