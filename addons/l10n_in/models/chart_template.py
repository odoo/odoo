# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        if self == self.env.ref('l10n_in.indian_chart_template_standard'):
            for journal in res:
                if journal['code'] == 'INV':
                    journal['name'] = _('Tax Invoices')
        return res

    def _load(self, company):
        res = super(AccountChartTemplate, self)._load(company)
        if self == self.env.ref("l10n_in.indian_chart_template_standard"):
            company.write({'fiscalyear_last_month': '3'})
        return res
