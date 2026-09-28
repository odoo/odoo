from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cr_district_id = fields.Many2one(related='partner_id.l10n_cr_district_id', readonly=False)

    def _localization_use_documents(self):
        self.ensure_one()
        return self.chart_template == 'cr' or self.account_fiscal_country_id.code == 'CR' or super()._localization_use_documents()
