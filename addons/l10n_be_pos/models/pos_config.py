# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosConfig(models.Model):
    _name = 'pos.config'
    _inherit = 'pos.config'

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)

        company = self.env.company
        if company.country_id.code == 'BE':
            rounding_method = self.env.ref(
                    'l10n_be_pos.cash_rounding_be_05', raise_if_not_found=False,
            )
            if rounding_method:
                defaults['cash_rounding'] = True
                defaults['rounding_method'] = rounding_method.id

        return defaults
