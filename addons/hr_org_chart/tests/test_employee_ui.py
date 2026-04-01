from odoo.tests import HttpCase, tagged

from odoo.addons.hr.tests.common import TestHrCommon


@tagged('-at_install', 'post_install')
class TestEmployeeUi(TestHrCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_georges, cls.employee_paul, cls.employee_pierre = cls.env['hr.employee'].with_user(cls.res_users_hr_officer).create([
            {'name': 'Georges'},
            {'name': 'Paul'},
            {'name': 'Pierre'},
        ])

    def test_indirect_subordinates(self):
        self.res_users_hr_officer.employee_id = self.employee_georges
        self.employee_paul.parent_id = self.employee_georges
        self.employee_pierre.parent_id = self.employee_paul

        self.start_tour(f"/odoo/employees/{self.employee_georges.id}", 'indirect_subordinates_tour', login="admin")
        indirect_subordinates = len(self.employee_georges.subordinate_ids - self.employee_georges.child_ids)
        self.assertEqual(indirect_subordinates, 1,
            "Georges should have 1 indirect subordinates: Pierre."
        )

    def test_employee_view_access_multicompany(self):
        """checks that an employee still has access to the organization chart even if the manager was created with
        another company, to which that employee doesn't have access."""
        company_0, company_1 = self.env['res.company'].create([{
            'name': "Company 0",
        },
            {
                'name': "Company 1",
            }])
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=[company_0.id, company_1.id]))

        employee_a = self.env['hr.employee'].with_company(company_0).create({
            'name': 'Employee A',
        })
        employee_b = self.env['hr.employee'].with_company(company_1).create({
            'name': 'Employee B',
            'parent_id': employee_a.id,
        })
        self.env['hr.employee'].with_company(company_1).create({
            'name': 'Employee C',
            'parent_id': employee_b.id,
        })
        self.env = self.env(context=dict(self.env.context, allowed_company_ids=[company_1.id]))
        self.restricted_user = self.env['res.users'].with_company(company_1).create({
            'name': 'Restricted User (Test)',
            'login': 'restricted_user',
            'password': 'restricted_user',
            'group_ids': [(6, 0, self.res_users_hr_manager.group_ids.ids)],
        })
        self.start_tour("/odoo/employees", 'employee_view_access_multicompany', login="restricted_user")
