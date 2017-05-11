# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013_Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

try:
    import simplejson as json
except ImportError:
    import json     # noqa
import urllib

from openerp.osv import osv, fields
from openerp import tools
from openerp.tools.translate import _


def geo_find(street=None, zip=None, city=None, state=None, country_code=None):
    url = 'http://nominatim.openstreetmap.org/search'
    p = {
        'limit': 1,
        'format': 'json',
        'street': street or '',
        'city': city or '',
        'country': country_code or '',
        'postalcode': zip or '',
    }
    params = {}
    for k, v in p.iteritems():
        params[k] = tools.ustr(v).encode('utf-8')
    query = urllib.urlencode(params)
    url = url+'?%s' % query
    try:
        result = json.load(urllib.urlopen(url))
    except Exception, e:
        raise osv.except_osv(_('Network error'),
                             _('Cannot contact geolocation servers. Please make sure that your internet connection is up and running (%s).') % e)
    if not result:
        return None

    try:
        geo = result[0]
        return float(geo['lat']), float(geo['lon'])
    except (KeyError, ValueError):
        return None


class res_partner(osv.osv):
    _inherit = "res.partner"

    _columns = {
        'partner_latitude': fields.float('Geo Latitude', digits=(16, 5)),
        'partner_longitude': fields.float('Geo Longitude', digits=(16, 5)),
        'date_localization': fields.date('Geo Localization Date'),
    }

    def geo_localize(self, cr, uid, ids, context=None):
        # Don't pass context to browse()! We need country names in english below
        for partner in self.browse(cr, uid, ids):
            if not partner:
                continue
            result = geo_find(street=partner.street,
                              zip=partner.zip,
                              city=partner.city,
                              state=partner.state_id.name,
                              country_code=partner.country_id.code)
            if result:
                self.write(cr, uid, [partner.id], {
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': fields.date.context_today(self, cr, uid, context=context)
                }, context=context)
        return True
