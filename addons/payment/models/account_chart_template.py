# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load_chart_template(self):
        # OVERRIDE
        res = super()._load_chart_template()
        self.env['payment.acquirer']._create_missing_journals()
        return res
