# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase


class TestCalendarWeekendDays(TransactionCase):

    def test_default_and_company_settings(self):
        company = self.env['res.company'].create({'name': "Friday weekend"})
        other_company = self.env['res.company'].create({'name': "Default weekend"})
        self.assertEqual(company.calendar_weekend_days, [0, 6])
        settings = self.env['res.config.settings'].create({'company_id': company.id})
        checkboxes = settings.calendar_weekend_days_checkboxes
        self.assertEqual([key for key, value in checkboxes.items() if value['checked']], ['6', '0'])
        settings.calendar_weekend_days_checkboxes = {
            key: {**value, 'checked': key == '5'} for key, value in checkboxes.items()
        }
        self.assertEqual(company.calendar_weekend_days, [5])
        self.assertEqual(other_company.calendar_weekend_days, [0, 6])
        settings.company_id = other_company
        self.assertFalse(settings.calendar_weekend_days_checkboxes['5']['checked'])
        self.assertTrue(settings.calendar_weekend_days_checkboxes['6']['checked'])
        self.assertTrue(settings.calendar_weekend_days_checkboxes['0']['checked'])

    def test_no_weekend_days(self):
        company = self.env['res.company'].create({'name': "No weekends", 'calendar_weekend_days': []})
        settings = self.env['res.config.settings'].create({'company_id': company.id})
        self.assertFalse(any(value['checked'] for value in settings.calendar_weekend_days_checkboxes.values()))

    def test_invalid_weekend_days(self):
        for days in ([0, 1, 2, 3, 4, 5, 6], [7], [-1], [5, 5], ['5'], [True], {'5': True}):
            with self.subTest(days=days), self.assertRaises(ValidationError), self.env.cr.savepoint():
                self.env.company.calendar_weekend_days = days
