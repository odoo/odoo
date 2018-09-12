# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import urllib2
import logging

from odoo import api, models, tools, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class GeoCoder(models.AbstractModel):
    """
    Abstract class used to call Geolocalization API and convert addresses
    into GPS coordinates.
    """
    _name = "base.geocoder"

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
        provider = self.env['ir.config_parameter'].get_param('base_geolocalize.provider', 'openstreetmap')
        if hasattr(self, '_geo_query_address_' + provider):
            # Makes the transformation defined for provider
            service = getattr(self, '_geo_query_address_' + provider)
            return service(street, zip, city, state, country)
        else:
            # By default, join the non-empty parameters
            return tools.ustr(', '.join(filter(None, [
                street,
                ("%s %s" % (zip or '', city or '')).strip(),
                state,
                country])))

    @api.model
    def geo_find(self, addr):
        """Use a location provider API to convert an address string into a latitude, longitude tuple.
        Here we use Openstreetmap Nominatim by default.
        :param addr: Address string passed to API
        :return: (latitude, longitude) or None if not found
        """
        provider = self.env['ir.config_parameter'].get_param(
            'base_geolocalize.provider', 'openstreetmap')
        try:
            service = getattr(self, '_call_' + provider)
            result = service(addr)
        except AttributeError:
            raise UserError(_(
                'Provider %s is not implemented for geolocation service.'
            ) % provider)
        except UserError:
            raise
        except:
            _logger.debug('Geolocalize call failed', exc_info=True)
            result = None
        return result

    @api.model
    def _call_openstreetmap(self, addr):
        """
        Use Openstreemap Nominatim service to retrieve location
        :return: (latitude, longitude) or None if not found
        """
        if not addr:
            _logger.info('invalid address given')
            return None
        url = 'https://nominatim.openstreetmap.org/search?format=json&q='
        url += urllib2.quote(addr.encode('utf8'))
        try:
            _logger.info('openstreetmap nominatim service called')
            result = json.load(urllib2.urlopen(url))
        except Exception as e:
            self._raise_internet_access_error(e)
        geo = result[0]
        return float(geo['lat']), float(geo['lon'])

    @api.model
    def _call_google(self, addr):
        """ Use google maps API. It won't work without a valid API key.
        :return: (latitude, longitude) or None if not found
        """
        apikey = self.env['ir.config_parameter'].sudo().get_param(
            'google.api_key_geocode')
        if not apikey:
            raise UserError(_(
                "API key for GeoCoding (Places) required.\n"
                "Save this key in System Parameters with key: google.api_key_geocode, value: <your api key> Visit https://developers.google.com/maps/documentation/geocoding/get-api-key for more information."
            ))
        url = 'https://maps.googleapis.com/maps/api/geocode/json?key=%s&sensor=false&address=' % apikey
        url += urllib2.quote(addr.encode('utf8'))
        try:
            result = json.load(urllib2.urlopen(url))
        except Exception as e:
            self._raise_internet_access_error(e)

        try:
            if result['status'] != 'OK':
                _logger.debug('Invalid Gmaps call: %s - %s',
                              result['status'], result.get('error_message', ''))
                return None
            geo = result['results'][0]['geometry']['location']
            return float(geo['lat']), float(geo['lng'])
        except (KeyError, ValueError):
            _logger.debug('Unexpected Gmaps API answer %s', result.get('error_message', ''))
            return None

    @api.model
    def _geo_query_address_google(self, street=None, zip=None, city=None,
                                   state=None, country=None):
        # This may be useful if using GMaps API.
        # put country qualifier in front, otherwise GMap gives wrong
        # results, e.g. 'Congo, Democratic Republic of the' =>
        # 'Democratic Republic of the Congo'
        if country and ',' in country and (
                country.endswith(' of') or country.endswith(' of the')):
            country = '{1} {0}'.format(*country.split(',', 1))
        return tools.ustr(', '.join(filter(None, [
            street,
            ("%s %s" % (zip or '', city or '')).strip(),
            state,
            country])))

    def _raise_internet_access_error(self, error):
        raise UserError(_(
            'Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).'
        ) % error)
