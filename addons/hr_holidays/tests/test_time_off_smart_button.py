from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged("post_install", "-at_install")
class TestTimeOffSmartButton(TestHrHolidaysCommon):
    """The Time Off smart button on an employee form.

    It is the officer's way into one employee's time off, so what it opens has
    to be about *that* employee: the record it prepares when the officer hits
    New, and the group-wide affordances that make no sense once the action is
    already scoped to a single person.
    """

    def test_smart_button_prefills_the_employee_of_the_form(self):
        action = self.employee_emp.action_time_off_dashboard()

        leave = (
            self.env["hr.leave"]
            .with_user(self.user_hrmanager)
            .with_context(**action["context"])
            .new({})
        )
        self.assertEqual(
            leave.employee_id,
            self.employee_emp,
            "opening the Time Off smart button of an employee and creating a "
            "request must prepare it for that employee, not for the officer "
            "who is looking at the form",
        )

    def test_smart_button_offers_more_than_a_calendar(self):
        action = self.employee_emp.action_time_off_dashboard()

        self.assertEqual(action["view_mode"], "calendar,list,form")
        view_types = [view_type for _view_id, view_type in action["views"]]
        self.assertEqual(view_types, ["calendar", "list", "form"])
