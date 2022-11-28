from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _get_account_vals(self, company, account_template, code_acc, tax_template_ref):
        vals = super()._get_account_vals(company, account_template, code_acc, tax_template_ref)
        vals['l10n_pt_taxonomy_code'] = account_template.l10n_pt_taxonomy_code
        return vals

    def _create_bank_journals(self, company, acc_template_ref):
        journals = super()._create_bank_journals(company, acc_template_ref)
        if company.account_fiscal_country_id.code == 'PT':
            for journal in journals:
                if journal.type == 'cash':
                    journal.default_account_id.l10n_pt_taxonomy_code = 1
                elif journal.type == 'bank':
                    journal.default_account_id.l10n_pt_taxonomy_code = 2
        return journals
