from datetime import date

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('post_install', '-at_install', 'hours_per_day_rounding')
class TestHoursPerDayRounding(TestHrHolidaysCommon):
    """ Allocations are stored in days and converted into hours with the average hours per day
        of the schedule. That average must not be rounded: on a 38 hours schedule over 6 days,
        6 days must be worth exactly 38 hours, not 6 * 6.33333 = 37.99998 hours.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 7 hours from Monday to Friday, 3 hours on Saturday: 38 hours over 6 days
        cls.calendar_38h = cls.env['resource.calendar'].create({
            'name': '38 hours over 6 days',
            'company_id': cls.company.id,
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour_from, 'hour_to': hour_to})
                for day in range(5)
                for hour_from, hour_to in ((8, 12), (13, 16))
            ] + [(0, 0, {'dayofweek': '5', 'hour_from': 8, 'hour_to': 11})],
        })
        cls.employee_38h = cls.env['hr.employee'].create({
            'name': '38 hours employee',
            'company_id': cls.company.id,
            'resource_calendar_id': cls.calendar_38h.id,
            'tz': 'UTC',
        })
        cls.hour_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Hourly time off',
            'code': 'Hourly time off',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
            'unit_of_measure': 'hour',
        })
        cls.day_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Daily time off',
            'code': 'Daily time off',
            'count_as': 'absence',
            'requires_allocation': True,
            'allocation_validation_type': 'no_validation',
            'leave_validation_type': 'no_validation',
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

    def _allocate(self, work_entry_type, days, employee=None):
        return self.env['hr.leave.allocation'].create({
            'name': 'Allocation',
            'employee_id': (employee or self.employee_38h).id,
            'work_entry_type_id': work_entry_type.id,
            'number_of_days': days,
            'date_from': date(2026, 11, 1),
        })

    def _remaining(self, allocation, unit):
        employee, work_entry_type = allocation.employee_id, allocation.work_entry_type_id
        consumed = employee._get_consumed_leaves(work_entry_type, date(2026, 11, 16))[0]
        return consumed[employee][work_entry_type][allocation][f'{unit}_virtual_remaining_leaves']

    def test_hours_per_day_not_rounded(self):
        self.assertEqual(self.calendar_38h.hours_per_week, 38)
        self.assertEqual(self.calendar_38h.days_per_week, 6)
        self.assertEqual(self.calendar_38h.hours_per_day, 38 / 6)
        self.assertEqual(self.calendar_38h.hours_per_day * 6, 38)

    def test_allocation_in_days_is_worth_exact_hours(self):
        allocation = self._allocate(self.hour_work_entry_type, days=6)
        self.assertEqual(allocation.number_of_hours, 38)

    def test_allocation_in_hours_is_worth_exact_days(self):
        with Form(self.env['hr.leave.allocation']) as allocation_form:
            allocation_form.employee_id = self.employee_38h
            allocation_form.work_entry_type_id = self.hour_work_entry_type
            allocation_form.date_from = date(2026, 11, 1)
            allocation_form.number_of_hours = 38
            allocation = allocation_form.save()
        self.assertEqual(allocation.number_of_hours, 38)
        self.assertEqual(allocation.number_of_days, 6)

    @freeze_time('2026-11-01')
    def test_whole_allocation_in_hours_can_be_taken(self):
        allocation = self._allocate(self.hour_work_entry_type, days=6)
        leave = self._create_leave(
            self.employee_38h, self.hour_work_entry_type, date(2026, 11, 2), date(2026, 11, 7))
        self.assertEqual(leave.number_of_hours, 38)
        self.assertEqual(leave.state, 'validate')
        self.assertEqual(self._remaining(allocation, 'hours'), 0)
        self.assertEqual(self._remaining(allocation, 'days'), 0)

    @freeze_time('2026-11-01')
    def test_whole_allocation_in_days_can_be_taken(self):
        allocation = self._allocate(self.day_work_entry_type, days=6)
        leave = self._create_leave(
            self.employee_38h, self.day_work_entry_type, date(2026, 11, 2), date(2026, 11, 7))
        self.assertEqual(leave.number_of_days, 6)
        self.assertEqual(leave.state, 'validate')
        self.assertEqual(self._remaining(allocation, 'days'), 0)
        self.assertEqual(self._remaining(allocation, 'hours'), 0)

    @freeze_time('2026-11-01')
    def test_real_shortage_still_refused(self):
        # 6 minutes missing
        self._allocate(self.hour_work_entry_type, days=37.9 / (38 / 6))
        with self.assertRaises(ValidationError):
            self._create_leave(
                self.employee_38h, self.hour_work_entry_type, date(2026, 11, 2), date(2026, 11, 7))

    def _create_calendar_employee(self, end_of_day):
        calendar = self.env['resource.calendar'].create({
            'name': 'Schedule',
            'company_id': self.company.id,
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour_from, 'hour_to': hour_to})
                for day in range(5)
                for hour_from, hour_to in ((8, 12), (13, end_of_day))
            ],
        })
        return self.env['hr.employee'].create({
            'name': 'Employee',
            'company_id': self.company.id,
            'resource_calendar_id': calendar.id,
            'tz': 'UTC',
        })

    def test_schedule_not_representable_in_five_digits(self):
        """ 7h20 a day: hours_per_week is still stored with 5 digits (36.66667), only the
            residue of that rounding remains, it is not rounded a second time per day. """
        employee = self._create_calendar_employee(16 + 1 / 3)
        calendar = employee.resource_calendar_id
        self.assertEqual(calendar.hours_per_week, 36.66667)
        self.assertEqual(calendar.hours_per_day, 36.66667 / 5)
        allocation = self._allocate(self.hour_work_entry_type, days=3, employee=employee)
        self.assertAlmostEqual(allocation.number_of_hours, 22, delta=1e-5)

    @freeze_time('2026-11-01')
    def test_whole_allocation_with_rounding_residue_can_be_taken(self):
        """ 7h40 a day: hours_per_week is rounded down to 38.33333, 3 days are worth
            22.999998 hours: that residue must not refuse a request of the whole 23 hours. """
        employee = self._create_calendar_employee(16 + 2 / 3)
        allocation = self._allocate(self.hour_work_entry_type, days=3, employee=employee)
        self.assertLess(allocation.number_of_hours, 23)
        leave = self._create_leave(employee, self.hour_work_entry_type, date(2026, 11, 2), date(2026, 11, 4))
        self.assertAlmostEqual(leave.number_of_hours, 23, places=9)
        self.assertEqual(leave.state, 'validate')
        self.assertAlmostEqual(self._remaining(allocation, 'hours'), 0, delta=1e-5)
