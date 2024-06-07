# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.hr.tests.common import TestHrCommon


class TestHrEmployee(TestHrCommon):

    def setUp(self):
        super().setUp()
        self.user_without_image = self.env['res.users'].create({
            'name': 'Marc Demo',
            'email': 'mark.brown23@example.com',
            'image_1920': False,
            'login': 'demo_1',
            'password': 'demo_123'
        })
        self.employee_without_image = self.env['hr.employee'].create({
            'user_id': self.user_without_image.id,
            'image_1920': False
        })

    def test_employee_linked_partner(self):
        user_partner = self.user_without_image.partner_id
        work_contact = self.employee_without_image.work_contact_id
        self.assertEqual(user_partner, work_contact)

    def test_employee_resource(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee = employee_form.save()
        self.assertEqual(employee.tz, _tz)

    def test_employee_from_user(self):
        _tz = 'Pacific/Apia'
        _tz2 = 'America/Tijuana'
        self.res_users_hr_officer.company_id.resource_calendar_id.tz = _tz
        self.res_users_hr_officer.tz = _tz2
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, self.res_users_hr_officer.tz)

    def test_employee_from_user_tz_no_reset(self):
        _tz = 'Pacific/Apia'
        self.res_users_hr_officer.tz = False
        Employee = self.env['hr.employee'].with_user(self.res_users_hr_officer)
        employee_form = Form(Employee)
        employee_form.name = 'Raoul Grosbedon'
        employee_form.work_email = 'raoul@example.com'
        employee_form.tz = _tz
        employee_form.user_id = self.res_users_hr_officer
        employee = employee_form.save()
        self.assertEqual(employee.name, 'Raoul Grosbedon')
        self.assertEqual(employee.work_email, self.res_users_hr_officer.email)
        self.assertEqual(employee.tz, _tz)

    def test_employee_has_avatar_even_if_it_has_no_image(self):
        self.assertTrue(self.employee_without_image.avatar_128)
        self.assertTrue(self.employee_without_image.avatar_256)
        self.assertTrue(self.employee_without_image.avatar_512)
        self.assertTrue(self.employee_without_image.avatar_1024)
        self.assertTrue(self.employee_without_image.avatar_1920)

    def test_employee_has_same_avatar_as_corresponding_user(self):
        self.assertEqual(self.employee_without_image.avatar_1920, self.user_without_image.avatar_1920)

    def test_employee_member_of_department(self):
        dept, dept_sub, dept_sub_sub, dept_other, dept_parent = self.env['hr.department'].create([
            {
                'name': 'main',
            },
            {
                'name': 'sub',
            },
            {
                'name': 'sub-sub',
            },
            {
                'name': 'other',
            },
            {
                'name': 'parent',
            },
        ])
        dept_sub.parent_id = dept
        dept_sub_sub.parent_id = dept_sub
        dept.parent_id = dept_parent
        emp, emp_sub, emp_sub_sub, emp_other, emp_parent = self.env['hr.employee'].with_user(self.res_users_hr_officer).create([
            {
                'name': 'employee',
                'department_id': dept.id,
            },
            {
                'name': 'employee sub',
                'department_id': dept_sub.id,
            },
            {
                'name': 'employee sub sub',
                'department_id': dept_sub_sub.id,
            },
            {
                'name': 'employee other',
                'department_id': dept_other.id,
            },
            {
                'name': 'employee parent',
                'department_id': dept_parent.id,
            },
        ])
        self.res_users_hr_officer.employee_id = emp
        self.assertTrue(emp.member_of_department)
        self.assertTrue(emp_sub.member_of_department)
        self.assertTrue(emp_sub_sub.member_of_department)
        self.assertFalse(emp_other.member_of_department)
        self.assertFalse(emp_parent.member_of_department)
        employees = emp + emp_sub + emp_sub_sub + emp_other + emp_parent
        self.assertEqual(
            employees.filtered_domain(employees._search_part_of_department('=', True)),
            emp + emp_sub + emp_sub_sub)
        self.assertEqual(
            employees.filtered_domain(employees._search_part_of_department('!=', False)),
            emp + emp_sub + emp_sub_sub)
        self.assertEqual(
            employees.filtered_domain(employees._search_part_of_department('=', False)),
            emp_other + emp_parent)
        self.assertEqual(
            employees.filtered_domain(employees._search_part_of_department('!=', True)),
            emp_other + emp_parent)

    def test_employee_create_from_user(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test User 3 - employee'
        })
        user_1, user_2, user_3 = self.env['res.users'].create([
            {
                'name': 'Test User',
                'login': 'test_user',
                'email': 'test_user@odoo.com',
            },
            {
                'name': 'Test User 2',
                'login': 'test_user_2',
                'email': 'test_user_2@odoo.com',
                'create_employee': True,
            },
            {
                'name': 'Test User 3',
                'login': 'test_user_3',
                'email': 'test_user_3@odoo.com',
                'create_employee_id': employee.id,
            },
        ])
        # Test that creating an user does not create an employee by default
        self.assertFalse(user_1.employee_id)
        # Test that setting create_employee does create the associated employee
        self.assertTrue(user_2.employee_id)
        # Test that creating an user with a given employee associates the employee correctly
        self.assertEqual(user_3.employee_id, employee)

    def test_employee_create_from_signup(self):
        # Test that an employee is not created when signin up on the website
        partner = self.env['res.partner'].create({
            'name': 'test partner'
        })
        self.env['res.users'].signup({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'test_user@odoo.com',
            'password': 'test_user_password',
            'partner_id': partner.id,
        })
        self.assertFalse(self.env['res.users'].search([('login', '=', 'test_user')]).employee_id)

    def test_employee_update_work_contact_id(self):
        """
            Check that the `work_contact_id` information is no longer
            updated when an employee's `user_id` is removed.
        """
        user = self.env['res.users'].create({
            'name': 'Test',
            'login': 'test',
            'email': 'test@example.com',
        })
        employee_A, employee_B = self.env['hr.employee'].create([
            {
                'name': 'Employee A',
                'user_id': user.id,
                'work_email': 'employee_A@example.com',
            },
            {
                'name': 'Employee B',
                'user_id': False,
                'work_email': 'employee_B@example.com',
            }
        ])
        employee_A.user_id = False
        employee_B.user_id = user.id
        employee_B.work_email = 'new_email@example.com'
        self.assertEqual(employee_A.work_email, 'employee_A@example.com')
        self.assertEqual(employee_B.work_email, 'new_email@example.com')

    def test_unlink_address(self):
        employee = self.employee_without_image
        partner = self.env["res.partner"].create({
            "name": "Mr. Bean",
            "street": "12 Arbour Road",
            "city": "London"
        })
        employee.address_home_id = partner.id
        bank = self.env['res.partner.bank'].create({
            "acc_number": "123",
            "partner_id": partner.id
        })
        employee.bank_account_id = bank.id

        employee.address_home_id = False
        self.assertFalse(employee.address_home_id)
