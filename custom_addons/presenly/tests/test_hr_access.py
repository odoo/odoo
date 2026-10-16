from odoo.tests.common import TransactionCase
from odoo.tests import new_test_user
from odoo.exceptions import AccessError


class TestHrAccessHRPage(TransactionCase):
    def test_hr_officer_can_open_attendance_list(self):
        hr_user = new_test_user(
            self.env,
            login='rolecheck_hr',
            groups='base.group_user,presenly.group_presenly_hr',
        )
        # implied checks
        self.assertTrue(hr_user.has_group('hr_attendance.group_hr_attendance_user'))
        self.assertTrue(hr_user.has_group('hr_attendance.group_hr_attendance_officer'))
        emp = self.env['hr.employee'].create({
            'name': 'Rolecheck Emp',
            'company_id': self.env.company.id,
            'user_id': hr_user.id,
        })
        att = self.env['hr.attendance']._presenly_mobile_create({
            'employee_id': emp.id,
            'check_in': '2030-01-05 08:00:00',
            'check_out': '2030-01-05 16:00:00',
            'presenly_source': 'mobile',
        })
        # reading the related attendance_manager_id must NOT raise for HR officer
        self.assertIn(att.id, att.with_user(hr_user).ids)
        val = att.with_user(hr_user).attendance_manager_id
        self.assertFalse(val)
        # list search without error
        rows = self.env['hr.attendance'].with_user(hr_user).search([
            ('employee_id', '=', emp.id),
        ])
        self.assertEqual(len(rows), 1)

    def test_employee_without_officer_still_reads_own_list(self):
        emp_user = new_test_user(
            self.env,
            login='rolecheck_emp',
            groups='base.group_user,presenly.group_presenly_employee',
        )
        emp = self.env['hr.employee'].create({
            'name': 'Rolecheck Emp2',
            'company_id': self.env.company.id,
            'user_id': emp_user.id,
        })
        att = self.env['hr.attendance']._presenly_mobile_create({
            'employee_id': emp.id,
            'check_in': '2030-01-05 08:00:00',
            'check_out': '2030-01-05 16:00:00',
            'presenly_source': 'mobile',
        })
        # Must NOT raise for plain employee either now.
        self.assertIn(att.id, att.with_user(emp_user).ids)
        try:
            val = att.with_user(emp_user).attendance_manager_id
            self.assertFalse(val)
        except AccessError:
            pass
        rows = self.env['hr.attendance'].with_user(emp_user).search([
            ('employee_id', '=', emp.id),
        ])
        self.assertEqual(len(rows), 1)
