# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, patch, tagged

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import (
    AutoCompleteController,
)


CONTROLLER_PATH = 'odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete.AutoCompleteController'
MOCK_GOOGLE_ID = 'aHR0cHM6Ly93d3cueW91dHViZS5jb20vd2F0Y2g/dj1kUXc0dzlXZ1hjUQ=='
MOCK_API_KEY = 'Tm9ib2R5IGV4cGVjdHMgdGhlIFNwYW5pc2ggaW5xdWlzaXRpb24gIQ=='


@tagged('post_install', '-at_install')
class TestUI(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'A test product',
            'website_published': True,
            'list_price': 1
        })

    def test_autocomplete(self):
        with patch.object(AutoCompleteController, '_perform_complete_place_search',
                          lambda controller, *args, **kwargs: {
                              'country': [self.env['res.country'].search([('code', '=', 'USA')]).id, 'United States'],
                              'state': [self.env['res.country.state'].search([('country_id.code', '=', 'USA')])[0].id, 'Alabama'],
                              'zip': '12345',
                              'city': 'A Fictional City',
                              'street': 'A fictional Street',
                              'number': 42,
                              'formatted_street_number': '42 A fictional Street'
                          }), \
                patch.object(AutoCompleteController, '_perform_place_search',
                             lambda controller, *args, **kwargs: {
                                 'results': [{
                                     'formatted_address': f'Result {x}',
                                     'google_place_id': MOCK_GOOGLE_ID
                                 } for x in range(5)]}):
            self.env['website'].get_current_website().google_places_api_key = MOCK_API_KEY
            self.start_tour('/shop/address', 'autocomplete_tour')
