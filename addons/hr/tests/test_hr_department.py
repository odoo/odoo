from odoo.addons.hr.tests.test_multi_company import TestMultiCompany
from odoo.tests import HttpCase, new_test_user, tagged


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

    def test_department_company_id(self):
        """
        When the parent exists and parent's company changes to non-empty company, the child's company must be equalized to the same company
        If the parent's company changes to empty, the child's company should not get affected
        """

        self.parent_department = self.env['hr.department'].create({
            'name': 'parent of the test department',
            'company_id': self.company_a.id,
        })
        self.department.company_id = self.company_b.id
        self.assertTrue(self.department.company_id == self.company_b)
        self.department.parent_id = self.parent_department.id
        self.assertTrue(self.department.company_id == self.company_a)
        self.parent_department.company_id = self.company_b
        self.assertTrue(self.department.company_id == self.company_b)
        self.parent_department.company_id = False

        # Child's company should not change

        self.assertTrue(self.department.company_id == self.company_b)

        self.parents_parent_department = self.env['hr.department'].create({
            'name': 'grandparent of test department',
            'company_id': False,
        })
        self.parent_department.parent_id = self.parents_parent_department.id

        #   Since the company of grandparent is False, it will not affect childs.

        self.assertFalse(self.parent_department.company_id)
        self.assertTrue(self.department.company_id == self.company_b)

        self.parents_parent_department.company_id = self.company_a.id
        self.assertTrue(self.parent_department.company_id == self.company_a)
        self.assertTrue(self.department.company_id == self.company_a)


@tagged('-at_install', 'post_install', 'is_tour')
class TestHrDepartmentUi(HttpCase):
    def test_department_plans_smart_button_no_plans(self):
        """
        A manager opening the department of one of their employees (through the
        employee's page) must see 0 plans on the smart button, and clicking it
        must not display any plan nor raise an error.
        """
        # Plans without department (e.g. Onboarding/Offboarding) count for every department
        self.env['mail.activity.plan'].search([]).action_archive()

        manager_user = new_test_user(self.env, login='plan_manager', groups='base.group_user')
        manager = self.env['hr.employee'].create({
            'name': 'Plan Manager',
            'user_id': manager_user.id,
        })
        department = self.env['hr.department'].create({
            'name': 'Department Without Plans',
            'manager_id': manager.id,
        })
        self.env['hr.employee'].create({
            'name': 'Employee Without Plans',
            'department_id': department.id,
            'parent_id': manager.id,
        })
        self.start_tour('/odoo', 'hr_department_no_plans_tour', login='plan_manager')
