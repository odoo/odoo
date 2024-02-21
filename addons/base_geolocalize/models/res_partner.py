# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import urllib2

from openerp.osv import osv, fields
from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import UserError


def geo_find(addr, apikey=False):
    if not addr:
        return None

    if not apikey:
        raise UserError(_('''API key for GeoCoding (Places) required.\n
                          Save this key in System Parameters with key: google.api_key_geocode, value: <your api key>
                          Visit https://developers.google.com/maps/documentation/geocoding/get-api-key for more information.
                          '''))

    url = "https://maps.googleapis.com/maps/api/geocode/json?key=%s&sensor=false&address=" % apikey
    url += urllib2.quote(addr.encode('utf8'))

    try:
        result = json.load(urllib2.urlopen(url))
    except Exception as e:
        raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

    if result['status'] != 'OK':
        if result.get('error_message'):
            _logger.error(result['error_message'])
            error_msg = _('Unable to geolocate, received the error:\n%s'
                          '\n\nGoogle made this a paid feature.\n'
                          'You should first enable billing on your Google account.\n'
                          'Then, go to Developer Console, and enable the APIs:\n'
                          'Geocoding, Maps Static, Maps Javascript.\n'
                          % result['error_message'])
            raise UserError(error_msg)

    try:
        geo = result['results'][0]['geometry']['location']
        return float(geo['lat']), float(geo['lng'])
    except (KeyError, ValueError):
        return None



def geo_query_address(street=None, zip=None, city=None, state=None, country=None):
    if country and ',' in country and (country.endswith(' of') or country.endswith(' of the')):
        # put country qualifier in front, otherwise GMap gives wrong results,
        # e.g. 'Congo, Democratic Republic of the' => 'Democratic Republic of the Congo'
        country = '{1} {0}'.format(*country.split(',', 1))
    return tools.ustr(', '.join(filter(None, [street,
                                              ("%s %s" % (zip or '', city or '')).strip(),
                                              state,
                                              country])))


class res_partner(osv.osv):
    _inherit = "res.partner"

    _columns = {
        'partner_latitude': fields.float('Geo Latitude', digits=(16, 5)),
        'partner_longitude': fields.float('Geo Longitude', digits=(16, 5)),
        'date_localization': fields.date('Geo Localization Date'),
    }

    def geo_localize(self, cr, uid, ids, context=None):
        apikey = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
        # Don't pass context to browse()! We need country names in english below
        for partner in self.browse(cr, uid, ids):
            if not partner:
                continue
            address = geo_query_address(street=partner.street,
                                                zip=partner.zip,
                                                city=partner.city,
                                                state=partner.state_id.name,
                                                country=partner.country_id.name)
            result = geo_find(address, apikey)
            if result:
                self.write(cr, uid, [partner.id], {
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': fields.date.context_today(self, cr, uid, context=context)
                }, context=context)
        return True
