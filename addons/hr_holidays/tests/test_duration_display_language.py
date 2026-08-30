from odoo import Command
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install")
class TestDurationDisplayLanguage(TestHrHolidaysCommon):
    """`duration_display` is built with translated unit words.

    While it was stored, the string kept the language of whoever last triggered
    the compute -- and models/resource.py re-queues that compute from a public
    holiday write, so the person who fixes the company calendar decides what
    language every affected employee reads their own request in.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("es_ES")
        cls.env["ir.module.module"]._load_module_terms(["hr_holidays"], ["es_ES"])
        cls.user_employee.lang = "es_ES"
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Sick Leave (days)",
                "request_unit": "day",
                "leave_validation_type": "hr",
                "requires_allocation": False,
            }
        )

    def _spanish_leave(self):
        return (
            self.env["hr.leave"]
            .with_user(self.user_employee)
            .create(
                {
                    "name": "Baja",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": "2021-11-15",
                    "request_date_to": "2021-11-17",
                }
            )
        )

    def test_duration_display_is_translated_for_the_reader(self):
        leave = self._spanish_leave()
        self.assertEqual(leave.duration_display, "3 días")

    def test_a_public_holiday_added_in_another_language_does_not_translate_the_leave(
        self,
    ):
        leave = self._spanish_leave()
        self.assertEqual(leave.duration_display, "3 días")

        # Somebody else -- an admin working in English -- fixes the company
        # calendar.  This re-triggers the leave's duration compute.
        english_env = self.env(context={**self.env.context, "lang": "en_US"})
        english_env["resource.calendar"].browse(
            self.employee_emp.resource_calendar_id.id
        ).global_leave_ids = [
            Command.create(
                {
                    "name": "Autumn Holidays",
                    "date_from": "2021-11-16 00:00:00",
                    "date_to": "2021-11-16 23:59:59",
                    "time_type": "leave",
                }
            )
        ]
        # Their request ends here: whatever the recompute produced is now on
        # disk.  The employee reads it afterwards, in a later request.
        english_env.flush_all()
        leave.invalidate_recordset()

        self.assertEqual(
            leave.duration_display,
            "2 días",
            "the employee reads their own request in their own language, "
            "whatever language the person who edited the calendar was using",
        )
