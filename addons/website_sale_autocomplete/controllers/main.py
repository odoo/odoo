# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from pprint import pformat
from urllib.parse import quote_plus
import uuid

import requests

from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext

import logging
_logger = logging.getLogger(__name__)


FIELDS_MAPPING = {
    'country': ['country'],
    'street_number': ['number'],
    'locality': ['city'],  # If locality exists, use it instead of the more general administrative area
    'postal_town': ['city'],  # Used instead of locality in some countries
    'route': ['street'],
    'postal_code': ['zip'],
    'administrative_area_level_1': ['state', 'city'],
    'administrative_area_level_2': ['state', 'country']
}

# If a google fields may correspond to multiple standard fields, the first occurrence in the list will overwrite following entries.
FIELDS_PRIORITY = ['country', 'street_number', 'locality', 'postal_town', 'route', 'postal_code',
                   'administrative_area_level_1', 'administrative_area_level_2']
GOOGLE_PLACES_ENDPOINT = 'https://maps.googleapis.com/maps/api/place'
GOOGLE_PLACES_NEW_ENDPOINT = 'https://places.googleapis.com/v1'
TIMEOUT = 2.5


class AutoCompleteController(http.Controller):

    def _translate_google_to_standard(self, google_fields):
        standard_data = {}

        for google_field in google_fields:
            fields_standard = FIELDS_MAPPING[google_field['type']] if google_field['type'] in FIELDS_MAPPING else []

            for field_standard in fields_standard:
                if field_standard in standard_data:  # if a value is already assigned, do not overwrite it.
                    continue
                # Convert state and countries to odoo ids
                if field_standard == 'country':
                    standard_data[field_standard] = request.env['res.country'].search(
                        [('code', '=', google_field['short_name'].upper())])[0].id
                elif field_standard == 'state':
                    if 'country' not in standard_data:
                        _logger.warning(
                            "Cannot assign state before country:\n%s", pformat(google_fields),
                        )
                        continue
                    state = request.env['res.country.state'].search(
                        [('code', '=', google_field['short_name'].upper()),
                         ('country_id', '=', standard_data['country'])])
                    if len(state) == 1:
                        standard_data[field_standard] = state.id
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

    def _use_places_api_new(self):
        return request.env['website'].get_current_website()._google_places_use_api_new()

    def _perform_place_search(self, partial_address, api_key=None, session_id=None, language_code=None, country_code=None):
        if self._use_places_api_new():
            return self._perform_place_search_new(partial_address, api_key=api_key, session_id=session_id,
                                                  language_code=language_code, country_code=country_code)
        if len(partial_address) <= 5:
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
            results = requests.get(f'{GOOGLE_PLACES_ENDPOINT}/autocomplete/json', params=params, timeout=TIMEOUT).json()
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
        if self._use_places_api_new():
            return self._perform_complete_place_search_new(address, api_key=api_key, google_place_id=google_place_id,
                                                           language_code=language_code, session_id=session_id)
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
            results = requests.get(f'{GOOGLE_PLACES_ENDPOINT}/details/json', params=params, timeout=TIMEOUT).json()
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
            res['type'] = next(iter(t for t in types if t in FIELDS_MAPPING), types[0])

        return self._google_components_to_standard_address(address, results, html_address)

    def _google_components_to_standard_address(self, address, results, html_address):
        # Sort the result by their priority.
        results.sort(key=lambda r: FIELDS_PRIORITY.index(r['type']) if r['type'] in FIELDS_PRIORITY else 100)

        standard_address = self._translate_google_to_standard(results)

        if 'number' not in standard_address:
            standard_address['number'] = self._guess_number_from_input(address, standard_address)
            standard_address['formatted_street_number'] = f'{standard_address["number"]} {standard_address.get("street", "")}'
        else:
            formatted_from_html = html2plaintext(html_address.split(',')[0])
            formatted_manually = f'{standard_address["number"]} {standard_address.get("street", "")}'
            # Sometimes, the google api sends back abbreviated data :
            # "52 High Road Street" becomes "52 HR St" for example. We usually take the result from google, but if it's an abbreviation, take our guess instead.
            if len(formatted_from_html) >= len(formatted_manually):
                standard_address['formatted_street_number'] = formatted_from_html
            else:
                standard_address['formatted_street_number'] = formatted_manually
        return standard_address

    # ------------------------------------------------------------
    # Places API (New)
    # ------------------------------------------------------------

    def _perform_place_search_new(self, partial_address, api_key=None, session_id=None, language_code=None, country_code=None):
        if len(partial_address) <= 5:
            return {
                'results': [],
                'session_id': session_id,
            }

        params = {
            'input': partial_address,
            'includedPrimaryTypes': ['street_address', 'premise', 'subpremise', 'route'],
        }
        if country_code:
            params['includedRegionCodes'] = [country_code]
        if language_code:
            params['languageCode'] = language_code
        if session_id:
            params['sessionToken'] = session_id

        results = self._call_google_route_new(
            '/places:autocomplete', api_key,
            'suggestions.placePrediction.placeId,suggestions.placePrediction.text.text',
            params, method='POST',
        )
        predictions = [suggestion['placePrediction'] for suggestion in results.get('suggestions', []) if 'placePrediction' in suggestion]

        # Convert google specific format to standard format.
        return {
            'results': [{
                'formatted_address': prediction['text']['text'],
                'google_place_id': prediction['placeId'],
            } for prediction in predictions],
            'session_id': session_id
        }

    def _perform_complete_place_search_new(self, address, api_key=None, google_place_id=None, language_code=None, session_id=None):
        params = {}
        if language_code:
            params['languageCode'] = language_code
        if session_id:
            params['sessionToken'] = session_id

        results = self._call_google_route_new(
            f'/places/{quote_plus(google_place_id or "")}', api_key,
            'addressComponents,adrFormatAddress', params,
        )

        # The Place Details call concludes the session: reusing its token would get the next
        # requests billed as unsessioned, so hand a fresh one back to the client.
        new_session_id = str(uuid.uuid4())
        try:
            html_address = results['adrFormatAddress']
            components = results['addressComponents']  # Get rid of useless extra data
        except KeyError:
            return {'address': None, 'session_id': new_session_id}

        # Keep only the first known type from the list of types
        results = [{
            'long_name': component.get('longText', ''),
            'short_name': component.get('shortText', ''),
            'type': next(filter(FIELDS_MAPPING.get, types), types[0] if types else None),
        } for component in components for types in [component.get('types', [])]]

        standard_address = self._google_components_to_standard_address(address, results, html_address)
        standard_address['session_id'] = new_session_id
        return standard_address

    def _call_google_route_new(self, route, api_key, field_mask, params, method='GET'):
        """ Call the Google Places API (New). The API key and field mask are sent as headers,
        the other params in the JSON body for POST requests or in the query string otherwise.
        Errors are logged and an empty dict is returned. """
        headers = {
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': field_mask,
        }
        payload = {'json': params} if method == 'POST' else {'params': params}
        try:
            response = requests.request(method, f'{GOOGLE_PLACES_NEW_ENDPOINT}{route}', headers=headers, timeout=TIMEOUT, **payload)
            results = response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            _logger.error("Google Places API call to %s failed: %s", route, e)
            return {}
        if not response.ok:
            # The API (New) reports errors with an HTTP error status and an {"error": {"message": ...}} body
            error_message = results.get('error', {}).get('message') if isinstance(results, dict) else None
            _logger.error("Google Places API call to %s failed (HTTP %s): %s", route, response.status_code, error_message or response.text)
            return {}
        return results

    @http.route('/autocomplete/address', methods=['POST'], type='json', auth='public', website=True)
    def _autocomplete_address(self, partial_address, session_id=None):
        api_key = request.env['website'].get_current_website().sudo().google_places_api_key
        return self._perform_place_search(partial_address, session_id=session_id, api_key=api_key)

    @http.route('/autocomplete/address_full', methods=['POST'], type='json', auth='public', website=True)
    def _autocomplete_address_full(self, address, session_id=None, google_place_id=None, **kwargs):
        api_key = request.env['website'].get_current_website().sudo().google_places_api_key
        return self._perform_complete_place_search(address, google_place_id=google_place_id,
                                                   session_id=session_id, api_key=api_key, **kwargs)
