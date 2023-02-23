# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon

@tagged('-at_install', 'post_install')
class TestEmployee(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_is_subordinate(self):
        employee_georges, employee_paul, employee_pierre = self.env['hr.employee'].with_user(self.res_users_hr_officer).create([
            {'name': 'Georges'},
            {'name': 'Paul'},
            {'name': 'Pierre'},
        ])
        self.res_users_hr_officer.employee_id = employee_georges
        employee_paul.parent_id = employee_georges
        employees = employee_paul + employee_pierre
        self.assertTrue(
            employee_paul.is_subordinate,
            'Paul should be a subordinate of the current user since the current is his manager.')
        self.assertFalse(
            employee_pierre.is_subordinate,
            'Pierre should not be a subordinate of the current user since Pierre has no manager.')

        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', True)), employee_paul)
        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', False)), employee_pierre)

        employee_pierre.parent_id = employee_paul
        self.assertTrue(
            employee_paul.is_subordinate,
            'Paul should be a subordinate of the current user since the current is his manager.')
        self.assertTrue(
            employee_pierre.is_subordinate,
            "Pierre should now be a subordinate of the current user since Paul is his manager and the current user is the Paul's manager.")

        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', True)), employees)
        self.assertFalse(employees.filtered_domain(employees._search_is_subordinate('=', False)))

        employee_paul.parent_id = False
        employees._compute_is_subordinate()

        self.assertFalse(
            employee_paul.is_subordinate,
            'Paul should no longer be a subordinate of the current user since Paul has no manager.')
        self.assertFalse(
            employee_pierre.is_subordinate,
            "Pierre should not be a subordinate of the current user since Paul is his manager and the current user is not the Paul's manager.")

        self.assertFalse(employees.filtered_domain(employees._search_is_subordinate('=', True)))
        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', False)), employees)
