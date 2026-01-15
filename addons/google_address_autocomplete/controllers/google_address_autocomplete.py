# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from pprint import pformat

import requests

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)


# API Documentation: https://developers.google.com/maps/documentation/geocoding/requests-geocoding#Types
# ** sublocality indicates a first-order civil entity below a locality
# ** administrative_area_level_1 indicates a first-order civil entity below the country level.
#    Within the United States, these administrative levels are states.
#    In most cases, administrative_area_level_1 short names will closely match ISO 3166-2
# ** administrative_area_level_2 indicates a second-order civil entity below the country level.
#    Within the United States, these administrative levels are counties.
FIELDS_MAPPING = {
    'country': ['country'],
    'street_number': ['number'],
    'locality': ['city'],  # If locality exists, use it instead of the more general administrative area
    'postal_town': ['city'],  # Used instead of locality in some countries
    'route': ['street'],
    'sublocality_level_1': ['street2'],
    'postal_code': ['zip'],
    'administrative_area_level_1': ['state', 'city'],
    'administrative_area_level_2': ['state', 'city']
}

# If a google fields may correspond to multiple standard fields, the first occurrence in the list will overwrite following entries.
FIELDS_PRIORITY = ['country', 'street_number', 'locality', 'postal_town', 'route', 'postal_code',
                   'administrative_area_level_1', 'administrative_area_level_2']
GOOGLE_PLACES_ENDPOINT = 'https://maps.googleapis.com/maps/api/place'
TIMEOUT = 2.5


class AutoCompleteController(http.Controller):

    def _translate_google_to_standard(self, google_fields):
        standard_data = {}

        for google_field in google_fields:
            fields_standard = FIELDS_MAPPING.get(google_field['type'], [])

            for field_standard in fields_standard:
                if field_standard in standard_data:  # if a value is already assigned, do not overwrite it.
                    continue
                if field_standard == 'country':
                    country = request.env['res.country'].search([('code', '=', google_field['short_name'].upper())], limit=1)
                    standard_data[field_standard] = [country.id, country.name]
                elif field_standard == 'state':
                    if 'country' not in standard_data:
                        _logger.warning(
                            "Cannot assign state before country:\n%s", pformat(google_fields),
                        )
                        continue
                    state = request.env['res.country.state'].search(
                        [('code', '=', google_field['short_name'].upper()),
                         ('country_id', '=', standard_data['country'][0])])
                    if len(state) == 1:
                        standard_data[field_standard] = [state.id, state.name]
                else:
                    standard_data[field_standard] = google_field['long_name']
        return standard_data

    def _guess_number_from_input(self, source_input, standard_address):
        """
        Google might not send the house number in case the address
        does not exist in their database.
        We try to guess the number from the user's input to avoid losing the info.
        """
        # Remove other parts from address to make better guesses
        guessed_house_number = source_input \
            .replace(standard_address.get('zip', ''), '') \
            .replace(standard_address.get('street', ''), '') \
            .replace(standard_address.get('city', ''), '')
        guessed_house_number = guessed_house_number.split(',')[0].strip()
        return guessed_house_number

    def _perform_place_search(self, partial_address, api_key=None, session_id=None, language_code=None, country_code=None):
        minimal_input_size = int(request.env['ir.config_parameter'].sudo().get_param('google_address_autocomplete.minimal_partial_address_size', '5'))
        if len(partial_address) <= minimal_input_size:
            return {
                'results': [],
                'session_id': session_id
            }

        params = {
            'key': api_key,
            'fields': 'formatted_address,name',
            'inputtype': 'textquery',
            'types': 'address',
            'input': partial_address
        }
        if country_code:
            params['components'] = f'country:{country_code}'
        if language_code:
            params['language'] = language_code
        if session_id:
            params['sessiontoken'] = session_id

        try:
            results = self._call_google_route("/autocomplete/json", params)
        except (TimeoutError, ValueError) as e:
            _logger.error(e)
            return {
                'results': [],
                'session_id': session_id
            }

        if results.get('error_message'):
            _logger.error(results['error_message'])

        results = results.get('predictions', [])

        # Convert google specific format to standard format.
        return {
            'results': [{
                'formatted_address': result['description'],
                'google_place_id': result['place_id'],
            } for result in results],
            'session_id': session_id
        }

    def _perform_complete_place_search(self, address, api_key=None, google_place_id=None, language_code=None, session_id=None):
        params = {
            'key': api_key,
            'place_id': google_place_id,
            'fields': 'address_component,adr_address'
        }

        if language_code:
            params['language'] = language_code
        if session_id:
            params['sessiontoken'] = session_id

        try:
            results = self._call_google_route("/details/json", params)
        except (TimeoutError, ValueError) as e:
            _logger.error(e)
            return {'address': None}

        if results.get('error_message'):
            _logger.error(results['error_message'])

        try:
            html_address = results['result']['adr_address']
            results = results['result']['address_components']  # Get rid of useless extra data
        except KeyError:
            return {'address': None}

        # Keep only the first known type from the list of types
        for res in results:
            types = res.pop('types')
            res['type'] = next(filter(FIELDS_MAPPING.get, types), types[0])

        # Sort the result by their priority.
        results.sort(key=lambda r: FIELDS_PRIORITY.index(r['type']) if r['type'] in FIELDS_PRIORITY else 100)

        standard_address = self._translate_google_to_standard(results)

        if 'number' not in standard_address:
            standard_address['number'] = self._guess_number_from_input(address, standard_address)
            standard_address['formatted_street_number'] = f'{standard_address["number"]} {standard_address.get("street", "")}'.strip()
        else:
            formatted_from_html = html2plaintext(html_address.split(',')[0])
            formatted_manually = f'{standard_address["number"]} {standard_address.get("street", "")}'.strip()
            # Sometimes, the google api sends back abbreviated data :
            # "52 High Road Street" becomes "52 HR St" for example. We usually take the result from google, but if it's an abbreviation, take our guess instead.
            if len(formatted_from_html) >= len(formatted_manually):
                standard_address['formatted_street_number'] = formatted_from_html
            else:
                standard_address['formatted_street_number'] = formatted_manually
        return standard_address

    def _call_google_route(self, route, params):
        return requests.get(f'{GOOGLE_PLACES_ENDPOINT}{route}', params=params, timeout=TIMEOUT).json()

    def _get_api_key(self, use_employees_key):
        assert request.env.user._is_internal()
        return request.env['ir.config_parameter'].sudo().get_param('google_address_autocomplete.google_places_api_key')

    @http.route('/autocomplete/address', methods=['POST'], type='jsonrpc', auth='public', website=True)
    def _autocomplete_address(self, partial_address, session_id=None, use_employees_key=None):
        try:
            api_key = self._get_api_key(use_employees_key)
        except AssertionError:
            api_key = None
        if not api_key:
            return {
                'results': [],
                'session_id': session_id
            }
        return self._perform_place_search(partial_address, session_id=session_id, api_key=api_key)

    @http.route('/autocomplete/address_full', methods=['POST'], type='jsonrpc', auth='public', website=True)
    def _autocomplete_address_full(self, address, session_id=None, google_place_id=None, use_employees_key=None, **kwargs):
        try:
            api_key = self._get_api_key(use_employees_key)
        except AssertionError:
            raise AccessError(_("You don't have access to the full autocomplete feature."))
        return self._perform_complete_place_search(address, google_place_id=google_place_id,
                                                   session_id=session_id, api_key=api_key, **kwargs)
