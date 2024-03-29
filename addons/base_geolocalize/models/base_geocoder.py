# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class GeoProvider(models.Model):
    _name = "base.geo_provider"
    _description = "Geo Provider"

    tech_name = fields.Char(string="Technical Name")
    name = fields.Char()


class GeoCoder(models.AbstractModel):
    """
    Abstract class used to call Geolocalization API and convert addresses
    into GPS coordinates.
    """
    _name = "base.geocoder"
    _description = "Geo Coder"

    @api.model
    def _get_provider(self):
        prov_id = self.env['ir.config_parameter'].sudo().get_param('base_geolocalize.geo_provider')
        if prov_id:
            provider = self.env['base.geo_provider'].browse(int(prov_id))
        if not prov_id or not provider.exists():
            provider = self.env['base.geo_provider'].search([], limit=1)
        return provider

    @api.model
    def geo_query_address(self, street=None, zip=None, city=None, state=None, country=None):
        """ Converts address fields into a valid string for querying
        geolocation APIs.
        :param street: street address
        :param zip: zip code
        :param city: city
        :param state: state
        :param country: country
        :return: formatted string
        """
        provider = self._get_provider().tech_name
        if hasattr(self, '_geo_query_address_' + provider):
            # Makes the transformation defined for provider
            return getattr(self, '_geo_query_address_' + provider)(street, zip, city, state, country)
        else:
            # By default, join the non-empty parameters
            return self._geo_query_address_default(street=street, zip=zip, city=city, state=state, country=country)

    @api.model
    def geo_find(self, addr, **kw):
        """Use a location provider API to convert an address string into a latitude, longitude tuple.
        Here we use Openstreetmap Nominatim by default.
        :param addr: Address string passed to API
        :return: (latitude, longitude) or None if not found
        """
        provider = self._get_provider().tech_name
        try:
            service = getattr(self, '_call_' + provider)
            result = service(addr, **kw)
        except AttributeError:
            raise UserError(_(
                'Provider %s is not implemented for geolocation service.',
                provider))
        except UserError:
            raise
        except Exception:
            _logger.debug('Geolocalize call failed', exc_info=True)
            result = None
        return result

    @api.model
    def _call_openstreetmap(self, addr, **kw):
        """
        Use Openstreemap Nominatim service to retrieve location
        :return: (latitude, longitude) or None if not found
        """
        if not addr:
            _logger.info('invalid address given')
            return None
        url = 'https://nominatim.openstreetmap.org/search'
        try:
            headers = {'User-Agent': 'Odoo (http://www.odoo.com/contactus)'}
            response = requests.get(url, headers=headers, params={'format': 'json', 'q': addr})
            _logger.info('openstreetmap nominatim service called')
            if response.status_code != 200:
                _logger.warning('Request to openstreetmap failed.\nCode: %s\nContent: %s', response.status_code, response.content)
            result = response.json()
        except Exception as e:
            self._raise_query_error(e)
        geo = result[0]
        return float(geo['lat']), float(geo['lon'])

    @api.model
    def _call_googlemap(self, addr, **kw):
        """ Use google maps API. It won't work without a valid API key.
        :return: (latitude, longitude) or None if not found
        """
        apikey = self.env['ir.config_parameter'].sudo().get_param('base_geolocalize.google_map_api_key')
        if not apikey:
            raise UserError(_(
                "API key for GeoCoding (Places) required.\n"
                "Visit https://developers.google.com/maps/documentation/geocoding/get-api-key for more information."
            ))
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {'sensor': 'false', 'address': addr, 'key': apikey}
        if kw.get('force_country'):
            params['components'] = 'country:%s' % kw['force_country']
        try:
            result = requests.get(url, params).json()
        except Exception as e:
            self._raise_query_error(e)

        try:
            if result['status'] == 'ZERO_RESULTS':
                return None
            if result['status'] != 'OK':
                _logger.debug('Invalid Gmaps call: %s - %s',
                              result['status'], result.get('error_message', ''))
                error_msg = _('Unable to geolocate, received the error:\n%s'
                              '\n\nGoogle made this a paid feature.\n'
                              'You should first enable billing on your Google account.\n'
                              'Then, go to Developer Console, and enable the APIs:\n'
                              'Geocoding, Maps Static, Maps Javascript.\n', result.get('error_message'))
                raise UserError(error_msg)
            geo = result['results'][0]['geometry']['location']
            return float(geo['lat']), float(geo['lng'])
        except (KeyError, ValueError):
            _logger.debug('Unexpected Gmaps API answer %s', result.get('error_message', ''))
            return None

    @api.model
    def _geo_query_address_default(self, street=None, zip=None, city=None, state=None, country=None):
        address_list = [
            street,
            ("%s %s" % (zip or '', city or '')).strip(),
            state,
            country
        ]
        address_list = [item for item in address_list if item]
        return tools.ustr(', '.join(address_list))

    @api.model
    def _geo_query_address_googlemap(self, street=None, zip=None, city=None, state=None, country=None):
        # put country qualifier in front, otherwise GMap gives wrong# results
        #  e.g. 'Congo, Democratic Republic of the' =>  'Democratic Republic of the Congo'
        if country and ',' in country and (
                country.endswith(' of') or country.endswith(' of the')):
            country = '{1} {0}'.format(*country.split(',', 1))
        return self._geo_query_address_default(street=street, zip=zip, city=city, state=state, country=country)

    def _raise_query_error(self, error):
        raise UserError(_('Error with geolocation server:') + ' %s' % error)
