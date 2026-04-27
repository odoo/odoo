from odoo import fields, models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    nacha_effective_date = fields.Date('The effective date of the NACHA file generated for this batch')

    def action_payment_report(self, export_format='nacha'):
        action = super().action_payment_report()
        if self.company_id.country_code != 'US':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
