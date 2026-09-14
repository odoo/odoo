from freezegun import freeze_time

from odoo.tests import tagged

from .common import HomeworkingCase


@tagged("post_install", "-at_install")
class TestEmployeeWorkLocation(HomeworkingCase):
    @freeze_time("2025-07-13")
    def test_a_day_without_a_location_reports_none(self):
        self.assertFalse(self.employee.work_location_name)
        self.assertFalse(self.employee.work_location_type)

    @freeze_time("2025-07-08")
    def test_the_weekly_location_of_the_day_is_the_work_location(self):
        self.assertEqual(self.employee.work_location_name, "Office 1")
        self.assertEqual(self.employee.work_location_type, "office")

    @freeze_time("2025-07-09")
    def test_an_exception_created_today_takes_effect_without_a_manual_recompute(self):
        self.assertEqual(self.employee.work_location_name, "Home")

        self.set_exception("2025-07-09", self.work_office_1)

        self.assertEqual(self.employee.work_location_name, "Office 1")
        self.assertEqual(self.employee.work_location_type, "office")
        self.assertEqual(self.employee.hr_icon_display, "presence_office")

    @freeze_time("2025-07-09")
    def test_deleting_an_exception_restores_the_weekly_location(self):
        exception = self.set_exception("2025-07-09", self.work_office_1)
        self.assertEqual(self.employee.work_location_name, "Office 1")

        exception.unlink()

        self.assertEqual(self.employee.work_location_name, "Home")
        self.assertEqual(self.employee.work_location_type, "home")

    @freeze_time("2025-07-09")
    def test_repointing_an_exception_takes_effect(self):
        exception = self.set_exception("2025-07-09", self.work_office_1)
        self.assertEqual(self.employee.work_location_name, "Office 1")

        exception.work_location_id = self.work_office_2

        self.assertEqual(self.employee.work_location_name, "Office 2")

    @freeze_time("2025-07-09")
    def test_an_exception_on_another_day_does_not_apply(self):
        self.set_exception("2025-07-10", self.work_office_1)
        self.assertEqual(self.employee.work_location_name, "Home")

    @freeze_time("2025-07-09")
    def test_changing_the_weekly_location_takes_effect(self):
        self.assertEqual(self.employee.work_location_name, "Home")
        self.employee.wednesday_location_id = self.work_office_1
        self.assertEqual(self.employee.work_location_name, "Office 1")
        self.assertEqual(self.employee.work_location_type, "office")

    @freeze_time("2025-07-09")
    def test_an_archived_employee_keeps_the_base_presence_icon(self):
        self.assertEqual(self.employee.hr_icon_display, "presence_home")

        self.employee.action_archive()

        self.assertEqual(self.employee.hr_presence_state, "archive")
        self.assertEqual(self.employee.hr_icon_display, "presence_archive")

    @freeze_time("2025-07-09")
    def test_the_exceptional_location_is_resolved_in_one_query(self):
        employees = self.env["hr.employee"].create(
            [
                {"name": f"Batch {index}", "wednesday_location_id": self.work_home.id}
                for index in range(20)
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        with self.assertQueryCount(__system__=6):
            employees.mapped("work_location_name")
