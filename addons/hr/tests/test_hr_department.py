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
