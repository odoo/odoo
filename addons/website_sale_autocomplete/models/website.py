# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import str2bool

USE_PLACES_API_NEW_PARAM = 'google_places.use_places_api_new.{website_id}'


class Website(models.Model):
    _inherit = 'website'

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        groups="base.group_system")

    def has_google_places_api_key(self):
        return bool(self.sudo().google_places_api_key)

    def _google_places_use_api_new(self):
        if not self:
            return False
        return str2bool(self.env['ir.config_parameter'].sudo().get_param(USE_PLACES_API_NEW_PARAM.format(website_id=self.id), 'False'), default=False)

    def _switch_to_google_places_api_new(self):
        self.ensure_one()
        self.env['ir.config_parameter'].sudo().set_param(USE_PLACES_API_NEW_PARAM.format(website_id=self.id), 'True')
