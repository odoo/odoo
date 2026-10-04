from freezegun import freeze_time

from odoo.tests.common import TransactionCase


class TestTodayLocation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        main_partner_id = cls.env.ref('base.main_partner')
        house_partner_id = cls.env['res.partner'].create({
            'name': 'My House',
            'is_company': False,
            'street': 'example address 1',
            'city': 'city',
            'zip': '0001',
        })

        cls.default_location = cls.env['hr.work.location'].create({
            'name': 'Main Office',
            'location_type': "office",
            'address_id': main_partner_id.id,
        })
        cls.monday_location = cls.env['hr.work.location'].create({
            'name': 'Home Office (Monday)',
            'location_type': 'home',
            'address_id': house_partner_id.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test User',
            'work_location_id': cls.default_location.id,
            'monday_location_id': cls.monday_location.id,
        })

    @freeze_time('2026-09-21')
    def test_01_monday_specific_location(self):
        """ Test that on a Monday, the employee gets their specific Monday location """
        self.employee._compute_today_actual_location()

        self.assertEqual(
            self.employee.today_location_id,
            self.monday_location,
            "On Monday, the location should be the designated Monday location.",
        )

    @freeze_time('2026-09-22')  # 2026-09-22 is a Tuesday
    def test_02_tuesday_fallback_location(self):
        """ Test that on a Tuesday (where no location is set), it falls back to default """
        self.employee._compute_today_actual_location()
        self.assertEqual(
            self.employee.today_location_id,
            self.default_location,
            "On Tuesday (unset), the location should fall back to the default work location.",
        )

    @freeze_time('2026-09-23')  # 2026-09-23 is a Wednesday
    def test_03_cron_job_execution(self):
        """ Test that the cron method executes without errors and updates the field """
        # We start by forcing a known bad state to ensure the cron actually fixes it
        self.employee.today_location_id = self.monday_location

        # Execute the cron job method just like the Odoo scheduler would
        self.env['hr.employee']._cron_update_today_location()

        self.assertEqual(
            self.employee.today_location_id,
            self.default_location,
            "The cron job failed to update the stored location for Wednesday.",
        )
