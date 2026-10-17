# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from threading import Event
from unittest.mock import patch

from odoo import Command
from odoo.tests import new_test_user

from odoo.addons.bus.bus_dispatcher import BusDispatcher
from odoo.addons.bus.models.bus import send_notify_payloads
from odoo.addons.bus.tests.common import WebsocketCase


class TestWebsocketGroups(WebsocketCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_user = new_test_user(cls.env, login="alice_user", password="Password!1")
        cls.group_a = cls.env["res.groups"].create({"name": "Group A"})
        cls.group_b = cls.env["res.groups"].create({"name": "Group B"})

    def _connect_alice(self):
        session = self.authenticate("alice_user", "Password!1")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id())
        return websocket

    def _commit_and_wait_for_subscribe(self):
        subscribed = Event()
        original_subscribe = BusDispatcher.subscribe

        def subscribe(dispatcher, *args):
            original_subscribe(dispatcher, *args)
            subscribed.set()

        with patch.object(BusDispatcher, "subscribe", subscribe):
            self.trigger_notification_dispatching()
            self.wait_for_event(subscribed)

    def _recv_types_until(self, websocket, notification_type):
        types = []
        while notification_type not in types:
            types += [notif["message"]["type"] for notif in json.loads(websocket.recv())]
        return types

    def _assert_receives_only_alice_rows(self, websocket, group):
        group._bus_send("group_row", None)
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        types = self._recv_types_until(websocket, "alice_row")
        self.alice_user._bus_send("alice_last_row", None)
        self.trigger_notification_dispatching()
        types += self._recv_types_until(websocket, "alice_last_row")
        self.assertEqual(sorted(types), ["alice_last_row", "alice_row"])

    def test_join_group(self):
        websocket = self._connect_alice()
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.group_a._bus_send("group_a_row", None)
        self._commit_and_wait_for_subscribe()
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_join_implied_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_a.implied_ids = [Command.link(self.group_b.id)]
        self.group_b._bus_send("group_b_row", None)
        self._commit_and_wait_for_subscribe()
        self.assertEqual(self._recv_types_until(websocket, "group_b_row"), ["group_b_row"])

    def test_join_implying_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_b.implied_by_ids = [Command.link(self.group_a.id)]
        self.group_b._bus_send("group_b_row", None)
        self._commit_and_wait_for_subscribe()
        self.assertEqual(self._recv_types_until(websocket, "group_b_row"), ["group_b_row"])

    def test_join_group_after_malformed_payloads(self):
        websocket = self._connect_alice()
        with self.assertLogs("odoo.addons.bus.bus_dispatcher", "WARNING"):
            send_notify_payloads("imbus_resubscribe", ["not json", "[1]", "[[[], 1]]"])
            self.alice_user.group_ids = [Command.link(self.group_a.id)]
            self.group_a._bus_send("group_a_row", None)
            self._commit_and_wait_for_subscribe()
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_leave_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_a.user_ids = [Command.unlink(self.alice_user.id)]
        self._commit_and_wait_for_subscribe()
        self._assert_receives_only_alice_rows(websocket, self.group_a)

    def test_leave_implied_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.group_a.implied_ids = [Command.link(self.group_b.id)]
        websocket = self._connect_alice()
        self.group_a.implied_ids = [Command.unlink(self.group_b.id)]
        self._commit_and_wait_for_subscribe()
        self._assert_receives_only_alice_rows(websocket, self.group_b)
