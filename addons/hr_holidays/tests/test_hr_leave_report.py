
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestHrLeaveReport(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.overtime_work_entry_type = cls.env['hr.work.entry.type'].create({
            'name': 'Overtime Type',
            'code': 'OVERTIME',
            'requires_allocation': True,
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
            'count_as': 'absence',
        })

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
