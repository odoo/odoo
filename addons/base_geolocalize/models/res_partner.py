from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    date_localization = fields.Date(string='Geolocation Date')
    partner_latitude = fields.Float(compute="_compute_geo_coordinates", readonly=False, store=True)
    partner_longitude = fields.Float(compute="_compute_geo_coordinates", readonly=False, store=True)

    @api.depends('street', 'zip', 'city', 'state_id', 'country_id')
    def _compute_geo_coordinates(self):
        for partner in self:
            if not (partner.city and partner.country_id):
                partner.partner_latitude = 0.0
                partner.partner_longitude = 0.0
            else:
                partner.geo_localize()

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
        return True
