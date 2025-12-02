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
