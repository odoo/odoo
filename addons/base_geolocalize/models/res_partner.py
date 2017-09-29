# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

import requests

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


def geo_find(addr):
    if not addr:
        return None
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    try:
        result = requests.get(url, params={'sensor': 'false', 'address': addr}).json()
    except Exception as e:
        raise UserError(_('Cannot contact geolocation servers. Please make sure that your Internet connection is up and running (%s).') % e)

    if result['status'] != 'OK':
        return None

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
    return tools.ustr(', '.join(
        field for field in [street, ("%s %s" % (zip or '', city or '')).strip(), state, country]
        if field
    ))


class ResPartner(models.Model):
    _inherit = "res.partner"

    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    date_localization = fields.Date(string='Geolocation Date')

    @api.multi
    def geo_localize(self):
        # We need country names in English below
        for partner in self.with_context(lang='en_US'):
            result = geo_find(geo_query_address(street=partner.street,
                                                zip=partner.zip,
                                                city=partner.city,
                                                state=partner.state_id.name,
                                                country=partner.country_id.name))
            if result is None:
                result = geo_find(geo_query_address(
                    city=partner.city,
                    state=partner.state_id.name,
                    country=partner.country_id.name
                ))

            if result:
                partner.write({
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': fields.Date.context_today(partner)
                })
        return True
