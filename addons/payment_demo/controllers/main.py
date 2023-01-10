# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PaymentDemoController(http.Controller):
    _simulation_url = '/payment/demo/simulate_payment'
    _country_list_url = '/payment/demo/country_list'

    @http.route(_simulation_url, type='json', auth='public')
    def demo_simulate_payment(self, **data):
        """ Simulate the response of a payment request.

        :param dict data: The simulated notification data.
        :return: None
        """
        request.env['payment.transaction'].sudo()._handle_notification_data('demo', data)

    @http.route(_country_list_url, type='json', auth='public')
    def get_country_list(self):
        countries = request.env['res.country'].search([])
        countries_list = {}
        for country in countries:
            countries_list[country.code] = country.name
        return countries_list
