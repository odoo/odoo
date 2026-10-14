# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from pprint import pformat
from urllib.parse import quote

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
GOOGLE_PLACES_ENDPOINT = 'https://places.googleapis.com/v1'
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
                        [
                            ('country_id', '=', standard_data['country'][0]),
                            '|',
                            ('code', '=', google_field['short_name'].upper()),
                            ('name', 'ilike', google_field['long_name']),
                        ],
                    )
                    if len(state) == 1:
                        standard_data[field_standard] = [state.id, state.name]
                else:
                    standard_data[field_standard] = google_field['long_name']
        city_name = standard_data.get('city')
        country = standard_data.get('country')
        country_id = country[0] if country else False
        if city := self.env['res.partner']._get_res_city_by_name(city_name, country_id):
            standard_data['city_id'] = [city.id, city.name]
            if not standard_data.get('state') and city.state_id:  # Derive state from city if missing
                standard_data['state'] = [city.state_id.id, city.state_id.name]
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
        minimal_input_size = request.env['ir.config_parameter'].sudo().get_int('google_address_autocomplete.minimal_partial_address_size', 5)
        if len(partial_address) <= minimal_input_size:
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

        results = self._call_google_route(
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

    def _perform_complete_place_search(self, address, api_key=None, google_place_id=None, language_code=None, session_id=None):
        params = {}
        if language_code:
            params['languageCode'] = language_code
        if session_id:
            params['sessionToken'] = session_id

        results = self._call_google_route(
            f'/places/{quote(google_place_id or "", safe="")}', api_key,
            'addressComponents,adrFormatAddress', params,
        )

        try:
            html_address = results['adrFormatAddress']
            components = results['addressComponents']  # Get rid of useless extra data
        except KeyError:
            return {'address': None}

        # Keep only the first known type from the list of types
        results = [{
            'long_name': component.get('longText', ''),
            'short_name': component.get('shortText', ''),
            'type': next(filter(FIELDS_MAPPING.get, component['types']), component['types'][0]),
        } for component in components]

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

    def _call_google_route(self, route, api_key, field_mask, params, method='GET'):
        """ Call the Google Places API (New). The API key and field mask are sent as headers,
        the other params in the JSON body for POST requests or in the query string otherwise.
        Errors are logged and an empty dict is returned. """
        headers = {
            'X-Goog-Api-Key': api_key,
            'X-Goog-FieldMask': field_mask,
        }
        payload = {'json': params} if method == 'POST' else {'params': params}
        try:
            response = requests.request(method, f'{GOOGLE_PLACES_ENDPOINT}{route}', headers=headers, timeout=TIMEOUT, **payload)
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

    def _get_api_key(self, use_employees_key):
        assert request.env.user._is_internal()
        return request.env['ir.config_parameter'].sudo().get_str('google_address_autocomplete.google_places_api_key') or None

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
