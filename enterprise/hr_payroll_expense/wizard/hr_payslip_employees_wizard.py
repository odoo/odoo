from odoo import models


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def compute_sheet(self):
        # EXTENDS hr_payroll to avoid adding the expenses input line to the payslips when generating them
        self_ = self.with_context(payslip_batch_creation=True)
        return super(HrPayslipEmployees, self_).compute_sheet()
