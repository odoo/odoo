# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon


@tagged('-at_install', 'post_install')
class TestEmployee(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_georges, cls.employee_paul, cls.employee_pierre, cls.employee_john, cls.employee_alice = cls.env['hr.employee'].with_user(cls.res_users_hr_officer).create([
            {'name': 'Georges'},
            {'name': 'Paul'},
            {'name': 'Pierre'},
            {'name': 'John'},
            {'name': 'Alice'},
        ])

    def test_compute_subordinates(self):
        # hierarchy
        #
        #   georges
        #      |
        #     paul
        #    /    \
        # pierre   \
        #         john
        #            \
        #           alice

        self.employee_paul.parent_id = self.employee_georges
        self.employee_pierre.parent_id = self.employee_paul
        self.employee_john.parent_id = self.employee_paul
        self.employee_alice.parent_id = self.employee_john

        self.assertEqual(
            self.employee_georges.subordinate_ids,
            self.employee_paul
            | self.employee_pierre
            | self.employee_john
            | self.employee_alice,
        )
        self.assertEqual(
            self.employee_paul.subordinate_ids,
            self.employee_pierre | self.employee_john | self.employee_alice,
        )
        self.assertEqual(self.employee_pierre.subordinate_ids, self.env["hr.employee"])
        self.assertEqual(self.employee_john.subordinate_ids, self.employee_alice)
        self.assertEqual(self.employee_alice.subordinate_ids, self.env["hr.employee"])

        # create a cycle between Alice and Georges
        self.employee_georges.parent_id = self.employee_alice

        self.assertEqual(
            self.employee_georges.subordinate_ids,
            self.employee_paul
            | self.employee_pierre
            | self.employee_john
            | self.employee_alice,
        )
        self.assertEqual(
            self.employee_paul.subordinate_ids,
            self.employee_georges
            | self.employee_pierre
            | self.employee_john
            | self.employee_alice,
        )
        self.assertEqual(self.employee_pierre.subordinate_ids, self.env["hr.employee"])
        self.assertEqual(
            self.employee_john.subordinate_ids,
            self.employee_paul
            | self.employee_pierre
            | self.employee_georges
            | self.employee_alice,
        )
        self.assertEqual(
            self.employee_alice.subordinate_ids,
            self.employee_paul
            | self.employee_pierre
            | self.employee_john
            | self.employee_georges,
        )
