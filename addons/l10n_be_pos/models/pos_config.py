# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def create(self, vals_list):
        for val in vals_list:
            company_id = self.env['res.company'].browse(val.get('company_id'))
            if company_id.exists() and company_id.country_id.code == 'BE':
                rounding_method = self.env['account.cash.rounding'].search([
                    ('company_id', '=', company_id.id),
                    ('name', '=', 'Round to 0.05'),
                    ], limit=1)
                if rounding_method:
                    val['cash_rounding'] = True
                    val['rounding_method'] = rounding_method.id
                    val['only_round_cash_method'] = True

        return super().create(vals_list)
