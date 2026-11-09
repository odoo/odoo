# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, HttpCase, tagged
from odoo.exceptions import MissingError

from odoo.addons.hr.tests.common import TestHrCommon


@tagged('post_install', '-at_install')
class TestHrOrgChart(TestHrCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_georges, cls.employee_paul, cls.employee_pierre = cls.env['hr.employee'].with_user(cls.res_users_hr_officer).create([
            {'name': 'Georges'},
            {'name': 'Paul'},
            {'name': 'Pierre'},
        ])
        cls.department_a, cls.department_b = cls.env['hr.department'].create([
            {
                'name': 'DEP A',
                'manager_id': cls.employee_georges.id,
            },
            {
                'name': 'DEP B',
                'manager_id': cls.employee_paul.id,
            },
        ])

    def test_employee_deletion(self):
        self.cr.flush()  # detect tracking issues
        # Tests an issue with the form view where the employee could be deleted
        self.employee_georges.write({
            'parent_id': self.employee_georges.id,
            'coach_id': self.employee_georges.id,
            'department_id': self.department_a.id,
        })
        try:
            with Form(self.employee_georges) as form:
                form.department_id = self.department_b
        except MissingError:
            self.fail('The employee should not have been deleted')

    def test_indirect_subordinates(self):
        self.res_users_hr_officer.employee_ids = self.employee_georges
        self.employee_paul.parent_id = self.employee_georges
        self.employee_pierre.parent_id = self.employee_paul

        self.start_tour(f"/odoo/employees/{self.employee_georges.id}", 'indirect_subordinates_tour', login="admin")
        indirect_subordinates = len(self.employee_georges.subordinate_ids - self.employee_georges.child_ids)
        self.assertEqual(indirect_subordinates, 1,
            "Georges should have 1 indirect subordinates: Pierre."
        )

    def test_is_subordinate(self):
        self.res_users_hr_officer.employee_ids = self.employee_georges
        self.employee_paul.parent_id = self.employee_georges
        employees = self.employee_paul + self.employee_pierre
        self.assertTrue(
            self.employee_paul.is_subordinate,
            'Paul should be a subordinate of the current user since the current is his manager.')
        self.assertFalse(
            self.employee_pierre.is_subordinate,
            'Pierre should not be a subordinate of the current user since Pierre has no manager.')

        def _filtered_is_subordinate(flag):
            dom = employees._search_is_subordinate('in', [True])
            if not flag:
                dom = ['!', *dom]
            return employees.filtered_domain(dom)

        self.assertEqual(_filtered_is_subordinate(True), self.employee_paul)
        self.assertEqual(_filtered_is_subordinate(False), self.employee_pierre)

        self.employee_pierre.parent_id = self.employee_paul
        self.assertTrue(
            self.employee_paul.is_subordinate,
            'Paul should be a subordinate of the current user since the current is his manager.')
        self.assertTrue(
            self.employee_pierre.is_subordinate,
            "Pierre should now be a subordinate of the current user since Paul is his manager and the current user is the Paul's manager.")

        self.assertEqual(_filtered_is_subordinate(True), employees)
        self.assertFalse(_filtered_is_subordinate(False))

        self.employee_paul.parent_id = False
        employees._compute_is_subordinate()

        self.assertFalse(
            self.employee_paul.is_subordinate,
            'Paul should no longer be a subordinate of the current user since Paul has no manager.')
        self.assertFalse(
            self.employee_pierre.is_subordinate,
            "Pierre should not be a subordinate of the current user since Paul is his manager and the current user is not the Paul's manager.")

        self.assertFalse(_filtered_is_subordinate(True))
        self.assertEqual(_filtered_is_subordinate(False), employees)
