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
