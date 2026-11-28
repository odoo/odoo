# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, freeze_time, new_test_user, tagged
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

    def test_leave_overlapping_contracts_is_split(self):
        # Overlap two contracts with different schedules: one time off per contract
        start = datetime.strptime('2015-11-12 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2015-11-17 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)
        leaves = self.env['hr.leave'].search([('employee_id', '=', self.jules_emp.id)], order='request_date_from')
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id) for l in leaves],
            [
                (date(2015, 11, 12), date(2015, 11, 15), self.calendar_40h),
                (date(2015, 11, 16), date(2015, 11, 17), self.calendar_35h),
            ],
        )

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
        # across the versions with different schedules: one time off per version
        self.create_leave(datetime(2022, 6, 8, 7, 0, 0), datetime(2022, 6, 14, 18, 0, 0), name="Doctor Appointment", employee_id=self.jules_emp.id)
        parts = self.env['hr.leave'].search([('employee_id', '=', self.jules_emp.id)], order='request_date_from')
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id) for l in parts],
            [
                (date(2022, 6, 8), date(2022, 6, 9), self.calendar_35h),
                (date(2022, 6, 10), date(2022, 6, 14), self.calendar_40h),
            ],
        )

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

    def _create_leave_type(self, code, request_unit='day', **vals):
        return self.env['hr.work.entry.type'].create({
            'name': code,
            'code': code,
            'count_as': 'absence',
            'requires_allocation': False,
            'request_unit': request_unit,
            'unit_of_measure': 'hour' if request_unit == 'hour' else 'day',
            **vals,
        })

    def _create_allocation(self, leave_type, days):
        allocation = self.env['hr.leave.allocation'].create({
            'name': 'Allocation',
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': leave_type.id,
            'number_of_days': days,
            'state': 'confirm',
            'date_from': date(2022, 1, 1),
            'date_to': date(2022, 12, 31),
        })
        allocation.action_approve()
        return allocation

    def _create_approval_setup(self):
        """Return an employee user, the approver of its time off and a type needing the approval."""
        approver = new_test_user(self.env, login='leave_approver', groups='base.group_user,hr_holidays.group_hr_holidays_responsible')
        employee_user = new_test_user(self.env, login='leave_employee', groups='base.group_user,hr_holidays.group_hr_holidays_employee')
        self.jules_emp.write({'user_id': employee_user.id, 'leave_manager_id': approver.id})
        return employee_user, approver, self._create_leave_type('MANAGER', leave_validation_type='manager')

    def _create_employee_without_contract(self, last_calendar=None):
        """Return an employee without contract with three versions and three schedules.

        The versions start on 2022-01-01 (35h, Monday to Friday), 2022-06-10 (40h, Monday to
        Friday) and 2022-06-20 (``last_calendar``, the 35h schedule by default).
        """
        employee = self.env['hr.employee'].create({
            'name': 'Employee without contract',
            'date_version': date(2022, 1, 1),
            'resource_calendar_id': self.calendar_35h.id,
        })
        employee.create_version({'date_version': date(2022, 6, 10), 'resource_calendar_id': self.calendar_40h.id})
        employee.create_version({
            'date_version': date(2022, 6, 20),
            'resource_calendar_id': (last_calendar or self.calendar_35h).id,
        })
        return employee

    def _create_four_days_calendar(self):
        return self.env['resource.calendar'].create({
            'name': '4 days calendar',
            'attendance_ids': [
                (0, 0, {'dayofweek': str(weekday), 'hour_from': hour, 'hour_to': hour + 4})
                for weekday in range(4)
                for hour in (8, 13)
            ],
        })

    def _create_three_versions(self, last_calendar):
        """Give Jules three versions of the same contract, with three working schedules.

        The versions start on 2022-06-01 (35h, Monday to Friday), 2022-06-10 (40h, Monday to
        Friday) and 2022-06-20 (``last_calendar``).
        """
        self.jules_emp.create_version({'date_version': date(2022, 6, 10), 'resource_calendar_id': self.calendar_40h.id})
        return self.jules_emp.create_version({'date_version': date(2022, 6, 20), 'resource_calendar_id': last_calendar.id})

    def _create_leave_across_versions(self, vals):
        # The versions are changed after the creation of the time off, to reach the split of
        # the existing time off: the check of the versions is skipped for the creation.
        leave = self.env['hr.leave'].with_context(skip_leave_version_check=True).create({
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            **vals,
        })
        leave.with_context(skip_leave_version_check=True).action_approve()
        return leave

    def test_leave_three_versions_split(self):
        # A time off over three versions with three different schedules is cut in three parts,
        # each one with the schedule of its version
        four_days_calendar = self._create_four_days_calendar()
        last_version = self._create_three_versions(self.calendar_35h)
        leave = self._create_leave_across_versions({
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        })
        self.assertEqual(leave.resource_calendar_id, self.calendar_35h)
        self.assertEqual(leave.state, 'validate')

        last_version.resource_calendar_id = four_days_calendar

        self.assertEqual(leave.state, 'refuse')
        leaves = self.env['hr.leave'].search(
            [('employee_id', '=', self.jules_emp.id), ('state', '!=', 'refuse')], order='request_date_from')
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id, l.state, l.number_of_days) for l in leaves],
            [
                (date(2022, 6, 1), date(2022, 6, 9), self.calendar_35h, 'validate', 7),
                (date(2022, 6, 10), date(2022, 6, 19), self.calendar_40h, 'validate', 6),
                # 4 days a week: the Fridays are not counted
                (date(2022, 6, 20), date(2022, 6, 30), four_days_calendar, 'confirm', 8),
            ],
        )

    def test_leave_three_versions_split_half_days(self):
        # The first and last days of the whole request keep their half day, the days where the
        # request is cut between two versions are whole days
        four_days_calendar = self._create_four_days_calendar()
        half_day_type = self._create_leave_type('HALFDAY', 'half_day')
        last_version = self._create_three_versions(self.calendar_35h)
        self._create_leave_across_versions({
            'work_entry_type_id': half_day_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_from_period': 'pm',
            'request_date_to': date(2022, 6, 30),
            'request_date_to_period': 'am',
        })

        last_version.resource_calendar_id = four_days_calendar

        leaves = self.env['hr.leave'].search(
            [('employee_id', '=', self.jules_emp.id), ('state', '!=', 'refuse')], order='request_date_from')
        self.assertEqual(
            [(l.request_date_from, l.request_date_from_period, l.request_date_to, l.request_date_to_period, l.number_of_days) for l in leaves],
            [
                (date(2022, 6, 1), 'pm', date(2022, 6, 9), 'pm', 6.5),
                (date(2022, 6, 10), 'am', date(2022, 6, 19), 'pm', 6),
                (date(2022, 6, 20), 'am', date(2022, 6, 30), 'am', 7.5),
            ],
        )

    def test_leave_three_versions_split_hours(self):
        # A time off in hours keeps its first and last hours, the hours where the request is
        # cut between two versions are the first and last hours of the schedule of that day
        four_days_calendar = self._create_four_days_calendar()
        hour_type = self._create_leave_type('HOURLY', 'hour')
        last_version = self._create_three_versions(self.calendar_35h)
        leave = self._create_leave_across_versions({
            'work_entry_type_id': hour_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_hour_from': 10.0,
            'request_date_to': date(2022, 6, 30),
            'request_hour_to': 15.0,
        })

        last_version.resource_calendar_id = four_days_calendar

        self.assertEqual(leave.state, 'refuse')
        leaves = self.env['hr.leave'].search(
            [('employee_id', '=', self.jules_emp.id), ('state', '!=', 'refuse')], order='request_date_from')
        self.assertEqual(
            [(l.request_date_from, l.request_hour_from, l.request_date_to, l.request_hour_to) for l in leaves],
            [
                # the 35h schedule ends at 16h, the others at 17h
                (date(2022, 6, 1), 10.0, date(2022, 6, 9), 16.0),
                (date(2022, 6, 10), 8.0, date(2022, 6, 19), 17.0),
                (date(2022, 6, 20), 8.0, date(2022, 6, 30), 15.0),
            ],
        )

    def test_leave_three_versions_same_schedule_neighbours(self):
        # Two neighbour versions with the same schedule do not change the days counted: each
        # part counts the days of the schedule of its own versions
        last_version = self._create_three_versions(self.calendar_35h)
        leave = self._create_leave_across_versions({
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        })

        # the schedules of the versions are 35h, 40h and 40h, the time off has the first one
        last_version.resource_calendar_id = self.calendar_40h

        leaves = self.env['hr.leave'].search(
            [('employee_id', '=', self.jules_emp.id), ('state', '!=', 'refuse')], order='request_date_from')
        self.assertEqual(leave.state, 'refuse')
        self.assertEqual(leaves[0].request_date_from, date(2022, 6, 1))
        self.assertEqual(leaves[-1].request_date_to, date(2022, 6, 30))
        self.assertEqual(sum(leaves.mapped('number_of_days')), 22)
        for part in leaves:
            self.assertEqual(
                part.resource_calendar_id,
                self.jules_emp._get_version(part.request_date_from).resource_calendar_id)

    def _get_employee_leaves(self, employee=None):
        return self.env['hr.leave'].search(
            [('employee_id', '=', (employee or self.jules_emp).id), ('state', '!=', 'refuse')], order='request_date_from')

    def test_create_leave_three_versions(self):
        # A request over three versions with three schedules creates one time off per version,
        # each one with the schedule and the duration of its version
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)

        self.create_leave(date(2022, 6, 1), date(2022, 6, 30), employee_id=self.jules_emp.id)

        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id, l.number_of_days) for l in self._get_employee_leaves()],
            [
                (date(2022, 6, 1), date(2022, 6, 9), self.calendar_35h, 7),
                (date(2022, 6, 10), date(2022, 6, 19), self.calendar_40h, 6),
                # 4 days a week: the Fridays are not counted
                (date(2022, 6, 20), date(2022, 6, 30), four_days_calendar, 8),
            ],
        )

    def test_create_leave_three_versions_half_days(self):
        four_days_calendar = self._create_four_days_calendar()
        half_day_type = self._create_leave_type('HALFDAY', 'half_day')
        self._create_three_versions(four_days_calendar)

        self.env['hr.leave'].create({
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': half_day_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_from_period': 'pm',
            'request_date_to': date(2022, 6, 30),
            'request_date_to_period': 'am',
        })

        self.assertEqual(
            [(l.request_date_from, l.request_date_from_period, l.request_date_to, l.request_date_to_period, l.number_of_days) for l in self._get_employee_leaves()],
            [
                (date(2022, 6, 1), 'pm', date(2022, 6, 9), 'pm', 6.5),
                (date(2022, 6, 10), 'am', date(2022, 6, 19), 'pm', 6),
                (date(2022, 6, 20), 'am', date(2022, 6, 30), 'am', 7.5),
            ],
        )

    def test_create_leave_three_versions_hours(self):
        four_days_calendar = self._create_four_days_calendar()
        hour_type = self._create_leave_type('HOURLY', 'hour')
        self._create_three_versions(four_days_calendar)

        self.env['hr.leave'].create({
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': hour_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_hour_from': 10.0,
            'request_date_to': date(2022, 6, 30),
            'request_hour_to': 15.0,
        })

        self.assertEqual(
            [(l.request_date_from, l.request_hour_from, l.request_date_to, l.request_hour_to) for l in self._get_employee_leaves()],
            [
                (date(2022, 6, 1), 10.0, date(2022, 6, 9), 16.0),
                (date(2022, 6, 10), 8.0, date(2022, 6, 19), 17.0),
                (date(2022, 6, 20), 8.0, date(2022, 6, 30), 15.0),
            ],
        )

    def test_create_leave_part_without_working_time(self):
        # A version lasting a weekend has nothing to take off: no time off for it, the request
        # is not refused for that
        self.jules_emp.create_version({'date_version': date(2022, 6, 11), 'resource_calendar_id': self.calendar_40h.id})
        self.jules_emp.create_version({'date_version': date(2022, 6, 13), 'resource_calendar_id': self.calendar_35h.id})

        self.create_leave(date(2022, 6, 6), date(2022, 6, 17), employee_id=self.jules_emp.id)

        self.assertEqual(
            [(l.request_date_from, l.request_date_to) for l in self._get_employee_leaves()],
            [(date(2022, 6, 6), date(2022, 6, 10)), (date(2022, 6, 13), date(2022, 6, 17))],
        )

    def test_create_leave_three_versions_allocation(self):
        # The parts of a request are checked together against the allocation: the request is
        # accepted or refused as a whole
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)
        allocation_type = self._create_leave_type(
            'ALLOC', requires_allocation=True, leave_validation_type='no_validation')
        allocation = self._create_allocation(allocation_type, 10)
        request_vals = {
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': allocation_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        }

        # each part (7, 6 and 8 days) fits in the 10 days, the 21 days together do not
        with self.assertRaises(ValidationError):
            self.env['hr.leave'].create(request_vals)
        self.assertFalse(self._get_employee_leaves())

        allocation.number_of_days = 21
        self.env['hr.leave'].create(request_vals)
        self.assertEqual(len(self._get_employee_leaves()), 3)

    def test_create_leave_split_chatter_note(self):
        self._create_three_versions(self.calendar_35h)

        self.create_leave(date(2022, 6, 1), date(2022, 6, 30), employee_id=self.jules_emp.id)

        parts = self._get_employee_leaves()
        self.assertEqual(len(parts), 3)
        for part in parts:
            note = part.message_ids.filtered(lambda m: 'working schedules' in (m.body or ''))
            self.assertEqual(len(note), 1)
            for other in parts - part:
                # a real link, not its escaped text
                self.assertIn(f"<a href=\"/mail/view?model=hr.leave&amp;res_id={other.id}\"", note.body)

    def test_write_leave_three_versions(self):
        # Extending a time off over versions with other schedules keeps it as the first part
        # and creates the other parts as new requests
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)
        leave = self.create_leave(date(2022, 6, 1), date(2022, 6, 8), employee_id=self.jules_emp.id)
        # the dates of an approved time off cannot be changed
        leave.action_back_to_approval()

        leave.request_date_to = date(2022, 6, 30)

        leaves = self._get_employee_leaves()
        self.assertIn(leave, leaves)
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id, l.number_of_days) for l in leaves],
            [
                (date(2022, 6, 1), date(2022, 6, 9), self.calendar_35h, 7),
                (date(2022, 6, 10), date(2022, 6, 19), self.calendar_40h, 6),
                (date(2022, 6, 20), date(2022, 6, 30), four_days_calendar, 8),
            ],
        )
        for part in leaves:
            self.assertEqual(len(part.message_ids.filtered(lambda m: 'working schedules' in (m.body or ''))), 1)

    def test_create_leave_over_versions_parts_need_their_own_approval(self):
        # The parts are independent time off: each one is to approve
        self._create_three_versions(self.calendar_35h)
        employee_user, approver, leave_type = self._create_approval_setup()

        self.env['hr.leave'].with_user(employee_user).create({
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': leave_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        })

        parts = self._get_employee_leaves()
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertEqual(part.state, 'confirm')
            self.assertEqual(part.sudo().activity_ids.user_id, approver)

    def test_write_leave_over_versions_parts_need_their_own_approval(self):
        # The parts created by the change are new requests: the approver is asked for each one
        self._create_three_versions(self.calendar_35h)
        employee_user, approver, leave_type = self._create_approval_setup()
        leave = self.env['hr.leave'].with_user(employee_user).create({
            'name': 'Family trip',
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': leave_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 3),
        })
        self.assertEqual(leave.state, 'confirm')

        leave.with_user(employee_user).request_date_to = date(2022, 6, 30)

        parts = self._get_employee_leaves()
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertEqual(part.state, 'confirm')
            self.assertEqual(part.sudo().activity_ids.user_id, approver)
            self.assertEqual(part.sudo().private_name, 'Family trip')

    def test_write_leave_same_version(self):
        # A time off staying in one version is not cut
        self._create_three_versions(self.calendar_35h)
        leave = self.create_leave(date(2022, 6, 1), date(2022, 6, 3), employee_id=self.jules_emp.id)
        leave.action_back_to_approval()

        leave.request_date_to = date(2022, 6, 8)

        self.assertEqual(self._get_employee_leaves(), leave)
        self.assertEqual(leave.request_date_to, date(2022, 6, 8))

    def test_write_leave_three_versions_allocation(self):
        # The change is accepted or refused as a whole: nothing is cut when the parts do not
        # fit in the allocation together
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)
        allocation_type = self._create_leave_type(
            'ALLOC', requires_allocation=True, leave_validation_type='no_validation')
        self._create_allocation(allocation_type, 10)
        leave = self.env['hr.leave'].create({
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': allocation_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 3),
        })
        self.assertEqual(leave.state, 'validate')
        leave.action_back_to_approval()

        with self.assertRaises(ValidationError):
            leave.request_date_to = date(2022, 6, 30)

        self.assertEqual(self._get_employee_leaves(), leave)
        self.assertEqual(leave.request_date_to, date(2022, 6, 3))

    def test_create_leave_half_days_on_the_boundary(self):
        # Afternoon of the last day of a version and morning of the first day of the next one
        half_day_type = self._create_leave_type('HALFDAY', 'half_day')
        self._create_three_versions(self.calendar_35h)

        self.env['hr.leave'].create({
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': half_day_type.id,
            'request_date_from': date(2022, 6, 9),
            'request_date_from_period': 'pm',
            'request_date_to': date(2022, 6, 10),
            'request_date_to_period': 'am',
        })

        self.assertEqual(
            [(l.request_date_from, l.request_date_from_period, l.request_date_to, l.request_date_to_period, l.number_of_days) for l in self._get_employee_leaves()],
            [
                (date(2022, 6, 9), 'pm', date(2022, 6, 9), 'pm', 0.5),
                (date(2022, 6, 10), 'am', date(2022, 6, 10), 'am', 0.5),
            ],
        )

    def test_write_several_leaves(self):
        # Only the time off moved over versions with different schedules are cut
        self._create_three_versions(self.calendar_35h)
        other_employee = self.env['hr.employee'].create({'name': 'Other employee'})
        leave = self.create_leave(date(2022, 6, 6), date(2022, 6, 7), employee_id=self.jules_emp.id)
        other_leave = self.create_leave(date(2022, 6, 6), date(2022, 6, 7), employee_id=other_employee.id)
        (leave | other_leave).action_back_to_approval()

        (leave | other_leave).write({'request_date_to': date(2022, 6, 14)})

        self.assertEqual(
            [(l.request_date_from, l.request_date_to) for l in self._get_employee_leaves()],
            [(date(2022, 6, 6), date(2022, 6, 9)), (date(2022, 6, 10), date(2022, 6, 14))],
        )
        self.assertEqual((other_leave.request_date_from, other_leave.request_date_to), (date(2022, 6, 6), date(2022, 6, 14)))

    def test_write_employee_over_versions(self):
        # Giving the time off to an employee with other schedules cuts it too
        self._create_three_versions(self.calendar_35h)
        other_employee = self.env['hr.employee'].create({'name': 'Other employee'})
        leave = self.create_leave(date(2022, 6, 6), date(2022, 6, 14), employee_id=other_employee.id)
        leave.action_back_to_approval()

        leave.employee_id = self.jules_emp

        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.employee_id) for l in self._get_employee_leaves()],
            [(date(2022, 6, 6), date(2022, 6, 9), self.jules_emp), (date(2022, 6, 10), date(2022, 6, 14), self.jules_emp)],
        )

    def test_generate_time_off_over_versions(self):
        # The wizard creates validated time off, each part is validated with its resource leave
        self._create_three_versions(self.calendar_35h)

        self.env['hr.leave.generate.multi.wizard'].create({
            'work_entry_type_id': self.work_entry_type.id,
            'date_from': date(2022, 6, 6),
            'date_to': date(2022, 6, 14),
            'employee_ids': self.jules_emp.ids,
        }).action_generate_time_off()

        leaves = self._get_employee_leaves()
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.state) for l in leaves],
            [(date(2022, 6, 6), date(2022, 6, 9), 'validate'), (date(2022, 6, 10), date(2022, 6, 14), 'validate')],
        )
        for leave in leaves:
            self.assertTrue(self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave.id)]))

    def test_unsaved_leave_duration_over_versions(self):
        # What the form shows before saving is what the parts will hold together
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)

        leave = self.env['hr.leave'].new({
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        })

        # 7 days of 7h (35h calendar), 6 days of 8h (40h calendar), 8 days of 8h (4 days calendar)
        shown_days, shown_hours = leave.number_of_days, leave.number_of_hours
        self.assertEqual(shown_days, 21)
        self.assertEqual(shown_hours, 7 * 7 + 6 * 8 + 8 * 8)

        self.create_leave(date(2022, 6, 1), date(2022, 6, 30), employee_id=self.jules_emp.id)
        parts = self._get_employee_leaves()
        self.assertEqual(sum(parts.mapped('number_of_days')), shown_days)
        self.assertEqual(sum(parts.mapped('number_of_hours')), shown_hours)

    def test_unsaved_leave_allocation_warning_over_versions(self):
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)
        allocation_type = self._create_leave_type(
            'ALLOC', requires_allocation=True, leave_validation_type='no_validation')
        allocation = self._create_allocation(allocation_type, 20)
        vals = {
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': allocation_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        }

        # 21 days over the versions: with the calendar of the first version it would be 22 days
        # of the period, and 20 days of the allocation would not be enough in both cases
        self.assertTrue(self.env['hr.leave'].new(vals).allocation_display_warning)

        allocation.number_of_days = 21
        self.assertFalse(self.env['hr.leave'].new(vals).allocation_display_warning)

    def test_create_returns_one_record_per_values(self):
        # The other parts of a request are created too, create keeps returning one record per values
        self._create_three_versions(self.calendar_35h)
        other_employee = self.env['hr.employee'].create({'name': 'Other employee'})
        common_vals = {'work_entry_type_id': self.work_entry_type.id}

        leaves = self.env['hr.leave'].create([
            {**common_vals, 'employee_id': self.jules_emp.id, 'request_date_from': date(2022, 6, 1), 'request_date_to': date(2022, 6, 30)},
            {**common_vals, 'employee_id': other_employee.id, 'request_date_from': date(2022, 6, 1), 'request_date_to': date(2022, 6, 3)},
        ])

        self.assertEqual(leaves.employee_id, self.jules_emp | other_employee)
        # the first part of the request over the versions
        self.assertEqual((leaves[0].request_date_from, leaves[0].request_date_to), (date(2022, 6, 1), date(2022, 6, 9)))
        self.assertEqual(len(self._get_employee_leaves()), 3)

    def test_create_leave_employee_from_context(self):
        # The employee given by the context is the one the parts are timed for
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)

        self.env['hr.leave'].with_context(default_employee_id=self.jules_emp.id).create({
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        })

        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id, l.number_of_days) for l in self._get_employee_leaves()],
            [
                (date(2022, 6, 1), date(2022, 6, 9), self.calendar_35h, 7),
                (date(2022, 6, 10), date(2022, 6, 19), self.calendar_40h, 6),
                (date(2022, 6, 20), date(2022, 6, 30), four_days_calendar, 8),
            ],
        )

    def test_create_leave_over_versions_attachments(self):
        # The files of a request go to each of its parts, one file per time off
        self._create_three_versions(self.calendar_35h)
        # uploaded by the web client before the time off exists
        attachment_vals = {'name': 'certificate.txt', 'raw': b'certificate', 'res_model': 'hr.leave', 'res_id': 0}
        vals = {
            'employee_id': self.jules_emp.id,
            'work_entry_type_id': self.work_entry_type.id,
        }
        # control: the same request in one version
        single_leave = self.env['hr.leave'].create({
            **vals,
            'request_date_from': date(2022, 5, 2),
            'request_date_to': date(2022, 5, 3),
            'supported_attachment_ids': [Command.set(self.env['ir.attachment'].create(attachment_vals).ids)],
        })
        self.assertEqual(single_leave.attachment_ids.mapped('name'), ['certificate.txt'])

        self.env['hr.leave'].create({
            **vals,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
            'supported_attachment_ids': [Command.set(self.env['ir.attachment'].create(attachment_vals).ids)],
        })

        parts = self._get_employee_leaves() - single_leave
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertEqual(part.attachment_ids.mapped('name'), ['certificate.txt'])
        self.assertEqual(len(parts.attachment_ids), 3)

    def test_form_create_over_versions(self):
        # What the form shows is what is created
        four_days_calendar = self._create_four_days_calendar()
        self._create_three_versions(four_days_calendar)
        leave_type = self._create_leave_type(
            'ALLOC', requires_allocation=True, leave_validation_type='no_validation')
        self._create_allocation(leave_type, 21)

        with Form(self.env['hr.leave'].with_context(default_employee_id=self.jules_emp.id)) as leave_form:
            leave_form.work_entry_type_id = leave_type
            leave_form.request_date_from = date(2022, 6, 1)
            leave_form.request_date_to = date(2022, 6, 30)
            # 22 days with the schedule of the first day for the whole period
            self.assertEqual(leave_form.number_of_days, 21)
            self.assertFalse(leave_form.allocation_display_warning)
        leave = leave_form.save()

        # the first part is the record of the form, the others are created too
        self.assertEqual((leave.request_date_from, leave.request_date_to), (date(2022, 6, 1), date(2022, 6, 9)))
        self.assertEqual(len(self._get_employee_leaves()), 3)

    def test_form_edit_over_versions(self):
        self._create_three_versions(self._create_four_days_calendar())
        leave = self.create_leave(date(2022, 6, 1), date(2022, 6, 3), employee_id=self.jules_emp.id)
        leave.action_back_to_approval()

        with Form(leave) as leave_form:
            leave_form.request_date_to = date(2022, 6, 30)
            self.assertEqual(leave_form.number_of_days, 21)

        self.assertEqual(leave.request_date_to, date(2022, 6, 9))
        self.assertEqual(len(self._get_employee_leaves()), 3)

    def test_create_leave_over_versions_without_contract(self):
        # Without contract the versions are the ones of their effective dates
        four_days_calendar = self._create_four_days_calendar()
        employee = self._create_employee_without_contract(four_days_calendar)

        self.create_leave(date(2022, 6, 1), date(2022, 6, 30), employee_id=employee.id)

        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id, l.number_of_days) for l in self._get_employee_leaves(employee)],
            [
                (date(2022, 6, 1), date(2022, 6, 9), self.calendar_35h, 7),
                (date(2022, 6, 10), date(2022, 6, 19), self.calendar_40h, 6),
                (date(2022, 6, 20), date(2022, 6, 30), four_days_calendar, 8),
            ],
        )

    def test_create_leave_half_days_on_the_boundary_without_contract(self):
        half_day_type = self._create_leave_type('HALFDAY', 'half_day')
        employee = self._create_employee_without_contract()

        self.env['hr.leave'].create({
            'employee_id': employee.id,
            'work_entry_type_id': half_day_type.id,
            'request_date_from': date(2022, 6, 9),
            'request_date_from_period': 'pm',
            'request_date_to': date(2022, 6, 10),
            'request_date_to_period': 'am',
        })

        self.assertEqual(
            [(l.request_date_from, l.request_date_from_period, l.request_date_to, l.request_date_to_period, l.number_of_days) for l in self._get_employee_leaves(employee)],
            [
                (date(2022, 6, 9), 'pm', date(2022, 6, 9), 'pm', 0.5),
                (date(2022, 6, 10), 'am', date(2022, 6, 10), 'am', 0.5),
            ],
        )

    def test_write_leave_over_versions_without_contract(self):
        employee = self._create_employee_without_contract()
        leave = self.create_leave(date(2022, 6, 1), date(2022, 6, 3), employee_id=employee.id)
        leave.action_back_to_approval()

        leave.request_date_to = date(2022, 6, 14)

        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id) for l in self._get_employee_leaves(employee)],
            [
                (date(2022, 6, 1), date(2022, 6, 9), self.calendar_35h),
                (date(2022, 6, 10), date(2022, 6, 14), self.calendar_40h),
            ],
        )
        self.assertIn(leave, self._get_employee_leaves(employee))

    def test_unsaved_leave_duration_over_versions_without_contract(self):
        four_days_calendar = self._create_four_days_calendar()
        employee = self._create_employee_without_contract(four_days_calendar)

        leave = self.env['hr.leave'].new({
            'employee_id': employee.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        })

        # 7 days of 7h (35h calendar), 6 days of 8h (40h calendar), 8 days of 8h (4 days calendar)
        self.assertEqual(leave.number_of_days, 21)
        self.assertEqual(leave.number_of_hours, 7 * 7 + 6 * 8 + 8 * 8)

    def test_create_leave_over_versions_without_contract_same_schedule(self):
        # Versions sharing their schedule are one working time: nothing to cut
        employee = self._create_employee_without_contract()
        employee.create_version({'date_version': date(2022, 7, 4), 'resource_calendar_id': self.calendar_35h.id})

        self.create_leave(date(2022, 6, 20), date(2022, 7, 8), employee_id=employee.id)

        self.assertEqual(
            [(l.request_date_from, l.request_date_to) for l in self._get_employee_leaves(employee)],
            [(date(2022, 6, 20), date(2022, 7, 8))],
        )

    def test_create_leave_in_one_version_without_contract(self):
        employee = self._create_employee_without_contract()

        self.create_leave(date(2022, 6, 13), date(2022, 6, 17), employee_id=employee.id)

        leaves = self._get_employee_leaves(employee)
        self.assertEqual(len(leaves), 1)
        self.assertEqual(leaves.resource_calendar_id, self.calendar_40h)

    def test_create_leave_in_hours_over_versions_without_contract(self):
        # A 35h schedule then a 40h one: 7 hours on the Friday and 8 hours on the Monday
        hour_type = self._create_leave_type('HOURLY', 'hour')
        employee = self.env['hr.employee'].create({
            'name': 'Employee without contract',
            'date_version': date(2025, 10, 1),
            'resource_calendar_id': self.calendar_35h.id,
        })
        employee.create_version({'date_version': date(2026, 2, 1), 'resource_calendar_id': self.calendar_40h.id})
        vals = {
            'employee_id': employee.id,
            'work_entry_type_id': hour_type.id,
            'request_date_from': date(2026, 1, 30),
            'request_date_to': date(2026, 2, 2),
        }

        # what the form shows before saving, with the hours of the whole days or without hours
        self.assertEqual(self.env['hr.leave'].new({**vals, 'request_hour_from': 8, 'request_hour_to': 17}).number_of_hours, 15)
        self.assertEqual(self.env['hr.leave'].new(vals).number_of_hours, 15)

        self.env['hr.leave'].create(vals)

        leaves = self._get_employee_leaves(employee)
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.number_of_hours) for l in leaves],
            # the second version starts on a Sunday
            [(date(2026, 1, 30), date(2026, 1, 31), 7), (date(2026, 2, 1), date(2026, 2, 2), 8)],
        )

    def test_create_leave_over_an_ended_contract_and_a_version_without_contract(self):
        # The versions count with or without contract: 35h in contract until the 15th, then 40h
        employee = self.env['hr.employee'].create({
            'name': 'Employee with an ended contract',
            'date_version': date(2022, 1, 1),
            'resource_calendar_id': self.calendar_35h.id,
        })
        employee.version_id.write({'contract_date_start': date(2022, 1, 1), 'contract_date_end': date(2022, 6, 15)})
        employee.create_version({'date_version': date(2022, 6, 16), 'resource_calendar_id': self.calendar_40h.id})

        self.create_leave(date(2022, 6, 10), date(2022, 6, 24), employee_id=employee.id)

        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id, l.number_of_days) for l in self._get_employee_leaves(employee)],
            [
                (date(2022, 6, 10), date(2022, 6, 15), self.calendar_35h, 4),
                (date(2022, 6, 16), date(2022, 6, 24), self.calendar_40h, 7),
            ],
        )

    def test_new_version_in_leave_without_contract(self):
        # Adding a version with another schedule in a time off cuts it, with or without contract
        employee = self.env['hr.employee'].create({
            'name': 'Employee without contract',
            'date_version': date(2022, 1, 1),
            'resource_calendar_id': self.calendar_35h.id,
        })
        leave = self.create_leave(date(2022, 6, 6), date(2022, 6, 17), employee_id=employee.id)
        leave.action_approve()
        self.assertEqual(leave.state, 'validate')

        employee.create_version({'date_version': date(2022, 6, 10), 'resource_calendar_id': self._create_four_days_calendar().id})

        self.assertEqual(leave.state, 'refuse')
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id.name, l.number_of_days, l.state) for l in self._get_employee_leaves(employee)],
            [
                (date(2022, 6, 6), date(2022, 6, 9), '35h calendar', 4, 'validate'),
                (date(2022, 6, 10), date(2022, 6, 17), '4 days calendar', 4, 'confirm'),
            ],
        )

    def test_new_version_in_leave_of_a_contract(self):
        # A version with another schedule in a contract cuts the time off, as without contract
        leave = self.create_leave(date(2022, 6, 6), date(2022, 6, 17), employee_id=self.jules_emp.id)
        leave.action_approve()
        self.assertEqual(leave.state, 'validate')

        self.jules_emp.create_version({'date_version': date(2022, 6, 10), 'resource_calendar_id': self.calendar_40h.id})

        self.assertEqual(leave.state, 'refuse')
        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.resource_calendar_id, l.state) for l in self._get_employee_leaves()],
            [
                (date(2022, 6, 6), date(2022, 6, 9), self.calendar_35h, 'validate'),
                (date(2022, 6, 10), date(2022, 6, 17), self.calendar_40h, 'confirm'),
            ],
        )

    def test_create_leave_over_versions_without_contract_as_employee(self):
        # An ordinary employee does not read the versions: the preview and the creation work for them
        four_days_calendar = self._create_four_days_calendar()
        employee = self._create_employee_without_contract(four_days_calendar)
        employee_user = new_test_user(
            self.env, login='leave_employee_no_contract', groups='base.group_user,hr_holidays.group_hr_holidays_employee')
        employee.user_id = employee_user
        vals = {
            'employee_id': employee.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        }

        self.assertEqual(self.env['hr.leave'].with_user(employee_user).new(vals).number_of_days, 21)

        self.env['hr.leave'].with_user(employee_user).create(vals)

        self.assertEqual(
            [(l.request_date_from, l.request_date_to, l.number_of_days) for l in self._get_employee_leaves(employee)],
            [(date(2022, 6, 1), date(2022, 6, 9), 7), (date(2022, 6, 10), date(2022, 6, 19), 6), (date(2022, 6, 20), date(2022, 6, 30), 8)],
        )

    def test_check_contracts_without_contract(self):
        # The safety net covers the time off reaching it without being cut
        employee = self._create_employee_without_contract()
        leave = self.env['hr.leave'].with_context(skip_leave_version_check=True).create({
            'employee_id': employee.id,
            'work_entry_type_id': self.work_entry_type.id,
            'request_date_from': date(2022, 6, 1),
            'request_date_to': date(2022, 6, 30),
        })

        # the context of the creation is the one of the record
        with self.assertRaises(ValidationError):
            leave.with_context(skip_leave_version_check=False)._check_contracts()

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
        self.env['hr.leave.allocation'].create({
            'name': 'Allocation',
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'number_of_days': 10,
            'state': 'confirm',
            'date_from': datetime.strptime('2023-01-01', '%Y-%m-%d').date(),
            'date_to': datetime.strptime('2023-12-31', '%Y-%m-%d').date(),
        })
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

    def _create_leave_managers(self):
        manager_user_1 = new_test_user(self.env, login='version_manager_1', groups='base.group_user')
        manager_user_2 = new_test_user(self.env, login='version_manager_2', groups='base.group_user')
        manager_1, manager_2 = self.env['hr.employee'].create([
            {'name': 'Manager 1', 'user_id': manager_user_1.id},
            {'name': 'Manager 2', 'user_id': manager_user_2.id},
        ])
        return manager_1, manager_2

    def test_leave_manager_is_versioned(self):
        manager_1, manager_2 = self._create_leave_managers()
        employee = self.env['hr.employee'].create({
            'name': 'Employee', 'parent_id': manager_1.id, 'date_version': '2020-01-01',
        })
        old_version = employee.version_id
        self.assertEqual(old_version.leave_manager_id, manager_1.user_id)

        new_version = employee.create_version({'date_version': '2021-01-01'})
        self.assertEqual(employee.current_version_id, new_version)
        employee.parent_id = manager_2

        self.assertEqual(old_version.leave_manager_id, manager_1.user_id, "Past versions keep their approver")
        self.assertEqual(new_version.leave_manager_id, manager_2.user_id)
        self.assertEqual(employee.leave_manager_id, manager_2.user_id, "The current version drives the employee's approver")
        self.assertEqual(
            employee.with_context(version_id=old_version.id).leave_manager_id, manager_1.user_id,
        )
        self.assertEqual(self.env['hr.employee'].search([('leave_manager_id', '=', manager_1.user_id.id)]).ids, [])
        self.assertIn(employee, self.env['hr.employee'].search([('leave_manager_id', '=', manager_2.user_id.id)]))

    @freeze_time('2026-06-01')
    def test_archive_approver_keeps_past_versions(self):
        manager_1, _manager_2 = self._create_leave_managers()
        employee = self.env['hr.employee'].create({
            'name': 'Employee', 'parent_id': manager_1.id, 'date_version': '2020-01-01',
        })
        past_version = employee.version_id
        current_version = employee.create_version({'date_version': '2026-01-01'})
        future_version = employee.create_version({'date_version': '2030-01-01'})
        self.assertEqual(employee.current_version_id, current_version)
        self.assertEqual((past_version | current_version | future_version).leave_manager_id, manager_1.user_id)

        manager_1.action_archive()
        self.assertEqual(past_version.leave_manager_id, manager_1.user_id, "Past versions keep their approver history")
        self.assertFalse((current_version | future_version).leave_manager_id)

    @freeze_time('2026-06-01')
    def test_future_manager_applies_with_its_version(self):
        """A manager set on a future version does not grant the approver group yet, only on the current version."""
        manager_1, manager_2 = self._create_leave_managers()
        employee = self.env['hr.employee'].create({
            'name': 'Employee', 'parent_id': manager_1.id, 'date_version': '2020-01-01',
        })
        future_version = employee.create_version({'date_version': '2030-01-01'})
        approver_group = 'hr_holidays.group_hr_holidays_responsible'

        employee.with_context(version_id=future_version.id).parent_id = manager_2
        self.assertEqual(future_version.leave_manager_id, manager_2.user_id)
        self.assertEqual(employee.leave_manager_id, manager_1.user_id)
        self.assertFalse(manager_2.user_id.has_group(approver_group))

        employee.parent_id = manager_2
        self.assertEqual(employee.leave_manager_id, manager_2.user_id)
        self.assertTrue(manager_2.user_id.has_group(approver_group))
