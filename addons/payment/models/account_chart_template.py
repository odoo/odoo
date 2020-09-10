# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _create_bank_journals(self, company, acc_template_ref):
        res = super()._create_bank_journals(company, acc_template_ref)

        # Try to generate the missing journals
        return res + self.env['payment.acquirer']._create_missing_journals(company=company)
