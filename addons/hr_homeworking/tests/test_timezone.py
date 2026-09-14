from freezegun import freeze_time

from odoo.tests import tagged

from .common import HomeworkingCase
from odoo.addons.hr_homeworking.models.hr_homeworking import DAYS


@tagged("post_install", "-at_install")
class TestTodayIsTheEmployeesOwn(HomeworkingCase):
    """A weekday work location is keyed to the employee's day, not the host's.

    2026-09-14 20:36 UTC is Monday in Mexico City, where this host runs, and
    already Tuesday in Tokyo. Resolving "today" from the server's clock gives a
    Tokyo employee their Monday location for the last nine hours of every day.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tokyo = cls.env["hr.employee"].create(
            {
                "name": "Tokyo worker",
                "tz": "Asia/Tokyo",
                "monday_location_id": cls.work_home.id,
                "tuesday_location_id": cls.work_office_1.id,
            }
        )
        cls.mexico = cls.env["hr.employee"].create(
            {
                "name": "Mexico worker",
                "tz": "America/Mexico_City",
                "monday_location_id": cls.work_home.id,
                "tuesday_location_id": cls.work_office_1.id,
            }
        )

    @freeze_time("2026-09-14 20:36:00")
    def test_two_employees_in_one_batch_get_their_own_weekday(self):
        # Monday 14:36 in Mexico City, Tuesday 05:36 in Tokyo.
        self.assertEqual(self.mexico.work_location_name, "Home")
        self.assertEqual(self.tokyo.work_location_name, "Office 1")

    @freeze_time("2026-09-14 20:36:00")
    def test_the_presence_icon_follows_the_employees_own_weekday(self):
        self.assertEqual(self.mexico.hr_icon_display, "presence_home")
        self.assertEqual(self.tokyo.hr_icon_display, "presence_office")

    @freeze_time("2026-09-14 05:00:00")
    def test_before_the_split_both_are_on_the_same_weekday(self):
        # Monday 05:00 UTC: Sunday 23:00 in Mexico City, Monday 14:00 in Tokyo.
        self.assertEqual(self.tokyo.work_location_name, "Home")
        self.assertFalse(self.mexico.work_location_name)

    @freeze_time("2026-09-14 20:36:00")
    def test_an_exception_is_matched_against_the_employees_own_date(self):
        self.set_exception("2026-09-15", self.work_office_2, employee=self.tokyo)
        self.set_exception("2026-09-15", self.work_office_2, employee=self.mexico)
        # The 15th is today in Tokyo and tomorrow in Mexico City.
        self.assertEqual(self.tokyo.work_location_name, "Office 2")
        self.assertEqual(self.mexico.work_location_name, "Home")

    @freeze_time("2026-09-14 20:36:00")
    def test_the_whole_batch_still_resolves_in_one_query(self):
        employees = self.tokyo | self.mexico | self.employee
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertQueryCount(__system__=8):
            employees.mapped("work_location_name")

    def test_the_view_column_follows_the_reader(self):
        Employee = self.env["hr.employee"]
        with freeze_time("2026-09-14 20:36:00"):
            reader_in_tokyo = Employee.with_context(tz="Asia/Tokyo")
            reader_in_mexico = Employee.with_context(tz="America/Mexico_City")
            self.assertEqual(reader_in_tokyo._get_current_day_location_field(), DAYS[1])
            self.assertEqual(
                reader_in_mexico._get_current_day_location_field(), DAYS[0]
            )
