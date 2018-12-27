# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def _create_bank_journals(self, company, acc_template_ref):
        res = super(AccountChartTemplate, self)._create_bank_journals(company, acc_template_ref)

        # Try to generate the missing journals
        return res + self.env['payment.acquirer']._create_missing_journal_for_acquirers(company=company)
