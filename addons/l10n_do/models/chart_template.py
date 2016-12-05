# coding: utf-8
# Copyright 2016 iterativo (https://www.iterativo.do) <info@iterativo.do>

from openerp import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def _prepare_all_journals(
            self, acc_template_ref, company, journals_dict=None):
        res = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_do.do_chart_template'):
            return res
        res.append(
            {'name': _('Caja Chica'),
             'type': 'cash',
             'code': _('CSH2'),
             'company_id': company.id,
             'show_on_dashboard': True,
             # 'sequence': 4,
             },
             )
        return res


class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'

    @api.multi
    def execute(self):
        """Overwrite the account code to Undistributed Profits/Losses"""
        res = super(WizardMultiChartsAccounts, self).execute()
        account_obj = self.env['account.account']
        account = account_obj.search(
                [('code', '=', '999999'), ('user_type_id', '=', self.env.ref(
                                     "account.data_unaffected_earnings").id)])
        account.write({'code': '61010100'})
        return res
