# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # === COMPUTE METHODS === #

    @api.depends('company_id', 'website_id')
    def _compute_active_provider_id(self):
        return super()._compute_active_provider_id()

    @api.depends('company_id', 'website_id')
    def _compute_has_enabled_provider(self):
        return super()._compute_has_enabled_provider()

    def _get_active_providers_domain(self, *args, **kwargs):
        """Override of `payment` to only return providers compatible with the current website."""
        self.ensure_one()
        return Domain.AND([
            super()._get_active_providers_domain(*args, **kwargs),
            ['|', ('website_id', '=', False), ('website_id', '=', self.website_id.id)],
        ])

    # === ACTION METHODS === #

    # Unique name to avoid colliding with `sale`.
    def action_w_payment_start_payment_onboarding(self):
        menu = self.env.ref('website.menu_website_website_settings', raise_if_not_found=False)
        return self._start_payment_onboarding(menu and menu.id)
