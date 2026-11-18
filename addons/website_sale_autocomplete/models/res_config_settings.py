from odoo import _, api, models, fields
from odoo.exceptions import AccessError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_places_api_key = fields.Char(
        string='Google Places API Key',
        related='website_id.google_places_api_key',
        readonly=False)
    google_places_use_api_new = fields.Boolean(compute='_compute_google_places_use_api_new')

    @api.depends('website_id')
    def _compute_google_places_use_api_new(self):
        for settings in self:
            settings.google_places_use_api_new = settings.website_id._google_places_use_api_new()

    def action_google_places_switch_to_api_new(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_("Only administrators can switch to the Places API (New)."))
        self.website_id._switch_to_google_places_api_new()
