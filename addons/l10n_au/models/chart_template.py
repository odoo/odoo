# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, company):
        res = super()._load(company)
        if self == self.env.ref("l10n_au.l10n_au_chart_template"):
            company.write({
                'fiscalyear_last_month': '6',
                'fiscalyear_last_day': 30,
                # Changing the opening date to the first day of the fiscal year.
                # This way the opening entries will be set to the 30th of June.
                'account_opening_date': fields.Date.context_today(self).replace(month=7, day=1),
            })
        return res
