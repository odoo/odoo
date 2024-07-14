# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo.tests.common import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase


@tagged('payslips_multi_contract')
class TestPayslipMultiContract(TestPayslipContractBase):

    def test_multi_contract(self):
        start = date(2015, 11, 1)
        end = date(2015, 11, 30)
        work_entries = self.richard_emp.contract_ids.generate_work_entries(start, end)
        work_entries.action_validate()

        # First contact: 40h, start of the month
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.richard_emp.id,
            'date_from': start,
            'date_to': end,
            'contract_id': self.contract_cdd.id,
            'struct_id': self.developer_pay_structure.id,
        })
        attendance_line = payslip.worked_days_line_ids[0]
        self.assertEqual(attendance_line.number_of_hours, 80)
        self.assertEqual(attendance_line.number_of_days, 10)
        out_of_contract_line = payslip.worked_days_line_ids[1]
        self.assertEqual(out_of_contract_line.number_of_hours, 88)
        self.assertEqual(out_of_contract_line.number_of_days, 11)

        # Second contract: 35h, end of the month
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.richard_emp.id,
            'date_from': start,
            'date_to': end,
            'contract_id': self.contract_cdi.id,
            'struct_id': self.developer_pay_structure.id,
        })
        attendance_line = payslip.worked_days_line_ids[0]
        self.assertEqual(attendance_line.number_of_hours, 77)
        self.assertEqual(attendance_line.number_of_days, 11)
        out_of_contract_line = payslip.worked_days_line_ids[1]
        self.assertEqual(out_of_contract_line.number_of_hours, 70)
        self.assertEqual(out_of_contract_line.number_of_days, 10)
