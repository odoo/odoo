# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _get_activated_providers(self):
        providers = super()._get_activated_providers()
        return providers.filtered(lambda p: not p.website_id or p.website_id == self.website_id.id)

    @api.depends('website_id')
    def _compute_providers_state(self):
        super()._compute_providers_state()

    def action_activate_payment_provider(self):
        menu = self.env.ref('website.menu_website_website_settings', raise_if_not_found=False)
        return self._activate_payment_provider(menu and menu.id)
