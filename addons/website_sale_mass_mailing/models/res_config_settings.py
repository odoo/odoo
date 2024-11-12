# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_newsletter_enabled = fields.Boolean()
    newsletter_id = fields.Many2one(related='website_id.newsletter_id', readonly=False)

    # === CRUD METHODS ===#

    @api.model
    def get_values(self):
        res = super().get_values()
        res['is_newsletter_enabled'] = self.env.ref('website_sale_mass_mailing.newsletter').active
        return res

    def set_values(self):
        super().set_values()
        newsletter_view = self.env.ref('website_sale_mass_mailing.newsletter')
        if newsletter_view.active != self.is_newsletter_enabled:
            newsletter_view.active = self.is_newsletter_enabled
