# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import Command
from odoo.tests import tagged, users

from odoo.addons.bus.tests.common import BusResult, WebsocketCase
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.mail.tools.discuss import Store


@tagged("post_install", "-at_install")
class TestDiscussChannelAutoSubscribe(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_user = mail_new_test_user(cls.env, login="alice", name="Alice")
        cls.bella_user = mail_new_test_user(cls.env, login="bella", name="Bella")
        cls.group_users = cls.alice_user | cls.bella_user
        cls.sales_group, cls.plain_group = cls.env["res.groups"].create(
            [
                {
                    "implied_ids": [Command.link(cls.env.ref("base.group_user").id)],
                    "name": "Sales",
                    "user_ids": [Command.set(cls.group_users.ids)],
                },
                {"name": "Plain", "user_ids": [Command.set(cls.group_users.ids)]},
            ],
        )
        cls.channel = cls.env["discuss.channel"].create({"name": "Sales"})

    def _groups_notification(self, groups):
        return BusResult(
            self.channel,
            "mail.record/insert",
            {"discuss.channel": [{"group_ids": groups.ids, "id": self.channel.id}]},
        )

    def _channel_notification(self, group):
        channel = self.channel.with_env(self.env).sudo()
        return BusResult(
            group,
            "mail.record/insert",
            Store(bus_channel=group).add(channel, "_store_channel_fields")._build_result(),
        )

    def _member_notifications(self, users, users_with_channel):
        channel = self.channel.with_env(self.env).sudo()
        notifications = []
        for member in channel.channel_member_ids.sorted("id"):
            user = member.partner_id.user_ids & users
            if not user:
                continue
            store = Store(bus_channel=user)
            if user in users_with_channel:
                store.add(channel, "_store_channel_fields")
            store.add(
                member,
                lambda res: (
                    res.from_method("_store_persona_default_fields"),
                    res.attr("unpin_dt"),
                ),
            )
            notifications.append(BusResult(user, "mail.record/insert", store._build_result()))
        return notifications

    @users("employee")
    def test_channel_sent_once_on_the_bus_of_the_group(self):
        with self.assertBus(
            lambda: [
                self._groups_notification(self.sales_group),
                *self._member_notifications(self.group_users, self.env["res.users"]),
                self._channel_notification(self.sales_group),
            ],
        ):
            self.channel.with_env(self.env).group_ids = self.sales_group
        self.assertEqual(self.channel.channel_partner_ids, self.group_users.partner_id)

    @users("employee")
    def test_channel_sent_to_the_current_user_with_its_own_data(self):
        self.sales_group.user_ids = [Command.link(self.user_employee.id)]
        new_users = self.group_users | self.user_employee
        with self.assertBus(
            lambda: [
                self._groups_notification(self.sales_group),
                *self._member_notifications(new_users, self.user_employee),
                self._channel_notification(self.sales_group),
            ],
        ):
            self.channel.with_env(self.env).group_ids = self.sales_group

    @users("employee")
    def test_channel_sent_to_each_user_of_a_group_without_internal_role(self):
        with self.assertBus(
            lambda: [
                self._groups_notification(self.plain_group),
                *self._member_notifications(self.group_users, self.group_users),
            ],
        ):
            self.channel.with_env(self.env).group_ids = self.plain_group

    @users("admin")
    def test_channel_sent_to_each_user_when_restricted_to_a_group(self):
        self.channel.group_public_id = self.sales_group
        with self.assertBus(
            lambda: [
                self._groups_notification(self.sales_group),
                *self._member_notifications(self.group_users, self.group_users),
            ],
        ):
            self.channel.with_env(self.env).group_ids = self.sales_group

    @users("admin")
    def test_channel_sent_to_the_user_joining_the_group(self):
        self.channel.group_ids = self.sales_group
        with self.assertBus(
            lambda: self._member_notifications(self.user_employee, self.user_employee),
        ):
            self.sales_group.with_env(self.env).user_ids = [Command.link(self.user_employee.id)]


@tagged("post_install", "-at_install")
class TestDiscussChannelAutoSubscribeWebsocket(WebsocketCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_user = mail_new_test_user(cls.env, login="alice", name="Alice")
        cls.sales_group = cls.env["res.groups"].create(
            {"implied_ids": [Command.link(cls.env.ref("base.group_user").id)], "name": "Sales"},
        )
        cls.channel = cls.env["discuss.channel"].create({"name": "Sales"})

    def test_channel_caught_up_by_a_user_that_just_joined_the_group(self):
        session = self.authenticate(self.alice_user.login, self.alice_user.password)
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(websocket, [], self.env["bus.bus"]._bus_last_id())
        # Simulate a user that joins the group after the subscription of its websocket.
        self.sales_group.user_ids = [Command.link(self.alice_user.id)]
        self.channel.group_ids = self.sales_group
        self.trigger_notification_dispatching()
        notifications = json.loads(websocket.recv())
        self.assertEqual(len(notifications), 1)
        payload = notifications[0]["message"]["payload"]
        self.assertEqual(payload["discuss.channel.member"][0]["channel_id"], self.channel.id)
        self.subscribe(websocket, [], notifications[0]["id"])
        notifications = json.loads(websocket.recv())
        self.assertEqual(len(notifications), 1)
        payload = notifications[0]["message"]["payload"]
        self.assertEqual(payload["discuss.channel"][0]["name"], "Sales")
