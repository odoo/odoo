# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import config


class ResPartner(models.Model):
    _inherit = "res.partner"

    date_localization = fields.Date(string='Geolocation Date')

    def write(self, vals):
        # Reset latitude/longitude in case we modify the address without
        # updating the related geolocation fields
        if any(field in vals for field in ['street', 'zip', 'city', 'state_id', 'country_id']) \
                and not all('partner_%s' % field in vals for field in ['latitude', 'longitude']):
            vals.update({
                'partner_latitude': 0.0,
                'partner_longitude': 0.0,
            })
        return super().write(vals)

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state, country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def geo_localize(self):
        # We need country names in English below
        if not self._context.get('force_geo_localize') \
                and (self._context.get('import_file') \
                     or any(config[key] for key in ['test_enable', 'test_file', 'init', 'update'])):
            return False
        partners_not_geo_localized = self.env['res.partner']
        for partner in self.with_context(lang='en_US'):
            result = self._geo_localize(partner.street,
                                        partner.zip,
                                        partner.city,
                                        partner.state_id.name,
                                        partner.country_id.name)

            if result:
                partner.write({
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': fields.Date.context_today(partner)
                })
            else:
                partners_not_geo_localized |= partner
        if partners_not_geo_localized:
            self.env.user._bus_send("simple_notification", {
                'type': 'danger',
                'title': _("Warning"),
                'message': _('No match found for %(partner_names)s address(es).', partner_names=', '.join(partners_not_geo_localized.mapped('name')))
            })
        return True
