# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import AccessError
from odoo.tools import str2bool

from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import USE_PLACES_API_NEW_PARAM


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        readonly=False,
        config_parameter='google_address_autocomplete.google_places_api_key')
    google_places_use_api_new = fields.Boolean(compute='_compute_google_places_use_api_new')

    def _compute_google_places_use_api_new(self):
        self.google_places_use_api_new = str2bool(self.env['ir.config_parameter'].sudo().get_param(USE_PLACES_API_NEW_PARAM, 'False'), default=False)

    def action_google_places_switch_to_api_new(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Only administrators can switch to the Places API (New)."))
        # the key of the legacy API may not have the Places API (New) enabled on its project
        self.env['ir.config_parameter'].sudo().set_param(USE_PLACES_API_NEW_PARAM, 'True')
