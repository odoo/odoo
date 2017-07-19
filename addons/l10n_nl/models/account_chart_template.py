# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _get_account_vals(self, company, account_template, code_acc, tax_template_ref):
        account_vals = super(AccountChartTemplate, self)._get_account_vals(company, account_template, code_acc, tax_template_ref)

        # Copy the SBR code from the template
        if account_template.l10n_nl_sbr:
            account_vals['l10n_nl_sbr'] = account_template.l10n_nl_sbr.id

        return account_vals


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def execute(self):
        # Add tag / SBR code to 999999 account
        res = super(WizardMultiChartsAccounts, self).execute()
        account = self.env['account.account'].search([('code', '=', '999999'), ('company_id', '=', self.company_id.id)])
        if account:
            account.tag_ids = [(4, self.env.ref('l10n_nl.account_tag_32').id)]
            account.l10n_nl_sbr = self.env.ref('l10n_nl.sbr_code_WNerNerNer')
        return res
