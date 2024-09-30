# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.address_autocomplete.controllers.address_autocomplete import AutoCompleteController
from odoo.tests import patch, HttpCase, tagged

CONTROLLER_PATH = 'odoo.addons.address_autocomplete.controllers.address_autocomplete.AutoCompleteController'
MOCK_GOOGLE_ID = 'aHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g/dj1kUXc0dzlXZ1hjUQ=='
MOCK_API_KEY = 'Tm9ib2R5IGV4cGVjdHMgdGhlIFNwYW5pc2ggaW5xdWlzaXRpb24gIQ=='


@tagged('post_install', '-at_install')
class TestUI(HttpCase):
    def test_address_autocomplete(self):
        with patch.object(AutoCompleteController, '_perform_complete_place_search',
                          lambda controller, *args, **kwargs: {
                              'country_id': [self.env['res.country'].search([('code', '=', 'USA')]).id, 'United States'],
                              'state_id': [self.env['res.country.state'].search([('country_id.code', '=', 'USA')])[0].id, 'Alabama'],
                              'zip': '12345',
                              'city': 'A Fictional City',
                              'street': 'A fictional Street',
                              'street2': 'A fictional Street 2',
                              'number': 42,
                              'formatted_street_number': '42 A fictional Street'
                          }), \
                patch.object(AutoCompleteController, '_perform_place_search',
                             lambda controller, *args, **kwargs: {
                                 'results': [{
                                     'formatted_address': f'Result {x}',
                                     'google_place_id': MOCK_GOOGLE_ID
                                 } for x in range(5)]}):
            self.env['ir.config_parameter'].sudo().set_param('address_autocomplete.google_places_api_key', MOCK_API_KEY)
            self.start_tour('/odoo/companies', 'autocomplete_address_tour', login='admin')
