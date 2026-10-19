# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date
from odoo.tests import tagged
from odoo.tests import TransactionCase


@tagged('post_install', '-at_install')
class TestHrMaintenance(TransactionCase):

    def test_employee_departure_maintenance(self):
        self.new_employee = self.env['hr.employee'].create({
            'name': 'New Employee',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
        })
        self.laptop = self.env['maintenance.equipment'].create({
            'name': 'New Laptop',
            'employee_id': self.new_employee.id,
        })
        self.assertEqual(self.laptop.employee_id, self.new_employee, "Equipment is not assign to the employee")

        self.env['hr.employee.departure'].create([{
            'employee_id': self.new_employee.id,
            'dismissal_date': date.today(),
            'action_date': date.today(),
            'departure_reason_id': self.env.ref('hr.departure_fired').id,
        }]).action_register()
        self.assertFalse(self.laptop.employee_id, "Equipment was not unassigned after employee's departure")
        self.assertFalse(self.laptop.is_assigned, "Equipment was not unassigned after employee's departure")
