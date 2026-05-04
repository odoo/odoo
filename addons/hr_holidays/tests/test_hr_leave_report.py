
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveReport(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.overtime_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Overtime Type',
            'code': 'overtime_test',
            'requires_allocation': True,
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
            'count_as': 'absence',
        })
        cls.leave_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Leave Type 2025 Scenarios',
            'code': 'overlapping_allocations_test',
            'requires_allocation': True,
            'leave_validation_type': 'no_validation',
            'request_unit': 'day',
            'unit_of_measure': 'day',
            'count_as': 'absence'
        })

        cls.alloc_a, cls.alloc_b = cls.env['hr.leave.allocation'].create([
            {
                'employee_id': cls.employee_emp.id,
                'work_entry_type_id': cls.leave_type.id,
                'date_from': '2024-01-01',
                'date_to': '2025-12-31',
                'number_of_days': 10,
            },
            {
                'employee_id': cls.employee_emp.id,
                'work_entry_type_id': cls.leave_type.id,
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
                'work_entry_type_id': self.overtime_work_entry_type.id,
                'date_from': '2025-12-01',
                'number_of_days': '1.875',
            },
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.overtime_work_entry_type.id,
                'date_from': '2026-01-01',
                'number_of_days': '12.6875',
            },
            {
                'name': 'Overtime',
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.overtime_work_entry_type.id,
                'date_from': '2026-02-01',
                'number_of_days': '1.5',
            },
        ]).action_approve()

        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.overtime_work_entry_type.id,
                'request_date_from': '2025-12-02',
                'request_date_to': '2025-12-02',
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
            {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.overtime_work_entry_type.id,
                'request_date_from': '2026-01-02',
                'request_date_to': '2026-01-02',
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
            {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.overtime_work_entry_type.id,
                'request_date_from': '2026-02-02',
                'request_date_to': '2026-02-02',
                'request_hour_from': 8,
                'request_hour_to': 17,
            },
        ]).action_approve()

        self.env.flush_all()

        domain = [
            ('employee_id', '=', self.employee_emp.id),
            ('work_entry_type_id', '=', self.overtime_work_entry_type.id),
        ]
        leave_balance = self.env['hr.leave.employee.type.report'].search(domain)

        left_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        self.assertEqual(sum(left_allocation.mapped('number_of_hours')), 104.5)
        self.assertEqual(sum(taken_allocation.mapped('number_of_hours')), 24.0)

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
        self.alloc_a.action_approve()
        self.alloc_b.action_approve()
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.leave_type.id,
                'request_date_from': '2026-01-01',
                'request_date_to': '2026-01-01',
            },
        ]).action_approve()

        domain = [
            ('employee_id', '=', self.employee_emp.id),
            ('work_entry_type_id', '=', self.leave_type.id),
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
        self.alloc_a.action_approve()
        self.alloc_b.action_approve()

        # Leave L1: 2024 (1 day)
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.leave_type.id,
                'request_date_from': '2024-01-01',
                'request_date_to': '2024-01-01',
            },
        ]).action_approve()
        self.assertEqual(self.alloc_a.leaves_taken, 1)
        self.assertEqual(self.alloc_b.leaves_taken, 0)

        # Leave L2: 2025 (1 day)
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.leave_type.id,
                'request_date_from': '2025-01-01',
                'request_date_to': '2025-01-01',
            },
        ]).action_approve()
        self.assertEqual(self.alloc_a.leaves_taken, 2)
        self.assertEqual(self.alloc_b.leaves_taken, 0)

        # Leave L3: 2025 (11 days)
        self.env['hr.leave'].create([
            {
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.leave_type.id,
                'request_date_from': '2025-01-02',
                'request_date_to': '2025-01-16',
            },
        ]).action_approve()
        self.assertEqual(self.alloc_a.leaves_taken, 10)
        self.assertEqual(self.alloc_b.leaves_taken, 3)

        domain = [
            ('employee_id', '=', self.employee_emp.id),
            ('work_entry_type_id', '=', self.leave_type.id),
        ]
        leave_balance = self.env['hr.leave.employee.type.report'].search(domain)

        left_records = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_records = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        # 20 total allocated - 13 taken = 7 remaining
        self.assertEqual(sum(left_records.mapped('number_of_days')), 7)
        self.assertEqual(sum(taken_records.mapped('number_of_days')), 13)
