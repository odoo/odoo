# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PaymentDemoController(http.Controller):
    _simulation_url = '/payment/demo/simulate_payment'

    @http.route(_simulation_url, type='json', auth='public')
    def demo_simulate_payment(self, **data):
        """ Simulate the response of a payment request.

        :param dict data: The simulated notification data.
        :return: None
        """
        request.env['payment.transaction'].sudo()._handle_notification_data('demo', data)
