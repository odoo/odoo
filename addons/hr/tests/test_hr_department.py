from odoo.addons.hr.tests.test_multi_company import TestMultiCompany


class TestHrDepartment(TestMultiCompany):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.department = cls.env['hr.department'].create({
            'name': 'test department',
        })
        cls.employee_a.department_id = cls.department
        cls.employee_other_a.department_id = cls.department
        cls.employee_b.department_id = cls.department

    def test_dapartment_total_employee_count(self):
        '''
            Test that employee_count has only the count of employees in the selected companies
        '''
        employee_count = self.department.with_company(self.company_a).total_employee  # should only count the 2 employees in company_a
        self.assertEqual(employee_count, 2)

        self.department._compute_total_employee()
        employee_count = self.department.total_employee  # should count all 3 employees
        self.assertEqual(employee_count, 3)

    def test_admin_user_without_group_hr_user_falls_back_to_public_employee_action(self):
        """
        Ensure users lacking 'hr.group_hr_user' are routed to 'hr.employee.public',
        even if they possess 'base.group_system'.
        """
        office_manager = self.env['res.users'].create({
            'name': 'Office Manager',
            'login': 'office_manager',
            'email': 'office_manager@example.com',
            'groups_id': [(6, 0, [self.env.ref('hr.group_hr_user').id])],
        })

        admin = self.env['res.users'].browse(self.ref('base.user_admin'))

        admin.write({
            'groups_id': [(6, 0, [self.env.ref('base.group_system').id])],
        })

        office_manager_result = self.department.with_user(office_manager).action_employee_from_department()

        admin_result = self.department.with_user(admin).action_employee_from_department()

        self.assertEqual(
            office_manager_result['res_model'],
            'hr.employee',
            'Expected action target to be "hr.employee" for users belonging to "hr.group_hr_user".'
        )
        self.assertEqual(
            admin_result['res_model'],
            'hr.employee.public',
            'Expected action target to fall back to "hr.employee.public" when the user lacks "hr.group_hr_user", regardless of administration rights.'
        )
