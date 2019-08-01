# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        # For Vietnamese accounting Standards compliance, sale and purchase journals must have a dedicated sequence for any refund
        journals = super(AccountChartTemplate, self)._prepare_all_journals(acc_template_ref, company, journals_dict)
        if company.country_id == self.env.ref('base.vn'):
            for journal in journals:
                if journal['type'] in ['sale', 'purchase']:
                    journal['refund_sequence'] = True
        return journals
