# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from freezegun import freeze_time

from odoo.addons.hr_holidays.tests.common import TestHolidayContract


class TestDeparture(TestHolidayContract):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Allocation based',
            'code': 'Allocation based',
            'leave_validation_type': 'hr',
            'allocation_validation_type': 'no_validation',
            'requires_allocation': True,
        })

        cls.jules_allocation = cls.env['hr.leave.allocation'].create([{
            'employee_id': cls.jules_emp.id,
            'work_entry_type_id': cls.work_entry_type.id,
            'date_from': date(2015, 11, 16),
            'number_of_days': 1000,
        }])

        cls.leave_before, cls.leave_during, cls.leave_after_1, cls.leave_after_2 = cls.env['hr.leave'].create([
            {
                'name': "Leave before the departure",
                'employee_id': cls.jules_emp.id,
                'work_entry_type_id': cls.work_entry_type.id,
                'request_date_from': date(2025, 12, 16),
                'request_date_to': date(2025, 12, 20),
            },
            {
                'name': "Leave during the departure",
                'employee_id': cls.jules_emp.id,
                'work_entry_type_id': cls.work_entry_type.id,
                'request_date_from': date(2026, 1, 28),
                'request_date_to': date(2026, 2, 5),
            },
            {
                'name': "Leave after the departure, validated",
                'employee_id': cls.jules_emp.id,
                'work_entry_type_id': cls.work_entry_type.id,
                'request_date_from': date(2026, 3, 3),
                'request_date_to': date(2026, 3, 16),
            },
            {
                'name': "Leave after the departure, draft",
                'employee_id': cls.jules_emp.id,
                'work_entry_type_id': cls.work_entry_type.id,
                'request_date_from': date(2026, 4, 6),
                'request_date_to': date(2026, 4, 16),
            },
        ])
        (cls.leave_before | cls.leave_during | cls.leave_after_1)._action_validate()

    @freeze_time("2026-02-01")
    def test_departure_with_leave_cancel(self):
        self.env['hr.employee.departure'].create([{
            'employee_id': self.jules_emp.id,
            'departure_date': date(2026, 2, 1),
            'departure_reason_id': self.env.ref('hr.departure_fired').id,
            'do_cancel_time_off_requests': True,
        }]).action_register()

        self.assertEqual(self.jules_allocation.date_to, date(2026, 2, 1))
        self.assertEqual(self.leave_before.state, 'validate')
        self.assertEqual(self.leave_during.state, 'validate')
        self.assertEqual(self.leave_during.request_date_to, date(2026, 2, 1))
        self.assertEqual(self.leave_after_1.state, 'cancel')
        self.assertFalse(self.leave_after_2.exists(), "The draft leave should have been deleted.")

    @freeze_time("2026-02-01")
    def test_departure_without_leave_cancel(self):
        self.env['hr.employee.departure'].create([{
            'employee_id': self.jules_emp.id,
            'departure_date': date(2026, 2, 1),
            'departure_reason_id': self.env.ref('hr.departure_fired').id,
            'do_cancel_time_off_requests': False,
        }]).action_register()

        self.assertFalse(self.jules_allocation.date_to)
        self.assertEqual(self.leave_before.state, 'validate')
        self.assertEqual(self.leave_during.state, 'validate')
        self.assertEqual(self.leave_after_1.state, 'validate')
        self.assertEqual(self.leave_after_2.state, 'confirm')
