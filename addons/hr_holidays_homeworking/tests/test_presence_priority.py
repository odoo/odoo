from freezegun import freeze_time

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLeaveBeatsWorkLocation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.home = cls.env["hr.work.location"].create(
            {
                "name": "Home",
                "location_type": "home",
                "address_id": cls.env.ref("base.main_partner").id,
            }
        )
        cls.user = cls.env["res.users"].create(
            {"name": "On leave at home", "login": "leave_at_home"}
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "On leave at home",
                "user_id": cls.user.id,
                "wednesday_location_id": cls.home.id,
            }
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Unpaid",
                "requires_allocation": False,
                "request_unit": "day",
            }
        )

    def _take_leave(self, day):
        leave = self.env["hr.leave"].create(
            {
                "holiday_status_id": self.leave_type.id,
                "employee_id": self.employee.id,
                "request_date_from": day,
                "request_date_to": day,
            }
        )
        leave.action_approve()
        return leave

    @freeze_time("2025-07-09 12:00:00")
    def test_without_a_leave_the_work_location_decides_the_icon(self):
        self.assertEqual(self.employee.hr_icon_display, "presence_home")

    @freeze_time("2025-07-09 12:00:00")
    def test_a_leave_outranks_the_work_location_on_the_employee_icon(self):
        self._take_leave("2025-07-09")
        self.env.invalidate_all()
        self.assertTrue(self.employee.is_absent)
        self.assertEqual(self.employee.hr_icon_display, "presence_holiday_absent")

    @freeze_time("2025-07-09 12:00:00")
    def test_a_leave_outranks_the_work_location_on_the_chat_status(self):
        self._take_leave("2025-07-09")
        self.env.invalidate_all()
        self.assertEqual(self.user.im_status, "leave_offline")
        self.assertEqual(self.user.partner_id.im_status, "leave_offline")
