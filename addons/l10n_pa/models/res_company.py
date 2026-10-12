# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pa_corregimiento = fields.Many2one(related='partner_id.l10n_pa_corregimiento', readonly=False)
    l10n_pa_dv = fields.Char(related='partner_id.l10n_pa_dv', readonly=False)

    def _localization_use_documents(self):
        # OVERRIDE
        self.ensure_one()
        return self.chart_template == 'pa' or self.account_fiscal_country_id.code == 'PA' or super()._localization_use_documents()
