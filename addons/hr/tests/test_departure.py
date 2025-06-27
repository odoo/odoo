# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from freezegun import freeze_time

from odoo.exceptions import ValidationError

from odoo.addons.hr.tests.common import TestHrCommon


class TestDeparture(TestHrCommon):

    @classmethod
    @freeze_time('2025-01-01')
    def setUpClass(cls):
        super().setUpClass()
        cls.emp_boss = cls.env['hr.employee'].create({
            'name': "Nice boss",
            'contract_date_start': date.today(),
        })

        cls.emp_A, cls.emp_B, cls.emp_C = cls.env['hr.employee'].create([
            {
                'name': f'Employee {code}',
                'parent_id': cls.emp_boss.id,
                'user_id': False,
                'work_email': f'employee_{code}@example.com',
                'contract_date_start': date(2025, 2, 1),
                'contract_date_end': False,
            } for code in ['A', 'B', 'C']
        ])

        cls.user_A = cls.env['res.users'].create({
            'name': 'Employee A',
            'login': 'empA',
            'password': 'longPasswordForEmployeeA',
            'email': 'empA@empa.com',
            'employee_ids': cls.emp_A.ids,
        })

    @freeze_time('2025-06-01')
    def test_immediate_departure(self):
        departure = self.env['hr.employee.departure'].create([{
            'employee_id': self.emp_A.id,
            'departure_date': date.today(),
            'departure_reason_id': self.env.ref('hr.departure_fired').id,
            'departure_description': "Didn't bring coffee",
        }])
        self.assertTrue(departure.apply_immediately)
        departure.action_register()
        self.assertEqual(departure.apply_date, date.today(), "The departure should have been applied.")

    @freeze_time('2025-06-01')
    def test_departure_actions_to_true(self):
        dep_date = date(2025, 6, 1)
        departure = self.env['hr.employee.departure'].create([{
            'employee_id': self.emp_A.id,
            'departure_date': dep_date,
            'do_set_date_end': True,
            'do_archive_employee': True,
            'do_archive_user': True,
        }])
        departure.action_register()
        self.assertFalse(self.emp_A.active, "Employee A should be archived.")
        self.assertFalse(self.user_A.active, "Employee A's user should be archived.")
        self.assertEqual(self.emp_A.contract_date_end, dep_date, "Employee A's contract dates should end at the departure date.")

    @freeze_time('2025-06-01')
    def test_departure_actions_to_false(self):
        departure = self.env['hr.employee.departure'].create([{
            'employee_id': self.emp_A.id,
            'departure_date': date(2025, 6, 1),
            'do_set_date_end': False,
            'do_archive_employee': False,
            'do_archive_user': False,
        }])
        departure.action_register()
        self.assertTrue(self.emp_A.active, "Employee A shouldn't be archived.")
        self.assertTrue(self.user_A.active, "Employee A's user shouldn't be archived.")
        self.assertFalse(self.emp_A.contract_date_end, "Employee A's contract should not end.")

    def test_wrong_departure_date(self):
        # the departure should be blocked if not after the first version date
        with self.assertRaises(ValidationError):
            self.env['hr.employee.departure'].create([{
                'employee_id': self.emp_A.id,
                'departure_date': date(2025, 1, 1),
            }])

        # the departure should be blocked if not after the first contract date
        with self.assertRaises(ValidationError):
            self.env['hr.employee.departure'].create([{
                'employee_id': self.emp_A.id,
                'departure_date': date(2025, 2, 1),
            }])

    def test_future_departure(self):
        with freeze_time('2025-04-01'):
            departure = self.env['hr.employee.departure'].create([{
                'employee_id': self.emp_A.id,
                'departure_date': date(2025, 6, 1),
                'departure_reason_id': self.env.ref('hr.departure_fired').id,
                'departure_description': "Didn't bring coffee",
                'do_archive_employee': True,
                'do_set_date_end': True,
            }])
            self.assertTrue(departure.has_selected_actions)
            self.assertFalse(departure.apply_immediately)
            with self.assertRaises(ValidationError):
                departure.action_register()
            self.assertFalse(departure.apply_date, "The departure shouldn't be applied yet.")

        with freeze_time('2025-06-01'):
            departure.action_register()
            self.assertEqual(departure.apply_date, date.today(), "The departure should have been applied.")
            self.assertFalse(self.emp_A.active, "The employee should have been archived.")
            self.assertEqual(
                self.emp_A.contract_date_end,
                date(2025, 6, 1),
                "The employee should have a contract date end.")

    @freeze_time('2025-06-01')
    def test_departure_wizard(self):
        """ Test the archiving wizard in the case of multiple employees """
        archiving_employees = [employee.id for employee in (self.emp_A, self.emp_C)]
        wizard = self.env['hr.departure.wizard'].with_context(active_ids=archiving_employees).create({})
        wizard.action_register_departure()

        all_employees = self.emp_A | self.emp_B | self.emp_C
        self.assertEqual(all_employees.filtered(lambda e: e.active), self.emp_B, "Employees A and C should have been archived")
