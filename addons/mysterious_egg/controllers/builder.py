# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class MysteriousEgg(http.Controller):

    @http.route('/mysterious_egg/builder_data', type="json", auth='user')
    def fetch_builder_data(self):
        company = request.env.company
        dashboard_data = {
            'company': {
                'street': company.street,
                'city': company.city,
                'state': company.state_id.display_name,
                'country': company.country_id.display_name,
            },
        }
        return dashboard_data
