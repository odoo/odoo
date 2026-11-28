# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import (
    AutoCompleteController,
    USE_PLACES_API_NEW_PARAM,
)
from odoo.addons.google_address_autocomplete.tests.mock_google_places import MockResponse
from odoo.tests import HttpCase, tagged

CONTROLLER_MODULE = 'odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete'
MOCK_API_KEY = 'Tm9ib2R5IGV4cGVjdHMgdGhlIFNwYW5pc2ggaW5xdWlzaXRpb24gIQ=='


@tagged('post_install', '-at_install')
class TestPlacesApiNew(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].get_current_website()
        cls.website.google_places_api_key = MOCK_API_KEY

    def test_places_api_new_per_website(self):
        other_website = self.env['website'].create({'name': 'Other website'})
        other_website._switch_to_google_places_api_new()
        self.assertTrue(other_website._google_places_use_api_new())
        self.assertFalse(self.website._google_places_use_api_new())

    def test_legacy_api_by_default(self):
        # the switch of the backend key does not apply to the website key
        self.env['ir.config_parameter'].sudo().set_param(USE_PLACES_API_NEW_PARAM, 'True')
        calls = []

        def mock_get(url, params=None, timeout=None):
            calls.append(url)
            if url.endswith('/autocomplete/json'):
                self.assertEqual(params, {
                    'key': MOCK_API_KEY,
                    'fields': 'formatted_address,name',
                    'inputtype': 'textquery',
                    'types': 'address',
                    'input': 'Bourlottes',
                    'sessiontoken': 'some_client_session_token',
                })
                return MockResponse({
                    'predictions': [{'description': 'Paris, France', 'place_id': 'ChIJD7fiBh9u5kcRYJSMaMOCCwQ'}],
                    'status': 'OK',
                })
            self.fail(f'Unexpected call to {url}')

        with patch(f'{CONTROLLER_MODULE}.requests.get', mock_get), \
             patch(f'{CONTROLLER_MODULE}.requests.request',
                   side_effect=AssertionError('Places API (New) must not be called')):
            result = self.make_jsonrpc_request('/autocomplete/address', {
                'partial_address': 'Bourlottes',
                'session_id': 'some_client_session_token',
            })

        self.assertEqual(calls, ['https://maps.googleapis.com/maps/api/place/autocomplete/json'])
        self.assertEqual(result, {
            'results': [{'formatted_address': 'Paris, France', 'google_place_id': 'ChIJD7fiBh9u5kcRYJSMaMOCCwQ'}],
            'session_id': 'some_client_session_token',
        })

    def test_places_api_new(self):
        self.website._switch_to_google_places_api_new()
        steps = []

        def mock_call_google_route_new(controller, route, api_key, field_mask, params, method='GET'):
            steps.append(route)
            self.assertEqual(api_key, MOCK_API_KEY)
            if route == '/places:autocomplete':
                self.assertEqual(params['sessionToken'], 'some_client_session_token')
                return {
                    'suggestions': [
                        {'placePrediction': {'placeId': 'custom_place_id', 'text': {'text': '48 Pirrama Rd, Pyrmont, Australia'}}},
                    ],
                }
            if route == '/places/custom_place_id':
                self.assertEqual(params, {'sessionToken': 'some_client_session_token'})
                return {
                    'addressComponents': [
                        {'longText': '48', 'shortText': '48', 'types': ['street_number']},
                        {'longText': 'Pirrama Road', 'shortText': 'Pirrama Rd', 'types': ['route']},
                        {'longText': 'Pyrmont', 'shortText': 'Pyrmont', 'types': ['locality', 'political']},
                        {'longText': 'Australia', 'shortText': 'AU', 'types': ['political', 'country']},
                        {'longText': '2009', 'shortText': '2009', 'types': ['postal_code']},
                    ],
                    'adrFormatAddress': '<span class="street-address">48 Pirrama Rd</span>, <span class="locality">Pyrmont</span> <span class="postal-code">2009</span>, <span class="country-name">Australia</span>',
                }
            self.fail(f'Unexpected call to {route}')

        with patch.object(AutoCompleteController, '_call_google_route_new', mock_call_google_route_new), \
             patch(f'{CONTROLLER_MODULE}.requests.get',
                   side_effect=AssertionError('Places API (Legacy) must not be called')):
            result = self.make_jsonrpc_request('/autocomplete/address', {
                'partial_address': 'Bourlottes',
                'session_id': 'some_client_session_token',
            })
            self.assertEqual(result, {
                'results': [{'formatted_address': '48 Pirrama Rd, Pyrmont, Australia', 'google_place_id': 'custom_place_id'}],
                'session_id': 'some_client_session_token',
            })

            result = self.make_jsonrpc_request('/autocomplete/address_full', {
                'address': '48 Pirrama Rd',
                'google_place_id': 'custom_place_id',
                'session_id': 'some_client_session_token',
            })

        australia = self.env.ref('base.au')
        self.assertEqual(result, {
            'country': [australia.id, australia.name],
            'number': '48',
            'city': 'Pyrmont',
            'street': 'Pirrama Road',
            'zip': '2009',
            'formatted_street_number': '48 Pirrama Road',
        })
        self.assertEqual(steps, ['/places:autocomplete', '/places/custom_place_id'])

    def test_places_api_setting(self):
        other_website = self.env['website'].create({'name': 'Other website', 'google_places_api_key': MOCK_API_KEY})
        self.assertFalse(self.env['res.config.settings'].create({'website_id': self.website.id}).website_google_places_use_api_new)
        self.start_tour('/odoo/action-website.action_website_configuration', 'website_sale_autocomplete_places_api_switch', login='admin')
        self.assertTrue(self.website._google_places_use_api_new())
        self.assertTrue(self.env['res.config.settings'].create({'website_id': self.website.id}).website_google_places_use_api_new)
        # the API key is kept: it works with the Places API (New) once enabled on its project
        self.assertEqual(self.website.google_places_api_key, MOCK_API_KEY)
        # the other website and the backend key are left untouched
        self.assertFalse(other_website._google_places_use_api_new())
        self.assertEqual(other_website.google_places_api_key, MOCK_API_KEY)
        self.assertFalse(self.env['res.config.settings'].create({}).google_places_use_api_new)
