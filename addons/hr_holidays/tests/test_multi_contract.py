# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo.exceptions import ValidationError
from odoo.tests import Form, freeze_time, tagged
from odoo.addons.hr_holidays.tests.common import TestHolidayContract


@tagged('multi_contract')
class TestHolidaysMultiContract(TestHolidayContract):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_move_contract_in_leave(self):
        # test move contract dates such that a leave is across two contracts
        start = datetime.strptime('2015-11-05 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.contract_cdi.write({'contract_date_start': datetime.strptime('2015-12-30', '%Y-%m-%d').date()})
        # begins during contract, ends after contract
        leave = self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        # move contract in the middle of the leave
        with self.assertRaises(ValidationError):
            self.contract_cdi.contract_date_start = datetime.strptime('2015-11-17', '%Y-%m-%d').date()

    def test_create_contract_in_leave(self):
        # test create contract such that a leave is across two contracts
        start = datetime.strptime('2015-11-05 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.contract_cdi.contract_date_start = datetime.strptime('2015-12-30', '%Y-%m-%d').date()  # remove this contract to be able to create the leave
        # begins during contract, ends after contract
        leave = self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        # move contract in the middle of the leave
        with self.assertRaises(ValidationError):
            self.jules_emp.create_version({
                'date_version': datetime.strptime('2015-11-30', '%Y-%m-%d').date(),
                'contract_date_start': datetime.strptime('2015-11-30', '%Y-%m-%d').date(),
                'contract_date_end': False,
                'name': 'Contract for Richard',
                'resource_calendar_id': self.calendar_40h.id,
                'wage': 5000.0,
            })

    def test_leave_outside_contract(self):
        # Leave outside contract => should not raise
        start = datetime.strptime('2014-10-18 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2014-10-20 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

        # begins before contract, ends during contract => should not raise
        start = datetime.strptime('2014-10-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-01-15 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

        # begins during contract, ends after contract => should not raise
        self.contract_cdi.date_end = datetime.strptime('2015-11-30', '%Y-%m-%d').date()
        start = datetime.strptime('2015-11-25 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-12-05 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

    def test_no_leave_overlapping_contracts(self):
        with self.assertRaises(ValidationError):
            # Overlap two contracts
            start = datetime.strptime('2015-11-12 07:00:00', '%Y-%m-%d %H:%M:%S')
            end = datetime.strptime('2015-11-17 18:00:00', '%Y-%m-%d %H:%M:%S')
            self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

        # Leave inside fixed term contract => should not raise
        start = datetime.strptime('2015-11-04 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-07 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

        # Leave inside contract (no end) => should not raise
        start = datetime.strptime('2015-11-18 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-20 09:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

    def test_leave_request_next_contracts(self):
        start = datetime.strptime('2015-11-23 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-24 18:00:00', '%Y-%m-%d %H:%M:%S')
        leave = self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)
        self.assertEqual(leave.number_of_hours, 14, "It should count hours according to the future contract.")

    def test_leave_multi_contracts_same_schedule(self):
        # TODO DBE / ARPI : Is this test still valid ?
        # Allow leaves overlapping multiple contracts if same
        # resource calendar
        leave = self.create_leave(datetime(2022, 6, 1, 7, 0, 0), datetime(2022, 6, 30, 18, 0, 0), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        self.contract_cdi.contract_date_end = date(2022, 6, 15)

        self.jules_emp.create_version({
            'date_version': date(2022, 6, 16),
            'contract_date_start': date(2022, 6, 16),
            'contract_date_end': False,
            'name': 'New Contract for Jules',
            'resource_calendar_id': self.calendar_35h.id,
            'wage': 5000.0,
        })

    def test_leave_same_contract_multiple_versions_with_different_schedules(self):
        self.contract_cdi.contract_date_end = date(2022, 7, 30)
        self.jules_emp.create_version({
            'date_version': date(2022, 6, 10),
            'contract_date_start': self.contract_cdi.contract_date_start,
            'contract_date_end': self.contract_cdi.contract_date_end,
            'name': 'New Version with a different schedule for Jules',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
        })
        with self.assertRaises(ValidationError):
            leave = self.create_leave(datetime(2022, 6, 1, 7, 0, 0), datetime(2022, 6, 30, 18, 0, 0), name="Doctor Appointment", employee_id=self.jules_emp.id)
            leave.action_approve()

        leave = self.create_leave(datetime(2022, 5, 1, 7, 0, 0), datetime(2022, 5, 10, 18, 0, 0), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()

        leave = self.create_leave(datetime(2022, 6, 15, 7, 0, 0), datetime(2022, 7, 20, 18, 0, 0), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()

    def test_leave_multi_contracts_split(self):
        # Check that setting a contract as running correctly
        # splits the existing time off for this employee that
        # are ovelapping with another contract with another
        # working schedule
        leave = self.create_leave(date(2022, 6, 1), date(2022, 6, 30), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        self.assertEqual(leave.number_of_days, 22)
        self.assertEqual(leave.state, 'validate')

        self.contract_cdi.contract_date_end = date(2022, 6, 15)
        self.jules_emp.create_version({
            'date_version': date(2022, 6, 16),
            'contract_date_start': date(2022, 6, 16),
            'contract_date_end': False,
            'name': 'New Contract for Jules',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
        })

        leaves = self.env['hr.leave'].search([('employee_id', '=', self.jules_emp.id)])
        self.assertEqual(len(leaves), 3)
        self.assertEqual(leave.state, 'refuse')

        first_leave = leaves.filtered(lambda l: l.date_from.day == 1 and l.date_to.day == 15)
        self.assertEqual(first_leave.state, 'validate')
        self.assertEqual(first_leave.number_of_days, 11)

        second_leave = leaves.filtered(lambda l: l.date_from.day == 16 and l.date_to.day == 30)
        self.assertEqual(second_leave.state, 'confirm')
        self.assertEqual(second_leave.number_of_days, 11)

    def test_multi_contracts_draft(self):
        # Check that setting a contract as running correctly
        # make the existing time off to draft for this employee
        # which is after another contract with another
        # working schedule
        leave = self.create_leave(date(2022, 6, 27), date(2022, 6, 30), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        self.assertEqual(leave.number_of_days, 4)
        self.assertEqual(leave.state, 'validate')

        self.contract_cdi.contract_date_end = date(2022, 6, 15)
        self.jules_emp.create_version({
            'date_version': date(2022, 6, 16),
            'contract_date_start': date(2022, 6, 16),
            'contract_date_end': False,
            'name': 'New Contract for Jules',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
        })

        leaves = self.env['hr.leave'].search([('employee_id', '=', self.jules_emp.id)])
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leave.state, 'confirm')
        self.assertEqual(leave.number_of_days, 4)

    def test_contract_traceability_calculate_nbr_leave(self):
        """
            The goal is to test the traceability of contracts in the past,
            i.e. to check that expired contracts are taken into account
            to ensure the consistency of leaves (number of days/hours) in the past.
        """
        calendar_full, calendar_partial = self.env['resource.calendar'].create([
            {
                'name': 'Full time (5/5)',
            },
            {
                'name': 'Partial time (4/5)',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    # Does not work on Wednesdays
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Evening', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
                ]
            },
        ])
        employee = self.env['hr.employee'].create({
            'name': 'Employee',
            'resource_calendar_id': calendar_partial.id,
        })
        employee.create_version({
            'name': 'Full time (5/5)',
            'date_version': datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            'contract_date_start': datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            'contract_date_end': datetime.strptime('2023-06-30', '%Y-%m-%d').date(),
            'resource_calendar_id': calendar_full.id,
            'wage': 1000.0,
        })
        employee.create_version({
            'name': 'Partial time (4/5)',
            'date_version': datetime.strptime('2023-07-01', '%Y-%m-%d').date(),
            'contract_date_start': datetime.strptime('2023-07-01', '%Y-%m-%d').date(),
            'contract_date_end': datetime.strptime('2023-12-31', '%Y-%m-%d').date(),
            'resource_calendar_id': calendar_partial.id,
            'wage': 1000.0,
        })
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Leave Type',
            'time_type': 'leave',
            'requires_allocation': True,
            'leave_validation_type': 'hr',
            'request_unit': 'day',
        })
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Allocation',
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'number_of_days': 10,
            'state': 'confirm',
            'date_from': datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            'date_to': datetime.strptime('2023-12-31', '%Y-%m-%d').date(),
        })
        allocation.action_approve()
        leave_during_full_time, leave_during_partial_time = self.env['hr.leave'].create([
            {
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2023-01-03',  # Tuesday
                'request_date_to': '2023-01-05',  # Thursday
            },
            {
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': '2023-12-05',  # Tuesday
                'request_date_to': '2023-12-07',  # Thursday
            },
        ])
        self.assertEqual(leave_during_full_time.number_of_days, 3)
        self.assertEqual(leave_during_partial_time.number_of_days, 2)
        self.assertEqual(leave_during_full_time.number_of_hours, 24)
        self.assertEqual(leave_during_partial_time.number_of_hours, 16)
        # Simulate the unit change days/hours of the time off type
        (leave_during_full_time + leave_during_partial_time)._compute_duration()
        self.assertEqual(leave_during_full_time.number_of_days, 3)
        self.assertEqual(leave_during_partial_time.number_of_days, 2)
        self.assertEqual(leave_during_full_time.number_of_hours, 24)
        self.assertEqual(leave_during_partial_time.number_of_hours, 16)
        # Check after leave approval
        (leave_during_full_time + leave_during_partial_time).action_approve()
        self.assertEqual(leave_during_full_time.number_of_hours, 24)
        self.assertEqual(leave_during_partial_time.number_of_hours, 16)

    @freeze_time('2024-01-05')
    def test_multi_contract_out_of_office(self):
        """
            Test that the out of office feature works correctly with multiple contracts
            The Case is when the employee is out of the office for a period that overlaps multiple contracts
        """
        calendar_full, calendar_partial = self.env['resource.calendar'].create([
            {
                'name': 'Full time (5/5)',
            },
            {
                'name': 'Partial time (4/5)',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Evening', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Evening', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Evening', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Evening', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
                ]
            },
        ])

        employee = self.env['hr.employee'].create({
            'name': 'Employee',
            'resource_calendar_id': calendar_full.id,
        })

        employee.create_version({
            'name': 'Full time (5/5)',
            'date_version': datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
            'contract_date_start': datetime.strptime('2024-01-01', '%Y-%m-%d').date(),
            'contract_date_end': datetime.strptime('2024-01-31', '%Y-%m-%d').date(),
            'resource_calendar_id': calendar_full.id,
            'wage': 1000.0,
        })
        employee.create_version({
            'name': 'Partial time (4/5)',
            'date_version': datetime.strptime('2024-02-01', '%Y-%m-%d').date(),
            'contract_date_start': datetime.strptime('2024-02-01', '%Y-%m-%d').date(),
            'contract_date_end': False,
            'resource_calendar_id': calendar_partial.id,
            'wage': 1000.0,
            # 'state': 'draft',
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Leave Type',
            'time_type': 'leave',
            'requires_allocation': False,
            'leave_validation_type': 'hr',
            'request_unit': 'day',
        })

        leave1 = self.env['hr.leave'].create({
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': '2024-01-01',
            'request_date_to': '2024-01-31',
        })

        leave2 = self.env['hr.leave'].create({
            'employee_id': employee.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': '2024-02-01',
            'request_date_to': '2024-02-29',
        })

        leave1.action_approve()
        leave2.action_approve()

        employee._compute_leave_status()
        self.assertEqual(employee.leave_date_to, date(2024, 3, 4))

    def test_multi_contracts_with_different_work_schedules(self):
        """
            Test that the employee can have multiple non-overlapping versions with different work schedules,
            and that the leave requests are correctly calculated based on corresponding the contract's working schedule.
        """
        calendar_full, calendar_partial = self.env['resource.calendar'].create([
            {
                'name': 'Full time (5/5, 8h/day)',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                ]
            },
            {
                'name': 'Partial time (5/5, 6h/day)',
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                    (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16, 'day_period': 'afternoon'}),
                ]
            },
        ])
        employee = self.env['hr.employee'].create({
            'name': "Employee",
            "resource_calendar_id": calendar_partial.id,
        })
        employee.create_version({
            "name": "Full time (5/5)",
            "date_version": datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            "contract_date_start": datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            "contract_date_end": datetime.strptime('2023-06-30', '%Y-%m-%d').date(),
            "resource_calendar_id": calendar_full.id,
            "wage": 1000.0,
        })
        employee.create_version({
            "name": "Partial time (5/5)",
            "date_version": datetime.strptime('2023-07-01', '%Y-%m-%d').date(),
            "contract_date_start": datetime.strptime('2023-07-01', '%Y-%m-%d').date(),
            "contract_date_end": datetime.strptime('2023-12-31', '%Y-%m-%d').date(),
            "resource_calendar_id": calendar_partial.id,
            "wage": 1000.0,
        })

        leave_type = self.env['hr.leave.type'].create({
            'name': 'Leave Type',
            'time_type': 'leave',
            'requires_allocation': False,
            'request_unit': 'day',
        })

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id)) as leave_form:
            leave_form.holiday_status_id = leave_type
            leave_form.request_date_from = date(2023, 2, 14)  # full-time calendar
            leave_form.request_date_to = date(2023, 2, 14)

        leave = leave_form.save()
        # Assert based on full-time calendar (8h)
        self.assertEqual(leave.number_of_days, 1)
        self.assertEqual(leave.number_of_hours, 8)
        # Change to date under partial-time contract
        leave.write({
            'request_date_from': date(2023, 7, 14),
            'request_date_to': date(2023, 7, 14),
        })
        # Assert based on partial-time calendar
        self.assertEqual(leave.number_of_days, 1)
        self.assertEqual(leave.number_of_hours, 6)
