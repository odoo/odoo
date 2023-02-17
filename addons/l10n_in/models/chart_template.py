# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        """ Set Opening Date and Fiscal Year End in Indian localization"""
        res = super(AccountChartTemplate, self)._load(company)
        if self == self.env.ref("l10n_in.indian_chart_template_standard"):
            company.write({
                'account_opening_date': fields.Date.context_today(self).replace(month=4, day=1),
                'fiscalyear_last_month': '3',
            })
        return res
