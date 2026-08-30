from datetime import date

from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon

# 01:00 UTC on Tuesday the 15th is 19:00 on Monday the 14th in Mexico: the same
# instant, two different calendar days. Everything a user reads as "a date"
# has to land on the 14th.
UTC_NIGHT = "2026-09-15 01:00:00"
LOCAL_DAY = date(2026, 9, 14)


@tagged("post_install", "-at_install")
class TestUserLocalDates(TestHrHolidaysCommon):
    """Date-only values belong to the user's calendar, not to UTC.

    Our deployment sits at UTC-6, so between 18:00 and midnight every single
    day the server's date is already tomorrow. Anything that asks "what day is
    it" on the user's behalf has to ask in the user's timezone.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee.tz = "America/Mexico_City"
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "request_unit": "day",
                "leave_validation_type": "hr",
                "requires_allocation": False,
            }
        )

    @freeze_time(UTC_NIGHT)
    def test_new_request_defaults_to_the_users_today(self):
        defaults = (
            self.env["hr.leave"]
            .with_user(self.user_employee)
            .default_get(["request_date_from", "request_date_to"])
        )
        self.assertEqual(defaults["request_date_from"], LOCAL_DAY)
        self.assertEqual(defaults["request_date_to"], LOCAL_DAY)

    @freeze_time(UTC_NIGHT)
    def test_todays_own_leave_is_not_in_the_past_yet(self):
        leave = (
            self.env["hr.leave"]
            .with_user(self.user_employee)
            .create(
                {
                    "name": "Day off",
                    "employee_id": self.employee_emp_id,
                    "holiday_status_id": self.leave_type.id,
                    "request_date_from": LOCAL_DAY,
                    "request_date_to": LOCAL_DAY,
                }
            )
        )
        leave.sudo().state = "validate"

        next_states = leave._get_next_states_by_state()
        self.assertIn(
            "cancel",
            next_states["validate"],
            "an employee whose time off starts today can still cancel it at "
            "19:00 local, even though the server clock already says tomorrow",
        )

        # And the cancel has to actually go through: write() asks the same
        # "has it begun?" question a second time, on its own.
        leave._action_user_cancel("changed my mind")
        self.assertEqual(leave.state, "cancel")
