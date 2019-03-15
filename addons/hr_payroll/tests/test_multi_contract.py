
import os
from datetime import datetime
from odoo.tools import config, test_reports
from odoo.tests.common import tagged
from odoo.exceptions import ValidationError
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase

@tagged('payslips_multi_contract')
class TestPayslipMultiContract(TestPayslipContractBase):

    def create_leave(self, start, end):
        return self.env['hr.leave'].create({
            'name': 'Doctor Appointment',
            'employee_id': self.richard_emp.id,
            'holiday_status_id': self.leave_type.id,
            'date_from': start,
            'date_to': end,
        })

    def test_multi_contract(self):
        # First contact: 40h, start of the month
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.richard_emp.id,
            'date_from': datetime.strptime('2015-11-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2015-11-30', '%Y-%m-%d'),
            'contract_id': self.contract_cdd.id,
        })
        payslip.onchange_employee()
        self.assertEqual(payslip.worked_days_line_ids.number_of_hours, 80, "It should be 80 hours of work this month for this contract")
        self.assertEqual(payslip.worked_days_line_ids.number_of_days, 10, "It should be 10 days of work this month for this contract")

        # Second contract: 35h, end of the month
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.richard_emp.id,
            'date_from': datetime.strptime('2015-11-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2015-11-30', '%Y-%m-%d'),
            'contract_id': self.contract_cdi.id,
        })
        payslip.onchange_employee()
        self.assertEqual(payslip.worked_days_line_ids.number_of_hours, 77, "It should be 77 hours of work this month for this contract")
        self.assertEqual(payslip.worked_days_line_ids.number_of_days, 11, "It should be 11 days of work this month for this contract")

    def test_multi_contract_holiday(self):
        # Leave during second contract
        leave = self.env['resource.calendar.leaves'].create({
            'name': 'leave name',
            'date_from': datetime.strptime('2015-11-17 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2015-11-20 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.richard_emp.resource_id.id,
            'calendar_id': self.calendar_35h.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
            'time_type': 'leave',
        })
        payslip = self.env['hr.payslip'].create({
            'name': 'November 2015',
            'employee_id': self.richard_emp.id,
            'date_from': datetime.strptime('2015-11-01', '%Y-%m-%d'),
            'date_to': datetime.strptime('2015-11-30', '%Y-%m-%d'),
            'contract_id': self.contract_cdi.id,
        })
        payslip.onchange_employee()
        work = payslip.worked_days_line_ids.filtered(lambda line: line.code == 'WORK100')
        leave = payslip.worked_days_line_ids.filtered(lambda line: line.code == 'LEAVE100')
        self.assertEqual(work.number_of_hours, 49, "It should be 49 hours of work this month for this contract")
        self.assertEqual(leave.number_of_hours, 28, "It should be 28 hours of leave this month for this contract")
        self.assertEqual(work.number_of_days, 7, "It should be 7 days of work this month for this contract")
        self.assertEqual(leave.number_of_days, 4, "It should be 4 days of leave this month for this contract")

    def test_move_contract_in_leave(self):
        # test move contract dates such that a leave is accross two contracts
        start = datetime.strptime('2015-11-05 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.contract_cdi.write({'date_start': datetime.strptime('2015-12-30', '%Y-%m-%d').date()})
        print(self.contract_cdi.date_start, 'test')
        # begins during contract, ends after contract
        leave = self.create_leave(start, end)
        leave.action_approve()
        # move contract in the middle of the leave
        with self.assertRaises(ValidationError):
            self.contract_cdi.date_start = datetime.strptime('2015-11-17', '%Y-%m-%d').date()

    def test_create_contract_in_leave(self):
        # test create contract such that a leave is accross two contracts
        start = datetime.strptime('2015-11-05 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.contract_cdi.date_start = datetime.strptime('2015-12-30', '%Y-%m-%d').date() # remove this contract to be able to create the leave
        # begins during contract, ends after contract
        leave = self.create_leave(start, end)
        leave.action_approve()
        # move contract in the middle of the leave
        with self.assertRaises(ValidationError):
            contract = self.env['hr.contract'].create({
                'date_start': datetime.strptime('2015-11-30', '%Y-%m-%d').date(),
                'name': 'Contract for Richard',
                'resource_calendar_id': self.calendar_40h.id,
                'wage': 5000.0,
                'employee_id': self.richard_emp.id,
                'structure_type_id': self.structure_type.id,
                'state': 'open',
            })

    def test_leave_outside_contract(self):

        # Leave outside contract => should not raise
        start = datetime.strptime('2014-10-18 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2014-10-20 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

        # begins before contract, ends during contract => should not raise
        start = datetime.strptime('2014-10-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-01-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

        # begins during contract, ends after contract => should not raise
        self.contract_cdi.date_end = datetime.strptime('2015-11-30', '%Y-%m-%d').date()
        start = datetime.strptime('2015-11-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-5 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end)

    def test_no_leave_overlapping_contracts(self):

        with self.assertRaises(ValidationError):
            # Overlap two contracts
            start = datetime.strptime('2015-11-12 07:00:00', '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime('2015-11-17 18:00:00', '%Y-%m-%d %H:%M:%S')
            leave = self.create_leave(start, end)

        # Leave inside fixed term contract => should not raise
        start = datetime.strptime('2015-11-04 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-07 09:00:00', '%Y-%m-%d %H:%M:%S')
        leave = self.create_leave(start, end)

        # Leave inside contract (no end) => should not raise
        start = datetime.strptime('2015-11-18 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-20 09:00:00', '%Y-%m-%d %H:%M:%S')
        leave = self.create_leave(start, end)

    def test_leave_request_next_contracts(self):

        start = datetime.strptime('2015-11-23 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-24 18:00:00', '%Y-%m-%d %H:%M:%S')
        leave = self.create_leave(start, end)

        leave._compute_number_of_hours_display()
        self.assertEqual(leave.number_of_hours_display, 14, "It should count hours according to the future contract.")
