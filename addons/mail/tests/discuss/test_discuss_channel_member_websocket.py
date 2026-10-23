# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user


class TestDiscussChannelMemberWebsocket(MailCommon, WebsocketCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_user = mail_new_test_user(cls.env, login="alice_user", name="Alice")
        cls.channel = cls.env["discuss.channel"]._create_channel(name="General", group_id=None)

    def _connect_alice(self):
        self._reset_bus()
        session = self.authenticate(self.alice_user.login, self.alice_user.password)
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id())
        return websocket

    def _assert_receives_no_channel_row(self, websocket):
        self.alice_user._bus_send("change_done", None)
        self.trigger_notification_dispatching()
        self._recv_types_until(websocket, "change_done")
        self.channel._bus_send("channel_row", None)
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        types = self._recv_types_until(websocket, "alice_row")
        self.alice_user._bus_send("alice_last_row", None)
        self.trigger_notification_dispatching()
        types += self._recv_types_until(websocket, "alice_last_row")
        self.assertEqual(sorted(types), ["alice_last_row", "alice_row"])

    def test_invited_member_receives_channel_rows(self):
        websocket = self._connect_alice()
        self.channel.with_user(self.user_employee)._add_members(users=self.alice_user)
        self.channel._bus_send("channel_row", None)
        self._commit_and_wait_for_subscribe()
        self.assertIn("channel_row", self._recv_types_until(websocket, "channel_row"))

    def test_left_member_receives_no_channel_rows(self):
        self.channel._add_members(users=self.alice_user)
        websocket = self._connect_alice()
        self.channel.with_user(self.alice_user).action_unfollow()
        self._commit_and_wait_for_subscribe()
        self._assert_receives_no_channel_row(websocket)

    def test_removed_member_receives_no_channel_rows(self):
        self.channel._add_members(users=self.alice_user)
        websocket = self._connect_alice()
        self.channel.channel_member_ids.filtered(
            lambda m: m.partner_id == self.alice_user.partner_id,
        ).with_user(self.user_admin).unlink()
        self._commit_and_wait_for_subscribe()
        self._assert_receives_no_channel_row(websocket)

    def test_guest_joined_through_invite_link_receives_channel_rows(self):
        guest = self.env["mail.guest"].create({"name": "Guest"})
        self._reset_bus()
        websocket = self.websocket_connect()
        self.subscribe(
            websocket,
            [f"mail.guest_{guest._format_auth_cookie()}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
        with self._wait_for_subscribe():
            self.url_open(f"/chat/{self.channel.id}/{self.channel.uuid}").raise_for_status()
        self.assertIn(guest, self.channel.channel_member_ids.guest_id)
        self.channel._bus_send("channel_row", None)
        self.trigger_notification_dispatching()
        self.assertIn("channel_row", self._recv_types_until(websocket, "channel_row"))

    def test_viewer_losing_access_receives_no_channel_rows(self):
        group = self.env["res.groups"].create({"name": "Sales"})
        self._reset_bus()
        session = self.authenticate(self.alice_user.login, self.alice_user.password)
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(
            websocket,
            [f"discuss.channel_{self.channel.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        self.channel.with_user(self.user_admin).group_public_id = group
        self._commit_and_wait_for_subscribe()
        self._assert_receives_no_channel_row(websocket)
