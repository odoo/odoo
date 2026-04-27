from odoo import models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_payment_report(self, export_format='sepa'):
        action = super().action_payment_report()
        if self.company_id.currency_id.name != 'EUR':
            return action
        action.update({
            'context': {
                **action['context'],
                'default_export_format': export_format,
            },
        })
        return action
