from datetime import date

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.fields import Date
from odoo.tests import tagged

from .common import HomeworkingCase
from odoo.addons.hr_homeworking.models.hr_homeworking import DAYS


@tagged("post_install", "-at_install")
class TestWorkLocationDelete(HomeworkingCase):
    @freeze_time("2026-09-14 20:36:00")
    def test_the_current_day_field_is_one_of_the_seven(self):
        # Frozen so the two clock reads cannot straddle a rollover, and against
        # the READER's today rather than the host's -- those disagree for six
        # hours a day on this server, so `Date.today()` here would be wrong as
        # well as racy.
        Employee = self.env["hr.employee"]
        field = Employee._get_current_day_location_field()
        self.assertIn(field, DAYS)
        self.assertEqual(field, DAYS[Date.context_today(Employee).weekday()])

    def test_an_unused_location_can_be_deleted(self):
        spare = self.env["hr.work.location"].create(
            {"name": "Spare", "location_type": "other", "address_id": self.address.id}
        )
        spare.unlink()
        self.assertFalse(spare.exists())

    def test_a_location_used_on_a_weekday_cannot_be_deleted(self):
        with self.assertRaises(UserError):
            self.work_home.unlink()

    def test_the_refusal_names_the_blocking_location(self):
        with self.assertRaises(UserError) as error:
            (self.work_home | self.work_office_1).unlink()
        message = str(error.exception)
        self.assertIn("Home", message)
        self.assertIn("Office 1", message)

    def test_a_location_used_by_an_archived_employee_cannot_be_deleted(self):
        spare = self.env["hr.work.location"].create(
            {"name": "Spare", "location_type": "other", "address_id": self.address.id}
        )
        archived = self.env["hr.employee"].create(
            {"name": "Archived", "monday_location_id": spare.id}
        )
        archived.action_archive()
        self.assertFalse(archived.active)

        with self.assertRaises(UserError):
            spare.unlink()

        self.assertEqual(archived.monday_location_id, spare)

    def test_a_location_used_in_another_company_cannot_be_deleted(self):
        other_company = self.env["res.company"].create({"name": "Other Co"})
        spare = self.env["hr.work.location"].create(
            {
                "name": "Spare",
                "location_type": "other",
                "address_id": self.address.id,
                "company_id": other_company.id,
            }
        )
        elsewhere = self.env["hr.employee"].create(
            {
                "name": "Elsewhere",
                "company_id": other_company.id,
                "monday_location_id": spare.id,
            }
        )
        manager = self.env["res.users"].create(
            {
                "name": "Single company manager",
                "login": "single_company_hr_manager",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, self.env.company.ids)],
                "group_ids": [(4, self.env.ref("hr.group_hr_manager").id)],
            }
        )

        with self.assertRaises(UserError):
            spare.with_user(manager).unlink()

        self.assertEqual(elsewhere.monday_location_id, spare)

    def test_deleting_a_location_cascades_the_exceptions_that_use_it(self):
        spare = self.env["hr.work.location"].create(
            {"name": "Spare", "location_type": "other", "address_id": self.address.id}
        )
        exception = self.set_exception(date(2025, 7, 9), spare)

        spare.unlink()

        self.assertFalse(spare.exists())
        self.assertFalse(exception.exists())
