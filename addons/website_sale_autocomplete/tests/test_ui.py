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

    def test_autocomplete_br(self):
        if self.env['ir.module.module']._get('l10n_br').state != 'installed':
            self.skipTest("l10n_br module is not installed")

        website = self.env['website'].get_current_website()
        website.company_id.account_fiscal_country_id = website.company_id.country_id = self.env.ref("base.br")

        with patch.object(AutoCompleteController, '_perform_complete_place_search',
                        lambda controller, *args, **kwargs: {
                            'country': [self.env['res.country'].search([('code', '=', 'BR')]).id, 'Brazil'],
                            'zip': '12345',
                            'street': 'Hello world',
                            'street_number': '42',
                            'street2': 'Bye Bye',
                            }), \
            patch.object(AutoCompleteController, '_perform_place_search',
                        lambda controller, *args, **kwargs: {
                            'results': [{
                                'formatted_address': f'Result {x}',
                                'google_place_id': MOCK_GOOGLE_ID
                            } for x in range(5)]}):

            website.google_places_api_key = MOCK_API_KEY
            self.start_tour('/shop/address', 'autocomplete_br_tour')

    def test_autocomplete_pe(self):
        if self.env['ir.module.module']._get('l10n_pe').state != 'installed':
            self.skipTest("l10n_pe module is not installed")

        website = self.env['website'].get_current_website()
        peru_country = self.env.ref("base.pe")
        website.company_id.account_fiscal_country_id = website.company_id.country_id = peru_country

        target_state = self.env['res.country.state'].search([('country_id', '=', peru_country.id)], limit=1)
        target_city = self.env['res.city'].search([('state_id', '=', target_state.id)], limit=1)

        with patch.object(AutoCompleteController, '_perform_complete_place_search',
                        lambda controller, *args, **kwargs: {
                            'country': [peru_country.id, 'Peru'],
                            'state': [target_state.id, target_state.name],
                            'city_id': [target_city.id, target_city.name],
                            'zip': '15001',
                            'street': 'Avenida Larco',
                            'street_number': '123',
                            'formatted_street_number': '123 Avenida Larco'
                            }), \
            patch.object(AutoCompleteController, '_perform_place_search',
                        lambda controller, *args, **kwargs: {
                            'results': [{
                                'formatted_address': f'Peru Result {x}',
                                'google_place_id': MOCK_GOOGLE_ID
                            } for x in range(5)]}):

            website.google_places_api_key = MOCK_API_KEY
            self.start_tour('/shop/address', 'autocomplete_pe_tour')
