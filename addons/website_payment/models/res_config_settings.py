# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def action_activate_payment_provider(self):
        menu = self.env.ref('website.menu_website_website_settings', raise_if_not_found=False)
        return self._activate_payment_provider(menu and menu.id)

    def _get_activated_providers_domain(self):
        return expression.AND([
            super()._get_activate_providers_domain(),
            ['|', ('website_id', '=', False), ('website_id', '=', self.website_id.id)]
        ])
