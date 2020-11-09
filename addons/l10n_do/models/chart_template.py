# coding: utf-8
# Copyright 2016 iterativo (https://www.iterativo.do) <info@iterativo.do>

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_journals(self, loaded_data):
        # OVERRIDE
        res = super()._prepare_journals(loaded_data)
        company = self.env.company
        if company.account_fiscal_country_id.code == 'DO':
            res['sale'].append({
                'type': 'sale',
                'name': _('Migración CxC'),
                'code': 'CXC',
                'company_id': company.id,
                'show_on_dashboard': True,
            })
            res['purchase'] += [
                {
                    'type': 'purchase',
                    'name': _('Gastos No Deducibles'),
                    'code': 'GASTO',
                    'company_id': company.id,
                    'show_on_dashboard': True,
                },
                {
                    'type': 'purchase',
                    'name': _('Migración CxP'),
                    'code': 'CXP',
                    'company_id': company.id,
                    'show_on_dashboard': True,
                },
            ]
            res['cash'] = [
                {
                    'type': 'cash',
                    'name': _('Cash'),
                    'company_id': company.id,
                },
                {
                    'type': 'cash',
                    'name': _('Caja Chica'),
                    'company_id': company.id,
                },
                {
                    'type': 'cash',
                    'name': _('Cheques Clientes'),
                    'company_id': company.id,
                },
            ]
            res['bank'] = [
                {
                    'type': 'bank',
                    'name': _('Bank'),
                    'company_id': company.id,
                },
            ]
        return res
