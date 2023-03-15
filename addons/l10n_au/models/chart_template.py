# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        res = super()._load(company)
        if self == self.env.ref("l10n_au.l10n_au_chart_template"):
            company.write({
                'fiscalyear_last_month': '6',
                'fiscalyear_last_day': 30,
            })
        return res
