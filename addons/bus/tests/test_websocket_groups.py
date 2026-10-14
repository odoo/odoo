# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import time
from threading import Event
from unittest.mock import patch

from odoo import Command
from odoo.tests import new_test_user
from odoo.tools import SQL

from odoo.addons.bus.bus_dispatcher import (
    POLL_TIMEOUT,
    SUBSCRIPTION_CHANGE_WINDOW,
    BusDispatcher,
    dispatch,
)
from odoo.addons.bus.models.bus import send_notify_payloads
from odoo.addons.bus.models.ir_websocket import IrWebsocket
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.tools.misc import acquire_cursor

on_listener_wake = BusDispatcher._on_listener_wake


class TestWebsocketGroups(WebsocketCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_user = new_test_user(cls.env, login="alice_user", password="Password!1")
        cls.group_a = cls.env["res.groups"].create({"name": "Group A"})
        cls.group_b = cls.env["res.groups"].create({"name": "Group B"})

    def _connect_alice(self):
        self._reset_bus()
        session = self.authenticate("alice_user", "Password!1")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id())
        return websocket

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
        self._commit_and_wait_for_subscription_changes()
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_join_group_during_catch_up(self):
        self._reset_bus()
        session = self.authenticate("alice_user", "Password!1")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        claimed, group_changed = Event(), Event()
        original_claim = BusDispatcher._claim

        def _claim(dispatcher, dbname):
            topics = original_claim(dispatcher, dbname)
            if any(topic._waiting_room_snapshot for topic in topics):
                claimed.set()
                group_changed.wait(5)
            return topics

        with patch.object(BusDispatcher, "_claim", _claim):
            self.subscribe(
                websocket,
                last=self.env["bus.bus"]._bus_last_id(),
                wait_for_dispatch=False,
            )
            self.assertTrue(self.wait_for_event(claimed))
            self.alice_user.group_ids = [Command.link(self.group_a.id)]
            self.group_a._bus_send("group_a_row", None)
            with self._wait_for_subscription_changes():
                self.trigger_notification_dispatching()
                group_changed.set()
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_join_implied_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_a.implied_ids = [Command.link(self.group_b.id)]
        self.group_b._bus_send("group_b_row", None)
        self._commit_and_wait_for_subscription_changes()
        self.assertEqual(self._recv_types_until(websocket, "group_b_row"), ["group_b_row"])

    def test_join_implying_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_b.implied_by_ids = [Command.link(self.group_a.id)]
        self.group_b._bus_send("group_b_row", None)
        self._commit_and_wait_for_subscription_changes()
        self.assertEqual(self._recv_types_until(websocket, "group_b_row"), ["group_b_row"])

    def test_join_group_without_notify_when_databases_are_queued(self):
        websocket = self._connect_alice()
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.group_a._bus_send("group_a_row", None)
        with patch("odoo.addons.bus.models.bus_subscription_change.send_notify_payloads"):
            self.trigger_notification_dispatching()
        with self._wait_for_subscription_changes():
            dispatch._queue_all_subscription_changes()
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_join_group_without_notify_at_a_later_listener_wake(self):
        websocket = self._connect_alice()
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.group_a._bus_send("group_a_row", None)
        with patch("odoo.addons.bus.models.bus_subscription_change.send_notify_payloads"):
            self.trigger_notification_dispatching()
        woken = Event()

        def _on_listener_wake(dispatcher, timed_out):
            on_listener_wake(dispatcher, timed_out)
            woken.set()

        with (
            patch.object(BusDispatcher, "_on_listener_wake", _on_listener_wake),
            patch.object(BusDispatcher, "_queue_subscription_changes") as queue,
        ):
            dispatch._all_subscription_changes_queued_at = time.monotonic()
            send_notify_payloads("imbus", ["[]"])
            self.assertTrue(self.wait_for_event(woken))
        queue.assert_not_called()
        dispatch._all_subscription_changes_queued_at -= POLL_TIMEOUT
        with (
            patch.object(BusDispatcher, "_on_listener_wake", on_listener_wake),
            self._wait_for_subscription_changes(),
        ):
            send_notify_payloads("imbus", ["[]"])
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_join_group_first_change_of_the_database(self):
        websocket = self._connect_alice()
        with self._wait_for_subscription_changes():
            dispatch._queue_subscription_changes(self.env.cr.dbname)
        dispatch._subscription_change_max_id_by_db.clear()
        self.env.cr.execute("SELECT last_value, is_called FROM bus_subscription_change_id_seq")
        self.addCleanup(
            self.env.cr.execute,
            "SELECT setval('bus_subscription_change_id_seq', %s, %s)",
            self.env.cr.fetchone(),
        )
        self.env.cr.execute("SELECT setval('bus_subscription_change_id_seq', 1, false)")
        with self._wait_for_subscription_changes():
            dispatch._queue_subscription_changes(self.env.cr.dbname)
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.group_a._bus_send("group_a_row", None)
        self._commit_and_wait_for_subscription_changes()
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_join_group_committed_after_a_later_change(self):
        websocket = self._connect_alice()
        with self._wait_for_subscription_changes():
            dispatch._queue_subscription_changes(self.env.cr.dbname)
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.group_a._bus_send("group_a_row", None)
        self.env.cr.precommit.run()
        self.env.cr.execute(
            "DELETE FROM bus_subscription_change RETURNING id, payload, create_date",
        )
        [(change_id, payload, create_date)] = self.env.cr.fetchall()
        self.group_b.user_ids = [Command.link(self.alice_user.id)]
        self._commit_and_wait_for_subscription_changes()
        self.env.cr.execute(SQL(
            "INSERT INTO bus_subscription_change (id, payload, create_date) VALUES (%s, %s, %s)",
            change_id,
            json.dumps(payload),
            create_date,
        ))
        with self._wait_for_subscription_changes():
            dispatch._queue_subscription_changes(self.env.cr.dbname)
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_imply_already_implied_group(self):
        group_c = self.env["res.groups"].create({"name": "Group C"})
        self.group_b.implied_ids = [Command.link(group_c.id)]
        self.group_a.implied_ids = [Command.link(self.group_b.id)]
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self._reset_bus()
        self.group_a.implied_ids = [Command.link(group_c.id)]
        self.assertNotIn("bus.subscription.change", self.env.cr.precommit.data)

    def test_link_group_already_had(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self._reset_bus()
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.assertNotIn("bus.subscription.change", self.env.cr.precommit.data)

    def test_join_group_after_malformed_changes(self):
        websocket = self._connect_alice()
        self.env.cr.execute(SQL(
            """INSERT INTO bus_subscription_change (payload, create_date)
               VALUES ('{"owner_model": 1}', clock_timestamp() AT TIME ZONE 'UTC')""",
        ))
        with self.assertLogs("odoo.addons.bus.bus_dispatcher", "WARNING"):
            send_notify_payloads("imbus_subscription", ["not json", "1"])
            self.alice_user.group_ids = [Command.link(self.group_a.id)]
            self.group_a._bus_send("group_a_row", None)
            self._commit_and_wait_for_subscription_changes()
        self.assertEqual(self._recv_types_until(websocket, "group_a_row"), ["group_a_row"])

    def test_leave_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_a.user_ids = [Command.unlink(self.alice_user.id)]
        self._commit_and_wait_for_subscription_changes()
        self._assert_receives_only_alice_rows(websocket, self.group_a)

    def test_leave_implied_group(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self.group_a.implied_ids = [Command.link(self.group_b.id)]
        websocket = self._connect_alice()
        self.group_a.implied_ids = [Command.unlink(self.group_b.id)]
        self._commit_and_wait_for_subscription_changes()
        self._assert_receives_only_alice_rows(websocket, self.group_b)

    def test_leave_group_sub_channel(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        original_build = IrWebsocket._build_bus_channel_list

        def _build_bus_channel_list(ir_websocket, channels):
            return [*original_build(ir_websocket, channels), (self.group_a, "sub")]

        with patch.object(IrWebsocket, "_build_bus_channel_list", _build_bus_channel_list):
            websocket = self._connect_alice()
        self.group_a.user_ids = [Command.unlink(self.alice_user.id)]
        self._commit_and_wait_for_subscription_changes()
        self.env["bus.bus"]._sendone((self.group_a, "sub"), "group_row", None)
        self._assert_receives_only_alice_rows(websocket, self.group_a)

    def test_leave_and_join_group_then_subscribe(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        original_build = IrWebsocket._build_bus_channel_list

        def _build_bus_channel_list(ir_websocket, channels):
            channels = original_build(ir_websocket, channels)
            if self.group_a in ir_websocket.env.user.all_group_ids:
                channels.append((self.group_a, "sub"))
            return channels

        with patch.object(IrWebsocket, "_build_bus_channel_list", _build_bus_channel_list):
            websocket = self._connect_alice()
            self.group_a.user_ids = [Command.unlink(self.alice_user.id)]
            self._commit_and_wait_for_subscription_changes()
            self.group_a.user_ids = [Command.link(self.alice_user.id)]
            self._commit_and_wait_for_subscription_changes()
            self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id())
        self.env["bus.bus"]._sendone((self.group_a, "sub"), "sub_row", None)
        self.trigger_notification_dispatching()
        self.assertEqual(self._recv_types_until(websocket, "sub_row"), ["sub_row"])

    def test_notify_of_a_database_without_topic_reads_nothing(self):
        websocket = self._connect_alice()
        queued = Event()

        def _queue_subscription_changes(dispatcher, dbname):
            if dbname == self.env.cr.dbname:
                queued.set()

        with patch.object(
            BusDispatcher,
            "_queue_subscription_changes",
            autospec=True,
            side_effect=_queue_subscription_changes,
        ) as queue:
            send_notify_payloads("imbus_subscription", [json.dumps("db_without_topic")])
            send_notify_payloads("imbus_subscription", [json.dumps(self.env.cr.dbname)])
            self.assertTrue(self.wait_for_event(queued))
        self.assertEqual(
            [call.args[1] for call in queue.call_args_list],
            [self.env.cr.dbname],
        )
        websocket.close()

    def test_leave_group_then_subscribe_with_old_groups_after_the_window(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_a.user_ids = [Command.unlink(self.alice_user.id)]
        self._commit_and_wait_for_subscription_changes()
        changes = dispatch._subscription_changes_by_db[self.env.cr.dbname]
        for change_id, (applied, *change) in list(changes.items()):
            changes[change_id] = (applied - SUBSCRIPTION_CHANGE_WINDOW, *change)
        original_build = IrWebsocket._build_bus_channel_list

        def _build_bus_channel_list(ir_websocket, channels):
            return [*original_build(ir_websocket, channels), self.group_a]

        with patch.object(IrWebsocket, "_build_bus_channel_list", _build_bus_channel_list):
            self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id())
        self.group_a._bus_send("group_row", None)
        self.trigger_notification_dispatching()
        self.assertEqual(self._recv_types_until(websocket, "group_row"), ["group_row"])

    def test_leave_group_before_the_first_topic_of_the_database(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self._reset_bus()
        dispatch._ensure_started()
        self.assertNotIn(self.env.cr.dbname, dispatch._topic_count_by_db)
        self.group_a.user_ids = [Command.unlink(self.alice_user.id)]
        self.trigger_notification_dispatching()
        original_build = IrWebsocket._build_bus_channel_list

        def _build_bus_channel_list(ir_websocket, channels):
            return [*original_build(ir_websocket, channels), self.group_a]

        session = self.authenticate("alice_user", "Password!1")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        with (
            patch.object(IrWebsocket, "_build_bus_channel_list", _build_bus_channel_list),
            self._wait_for_subscription_changes(),
        ):
            self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id())
        self._assert_receives_only_alice_rows(websocket, self.group_a)

    def test_last_websocket_of_the_database_drops_its_changes(self):
        websocket = self._connect_alice()
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        self._commit_and_wait_for_subscription_changes()
        dbname = self.env.cr.dbname
        self.assertIn(dbname, dispatch._subscription_changes_by_db)
        unsubscribed = Event()
        original_unsubscribe = BusDispatcher.unsubscribe

        def unsubscribe(dispatcher, ws):
            original_unsubscribe(dispatcher, ws)
            unsubscribed.set()

        with patch.object(BusDispatcher, "unsubscribe", unsubscribe):
            websocket.close()
            self.assertTrue(self.wait_for_event(unsubscribed))
        for _ in range(100):
            if dbname not in dispatch._topic_count_by_db:
                break
            # wait for the dispatch in flight to release its topics
            self.sleep(0.05)
        self.assertNotIn(dbname, dispatch._topic_count_by_db)
        with (
            patch(
                "odoo.addons.bus.bus_dispatcher.acquire_cursor",
                side_effect=acquire_cursor,
            ) as acquire,
            self._wait_for_subscription_changes(),
        ):
            dispatch._queue_subscription_changes(dbname)
        acquire.assert_not_called()
        self.assertNotIn(dbname, dispatch._subscription_change_max_id_by_db)
        self.assertNotIn(dbname, dispatch._subscription_change_gaps_by_db)
        self.assertNotIn(dbname, dispatch._subscription_changes_by_db)

    def test_leave_group_then_subscribe_with_old_groups(self):
        self.alice_user.group_ids = [Command.link(self.group_a.id)]
        websocket = self._connect_alice()
        self.group_a.user_ids = [Command.unlink(self.alice_user.id)]
        self._commit_and_wait_for_subscription_changes()
        original_build = IrWebsocket._build_bus_channel_list

        def _build_bus_channel_list(ir_websocket, channels):
            return [*original_build(ir_websocket, channels), self.group_a]

        subscribed = Event()
        original_subscribe = BusDispatcher.subscribe

        def subscribe(dispatcher, *args):
            original_subscribe(dispatcher, *args)
            subscribed.set()

        with (
            patch.object(IrWebsocket, "_build_bus_channel_list", _build_bus_channel_list),
            patch.object(BusDispatcher, "subscribe", subscribe),
        ):
            self.subscribe(
                websocket,
                last=self.env["bus.bus"]._bus_last_id(),
                wait_for_dispatch=False,
            )
            self.assertTrue(self.wait_for_event(subscribed))
        self._assert_receives_only_alice_rows(websocket, self.group_a)
