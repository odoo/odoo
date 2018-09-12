from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    date_localization = fields.Date(string='Geolocation Date')

    @api.multi
    def geo_localize(self):
        # We need country names in English below
        geo_obj = self.env['base.geocoder']
        for partner in self.with_context(lang='en_US'):
            result = geo_obj.geo_find(geo_obj.geo_query_address(
                street=partner.street,
                zip=partner.zip,
                city=partner.city,
                state=partner.state_id.name,
                country=partner.country_id.name
            ))
            if result is None:
                result = geo_obj.geo_find(geo_obj.geo_query_address(
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
