from freezegun import freeze_time

from odoo.tests import tagged

from .common import HomeworkingCase


@tagged("post_install", "-at_install")
class TestLocatedImStatus(HomeworkingCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {"name": "Located user", "login": "located_user"}
        )
        cls.employee.user_id = cls.user

    def _statuses(self):
        self.env.invalidate_all()
        return self.user.im_status, self.user.partner_id.im_status

    @freeze_time("2025-07-09")
    def test_the_user_and_the_partner_spell_the_located_status_the_same_way(self):
        user_status, partner_status = self._statuses()
        self.assertEqual(user_status, "home_offline")
        self.assertEqual(partner_status, "home_offline")

    @freeze_time("2025-07-13")
    def test_a_day_without_a_location_leaves_the_status_alone(self):
        user_status, partner_status = self._statuses()
        self.assertEqual(user_status, "offline")
        self.assertEqual(partner_status, "offline")

    @freeze_time("2025-07-09")
    def test_an_exceptional_location_reaches_the_chat_status(self):
        self.set_exception("2025-07-09", self.work_office_1)
        user_status, partner_status = self._statuses()
        self.assertEqual(user_status, "office_offline")
        self.assertEqual(partner_status, "office_offline")

    @freeze_time("2025-07-09")
    def test_a_user_without_an_employee_keeps_a_plain_status(self):
        outsider = self.env["res.users"].create(
            {"name": "Outsider", "login": "outsider_user"}
        )
        self.env.invalidate_all()
        self.assertEqual(outsider.im_status, "offline")
        self.assertEqual(outsider.partner_id.im_status, "offline")
