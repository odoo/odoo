from odoo import api, models


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'contract_id.wage_on_signature', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        return super()._compute_amount()
