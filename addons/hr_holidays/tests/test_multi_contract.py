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
        cls.calendar_8_17, cls.calendar_10_16 = cls.env['resource.calendar'].create([
            {
                'name': '8:00-17:00',
                'attendance_ids': [
                    (0, 0, {'dayofweek': str(day), 'hour_from': hour_from, 'hour_to': hour_to})
                    for day in range(5)
                    for hour_from, hour_to in [(8, 12), (13, 17)]
                ],
            },
            {
                'name': '10:00-16:00',
                'attendance_ids': [
                    (0, 0, {'dayofweek': str(day), 'hour_from': 10, 'hour_to': 16})
                    for day in range(5)
                ],
            },
        ])
        cls.hour_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Time Off in Hours',
            'code': 'Time Off in Hours',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
        })

    def _create_hour_employee(self, calendar):
        employee = self.env['hr.employee'].create({
            'name': 'Employee requesting hours',
            'tz': 'UTC',
        })
        employee.version_id.write({
            'date_version': date(2026, 9, 1),
            'contract_date_start': date(2026, 9, 1),
            'resource_calendar_id': calendar.id,
        })
        return employee

    def _create_hour_leave(self, employee, date_from, date_to, duration, hour_from, hour_to, work_entry_type=None):
        # The hours are written as the form sets them
        vals = {
            'employee_id': employee.id,
            'work_entry_type_id': (work_entry_type or self.hour_work_entry_type).id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'request_hour_from': hour_from,
            'request_hour_to': hour_to,
        }
        if duration:
            vals['request_duration'] = duration
        return self.env['hr.leave'].create(vals)

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

    def test_leave_multi_versions_split(self):
        # Check that the split of an existing time off is done on the version
        # periods, not on the contract dates shared by all the versions
        self.jules_emp.create_version({
            'date_version': date(2022, 6, 10),
            'wage': 6000.0,
        })
        leave = self.create_leave(date(2022, 6, 1), date(2022, 6, 30), name="Doctor Appointment", employee_id=self.jules_emp.id)
        leave.action_approve()
        self.assertEqual(leave.number_of_days, 22)

        self.contract_cdi.contract_date_end = date(2022, 6, 15)
        self.jules_emp.create_version({
            'date_version': date(2022, 6, 16),
            'contract_date_start': date(2022, 6, 16),
            'contract_date_end': False,
            'name': 'New Contract for Jules',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
        })

        self.assertEqual(leave.state, 'refuse')
        leaves = self.env['hr.leave'].search([('employee_id', '=', self.jules_emp.id), ('state', '!=', 'refuse')])
        self.assertEqual(sum(leaves.mapped('number_of_days')), 22)
        self.assertEqual(
            sorted((l.request_date_from, l.request_date_to) for l in leaves),
            [
                (date(2022, 6, 1), date(2022, 6, 9)),
                (date(2022, 6, 10), date(2022, 6, 15)),
                (date(2022, 6, 16), date(2022, 6, 30)),
            ],
        )

    def test_new_version_without_contract_with_leaves(self):
        # An employee without contract, having time off, can get a new
        # version with another working schedule
        employee = self.env['hr.employee'].create({
            'name': 'No Contract Employee',
            'date_version': date(2022, 1, 1),
            'resource_calendar_id': self.calendar_35h.id,
        })
        leave = self.create_leave(date(2022, 7, 6), date(2022, 7, 8), name="Doctor Appointment", employee_id=employee.id)
        employee.create_version({
            'date_version': date(2022, 7, 1),
            'resource_calendar_id': self.calendar_40h.id,
        })
        self.assertEqual(len(employee.version_ids), 2)
        self.assertNotEqual(leave.state, 'refuse')

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

    def test_update_calendar_preserves_leave_request_dates(self):
        duration_calendar = self.env['resource.calendar'].create({
            'name': 'Tuesday to Friday',
            'attendance_ids': [
                (0, 0, {
                    'dayofweek': dayofweek,
                    'duration_hours': 7.6,
                })
                for dayofweek in ['1', '2', '3', '4']
            ],
        })
        employee = self.env['hr.employee'].create({
            'name': 'Employee with a new working schedule',
            'tz': 'Europe/Brussels',
        })
        employee.version_id.write({
            'date_version': date(2025, 3, 3),
            'contract_date_start': date(2025, 3, 3),
        })
        monday_leave = self.create_leave(
            date(2026, 2, 23), date(2026, 2, 26), employee_id=employee.id,
        )
        control_leave = self.create_leave(
            date(2026, 3, 3), date(2026, 3, 6), employee_id=employee.id,
        )
        self.assertEqual(monday_leave.number_of_days, 4)
        self.assertEqual(control_leave.number_of_days, 4)

        employee.version_id.write({
            'resource_calendar_id': duration_calendar.id,
        })

        self.assertEqual(monday_leave.number_of_days, 3)
        self.assertEqual(monday_leave.request_date_from, date(2026, 2, 23))
        self.assertEqual(monday_leave.request_date_to, date(2026, 2, 26))
        self.assertEqual(control_leave.number_of_days, 4)
        self.assertEqual(control_leave.request_date_from, date(2026, 3, 3))
        self.assertEqual(control_leave.request_date_to, date(2026, 3, 6))

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
                    (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 17}),
                    # Does not work on Wednesdays
                    (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 17})
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
        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Leave Type',
            'code': 'Leave Type',
            'count_as': 'absence',
            'requires_allocation': True,
            'leave_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Allocation',
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'number_of_days': 10,
            'state': 'confirm',
            'date_from': datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            'date_to': datetime.strptime('2023-12-31', '%Y-%m-%d').date(),
        })
        allocation.action_approve()
        leave_during_full_time, leave_during_partial_time = self.env['hr.leave'].create([
            {
                'employee_id': employee.id,
                'work_entry_type_id': work_entry_type.id,
                'request_date_from': '2023-01-03',  # Tuesday
                'request_date_to': '2023-01-05',  # Thursday
            },
            {
                'employee_id': employee.id,
                'work_entry_type_id': work_entry_type.id,
                'request_date_from': '2023-12-05',  # Tuesday
                'request_date_to': '2023-12-07',  # Thursday
            },
        ])
        self.assertEqual(leave_during_full_time.number_of_days, 3)
        self.assertEqual(leave_during_partial_time.number_of_days, 2)
        self.assertEqual(leave_during_full_time.number_of_hours, 24)
        self.assertEqual(leave_during_partial_time.number_of_hours, 16)
        # Simulate the unit change days/hours of the time type
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
                    (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 17})
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

        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Leave Type',
            'code': 'Leave Type',
            'count_as': 'absence',
            'requires_allocation': False,
            'leave_validation_type': 'hr',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        leave1 = self.env['hr.leave'].create({
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'request_date_from': '2024-01-01',
            'request_date_to': '2024-01-31',
        })

        leave2 = self.env['hr.leave'].create({
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
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
                    (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 17}),
                    (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 17}),
                ]
            },
            {
                'name': 'Partial time (5/5, 6h/day)',
                'attendance_ids': [
                    (0, 0, {'dayofweek': '0', 'hour_from': 9, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 16}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 9, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 16}),
                    (0, 0, {'dayofweek': '2', 'hour_from': 9, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 16}),
                    (0, 0, {'dayofweek': '3', 'hour_from': 9, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 16}),
                    (0, 0, {'dayofweek': '4', 'hour_from': 9, 'hour_to': 12}),
                    (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 16}),
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

        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Leave Type',
            'code': 'Leave Type',
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        with Form(self.env['hr.leave'].with_context(default_employee_id=employee.id, leave_fast_create=True)) as leave_form:
            leave_form.work_entry_type_id = work_entry_type
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

    def test_cancelled_leave_next_version_calendar_change(self):
        # A cancelled time off shouldn't be impacted when the working schedule of the next version changes
        employee = self.env['hr.employee'].create({
            'name': 'Employee with two versions',
            'tz': 'Europe/Brussels',
        })
        employee.version_id.write({
            'date_version': date(2026, 9, 1),
            'contract_date_start': date(2026, 9, 1),
            'resource_calendar_id': self.calendar_40h.id,
        })
        october_version = employee.create_version({
            'date_version': date(2026, 10, 1),
            'resource_calendar_id': self.calendar_40h.id,
        })
        leave = self.create_leave(date(2026, 9, 30), date(2026, 10, 2), employee_id=employee.id)
        leave.action_approve()
        leave._force_cancel("Not needed anymore")
        self.assertEqual(leave.state, 'cancel')

        october_version.resource_calendar_id = self.calendar_35h

        self.assertEqual(leave.state, 'cancel')
        self.assertEqual(leave.resource_calendar_id, self.calendar_40h)
        self.assertEqual(self.env['hr.leave'].search([('employee_id', '=', employee.id)]), leave)

    def test_schedule_change_recomputes_prefilled_hours(self):
        """Requests in hours follow a new schedule of their version, unless their hours were chosen."""
        employee = self._create_hour_employee(self.calendar_8_17)
        full_day_leave = self._create_hour_leave(employee, date(2026, 11, 23), date(2026, 11, 25), 'full', 8, 17)
        morning_leave = self._create_hour_leave(employee, date(2026, 11, 26), date(2026, 11, 26), 'am', 8, 12)
        specific_leave = self._create_hour_leave(employee, date(2026, 11, 27), date(2026, 11, 27), 'specific', 9, 11)
        working_time_type = self.env['hr.work.entry.type'].create({
            'name': 'Training in Hours',
            'code': 'Training in Hours',
            'count_as': 'working_time',
            'requires_allocation': False,
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
        })
        # A day of working time lasts the planned hours from the start of the day
        working_time_leave = self._create_hour_leave(
            employee, date(2026, 11, 30), date(2026, 11, 30), 'full', 8, 16, working_time_type)
        # The batch time off wizard sets the hours without a duration, so the request gets Full Day
        batch_leave = self._create_hour_leave(employee, date(2026, 12, 1), date(2026, 12, 1), None, 14, 17)
        full_day_leave.action_approve()
        self.assertEqual(full_day_leave.number_of_hours, 24)
        self.assertEqual(morning_leave.number_of_hours, 4)

        employee.version_id.resource_calendar_id = self.calendar_10_16

        # The full day takes the bounds of the new schedule and stays approved
        self.assertEqual((full_day_leave.request_hour_from, full_day_leave.request_hour_to), (10, 16))
        self.assertEqual(full_day_leave.date_from, datetime(2026, 11, 23, 10))
        self.assertEqual(full_day_leave.date_to, datetime(2026, 11, 25, 16))
        self.assertEqual(full_day_leave.number_of_hours, 18)
        self.assertEqual(full_day_leave.number_of_days, 3)
        self.assertEqual(full_day_leave.state, 'validate')
        resource_leave = self.env['resource.calendar.leaves'].search([('holiday_id', '=', full_day_leave.id)])
        self.assertEqual((resource_leave.date_from, resource_leave.date_to), (full_day_leave.date_from, full_day_leave.date_to))
        # The morning takes the morning of the new schedule
        self.assertEqual((morning_leave.request_hour_from, morning_leave.request_hour_to), (10, 12))
        self.assertEqual(morning_leave.number_of_hours, 2)
        # The prefilled hours of working time are not taken as chosen ones
        self.assertEqual((working_time_leave.request_hour_from, working_time_leave.request_hour_to), (10, 16))
        # The hours chosen by the employee are kept
        self.assertEqual((specific_leave.request_hour_from, specific_leave.request_hour_to), (9, 11))
        # Only the hour inside the new schedule is counted
        self.assertEqual(specific_leave.number_of_hours, 1)
        # Hours other than the ones of the schedule were chosen, whatever the duration
        self.assertEqual((batch_leave.request_hour_from, batch_leave.request_hour_to), (14, 17))

    def test_new_version_recomputes_prefilled_hours(self):
        """A request in hours prefilled from a temporary schedule takes the hours of the next version."""
        calendar_temporary = self.env['resource.calendar'].create({
            'name': '7:00-11:30',
            'attendance_ids': [
                (0, 0, {'dayofweek': str(day), 'hour_from': 7, 'hour_to': 11.5})
                for day in range(5)
            ],
        })
        employee = self._create_hour_employee(calendar_temporary)
        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Overtime',
            'code': 'Overtime',
            'count_as': 'absence',
            'requires_allocation': True,
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
        })
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Overtime',
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'number_of_hours': 20,
            'date_from': date(2026, 9, 1),
        })
        allocation.action_approve()
        leave = self._create_hour_leave(employee, date(2026, 10, 27), date(2026, 10, 28), 'full', 7, 11.5, work_entry_type)
        self.assertEqual(leave.number_of_hours, 9)

        # The final schedule starts before the request
        employee.create_version({
            'date_version': date(2026, 10, 26),
            'resource_calendar_id': self.calendar_10_16.id,
        })

        self.assertEqual((leave.request_hour_from, leave.request_hour_to), (10, 16))
        self.assertEqual(leave.number_of_hours, 12)
        self.assertEqual(leave.number_of_days, 2)
        allocation.invalidate_recordset(['virtual_remaining_leaves'])
        self.assertEqual(allocation.virtual_remaining_leaves, 8)

    def test_split_leave_takes_hours_of_each_version(self):
        """Each part of a request in hours split between versions takes the hours of its own version."""
        employee = self._create_hour_employee(self.calendar_8_17)
        next_version = employee.create_version({
            'date_version': date(2026, 11, 24),
            'resource_calendar_id': self.calendar_8_17.id,
        })
        leave = self._create_hour_leave(employee, date(2026, 11, 23), date(2026, 11, 25), 'full', 8, 17)

        next_version.resource_calendar_id = self.calendar_10_16

        self.assertEqual(leave.state, 'refuse')
        parts = self.env['hr.leave'].search(
            [('employee_id', '=', employee.id), ('state', '!=', 'refuse')], order='request_date_from')
        self.assertEqual(
            [(part.request_date_from, part.request_hour_from, part.request_hour_to, part.number_of_hours) for part in parts],
            [
                (date(2026, 11, 23), 8, 17, 8),
                (date(2026, 11, 24), 10, 16, 12),
            ],
        )
