# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import (
    AutoCompleteController,
    USE_PLACES_API_NEW_PARAM,
)
from odoo.tests import HttpCase, tagged

from .mock_google_places import MockResponse

CONTROLLER_MODULE = 'odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete'
MOCK_API_KEY = 'Tm9ib2R5IGV4cGVjdHMgdGhlIFNwYW5pc2ggaW5xdWlzaXRpb24gIQ=='


@tagged('post_install', '-at_install')
class TestPlacesApiNew(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('google_address_autocomplete.google_places_api_key', MOCK_API_KEY)

    def _switch_to_api_new(self):
        self.env['ir.config_parameter'].sudo().set_param(USE_PLACES_API_NEW_PARAM, 'True')

    def test_legacy_api_by_default(self):
        self.authenticate('admin', 'admin')
        with patch(f'{CONTROLLER_MODULE}.requests.get', return_value=MockResponse({'predictions': []})) as mock_get, \
             patch(f'{CONTROLLER_MODULE}.requests.request',
                   side_effect=AssertionError('Places API (New) must not be called')):
            self.make_jsonrpc_request('/autocomplete/address', {
                'partial_address': 'Bourlottes',
                'use_employees_key': True,
            })
        self.assertEqual(mock_get.call_args.args, ('https://maps.googleapis.com/maps/api/place/autocomplete/json',))

    def test_places_api_new(self):
        self._switch_to_api_new()
        steps = []

        def mock_call_google_route_new(controller, route, api_key, field_mask, params, method='GET'):
            steps.append(route)
            self.assertEqual(api_key, MOCK_API_KEY)
            if route == '/places:autocomplete':
                self.assertEqual(method, 'POST')
                self.assertEqual(field_mask, 'suggestions.placePrediction.placeId,suggestions.placePrediction.text.text')
                self.assertEqual(params, {
                    'input': 'Bourlottes',
                    'includedPrimaryTypes': ['street_address', 'premise', 'subpremise', 'route'],
                    'sessionToken': 'some_client_session_token',
                })
                return {
                    'suggestions': [
                        {'placePrediction': {'placeId': 'custom_place_id', 'text': {'text': '48 Pirrama Rd, Pyrmont, Australia'}}},
                        {'queryPrediction': {'text': {'text': 'not a place'}}},
                    ],
                }
            if route == '/places/custom_place_id':
                self.assertEqual(method, 'GET')
                self.assertEqual(field_mask, 'addressComponents,adrFormatAddress')
                self.assertEqual(params, {'sessionToken': 'some_client_session_token'})
                return {
                    'addressComponents': [
                        {'longText': '48', 'shortText': '48', 'types': ['street_number']},
                        {'longText': 'Pirrama Road', 'shortText': 'Pirrama Rd', 'types': ['route']},
                        {'longText': 'Pyrmont', 'shortText': 'Pyrmont', 'types': ['locality', 'political']},
                        {'longText': 'City of Sydney', 'shortText': 'City of Sydney', 'types': ['administrative_area_level_2', 'political']},
                        {'longText': 'New South Wales', 'shortText': 'NSW', 'types': ['administrative_area_level_1', 'political']},
                        {'longText': 'Australia', 'shortText': 'AU', 'types': ['political', 'country']},  # should work w/ "unordered" types
                        {'longText': '2009', 'shortText': '2009', 'types': ['postal_code']},
                    ],
                    'adrFormatAddress': '<span class="street-address">48 Pirrama Rd</span>, <span class="locality">Pyrmont</span> <span class="region">NSW</span> <span class="postal-code">2009</span>, <span class="country-name">Australia</span>',
                }
            self.fail(f'Unexpected call to {route}')

        self.authenticate('admin', 'admin')
        with patch.object(AutoCompleteController, '_call_google_route_new', mock_call_google_route_new), \
             patch(f'{CONTROLLER_MODULE}.requests.get',
                   side_effect=AssertionError('Places API (Legacy) must not be called')):
            result = self.make_jsonrpc_request('/autocomplete/address', {
                'partial_address': 'Bourlottes',
                'session_id': 'some_client_session_token',
                'use_employees_key': True,
            })
            self.assertEqual(result, {
                'results': [{'formatted_address': '48 Pirrama Rd, Pyrmont, Australia', 'google_place_id': 'custom_place_id'}],
                'session_id': 'some_client_session_token',
            })

            result = self.make_jsonrpc_request('/autocomplete/address_full', {
                'address': '48 Pirrama Rd',
                'google_place_id': 'custom_place_id',
                'session_id': 'some_client_session_token',
                'use_employees_key': True,
            })

        australia = self.env.ref('base.au')
        nsw = self.env['res.country.state'].search([('country_id', '=', australia.id), ('code', '=', 'NSW')])
        self.assertEqual(result, {
            'country': [australia.id, australia.name],
            'number': '48',
            'city': 'Pyrmont',
            'street': 'Pirrama Road',
            'zip': '2009',
            'state': [nsw.id, nsw.name],
            'formatted_street_number': '48 Pirrama Road',  # abbreviated "48 Pirrama Rd" from adrFormatAddress is discarded
        })
        self.assertEqual(steps, ['/places:autocomplete', '/places/custom_place_id'])

    def test_places_api_new_errors(self):
        self._switch_to_api_new()
        error_response = MockResponse({'error': {'code': 403, 'message': 'Places API (New) has not been used in project'}}, 403)

        self.authenticate('admin', 'admin')
        with patch(f'{CONTROLLER_MODULE}.requests.request', return_value=error_response), \
             self.assertLogs(CONTROLLER_MODULE, 'ERROR') as logs:
            result = self.make_jsonrpc_request('/autocomplete/address', {
                'partial_address': 'Bourlottes',
                'use_employees_key': True,
            })
            self.assertEqual(result, {'results': [], 'session_id': None})
            result = self.make_jsonrpc_request('/autocomplete/address_full', {
                'address': 'Bourlottes',
                'google_place_id': 'custom_place_id',
                'use_employees_key': True,
            })
            self.assertEqual(result, {'address': None})
        self.assertEqual(len(logs.output), 2)
        self.assertIn('HTTP 403', logs.output[0])
        self.assertIn('Places API (New) has not been used in project', logs.output[0])

    def test_places_api_setting(self):
        self.assertFalse(self.env['res.config.settings'].create({}).google_places_use_api_new)
        self.start_tour('/odoo/action-base_setup.action_general_configuration', 'google_address_autocomplete_places_api_switch', login='admin')
        self.assertTrue(self.env['res.config.settings'].create({}).google_places_use_api_new)
        # the API key is kept: it works with the Places API (New) once enabled on its project
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('google_address_autocomplete.google_places_api_key'), MOCK_API_KEY)
