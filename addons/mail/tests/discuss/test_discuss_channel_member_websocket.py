# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import new_test_user

from odoo.addons.bus.bus_dispatcher import dispatch
from odoo.addons.bus.tests.common import WebsocketCase


class TestDiscussChannelMemberWebsocket(WebsocketCase):
    """The open websockets of a member follow its membership without subscribing again."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_user = new_test_user(cls.env, login="alice_user", password="Password!1")
        cls.portal_user = new_test_user(
            cls.env, login="portal_user", password="Password!1", groups="base.group_portal",
        )
        cls.channel = cls.env["discuss.channel"]._create_channel(group_id=None, name="General")

    def test_join_as_internal_user(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.channel._add_members(users=self.alice_user)
        # Same transaction as the join: received.
        self.channel._bus_send("channel_row", None)
        self.channel._bus_send("internal_row", None, subchannel="internal_users")
        self.trigger_notification_dispatching()
        # One frame per channel, in no given order.
        types = set()
        while not {"channel_row", "internal_row"} <= types:
            types.update(notif["message"]["type"] for notif in json.loads(websocket.recv()))

    def test_join_as_portal_user(self):
        websocket = self.connect_and_subscribe("portal_user", "Password!1")
        self.channel._add_members(users=self.portal_user)
        self.channel._bus_send("internal_row", None, subchannel="internal_users")
        self.channel._bus_send("channel_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "channel_row")
        # Frames of different channels come in no given order: only the topic proves it.
        self.assertNotIn(
            (self.env.cr.dbname, "discuss.channel", self.channel.id, "internal_users"),
            dispatch._topic_by_channel,
        )

    def test_leave(self):
        self.channel._add_members(users=self.alice_user)
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.channel._bus_send("channel_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "channel_row")
        self.channel.channel_member_ids.filtered(
            lambda member: member.partner_id == self.alice_user.partner_id
        ).unlink()
        # The leave is applied after its batch: ``alice_row`` comes after it.
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row")
        self.alice_user._bus_send("alice_row_2", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row_2")
        for channel in (
            (self.env.cr.dbname, "discuss.channel", self.channel.id),
            (self.env.cr.dbname, "discuss.channel", self.channel.id, "internal_users"),
        ):
            self.assertNotIn(channel, dispatch._topic_by_channel)

    def test_join_and_leave_as_guest(self):
        guest = self.env["mail.guest"].create({"name": "Guest"})
        websocket = self.connect_and_subscribe(
            channels=[f"mail.guest_{guest._format_auth_cookie()}"],
        )
        self.channel._add_members(guests=guest)
        self.channel._bus_send("channel_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "channel_row")
        self.channel.channel_member_ids.filtered(lambda member: member.guest_id == guest).unlink()
        # The leave is applied after its batch: ``guest_row`` comes after it.
        guest._bus_send("guest_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "guest_row")
        guest._bus_send("guest_row_2", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "guest_row_2")
        self.assertNotIn(
            (self.env.cr.dbname, "discuss.channel", self.channel.id), dispatch._topic_by_channel,
        )

    def test_leave_then_view_as_non_member(self):
        self.channel._add_members(users=self.alice_user)
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        other_channel = self.env["discuss.channel"]._create_channel(group_id=None, name="Other")
        self.channel.channel_member_ids.filtered(
            lambda member: member.partner_id == self.alice_user.partner_id
        ).unlink()
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row")
        self.alice_user._bus_send("alice_row_2", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row_2")
        # The client, still viewing the channel, subscribes to it as a non-member: the
        # channels are read after the leave, which must not be applied again.
        self.subscribe(
            websocket,
            [f"discuss.channel_{self.channel.id}", f"discuss.channel_{other_channel.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        self.channel._bus_send("channel_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "channel_row")

    def test_leave_not_applied_then_view_as_non_member(self):
        self.channel._add_members(users=self.alice_user)
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        last = self.env["bus.bus"]._bus_last_id()
        other_channel = self.env["discuss.channel"]._create_channel(group_id=None, name="Other")
        self.channel.channel_member_ids.filtered(
            lambda member: member.partner_id == self.alice_user.partner_id
        ).unlink()
        # The leave is committed, not applied yet.
        self.env.cr.precommit.run()
        # The channels are read after the leave: applying it later must not remove the
        # channel the client asked for as a non-member.
        self.subscribe(
            websocket,
            [f"discuss.channel_{self.channel.id}", f"discuss.channel_{other_channel.id}"],
            last,
        )
        self.env.cr.postcommit.run()
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row")
        self.channel._bus_send("channel_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "channel_row")
