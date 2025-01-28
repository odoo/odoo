from datetime import date

from odoo.tests.common import TransactionCase


class TestExternalAPI(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.calendar_40h = cls.env['resource.calendar'].create({'name': 'Default calendar'})
        cls.calendar_fixed_40h = cls.env['resource.calendar'].create({
            'name': 'Fixed calendar',
            'schedule_type': 'fixed_time',
            'monday': True,
            'tuesday': True,
            'wednesday': True,
            'thursday': True,
            'friday': True,
        })

    def test_works_on_date(self):
        tets_date = date(2025, 1, 1)
        self.assertTrue(self.calendar_fixed_40h._works_on_date(tets_date))
