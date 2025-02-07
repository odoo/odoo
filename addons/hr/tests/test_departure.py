# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time

from .common import TestHrCommon


class TestDeparture(TestHrCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.employee_wario = cls.env['hr.employee'].create({
            'name': 'Wario',
        })
        cls.departure_reason = cls.env.ref('hr.departure_fired')

    def test_employee_departure(self):
        emp = self.employee_wario

        with freeze_time('2025-02-01'):
            act = emp.action_new_departure()
            wizard = self.env['hr.employee.departure.wizard'].with_context(act['context']).create({})
            wizard.departure_reason_id = self.departure_reason.id
            wizard.departure_description = "Couldn't stop screaming WAAAAAAAH! in the office."
            wizard.departure_date = date(2025, 2, 4)
            wizard.action_at = 'other'
            wizard.action_other_date = date(2025, 2, 7)
            wizard.action_register_departure()

            self.assertTrue(emp.active, "Wario should not have been archived yet.")
            self.assertEqual(emp.departure_reason_id, self.departure_reason)
            self.assertTrue(emp.departure_description)
            self.assertEqual(emp.departure_date, date(2025, 2, 4))
            self.assertTrue(emp.departure_do_archive)
            self.assertEqual(emp.departure_action_at, 'other')
            self.assertEqual(emp.departure_action_other_date, date(2025, 2, 7))
            self.assertEqual(emp.departure_apply_date, date(2025, 2, 7))
            self.assertFalse(emp.departure_applied)

        with freeze_time('2025-02-05'):
            self.env['hr.employee']._cron_apply_departure()

            self.assertTrue(emp.active, "Wario should not have been archived yet.")
            self.assertFalse(emp.departure_applied)

        with freeze_time('2025-02-07'):
            self.env['hr.employee']._cron_apply_departure()

            self.assertFalse(emp.active, "Wario should have been archived.")
            self.assertTrue(emp.departure_applied)

        with freeze_time('2025-02-10'):
            emp.action_unarchive()
            explanation = "The departure values should be reset using the manual unarchive action."

            self.assertTrue(emp.active, "Wario should have been unarchived.")
            self.assertFalse(emp.departure_reason_id, explanation)
            self.assertFalse(emp.departure_description, explanation)
            self.assertFalse(emp.departure_date, explanation)
            self.assertFalse(emp.departure_action_other_date, explanation)
            self.assertFalse(emp.departure_apply_date, explanation)
            self.assertFalse(emp.departure_applied, explanation)

            emp.action_archive()
            explanation = "The departure values shouldn't be affected using the manual archive action."

            self.assertFalse(emp.active, "Wario should have been archived.")
            self.assertFalse(emp.departure_reason_id, explanation)
            self.assertFalse(emp.departure_description, explanation)
            self.assertFalse(emp.departure_date, explanation)
            self.assertFalse(emp.departure_action_other_date, explanation)
            self.assertFalse(emp.departure_apply_date, explanation)
            self.assertFalse(emp.departure_applied, explanation)

    def test_employee_departure_immediately(self):
        emp = self.employee_wario

        with freeze_time('2025-02-01'):
            act = emp.action_new_departure()
            wizard = self.env['hr.employee.departure.wizard'].with_context(act['context']).create({})
            wizard.departure_reason_id = self.departure_reason.id
            wizard.departure_description = "The employee couldn't stop screaming WAAAAAAAH! in the office."
            wizard.departure_date = date(2025, 2, 1)
            wizard.action_register_departure()

        self.assertFalse(emp.active, "Wario should have been archived.")
        self.assertEqual(emp.departure_reason_id, self.departure_reason)
        self.assertTrue(emp.departure_description)
        self.assertEqual(emp.departure_date, date(2025, 2, 1))
        self.assertTrue(emp.departure_do_archive)
        self.assertEqual(emp.departure_action_at, 'departure_date')
        self.assertTrue(emp.departure_applied)
