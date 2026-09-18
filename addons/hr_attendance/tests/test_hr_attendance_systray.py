# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestHrAttendanceSystray(HttpCase):
    """ Tests for the systray check in/out JSON route. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'systray_company'})

        # A user linked to an employee: the regular check in/out case.
        cls.user_with_employee = cls.env['res.users'].create({
            'name': 'user_with_employee',
            'login': 'user_with_employee',
            'password': 'user_with_employee',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, cls.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'employee_with_user',
            'company_id': cls.company.id,
            'user_id': cls.user_with_employee.id,
        })

        # A user with no linked employee: the previously crashing case.
        cls.user_without_employee = cls.env['res.users'].create({
            'name': 'user_without_employee',
            'login': 'user_without_employee',
            'password': 'user_without_employee',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, cls.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    def test_systray_check_in_out_without_employee(self):
        """ A user without a linked employee must not trigger a 500 (singleton
        ValueError); the route returns gracefully with an empty payload. """
        self.assertFalse(self.user_without_employee.employee_id)
        self.authenticate('user_without_employee', 'user_without_employee')
        result = self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', {})
        self.assertEqual(result, {})

    def test_systray_check_in_out_with_employee(self):
        """ Control case: a user with a linked employee checks in normally. """
        self.assertEqual(self.employee.attendance_state, 'checked_out')
        self.authenticate('user_with_employee', 'user_with_employee')
        result = self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', {})
        self.assertTrue(result)
        self.assertEqual(result['employee_name'], 'employee_with_user')
        self.assertEqual(self.employee.attendance_state, 'checked_in')
