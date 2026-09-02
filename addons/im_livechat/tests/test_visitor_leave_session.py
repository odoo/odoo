# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestVisitorLeaveSession(HttpCase):
    def test_leave_session_without_guest_context(self):
        """Leaving a livechat session while the visitor's guest context is no
        longer available (e.g. the ``dgid`` cookie expired, was cleared, or is
        blocked as a third-party cookie) must not raise.

        In that situation the ``is_self`` member lookup returns an empty
        recordset; the route must not call ``_rtc_leave_call`` on it (which
        asserts a singleton) and must still close the livechat session.
        """
        self.authenticate(None, None)
        operator = self.env["res.users"].create({"name": "Operator", "login": "operator_leave"})
        self.env["bus.presence"].create({"user_id": operator.id, "status": "online"})
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Test Leave Channel", "user_ids": [operator.id]}
        )
        channel_info = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {"anonymous_name": "Visitor", "channel_id": livechat_channel.id, "persisted": True},
        )
        channel = self.env["discuss.channel"].browse(channel_info["id"])
        self.assertTrue(channel.livechat_active)
        # Simulate the loss of the guest context: drop the guest cookie so the
        # next request cannot resolve the current guest, leaving the member
        # lookup empty.
        self.opener.cookies.pop("dgid", None)
        # Must not raise "Expected singleton: discuss.channel.member()".
        self.make_jsonrpc_request(
            "/im_livechat/visitor_leave_session", {"uuid": channel_info["uuid"]}
        )
        # The session must still be closed even though there was no member to
        # leave the RTC call for.
        self.assertFalse(channel.livechat_active)
