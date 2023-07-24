# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime

from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase


class TestHrAttendanceOvertime(TransactionCase):
    """ Tests for overtime """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'hr_attendance_overtime': True,
            'overtime_start_date': datetime(2023, 1, 1),
        })
        cls.user = new_test_user(cls.env, login='fru', groups='base.group_user,hr_attendance.group_hr_attendance', company_id=cls.company.id).with_company(cls.company)
        cls.employee = cls.env['hr.employee'].create({
            'name': "Marie-Edouard De La Court",
            'user_id': cls.user.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
        })

    def create_contract(self, state, resource_calendar, start, end=None):
        return self.env['hr.contract'].create({
            'name': 'Contract',
            'employee_id': self.employee.id,
            'state': state,
            'date_start': start,
            'date_end': end,
            'resource_calendar_id': resource_calendar.id,
            'wage': 1,
        })

    def test_overtime_contract(self):
        start = datetime.strptime('2023-06-01', '%Y-%m-%d').date()
        end = datetime.strptime('2023-06-30', '%Y-%m-%d').date()
        self.create_contract('open', self.env.ref('resource.resource_calendar_std'), start, end)

        start = datetime.strptime('2023-07-01', '%Y-%m-%d').date()
        end = datetime.strptime('2023-07-31', '%Y-%m-%d').date()
        self.create_contract('open', self.env.ref('resource.resource_calendar_std_35h'), start, end)

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 6, 5, 8, 0),
            'check_out': datetime(2023, 6, 5, 17, 0)
        })

        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2023, 6, 5))])
        self.assertEqual(overtime.duration, 1)

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2023, 7, 3, 8, 0),
            'check_out': datetime(2023, 7, 3, 16, 0)
        })
        overtime = self.env['hr.attendance.overtime'].search([('employee_id', '=', self.employee.id), ('date', '=', date(2023, 7, 3))])
        self.assertEqual(overtime.duration, 1)
