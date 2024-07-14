# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.rrule import rrule, DAILY
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.fields import Date
from odoo.tests import tagged
from odoo.addons.hr_payroll.tests.common import TestPayslipContractBase


@tagged('payslip_computation')
class TestPayslipComputation(TestPayslipContractBase):

    @classmethod
    def setUpClass(cls):
        super(TestPayslipComputation, cls).setUpClass()

        cls.richard_payslip = cls.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': cls.richard_emp.id,
            'contract_id': cls.contract_cdi.id,  # wage = 5000 => average/day (over 3months/13weeks): 230.77
            'struct_id': cls.developer_pay_structure.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31)
        })
        cls.richard_emp.resource_calendar_id = cls.contract_cdi.resource_calendar_id

        cls.richard_payslip_quarter = cls.env['hr.payslip'].create({
            'name': 'Payslip of Richard Quarter',
            'employee_id': cls.richard_emp.id,
            'contract_id': cls.contract_cdi.id,
            'struct_id': cls.developer_pay_structure.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 3, 31)
        })
        # To avoid having is_paid = False in some tests, as all the records are created on the
        # same transaction which is quite unlikely supposed to happen in real conditions
        worked_days = (cls.richard_payslip + cls.richard_payslip_quarter).worked_days_line_ids
        worked_days._compute_is_paid()
        worked_days.flush_model(['is_paid'])

    def _reset_work_entries(self, contract):
        # Use hr.leave to automatically regenerate work entries for absences
        self.env['hr.work.entry'].search([('employee_id', '=', contract.employee_id.id)]).unlink()
        now = datetime(2016, 1, 1, 0, 0, 0)
        contract.write({
            'date_generated_from': now,
            'date_generated_to': now,
        })

    def test_unpaid_amount(self):
        self.assertAlmostEqual(self.richard_payslip._get_unpaid_amount(), 0, places=2, msg="It should be paid the full wage")

        self._reset_work_entries(self.richard_payslip.contract_id)
        self.env['resource.calendar.leaves'].create({
            'name': 'Doctor Appointment',
            'date_from': datetime.strptime('2016-1-11 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2016-1-11 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.richard_emp.resource_id.id,
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': self.work_entry_type_unpaid.id,
            'time_type': 'leave',
        })

        self.richard_emp.contract_ids.generate_work_entries(date(2016, 1, 1), date(2016, 2, 1))
        self.richard_payslip._compute_worked_days_line_ids()
        # TBE: In master the Monetary field were not rounded because the currency_id wasn't computed yet.
        # The test was incorrect using the value 238.09, with 238.11 it is ok
        self.assertAlmostEqual(self.richard_payslip._get_unpaid_amount(), 238.11, delta=0.01, msg="It should be paid 238.11 less")

    def test_worked_days_amount_with_unpaid(self):
        self.env['resource.calendar.leaves'].create({
            'name': 'Doctor Appointment',
            'date_from': datetime.strptime('2016-1-11 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2016-1-11 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.richard_emp.resource_id.id,
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
            'time_type': 'leave',
        })

        self.env['resource.calendar.leaves'].create({
            'name': 'Unpaid Doctor Appointment',
            'date_from': datetime.strptime('2016-1-21 07:00:00', '%Y-%m-%d %H:%M:%S'),
            'date_to': datetime.strptime('2016-1-21 18:00:00', '%Y-%m-%d %H:%M:%S'),
            'resource_id': self.richard_emp.resource_id.id,
            'calendar_id': self.richard_emp.resource_calendar_id.id,
            'work_entry_type_id': self.work_entry_type_unpaid.id,
            'time_type': 'leave',
        })

        self._reset_work_entries(self.richard_payslip.contract_id)
        work_entries = self.richard_emp.contract_ids.generate_work_entries(date(2016, 1, 1), date(2016, 2, 1))
        work_entries.action_validate()

        self.richard_payslip._compute_worked_days_line_ids()
        work_days = self.richard_payslip.worked_days_line_ids

        self.assertAlmostEqual(sum(work_days.mapped('amount')), self.contract_cdi.wage - self.richard_payslip._get_unpaid_amount())

        leave_line = work_days.filtered(lambda l: l.code == self.work_entry_type_leave.code)
        self.assertAlmostEqual(leave_line.amount, 238.11, delta=0.01, msg="His paid time off must be paid 238.11")

        extra_attendance_line = work_days.filtered(lambda l: l.code == self.work_entry_type_unpaid.code)
        self.assertAlmostEqual(extra_attendance_line.amount, 0.0, places=2, msg="His unpaid time off must be paid 0.")

        attendance_line = work_days.filtered(lambda l: l.code == self.env.ref('hr_work_entry.work_entry_type_attendance').code)
        self.assertAlmostEqual(attendance_line.amount, 4524.11, delta=0.01, msg="His attendance must be paid 4524.11")

    def test_worked_days_with_unpaid(self):
        self.contract_cdi.resource_calendar_id = self.calendar_38h
        self.richard_emp.resource_calendar_id = self.calendar_38h

        # Create 2 hours upaid leave every day during 2 weeks
        for day in rrule(freq=DAILY, byweekday=[0, 1, 2, 3, 4], count=10, dtstart=datetime(2016, 2, 8)):
            start = day + timedelta(hours=13.6)
            end = day + timedelta(hours=15.6)
            self.env['resource.calendar.leaves'].create({
                'name': 'Unpaid Leave',
                'date_from': start,
                'date_to': end,
                'resource_id': self.richard_emp.resource_id.id,
                'calendar_id': self.richard_emp.resource_calendar_id.id,
                'work_entry_type_id': self.work_entry_type_unpaid.id,
                'time_type': 'leave',
            })

        self._reset_work_entries(self.richard_payslip_quarter.contract_id)
        work_entries = self.richard_emp.contract_ids.generate_work_entries(date(2016, 1, 1), date(2016, 3, 31))
        work_entries.action_validate()

        self.richard_payslip_quarter._compute_worked_days_line_ids()
        work_days = self.richard_payslip_quarter.worked_days_line_ids

        leave_line = work_days.filtered(lambda l: l.code == self.env.ref('hr_work_entry.work_entry_type_attendance').code)
        self.assertAlmostEqual(leave_line.number_of_days, 62.5, places=2)

        extra_attendance_line = work_days.filtered(lambda l: l.code == self.work_entry_type_unpaid.code)
        self.assertAlmostEqual(extra_attendance_line.number_of_days, 2.5, places=2)

    def test_worked_days_16h_with_unpaid(self):
        self.contract_cdi.resource_calendar_id = self.calendar_16h
        self.richard_emp.resource_calendar_id = self.calendar_16h

        # Create 2 hours upaid leave every Thursday Evening during 5 weeks
        for day in rrule(freq=DAILY, byweekday=3, count=5, dtstart=datetime(2016, 2, 4)):
            start = day + timedelta(hours=12.5)
            end = day + timedelta(hours=14.5)
            self.env['resource.calendar.leaves'].create({
                'name': 'Unpaid Leave',
                'date_from': start,
                'date_to': end,
                'resource_id': self.richard_emp.resource_id.id,
                'calendar_id': self.richard_emp.resource_calendar_id.id,
                'work_entry_type_id': self.work_entry_type_unpaid.id,
                'time_type': 'leave',
            })
        self._reset_work_entries(self.richard_payslip_quarter.contract_id)

        work_entries = self.richard_emp.contract_ids.generate_work_entries(date(2016, 1, 1), date(2016, 3, 31))
        work_entries.action_validate()

        self.richard_payslip_quarter._compute_worked_days_line_ids()
        work_days = self.richard_payslip_quarter.worked_days_line_ids

        leave_line = work_days.filtered(lambda l: l.code == self.env.ref('hr_work_entry.work_entry_type_attendance').code)
        self.assertAlmostEqual(leave_line.number_of_days, 49.5, places=2)

        extra_attendance_line = work_days.filtered(lambda l: l.code == self.work_entry_type_unpaid.code)
        self.assertAlmostEqual(extra_attendance_line.number_of_days, 2.5, places=2)

    def test_worked_days_38h_friday_with_unpaid(self):
        self.contract_cdi.resource_calendar_id = self.calendar_38h_friday_light
        self.richard_emp.resource_calendar_id = self.calendar_38h_friday_light

        # Create 4 hours (all work day) upaid leave every Friday during 5 weeks
        for day in rrule(freq=DAILY, byweekday=4, count=5, dtstart=datetime(2016, 2, 4)):
            start = day + timedelta(hours=7)
            end = day + timedelta(hours=11)
            self.env['resource.calendar.leaves'].create({
                'name': 'Unpaid Leave',
                'date_from': start,
                'date_to': end,
                'resource_id': self.richard_emp.resource_id.id,
                'calendar_id': self.richard_emp.resource_calendar_id.id,
                'work_entry_type_id': self.work_entry_type_unpaid.id,
                'time_type': 'leave',
            })

        self._reset_work_entries(self.richard_payslip_quarter.contract_id)
        work_entries = self.richard_emp.contract_ids.generate_work_entries(date(2016, 1, 1), date(2016, 3, 31))
        work_entries.action_validate()

        self.richard_payslip_quarter._compute_worked_days_line_ids()
        work_days = self.richard_payslip_quarter.worked_days_line_ids

        leave_line = work_days.filtered(lambda l: l.code == self.env.ref('hr_work_entry.work_entry_type_attendance').code)
        self.assertAlmostEqual(leave_line.number_of_days, 62.5, places=2)

        extra_attendance_line = work_days.filtered(lambda l: l.code == self.work_entry_type_unpaid.code)
        self.assertAlmostEqual(extra_attendance_line.number_of_days, 2.5, places=2)

    def test_sum_category(self):
        self.richard_payslip.compute_sheet()
        self.richard_payslip.action_payslip_done()

        self.richard_payslip2 = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
            'contract_id': self.contract_cdi.id,
            'struct_id': self.developer_pay_structure.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31)
        })
        self.richard_payslip2.compute_sheet()
        self.assertEqual(3010.13, self.richard_payslip2.line_ids.filtered(lambda x: x.code == 'SUMALW').total)

    def test_payslip_generation_with_extra_work(self):
        # /!\ this is in the weekend (Sunday) => no calendar attendance at this time
        start = datetime(2015, 11, 1, 10, 0, 0)
        end = datetime(2015, 11, 1, 17, 0, 0)
        work_entries = self.contract_cdd.generate_work_entries(start.date(), (end + relativedelta(days=2)).date())
        work_entries.action_validate()

        work_entry = self.env['hr.work.entry'].create({
            'name': 'Extra',
            'employee_id': self.richard_emp.id,
            'contract_id': self.contract_cdd.id,
            'work_entry_type_id': self.work_entry_type.id,
            'date_start': start,
            'date_stop': end,
        })
        work_entry.action_validate()
        payslip_wizard = self.env['hr.payslip.employees'].create({'employee_ids': [(4, self.richard_emp.id)]})
        batch_id = payslip_wizard.with_context({
            'default_date_start': Date.to_string(start),
            'default_date_end': Date.to_string(end + relativedelta(days=1))
        }).compute_sheet()['res_id']
        payslip = self.env['hr.payslip'].search([
            ('employee_id', '=', self.richard_emp.id),
            ('payslip_run_id', '=', batch_id),
        ])
        work_line = payslip.worked_days_line_ids.filtered(lambda l: l.work_entry_type_id == self.env.ref('hr_work_entry.work_entry_type_attendance'))  # From default calendar.attendance
        extra_work_line = payslip.worked_days_line_ids.filtered(lambda l: l.work_entry_type_id == self.work_entry_type)

        self.assertTrue(work_line, "It should have a work line in the payslip")
        self.assertTrue(extra_work_line, "It should have an extra work line in the payslip")
        self.assertEqual(work_line.number_of_hours, 8.0, "It should have 8 hours of work")  # Monday
        self.assertEqual(extra_work_line.number_of_hours, 7.0, "It should have 7 hours of extra work")  # Sunday

    def test_work_data_with_exceeding_interval(self):
        self.env['hr.work.entry'].create({
            'name': 'Attendance',
            'employee_id': self.richard_emp.id,
            'contract_id': self.contract_cdd.id,
            'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
            'date_start': datetime(2015, 11, 9, 20, 0),
            'date_stop': datetime(2015, 11, 10, 7, 0)
        }).action_validate()
        self.env['hr.work.entry'].create({
            'name': 'Attendance',
            'employee_id': self.richard_emp.id,
            'contract_id': self.contract_cdd.id,
            'work_entry_type_id': self.env.ref('hr_work_entry.work_entry_type_attendance').id,
            'date_start': datetime(2015, 11, 10, 21, 0),
            'date_stop': datetime(2015, 11, 11, 5, 0),
        }).action_validate()
        self.contract_cdd.generate_work_entries(date(2015, 11, 10), date(2015, 11, 10))
        hours = self.contract_cdd.get_work_hours(date(2015, 11, 10), date(2015, 11, 10))
        sum_hours = sum(v for k, v in hours.items() if k in self.env.ref('hr_work_entry.work_entry_type_attendance').ids)
        self.assertAlmostEqual(sum_hours, 18, delta=0.01, msg='It should count 18 attendance hours')  # 8h normal day + 7h morning + 3h night

    def test_payslip_without_contract(self):
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31)
        })
        self.assertTrue(payslip.contract_id)
        payslip.contract_id = False
        self.assertEqual(payslip._get_contract_wage(), 0, "It should have a default wage of 0")
        self.assertEqual(payslip.basic_wage, 0, "It should have a default wage of 0")
        self.assertEqual(payslip.gross_wage, 0, "It should have a default wage of 0")
        self.assertEqual(payslip.net_wage, 0, "It should have a default wage of 0")

    def test_payslip_with_salary_attachment(self):
        #Create multiple salary attachments, some running, some closed
        self.env['hr.salary.attachment'].create([
            {
                'employee_ids': [(4, self.richard_emp.id)],
                'monthly_amount': 150,
                'deduction_type_id': self.env.ref('hr_payroll.hr_salary_attachment_type_child_support').id,
                'date_start': date(2016, 1, 1),
                'description': 'Child Support',
            },
            {
                'employee_ids': [(4, self.richard_emp.id)],
                'monthly_amount': 400,
                'total_amount': 1000,
                'paid_amount': 1000,
                'deduction_type_id': self.env.ref('hr_payroll.hr_salary_attachment_type_assignment').id,
                'date_start': date(2015, 1, 1),
                'date_end': date(2015, 4, 1),
                'description': 'Unpaid fine',
                'state': 'close',
            },
        ])

        car_accident = self.env['hr.salary.attachment'].create({
                'employee_ids': [(4, self.richard_emp.id)],
                'monthly_amount': 250,
                'paid_amount': 1450,
                'total_amount': 1500,
                'deduction_type_id': self.env.ref('hr_payroll.hr_salary_attachment_type_attachment').id,
                'date_start': date(2016, 1, 1),
                'description': 'Car accident',
        })

        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
            'contract_id': self.contract_cdi.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31)
        })
        input_lines = payslip.input_line_ids
        self.assertTrue(input_lines.filtered(lambda r: r.code == 'CHILD_SUPPORT'), 'There should be an input line for child support.')
        self.assertTrue(input_lines.filtered(lambda r: r.code == 'ATTACH_SALARY'), 'There should be an input line for the car accident.')
        self.assertTrue(input_lines.filtered(lambda r: r.code == 'ATTACH_SALARY').amount <= 50, 'The amount for the car accident input line should be 50 or less.')
        self.assertFalse(input_lines.filtered(lambda r: r.code == 'ASSIG_SALARY'), 'There should not be an input line for the unpaid fine.')
        payslip.compute_sheet()
        lines = payslip.line_ids
        self.assertTrue(lines.filtered(lambda r: r.code == 'CHILD_SUPPORT'), 'There should be a salary line for child support.')
        self.assertTrue(lines.filtered(lambda r: r.code == 'ATTACH_SALARY'), 'There should be a salary line for car accident.')
        payslip.action_payslip_done()
        payslip.action_payslip_paid()
        self.assertEqual(car_accident.state, 'close', 'The salary attachment should be completed.')

    def test_payslip_with_multiple_input_same_type(self):
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
            'contract_id': self.contract_cdi.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31)
        })
        self.env['hr.payslip.input'].create([
            {
                'payslip_id': payslip.id,
                'sequence': 1,
                'input_type_id': self.env.ref("hr_payroll.BASIC").id,
                'amount': 100,
                'contract_id': self.contract_cdi.id
            },
            {
                'payslip_id': payslip.id,
                'sequence': 2,
                'input_type_id': self.env.ref("hr_payroll.BASIC").id,
                'amount': 200,
                'contract_id': self.contract_cdi.id
            },
        ])
        payslip.compute_sheet()
        lines = payslip.line_ids
        self.assertEqual(len(lines.filtered(lambda r: r.code == 'BASIC')), 1)

    def test_defaultdict_get(self):
        # defaultdict.get(key) returns None if the key doesn't exist instead of default factory value
        # which could lead to a traceback
        self.developer_pay_structure.rule_ids.filtered(lambda r: r.code == "NET").amount_python_compute = "result = categories['BASIC'] + categories['ALW'] + categories['DED'] + categories.get('TEST')"
        payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
            'date_from': date(2016, 1, 1),
            'date_to': date(2016, 1, 31)
        })
        payslip.compute_sheet()
