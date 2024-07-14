# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase


class TestPayslipComputation(TestPayslipContractBase):

    @classmethod
    def setUpClass(cls):
        super(TestPayslipComputation, cls).setUpClass()
        cls.contract_cdi.structure_type_id.country_id = cls.env.ref('base.be').id
        cls.contract_cdi.wage_on_signature = 4000.33
        cls.richard_payslip = cls.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': cls.richard_emp.id,
            'contract_id': cls.contract_cdi.id,
            'struct_id': cls.developer_pay_structure.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31)
        })

    def _reset_work_entries(self, contract):
        # Use hr.leave to automatically regenerate work entries for absences
        self.env['hr.work.entry'].search([('employee_id', '=', contract.employee_id.id)]).unlink()
        now = datetime(2016, 1, 1, 0, 0, 0)
        contract.write({
            'date_generated_from': now,
            'date_generated_to': now,
        })

    def test_worked_days_amount_with_unpaid(self):

        self._reset_work_entries(self.richard_payslip.contract_id)
        work_entries = self.richard_emp.contract_ids.generate_work_entries(date(2016, 1, 1), date(2016, 2, 1))
        work_entries.action_validate()

        self.richard_payslip._compute_worked_days_line_ids()
        work_days = self.richard_payslip.worked_days_line_ids

        attendance_line = work_days.filtered(lambda l: l.code == self.env.ref('hr_work_entry.work_entry_type_attendance').code)
        self.assertAlmostEqual(attendance_line.amount, 4000.33, delta=0.01, msg="His attendance must be paid 4033.33")
        self.richard_payslip.contract_id.wage_on_signature = 3000.33
        self.assertAlmostEqual(attendance_line.amount, 3000.33, delta=0.01, msg="His attendance must be paid 3033.33")
