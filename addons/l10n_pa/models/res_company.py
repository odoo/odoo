# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_pa.tools.postal_code import locate_postal_code


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pa_corregimiento = fields.Many2one(related='partner_id.l10n_pa_corregimiento', readonly=False)
    l10n_pa_poblado = fields.Many2one(related='partner_id.l10n_pa_poblado', readonly=False)
    l10n_pa_barrio = fields.Many2one(related='partner_id.l10n_pa_barrio', readonly=False)
    l10n_pa_dv = fields.Char(related='partner_id.l10n_pa_dv', readonly=False)

    @api.onchange('zip')
    def _onchange_l10n_pa_zip(self):
        if self.country_code != 'PA' or not self.zip:
            return
        location = locate_postal_code(self.env, self.zip)
        if not location:
            return {'warning': {
                'title': self.env._("Invalid postal code"),
                'message': self.env._(
                    "'%(code)s' could not be decoded, or doesn't fall within Panama.",
                    code=self.zip,
                ),
            }}
        if not location['corregimiento']:
            return {'warning': {
                'title': self.env._("Corregimiento not found"),
                'message': self.env._(
                    "The postal code is valid but doesn't fall within any known corregimiento boundary."
                ),
            }}
        self.l10n_pa_corregimiento = location['corregimiento']
        self.city = location['corregimiento'].city_id.name
        self.state_id = location['corregimiento'].city_id.state_id
        self.l10n_pa_poblado = location['poblado']
        self.l10n_pa_barrio = location['barrio']

    def _localization_use_documents(self):
        # OVERRIDE
        self.ensure_one()
        return self.chart_template == 'pa' or self.account_fiscal_country_id.code == 'PA' or super()._localization_use_documents()
