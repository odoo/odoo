
from datetime import date

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
        cls.annual_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave',
            'requires_allocation': 'yes',
            'leave_validation_type': 'no_validation',
            'request_unit': 'day',
            'time_type': 'leave',
        })

    def _get_report(self, employee, leave_type, extra_domain=None):
        domain = [
            ('company_id', '=', employee.company_id.id),
            ('employee_id', '=', employee.id),
            ('leave_type', '=', leave_type.id),
        ]
        if extra_domain:
            domain += extra_domain
        return self.env['hr.leave.employee.type.report'].search(domain)

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

        leave_balance = self._get_report(self.employee_emp, self.overtime_leave_type)

        left_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'left')
        taken_allocation = leave_balance.filtered(lambda l: l.holiday_status == 'taken')

        self.assertEqual(sum(left_allocation.mapped('number_of_hours')), 104.5)
        self.assertEqual(sum(taken_allocation.mapped('number_of_hours')), 24.0)

    def test_fifo_partial_overlap(self):
        """FIFO should assign leaves to the earliest overlapping allocation,
        not assume all leaves are visible to all prior allocations."""
        self.env['hr.leave.allocation'].create([
            {
                'name': 'Year 1',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.annual_leave_type.id,
                'date_from': '2024-01-01',
                'date_to': '2025-12-31',
                'number_of_days': 10,
            },
            {
                'name': 'Year 2',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.annual_leave_type.id,
                'date_from': '2025-01-01',
                'date_to': '2026-12-31',
                'number_of_days': 10,
            },
            {
                'name': 'Year 3',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.annual_leave_type.id,
                'date_from': '2026-01-01',
                'date_to': '2027-12-31',
                'number_of_days': 10,
            },
        ]).action_validate()

        # Leave 1: overlaps alloc 1 and 2
        self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.annual_leave_type.id,
            'request_date_from': '2025-06-02',
            'request_date_to': '2025-06-02',
        }).action_validate()
        # Leave 2: overlaps alloc 2 and 3, but NOT alloc 1
        self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.annual_leave_type.id,
            'request_date_from': '2026-06-01',
            'request_date_to': '2026-06-01',
        }).action_validate()

        report = self._get_report(self.employee_emp, self.annual_leave_type)
        left = report.filtered(lambda r: r.holiday_status == 'left')
        alloc1_left = left.filtered(lambda r: r.date_from.year == 2024)
        alloc2_left = left.filtered(lambda r: r.date_from.year == 2025)
        alloc3_left = left.filtered(lambda r: r.date_from.year == 2026)

        self.assertEqual(alloc1_left.number_of_days, 9, "Alloc 1 should absorb leave 1")
        self.assertEqual(alloc2_left.number_of_days, 9, "Alloc 2 should absorb leave 2")
        self.assertEqual(alloc3_left.number_of_days, 10, "Alloc 3 should have no leaves consumed")

        # Excluding expired alloc 1: remaining = 9 + 10 = 19
        active_left = left.filtered(lambda r: r.date_to.date() >= date(2026, 1, 1))
        self.assertEqual(sum(active_left.mapped('number_of_days')), 19)

    def test_fifo_overflow(self):
        """When an allocation is full, overflow goes to the next allocation."""
        self.env['hr.leave.allocation'].create([
            {
                'name': 'Small',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.annual_leave_type.id,
                'date_from': '2025-01-01',
                'date_to': '2026-12-31',
                'number_of_days': 2,
            },
            {
                'name': 'Large',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.annual_leave_type.id,
                'date_from': '2025-06-01',
                'date_to': '2027-12-31',
                'number_of_days': 10,
            },
        ]).action_validate()

        # 3 one-day leaves, all overlap both allocations
        for day in ['2025-09-01', '2025-09-02', '2025-09-03']:
            self.env['hr.leave'].create({
                'employee_id': self.employee_emp.id,
                'holiday_status_id': self.annual_leave_type.id,
                'request_date_from': day,
                'request_date_to': day,
            }).action_validate()

        report = self._get_report(self.employee_emp, self.annual_leave_type)
        left = report.filtered(lambda r: r.holiday_status == 'left')

        # FIFO: alloc "Small" absorbs 2, alloc "Large" absorbs 1
        small = left.filtered(lambda r: r.date_from.year == 2025 and r.date_from.month == 1)
        large = left.filtered(lambda r: r.date_from.year == 2025 and r.date_from.month == 6)
        self.assertEqual(small.number_of_days, 0, "Small alloc should be fully consumed")
        self.assertEqual(large.number_of_days, 9, "Large alloc should absorb 1 overflow day")
        self.assertEqual(sum(left.mapped('number_of_days')), 9)
