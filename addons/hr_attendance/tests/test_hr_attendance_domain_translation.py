import time

from odoo.tests.common import tagged, TransactionCase


@tagged('attendance_searchbar_user_domain')
class TestHrAttendanceDomainTranslation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.hr_attendance = cls.env['hr.attendance']
        cls.hr_employee = cls.env['hr.employee']
        cls.employee_musa, employee_tecna = cls.hr_employee.create([{'name': 'Musa'}, {'name': 'Tecna'}])
        cls.hr_attendance.create({
            'employee_id': employee_tecna.id,
            'check_in': time.strftime('%Y-%m-10 10:00'),
        })

    def test_searchbar_with_user_domain(self):
        companies_ids = self.env['res.company'].search([]).ids

        # Checks that this domain returns no attendance
        self.assertEqual(
            self.hr_attendance.search([
                '&',
                    ('check_out', "!=", False),
                    '|',
                        ('employee_id', 'ilike', 'Musa'),
                        ('employee_id', 'ilike', 'Flora')
            ]),
            self.hr_attendance
        )

        # Ensure that if an employee is searched with the search bar even if he doesn't have any attendance,
        # he will be returned.
        self.assertEqual(
            self.hr_attendance.with_context(
                allowed_company_ids=companies_ids,
                user_domain=[
                    '|',
                        ('employee_id', 'ilike', 'Musa'),
                        ('employee_id', 'ilike', 'Flora')
                ])._read_group_employee_id(self.hr_employee, [
                    '&',
                        ('check_out', "!=", False),
                        '|',
                            ('employee_id', 'ilike', 'Musa'),
                            ('employee_id', 'ilike', 'Flora')
                    ]),
            self.employee_musa
        )
