# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from freezegun import freeze_time

from odoo.exceptions import ValidationError

from odoo.addons.hr.tests.common import TestHrCommon


class TestDeparture(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        cls.test_company = cls.env['res.company'].create({
            'name': "Easy Departure SA",
            'country_id': cls.env.ref('base.vc').id,
        })

        with freeze_time('2025-01-01'):
            cls.emp_boss = cls.env['hr.employee'].create({
                'name': "Nice boss",
                'company_id': cls.test_company.id,
                'contract_date_start': date.today(),
            })

            cls.emp = cls.env['hr.employee'].create({
                'name': "Hard-working employee",
                'company_id': cls.test_company.id,
                'parent_id': cls.emp_boss.id,
                'contract_date_start': date.today(),
                'contract_date_end': False,
            })

    def test_future_departure(self):
        cron = self.env.ref('hr.ir_cron_apply_departure')

        with freeze_time('2025-04-01'):
            departure = self.env['hr.employee.departure'].create([{
                'employee_id': self.emp.id,
                'departure_date': date(2025, 6, 30),
                'departure_reason_id': self.env.ref('hr.departure_fired'),
                'departure_description': "Didn't bring coffee",
                'do_archive_employee': True,
                'do_set_date_end': True,
            }])
            self.assertTrue(departure.has_selected_actions)
            self.assertFalse(departure.apply_immediately)
            with self.assertRaises(ValidationError):
                departure.action_register()
            departure.action_schedule()
            cron.method_direct_trigger()
            self.assertEqual(departure.state, 'scheduled', "The departure shouldn't be applied yet.")

        with freeze_time('2025-06-01'):
            cron.method_direct_trigger()
            self.assertEqual(departure.state, 'done', "The departure should have been applied.")
            self.assertFalse(self.emp.active, "The employee should have been archived.")
            self.assertEqual(self.emp.contract_date_end, date(2025, 6, 1), "The employee should have a contract date end.")

    def test_immediate_departure(self):
        with freeze_time('2025-06-01'):
            departure = self.env['hr.employee.departure'].create([{
                'employee_id': self.emp.id,
                'departure_date': date(2025, 6, 30),
                'departure_reason_id': self.env.ref('hr.departure_fired'),
                'departure_description': "Didn't bring coffee",
            }])
            self.assertTrue(departure.apply_immediately)
            departure.action_register()
            self.assertEqual(departure.state, 'done', "The departure should have been applied.")
