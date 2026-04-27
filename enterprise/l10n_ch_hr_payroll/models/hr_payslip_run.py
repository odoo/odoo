# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    l10n_ch_pay_13th_month = fields.Boolean(
        string="Pay Thirteen Month")

    def action_payment_report(self, export_format='iso20022_ch'):
        action = super().action_payment_report()
        if self.company_id.country_code != 'CH':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
