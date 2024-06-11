# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged, TransactionCase
from odoo.exceptions import MissingError

@tagged('post_install', '-at_install')
class TestEmployeeDeletion(TransactionCase):

    def test_employee_deletion(self):
        # Tests an issue with the form view where the employee could be deleted
        employee_a, employee_b = self.env['hr.employee'].create([
                {
                    'name': 'A',
                },
                {
                    'name': 'B',
                },
        ])
        department_a, department_b = self.env['hr.department'].create([
            {
                'name': 'DEP A',
                'manager_id': employee_a.id,
            },
            {
                'name': 'DEP B',
                'manager_id': employee_b.id,
            },
        ])
        employee_a.write({
            'parent_id': employee_a.id,
            'coach_id': employee_a.id,
            'department_id': department_a.id,
        })
        try:
            with Form(employee_a) as form:
                form.department_id = department_b
        except MissingError:
            self.fail('The employee should not have been deleted')
