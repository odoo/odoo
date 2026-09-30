# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        groups="base.group_system")

    def has_google_places_api_key(self):
        return bool(self.sudo().google_places_api_key)
