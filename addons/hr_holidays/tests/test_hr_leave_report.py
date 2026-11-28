
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveReport(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.overtime_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Overtime Type',
            'requires_allocation': 'yes',
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
            'time_type': 'leave',
        })
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Test Leave Type 2025 Scenarios',
            'requires_allocation': 'yes',
            'leave_validation_type': 'no_validation',
            'request_unit': 'day',
        })

        cls.alloc_a, cls.alloc_b = cls.env['hr.leave.allocation'].create([
            {
                'employee_id': cls.employee_emp.id,
                'holiday_status_id': cls.leave_type.id,
                'date_from': '2024-01-01',
                'date_to': '2025-12-31',
                'number_of_days': 10,
            },
            {
                'employee_id': cls.employee_emp.id,
                'holiday_status_id': cls.leave_type.id,
                'date_from': '2025-01-01',
                'date_to': '2026-12-31',
                'number_of_days': 10,
            },
        ])

    def test_hr_leave_employee_report(self):
        self.env['hr.leave.allocation'].create([
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'date_from': '2025-12-01',
                'number_of_days': '1.875',
            },
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'date_from': '2026-01-01',
                'number_of_days': '12.6875',
            },
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'date_from': '2026-02-01',
                'number_of_days': '1.5',
            },
        ]).action_validate()

        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'request_date_from': '2025-12-02',
                'request_unit_hours': True,
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'request_date_from': '2026-01-02',
                'request_unit_hours': True,
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'request_date_from': '2026-02-02',
                'request_unit_hours': True,
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
        ]).action_validate()

        domain = [
            ('company_id', '=', self.employee_emp.company_id.id),
            ('employee_id', '=', self.employee_emp.id),
            ('leave_type', '=', self.overtime_leave_type.id),
        ]
        leave_balance = self.env['hr.leave.employee.type.report'].search(domain)

        left_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        self.assertEqual(sum(left_allocation.mapped('number_of_hours')), 104.5)
        self.assertEqual(sum(taken_allocation.mapped('number_of_hours')), 24.0)

    def test_hourly_remaining_days_follow_remaining_hours(self):
        calendar = self.env['resource.calendar'].create({
            'name': '35 hours with unequal half days',
            'tz': 'Europe/Brussels',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {
                    'name': period,
                    'dayofweek': str(day),
                    'day_period': period,
                    'hour_from': start,
                    'hour_to': end,
                })
                for day in range(5)
                for period, start, end in [
                    ('morning', 8.75, 12.5), ('afternoon', 13.5, 16.75),
                ]
            ],
        })
        self.employee_emp.resource_calendar_id = calendar
        self.assertEqual(calendar.hours_per_day, 7)
        allocation = self.env['hr.leave.allocation'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.overtime_leave_type.id,
            'date_from': '2026-01-01',
            'number_of_days': 7.5 / 7,
        })
        allocation.action_validate()
        self.assertAlmostEqual(allocation.number_of_hours_display, 7.5)

        leaves = self.env['hr.leave']
        for date, remaining_hours in [
            ('2026-05-15', 5), ('2026-05-18', 2.5), ('2026-05-19', 0),
        ]:
            leave = self.env['hr.leave'].create({
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.overtime_leave_type.id,
                'request_date_from': date,
                'request_date_to': date,
                'request_unit_hours': True,
                'request_hour_from': 9,
                'request_hour_to': 11.5,
            })
            leave.action_validate()
            leaves |= leave
            self.assertEqual(leave.number_of_hours, 2.5)
            self.assertEqual(leave.number_of_days, 0.333)
            self.env.flush_all()
            balances = {
                status: (hours, days)
                for status, hours, days in self.env['hr.leave.employee.type.report']._read_group(
                    [('employee_id', '=', self.employee_emp.id),
                     ('leave_type', '=', self.overtime_leave_type.id),
                     ('date_from', '>=', '2026-01-01'),
                     ('date_from', '<', '2027-01-01')],
                    ['holiday_status'], ['number_of_hours:sum', 'number_of_days:sum'],
                )
            }
            self.assert_virtual_leaves_equal(
                self.overtime_leave_type, remaining_hours, self.employee_emp, date='2026-05-20')
            self.assertAlmostEqual(balances['left'][0], remaining_hours)
            self.assertAlmostEqual(balances['taken'][0], 7.5 - remaining_hours)
            self.assertAlmostEqual(balances['taken'][1], sum(leaves.mapped('number_of_days')))
            with self.subTest(date=date):
                self.assertAlmostEqual(balances['left'][1], remaining_hours / 7)

    def test_overlapping_allocations_leaves_balance(self):
        """
        Test that leaves only deduct from allocations they actually overlap.

        Scenario:
            - Allocation A: 2024-2025 (10 days)
            - Allocation B: 2025-2026 (10 days)
            - Leave: 2026 (1 day)

        Verification:
            The leave occurs in 2026, so it should only overlap Allocation B.
            Allocation A should remain untouched (10 days), and Allocation B
            should have 1 day deducted (9 days), totaling 19 remaining days.
        """
        self.alloc_a.action_validate()
        self.alloc_b.action_validate()
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2026-01-01',
                'request_date_to': '2026-01-01',
            },
        ]).action_validate()

        domain = [
            ('employee_id', '=', self.employee_emp.id),
            ('leave_type', '=', self.leave_type.id),
        ]
        leave_balance = self.env['hr.leave.employee.type.report'].search(domain)

        left_records = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_records = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        # 20 total allocated - 1 taken = 19 remaining
        self.assertEqual(sum(left_records.mapped('number_of_days')), 19)
        self.assertEqual(sum(taken_records.mapped('number_of_days')), 1)

    def test_overlapping_allocations_leaves_deduction(self):
        """
        Scenario:
            - Allocation A: 2024-2025 (10 days)
            - Allocation B: 2025-2026 (10 days)
            - Leave L1: 2024 (1 day)
            - Leave L2: 2025 (1 day)
            - Leave L3: 2025 (11 days)

        Verification:
            L1 should deduct from Allocation A, leaving 9 days in Allocation A.
            L2 should deduct from Allocation A, leaving 8 days in Allocation A.
            L3 should deduct 8 days from Allocation A (emptying it) and 3 days from Allocation B.
        """
        self.alloc_a.action_validate()
        self.alloc_b.action_validate()

        # Leave L1: 2024 (1 day)
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2024-01-01',
                'request_date_to': '2024-01-01',
            },
        ]).action_validate()
        self.assertEqual(self.alloc_a.leaves_taken, 1)
        self.assertEqual(self.alloc_b.leaves_taken, 0)

        # Leave L2: 2025 (1 day)
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2025-01-01',
                'request_date_to': '2025-01-01',
            },
        ]).action_validate()
        self.assertEqual(self.alloc_a.leaves_taken, 2)
        self.assertEqual(self.alloc_b.leaves_taken, 0)

        # Leave L3: 2025 (11 days)
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'request_date_from': '2025-01-02',
                'request_date_to': '2025-01-16',
            },
        ]).action_validate()
        self.assertEqual(self.alloc_a.leaves_taken, 10)
        self.assertEqual(self.alloc_b.leaves_taken, 3)

        domain = [
            ('employee_id', '=', self.employee_emp.id),
            ('leave_type', '=', self.leave_type.id),
        ]
        leave_balance = self.env['hr.leave.employee.type.report'].search(domain)

        left_records = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_records = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        # 20 total allocated - 13 taken = 7 remaining
        self.assertEqual(sum(left_records.mapped('number_of_days')), 7)
        self.assertEqual(sum(taken_records.mapped('number_of_days')), 13)

    def test_open_ended_allocation_not_affected_by_earlier_leave(self):
        self.env['hr.leave.allocation'].create([
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'date_from': '2025-01-01',
                'date_to': '2025-12-31',
                'number_of_days': 20,
            },
            {
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.leave_type.id,
                'date_from': '2026-01-01',
                'number_of_days': 20,
            },
        ]).action_validate()
        self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': '2025-06-02',
            'request_date_to': '2025-06-02',
        }).action_validate()

        leave_balance = self.env['hr.leave.employee.type.report'].search([
            ('employee_id', '=', self.employee_emp.id),
            ('leave_type', '=', self.leave_type.id),
        ])
        left_records = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        self.assertEqual(sum(left_records.filtered(lambda l: l.date_from.year == 2025).mapped('number_of_days')), 19)
        self.assertEqual(sum(left_records.filtered(lambda l: l.date_from.year == 2026).mapped('number_of_days')), 20)
