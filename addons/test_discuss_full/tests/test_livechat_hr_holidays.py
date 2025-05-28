# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests.common import HttpCase, tagged
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestLivechatHrHolidays(HttpCase, MailCommon):
    """Tests for bridge between im_livechat and hr_holidays modules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["mail.presence"]._update_presence(cls.user_employee)
        leave_type = cls.env["hr.leave.type"].create(
            {"name": "Legal Leaves", "requires_allocation": False, "time_type": "leave"}
        )
        employee = cls.env["hr.employee"].create({"user_id": cls.user_employee.id})
        cls.env["hr.leave"].with_context(leave_skip_state_check=True).create(
            {
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": fields.Datetime.today() + relativedelta(days=-2),
                "request_date_to": fields.Datetime.today() + relativedelta(days=2),
                "state": "validate",
            }
        )

    def test_operator_available_on_leave(self):
        """Test operator is available on leave when they are online."""
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "support", "user_ids": [Command.link(self.user_employee.id)]}
        )
        self.assertEqual(self.user_employee.im_status, "leave_online")
        self.assertEqual(livechat_channel.available_operator_ids, self.user_employee)

    def test_operator_limit_on_leave(self):
        """Test livechat limit is correctly applied when operator is on leave and online."""
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "max_sessions_mode": "limited",
                "max_sessions": 1,
                "name": "support",
                "user_ids": [Command.link(self.user_employee.id)],
            }
        )
        self.make_jsonrpc_request("/im_livechat/get_session", {"channel_id": livechat_channel.id})
        self.assertEqual(self.user_employee.im_status, "leave_online")
        self.assertFalse(livechat_channel.available_operator_ids)
