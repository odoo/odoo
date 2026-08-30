from datetime import date, datetime

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install")
class TestLoadPublicHolidays(TestHrHolidaysCommon):
    """Loading the official Mexican holidays instead of typing them yearly."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create(
            {
                "name": "Compania Mexicana",
                "country_id": cls.env.ref("base.mx").id,
            }
        )
        cls.company.resource_calendar_id.tz = "America/Mexico_City"
        cls.wizard_model = cls.env["load.public.holiday.wizard"].with_context(
            allowed_company_ids=cls.company.ids
        )

    def _public_holidays(self, year):
        return self.env["resource.schedule.exception"].search(
            [
                ("company_id", "=", self.company.id),
                ("resource_id", "=", False),
                ("date_from", ">=", datetime(year - 1, 12, 31)),
                ("date_to", "<=", datetime(year + 1, 1, 2)),
            ]
        )

    def test_the_list_view_offers_the_loader(self):
        action = self.env["resource.schedule.exception"].load_public_holidays()
        self.assertEqual(action["res_model"], "load.public.holiday.wizard")
        self.assertEqual(action["target"], "new")

    def test_the_wizard_previews_the_year_without_creating_anything(self):
        before = self._public_holidays(2026)

        wizard = self.wizard_model.create({"year": 2026})

        self.assertEqual(len(wizard.line_ids), 10)
        self.assertTrue(
            wizard.line_ids.filtered(
                lambda line: (
                    line.start_date == date(2026, 9, 16)
                    and line.name == "Día de la Independencia"
                )
            ),
            "Independence Day has to come out of the Mexican data file, named "
            "the way the employees reading the calendar will name it",
        )
        self.assertEqual(
            self._public_holidays(2026),
            before,
            "previewing must not write anything yet",
        )

    def test_confirming_creates_the_holidays_once(self):
        wizard = self.wizard_model.create({"year": 2026})
        expected = len(wizard.line_ids)
        before = self._public_holidays(2026)

        wizard.action_add_public_holidays()

        created = self._public_holidays(2026) - before
        self.assertEqual(len(created), expected)
        self.assertTrue(created.filtered(lambda leave: leave.name == "Navidad"))

        # A second pass must not duplicate them.
        again = self.wizard_model.create({"year": 2026})
        self.assertFalse(again.line_ids)
        self.assertIn("2026", again.warning_message)

    def test_holidays_span_the_company_local_day(self):
        wizard = self.wizard_model.create({"year": 2026})
        wizard.action_add_public_holidays()

        christmas = self._public_holidays(2026).filtered(
            lambda leave: leave.name == "Navidad"
        )
        # Mexico City is UTC-6, so a full local day starts at 06:00 UTC.
        self.assertEqual(christmas.date_from, datetime(2026, 12, 25, 6, 0, 0))
        self.assertEqual(christmas.date_to, datetime(2026, 12, 26, 5, 59, 59))

    def test_a_company_without_data_says_so(self):
        self.company.country_id = self.env.ref("base.be")
        wizard = self.wizard_model.create({"year": 2026})
        self.assertFalse(wizard.line_ids)
        self.assertIn("2026", wizard.warning_message)
