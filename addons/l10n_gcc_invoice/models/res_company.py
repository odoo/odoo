from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_gcc_dual_language_invoice = fields.Boolean(string='GCC Formatted Invoices', compute="_compute_l10n_gcc_dual_language_invoice", store=True, readonly=False)
    l10n_gcc_country_is_gcc = fields.Boolean(compute="_compute_l10n_gcc_country_is_gcc")

    @api.depends('partner_id.country_id.country_group_ids.code')
    def _compute_l10n_gcc_country_is_gcc(self):
        for record in self:
            record.l10n_gcc_country_is_gcc = 'GCC' in record.country_id.country_group_codes

    @api.depends("country_id.code")
    def _compute_l10n_gcc_dual_language_invoice(self):
        gcc_companies = self.filtered(lambda rec: rec.country_code in ['SA', 'AE', 'KW', 'QA'])
        gcc_companies.l10n_gcc_dual_language_invoice = True
        (self - gcc_companies).l10n_gcc_dual_language_invoice = False
