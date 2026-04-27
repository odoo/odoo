# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipBase

@tagged('-at_install', 'post_install', 'payslip_line')
class TestPayslipLineEdit(TestPayslipBase, HttpCase):
    def test_ui(self):
        """ Test editing payslip line flow"""
        self.richard_emp.contract_ids[0].state = 'open'
        self.richard_emp.contract_ids[0].wage = 1234

        richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id
        })
        richard_payslip.compute_sheet()
        self.start_tour("/odoo", 'hr_payroll_edit_payslip_lines_tour', login='admin', step_delay=100)
