# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon

@tagged('-at_install', 'post_install')
class TestEmployee(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee_georges, cls.employee_paul, cls.employee_pierre = cls.env['hr.employee'].with_user(cls.res_users_hr_officer).create([
            {'name': 'Georges'},
            {'name': 'Paul'},
            {'name': 'Pierre'},
        ])

    def test_is_subordinate(self):
        self.res_users_hr_officer.employee_id = self.employee_georges
        self.employee_paul.parent_id = self.employee_georges
        employees = self.employee_paul + self.employee_pierre
        self.assertTrue(
            self.employee_paul.is_subordinate,
            'Paul should be a subordinate of the current user since the current is his manager.')
        self.assertFalse(
            self.employee_pierre.is_subordinate,
            'Pierre should not be a subordinate of the current user since Pierre has no manager.')

        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', True)), self.employee_paul)
        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', False)), self.employee_pierre)

        self.employee_pierre.parent_id = self.employee_paul
        self.assertTrue(
            self.employee_paul.is_subordinate,
            'Paul should be a subordinate of the current user since the current is his manager.')
        self.assertTrue(
            self.employee_pierre.is_subordinate,
            "Pierre should now be a subordinate of the current user since Paul is his manager and the current user is the Paul's manager.")

        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', True)), employees)
        self.assertFalse(employees.filtered_domain(employees._search_is_subordinate('=', False)))

        self.employee_paul.parent_id = False
        employees._compute_is_subordinate()

        self.assertFalse(
            self.employee_paul.is_subordinate,
            'Paul should no longer be a subordinate of the current user since Paul has no manager.')
        self.assertFalse(
            self.employee_pierre.is_subordinate,
            "Pierre should not be a subordinate of the current user since Paul is his manager and the current user is not the Paul's manager.")

        self.assertFalse(employees.filtered_domain(employees._search_is_subordinate('=', True)))
        self.assertEqual(employees.filtered_domain(employees._search_is_subordinate('=', False)), employees)

    def test_hierarchy_read(self):
        HrEmployee = self.env['hr.employee']
        employees = self.employee_georges + self.employee_paul + self.employee_pierre
        result = HrEmployee.hierarchy_read([('id', 'in', employees.ids)], ['id'], 'parent_id')
        for emp in employees:
            self.assertIn({'id': emp.id, 'parent_id': False}, result)

        self.employee_georges.parent_id = self.employee_paul
        self.employee_pierre.parent_id = self.employee_paul
        result = HrEmployee.hierarchy_read([('id', 'in', employees.ids)], ['id'], 'parent_id')
        self.assertEqual(len(result), 3)
        for emp in employees:
            emp_dict = {'id': emp.id, 'parent_id': emp.parent_id.id and (emp.parent_id.id, emp.parent_id.display_name)}
            if not emp.parent_id:
                emp_dict['__child_ids__'] = [self.employee_georges.id, self.employee_pierre.id]
            self.assertIn(emp_dict, result)

        employee_count = HrEmployee.search_count([('id', 'not in', employees.ids), ('parent_id', '=', False)])
        result = HrEmployee.hierarchy_read([('parent_id', '=', False)], ['id'], 'parent_id')
        self.assertEqual(len(result), 1 + employee_count)
        for employee_dict in result:
            self.assertFalse(employee_dict['parent_id'], "Each employee in the result should not have any parent set.")
        self.assertIn({'id': self.employee_paul.id, 'parent_id': False, '__child_ids__': [self.employee_georges.id, self.employee_pierre.id]}, result)

        result = HrEmployee.hierarchy_read([('id', '=', self.employee_paul.id)], ['id'], 'parent_id')
        self.assertEqual(len(result), 3)
        for emp in employees:
            emp_dict = {'id': emp.id, 'parent_id': emp.parent_id.id and (emp.parent_id.id, emp.parent_id.display_name)}
            self.assertIn(emp_dict, result)

        result = HrEmployee.hierarchy_read([('id', '=', self.employee_georges.id)], ['id'], 'parent_id')
        self.assertEqual(len(result), 3)
        for emp in employees:
            emp_dict = {'id': emp.id, 'parent_id': emp.parent_id.id and (emp.parent_id.id, emp.parent_id.display_name)}
            self.assertIn(emp_dict, result)

        self.employee_pierre.parent_id = self.employee_georges
        result = HrEmployee.hierarchy_read([('id', '=', self.employee_georges.id)], ['id'], 'parent_id')
        self.assertEqual(len(result), 3)
        for emp in employees:
            emp_dict = {'id': emp.id, 'parent_id': emp.parent_id.id and (emp.parent_id.id, emp.parent_id.display_name)}
            self.assertIn(emp_dict, result)

        result = HrEmployee.hierarchy_read([('id', '=', self.employee_pierre.id)], ['id'], 'parent_id')
        self.assertEqual(len(result), 2)
        self.assertIn(
            {'id': self.employee_pierre.id, 'parent_id': (self.employee_georges.id, self.employee_georges.name)},
            result
        )
        self.assertIn(
            {'id': self.employee_georges.id, 'parent_id': (self.employee_paul.id, self.employee_paul.name)},
            result
        )
