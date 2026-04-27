from odoo import models, Command


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _load(self, template_code, company, install_demo, force_create=True):
        # Override
        super()._load(template_code, company, install_demo, force_create)

        if template_code == 'ae':
            self._l10n_ae_corporate_tax_report_setup_account_tags([company])

    def _l10n_ae_corporate_tax_report_setup_account_tags(self, ae_companies):
        exp_tag = self.env.ref('l10n_ae_corporate_tax_report.uae_account_tag_c_tax_exp')
        cog_tag = self.env.ref('l10n_ae_corporate_tax_report.uae_account_tag_c_tax_cog')

        for company in ae_companies:
            for expense_account in self.env['account.account'].search([('company_ids', 'any', [('id', '=', company.id)]), ('account_type', 'in', ['expense', 'expense_depreciation'])]):
                expense_account.tag_ids = [Command.link(exp_tag.id)]

            for cog_account in self.env['account.account'].search([('company_ids', 'any', [('id', '=', company.id)]), ('account_type', '=', 'expense_direct_cost')]):
                cog_account.tag_ids = [Command.link(cog_tag.id)]
