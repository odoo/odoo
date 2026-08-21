# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.hr.tests.common import TestHrCommon


class TestHrEmployee(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.res_users_without_hr_right = mail_new_test_user(
            cls.env,
            email='nhr@example.com',
            login='nhr',
            groups='base.group_user,base.group_partner_manager',
            name='No HR Right',
        )

    def test_access_related_field_to_hr_employee(self):
        # Check if a related field related to hr_employee is accessible.
        self.env['hr.employee.public'].with_user(self.res_users_without_hr_right).search([("email", "!=", False)])

    def test_access_search_on_users_department(self):
        dep = self.env['hr.department'].create({'name': 'test'})
        emp = self.env['hr.employee'].create({'department_id': dep.id, 'name': 'Joe'})
        # the search can be performed on the user (without access error)
        User = self.env['res.users'].with_user(self.res_users_without_hr_right)
        User.search([('employee_id.department_id', '=', dep.id)])
        # the search on the resource should find the user
        res = self.env['resource.resource'].with_user(self.res_users_without_hr_right)
        res = res.search([('employee_id.department_id', '=', dep.id)])
        self.assertIn(emp.resource_id, res, "Resource should be found")
