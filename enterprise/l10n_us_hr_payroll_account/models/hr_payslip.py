# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    nacha_effective_date = fields.Date('The effective date of the NACHA file generated for this payslip')

    def action_payslip_payment_report(self, export_format='nacha'):
        action = super().action_payslip_payment_report()
        if self.company_id.country_code != 'US':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
