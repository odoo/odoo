from odoo.tests import new_test_user
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


class TestPosHrDataHttpCommon(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        # Ensure user access rights
        self.env.user.group_ids += self.env.ref('hr.group_hr_user')

        self.setup_test_employees(self)
        self.edit_test_pos_config(self)

    def setup_test_users(self):
        super().setup_test_users(self)
        self.user_one = new_test_user(
            self.env,
            login="emp1_user",
            groups="base.group_user",
            name="Pos Employee1",
            email="emp1_user@pos.com",
        )

    def setup_test_employees(self):
        self.employee_admin = self.env.ref("hr.employee_admin").sudo().copy({
            "company_id": self.env.company.id,
            "user_id": self.pos_admin.id,
            "name": "Mitchell Admin",
            "pin": False,
        })
        self.employee_one = self.env['hr.employee'].create({
            'name': 'Test Employee 1',
            "company_id": self.env.company.id,
            'pin': '2580',
            'user_id': self.user_one.id,
        })
        self.employee_two = self.env['hr.employee'].create({
            'name': 'Test Employee 2',
            "company_id": self.env.company.id,
            'pin': '1234',
        })
        self.employee_three = self.env['hr.employee'].create({
            'name': 'Test Employee 3',
            "user_id": self.pos_user.id,
            "company_id": self.env.company.id,
        })

    def edit_test_pos_config(self):
        self.pos_config.write({
            'module_pos_hr': True,
            'basic_employee_ids': [
                (4, self.employee_one.id),
                (4, self.employee_two.id),
                (4, self.employee_three.id),
            ]
        })
