# coding: utf-8
# Copyright 2016 iterativo (https://www.iterativo.do) <info@iterativo.do>

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def _get_default_bank_journals_data(self):
        if self.env.user.company_id.country_id and self.env.user.company_id.country_id.code.upper() == 'DO':
            return [
                {'acc_name': _('Cash'), 'account_type': 'cash'},
                {'acc_name': _('Caja Chica'), 'account_type': 'cash'},
                {'acc_name': _('Cheques Clientes'), 'account_type': 'cash'},
                {'acc_name': _('Bank'), 'account_type': 'bank'}
            ]
        return super(AccountChartTemplate, self)._get_default_bank_journals_data()

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """Create fiscal journals for buys"""
        res = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_do.do_chart_template'):
            return res
        for journal in res:
            if journal['code'] == 'FACT':
                journal['name'] = _('Compras Fiscales')
        res += [{
            'type': 'purchase',
            'name': _('Compras Informales'),
            'code': 'CINF',
            'company_id': company.id,
            'show_on_dashboard': True
        }, {
            'type': 'purchase',
            'name': _('Gastos Menores'),
            'code': 'GASM',
            'company_id': company.id,
            'show_on_dashboard': True
        }, {
            'type': 'purchase',
            'name': _('Compras al Exterior'),
            'code': 'CEXT',
            'company_id': company.id,
            'show_on_dashboard': True
        }, {
            'type': 'purchase',
            'name': _('Gastos No Deducibles'),
            'code': 'GASTO',
            'company_id': company.id,
            'show_on_dashboard': True
        }]
        return res

