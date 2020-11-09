# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_journals(self, loaded_data):
        # OVERRIDE
        res = super()._prepare_journals(loaded_data)
        if self.env.company.account_fiscal_country_id.code == 'LU':
            for journal_vals in res['sale'] + res['purchase']:
                journal_vals['refund_sequence'] = True
        return res
