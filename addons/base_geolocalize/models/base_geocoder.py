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
    def geo_query_address(self, street=None, zip=None, city=None, state=None,
                          country=None):
        """
        Converts address fields into a valid string for querying
        gelocation APIs.
        :param street: street address
        :param zip: zip code
        :param city: city
        :param state: state
        :param country: country
        :return: formatted string
        """
        if country and ',' in country and (
                country.endswith(' of') or country.endswith(' of the')):
            # put country qualifier in front, otherwise GMap gives wrong
            # results, e.g. 'Congo, Democratic Republic of the' =>
            # 'Democratic Republic of the Congo'
            country = '{1} {0}'.format(*country.split(',', 1))
        return tools.ustr(', '.join(filter(None, [
            street,
            ("%s %s" % (zip or '', city or '')).strip(),
            state,
            country])))

    @api.model
    def geo_find(self, addr):
        """Use a location provider API to convert an address string into
        a latitude, longitude tuple.
        Here we use Openstreetmap Nominatim by default.
        :param addr: Address string passed to API
        :return: (latitude, longitude) or None if not found
        """
        provider = self.env['ir.config_parameter'].get_param(
            'base_geolocalize.provider', 'openstreetmap')
        if not hasattr(self, '_call_' + provider):
            raise UserError(_(
                'Provider %s is not implemented for geolocation service.')
                % provider
            )
        try:
            service = getattr(self, '_call_' + provider)
            result = service(addr)
            return result
        except UserError:
            raise
        except:
            _logger.error('Geolocalize call failed', exc_info=True)
            return None

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
            raise UserError(_(
                'Cannot contact geolocation servers. Please make sure that '
                'your Internet connection is up and running (%s).') % e)

        geo = result[0]
        return float(geo['lat']), float(geo['lon'])
