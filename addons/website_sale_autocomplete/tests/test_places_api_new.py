# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
from unittest.mock import patch

from odoo.addons.website_sale_autocomplete.controllers.main import AutoCompleteController
from odoo.tests import HttpCase, tagged

MOCK_API_KEY = 'Tm9ib2R5IGV4cGVjdHMgdGhlIFNwYW5pc2ggaW5xdWlzaXRpb24gIQ=='


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.ok = status_code < 400
        self.text = str(json_data)

    def json(self):
        return self.json_data


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

        with patch('odoo.addons.website_sale_autocomplete.controllers.main.requests.get', mock_get), \
             patch('odoo.addons.website_sale_autocomplete.controllers.main.requests.request',
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

        with patch.object(AutoCompleteController, '_call_google_route_new', mock_call_google_route_new), \
             patch('odoo.addons.website_sale_autocomplete.controllers.main.requests.get',
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

        # Place Details concludes the session: the client must get a fresh token for the next one
        new_session_id = result.pop('session_id')
        self.assertNotEqual(new_session_id, 'some_client_session_token')
        self.assertEqual(uuid.UUID(new_session_id).version, 4)

        australia = self.env.ref('base.au')
        self.assertEqual(result, {
            'country': australia.id,
            'number': '48',
            'city': 'Pyrmont',
            'street': 'Pirrama Road',
            'zip': '2009',
            'state': self.env['res.country.state'].search([('country_id', '=', australia.id), ('code', '=', 'NSW')]).id,
            'formatted_street_number': '48 Pirrama Road',  # abbreviated "48 Pirrama Rd" from adrFormatAddress is discarded
        })
        self.assertEqual(steps, ['/places:autocomplete', '/places/custom_place_id'])

    def test_places_api_new_errors(self):
        self.website._switch_to_google_places_api_new()
        error_response = MockResponse({'error': {'code': 403, 'message': 'Places API (New) has not been used in project'}}, 403)

        with patch('odoo.addons.website_sale_autocomplete.controllers.main.requests.request', return_value=error_response), \
             self.assertLogs('odoo.addons.website_sale_autocomplete.controllers.main', 'ERROR') as logs:
            result = self.make_jsonrpc_request('/autocomplete/address', {'partial_address': 'Bourlottes'})
            self.assertEqual(result, {'results': [], 'session_id': None})
            result = self.make_jsonrpc_request('/autocomplete/address_full', {
                'address': 'Bourlottes',
                'google_place_id': 'custom_place_id',
            })
            self.assertEqual(result, {'address': None, 'session_id': result['session_id']})
            self.assertTrue(result['session_id'])
        self.assertEqual(len(logs.output), 2)
        self.assertIn('HTTP 403', logs.output[0])
        self.assertIn('Places API (New) has not been used in project', logs.output[0])

    def test_places_api_setting(self):
        other_website = self.env['website'].create({'name': 'Other website', 'google_places_api_key': MOCK_API_KEY})
        self.assertFalse(self.env['res.config.settings'].create({'website_id': self.website.id}).google_places_use_api_new)
        self.start_tour('/odoo/action-website.action_website_configuration', 'website_sale_autocomplete_places_api_switch', login='admin')
        self.assertTrue(self.website._google_places_use_api_new())
        self.assertTrue(self.env['res.config.settings'].create({'website_id': self.website.id}).google_places_use_api_new)
        # the API key is kept: it works with the Places API (New) once enabled on its project
        self.assertEqual(self.website.google_places_api_key, MOCK_API_KEY)
        # the other website is left untouched
        self.assertFalse(other_website._google_places_use_api_new())
        self.assertEqual(other_website.google_places_api_key, MOCK_API_KEY)
