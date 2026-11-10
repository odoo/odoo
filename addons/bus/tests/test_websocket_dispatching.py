# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import secrets
from threading import Event
from unittest.mock import patch

from freezegun import freeze_time
from psycopg2 import OperationalError

from odoo.addons.bus import bus_dispatcher
from odoo.addons.bus.bus_dispatcher import BusDispatcher, ChannelTopic, DispatchState, dispatch
from odoo.addons.bus.tests.common import WebsocketCase


class TestWebsocketDispatching(WebsocketCase):
    def test_receive_notifications_on_subscribed_channels(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["channel_A"], last=self.env["bus.bus"]._bus_last_id())
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification", None)
        self.trigger_notification_dispatching()
        notifications = json.loads(websocket.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification")

    @freeze_time("2026-04-02", as_kwarg="clock")
    def test_dispatch_notifications_for_new_channels(self, clock):
        client = self.websocket_connect()
        self.env["bus.bus"]._sendone("dummy", "dummy_notification", None)  # Subscribing with 0 would fallback to last id.
        self.trigger_notification_dispatching()
        initial_min_id = self.env["bus.bus"]._bus_last_id()
        self.subscribe(client, ["channel_A"], last=initial_min_id)
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification", None)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.trigger_notification_dispatching()
        self.assertEqual(len(json.loads(client.recv())), 1)
        # Make sure the min_id kept by the server advances in order to ensure the server
        # will fetch oldest notifications for the new channel and not retrieve them by
        # luck.
        clock.tick(ChannelTopic.MAX_HISTORY_SEC + 1)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.trigger_notification_dispatching()
        self.assertEqual(len(json.loads(client.recv())), 1)
        self.subscribe(client, ["channel_A", "channel_B"], last=initial_min_id)
        notifications = json.loads(client.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification")

    @freeze_time("2026-04-02", as_kwarg="clock")
    def test_subscribe_to_new_channel_with_higher_id(self, clock):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"], last=self.env["bus.bus"]._bus_last_id())
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_1", None)
        self.trigger_notification_dispatching()
        self.assertEqual(len(json.loads(client.recv())), 1)
        # Ensure the server state advances in order to avoid fresh state luck.
        clock.tick(ChannelTopic.MAX_HISTORY_SEC + 1)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.trigger_notification_dispatching()
        self.assertEqual(len(json.loads(client.recv())), 1)
        # At this point, the min_id for A is equal or below the last notification. B will
        # subscribe with an higher id. This means that the next dispatching *must* include
        # A and *must not* include `channel_b_notification_OLD`.
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_2", None)
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification_OLD", None)
        for _ in range(200):
            self.env["bus.bus"]._sendone("channel_C", "channel_c_notification", None)
        self.trigger_notification_dispatching()
        # The client has an higher id. This is common since the server min_id is held
        # back for the out-of-order commit case.
        self.subscribe(client, ["channel_A", "channel_B"], last=self.env["bus.bus"]._bus_last_id())
        notifications = json.loads(client.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification_NEW", None)
        self.trigger_notification_dispatching()
        notifications = json.loads(client.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification_NEW")

    def test_recv_notification_while_listener_is_down(self):
        channel = f"channel_{secrets.token_hex(4)}"
        websocket = self.websocket_connect()
        self.subscribe(websocket, [channel], last=self.env["bus.bus"]._bus_last_id())
        original_notify_topic = dispatch._notify_topic
        crashed = Event()

        def _crash_once(topic):
            if crashed.is_set() or topic._channel[1] != channel:
                return original_notify_topic(topic)
            crashed.set()
            raise OperationalError("connection lost")

        with (
            self.assertLogs("odoo.addons.bus.bus_dispatcher", "ERROR"),
            patch.object(bus_dispatcher, "ERROR_RETRY_DELAY", 0),
            patch.object(bus_dispatcher, "ERROR_RETRY_JITTER", 0),
            patch.object(dispatch, "_notify_topic", _crash_once),
        ):
            self.env["bus.bus"]._sendone(channel, "missed_notification", None)
            # The listener crashes handling this NOTIFY, which is therefore lost.
            self.trigger_notification_dispatching()
            notifications = json.loads(websocket.recv())
        self.assertTrue(crashed.is_set())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "missed_notification")

    def test_notify_all_topics_ignores_dropped_topics(self):
        dispatcher = BusDispatcher()
        topic = ChannelTopic((self.env.cr.dbname, "channel_A"), 0)
        dispatcher._topic_by_channel[topic._channel] = topic
        lock_for_db = dispatcher._lock_for_db

        def _drop_then_lock(dbname):
            # The topic is dropped between the listing and the lock acquisition.
            dispatcher._topic_by_channel.pop(topic._channel, None)
            return lock_for_db(dbname)

        dispatcher._lock_for_db = _drop_then_lock
        dispatcher._notify_all_topics()
        self.assertFalse(dispatcher._pending_topics_by_db)
        self.assertIs(topic._state, DispatchState.IDLE)
