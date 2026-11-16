# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import secrets
import time
from threading import Event
from unittest.mock import patch

from freezegun import freeze_time
from psycopg2 import OperationalError

try:
    import websocket as ws
except ImportError:
    ws = None

from odoo.addons.bus import bus_dispatcher
from odoo.addons.bus.bus_dispatcher import BusDispatcher, ChannelTopic, DispatchState, dispatch
from odoo.addons.bus.models.bus import channel_with_db
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.tools import notifications as bus_notifications
from odoo.addons.bus.tools.notifications import fetch_bus_notifications


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

    # A notification with a payload of 100 characters takes about 130 bytes. A budget of
    # 300 bytes cuts the fetch every 3 notifications.
    PAGE_BUDGET = 300

    def _send_notifications(self, channel_and_type_list, size=100):
        for channel, type_ in channel_and_type_list:
            self.env["bus.bus"]._sendone(channel, type_, "x" * size)
        self.trigger_notification_dispatching()

    def _recv_notifications(self, websocket, count):
        """Receive frames until ``count`` notifications arrived. Return the notifications
        and the number of frames."""
        notifications = []
        frame_count = 0
        while len(notifications) < count:
            notifications.extend(json.loads(websocket.recv()))
            frame_count += 1
        websocket.settimeout(1)
        with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
            websocket.recv()  # No duplicate.
        websocket.settimeout(10)
        return notifications, frame_count

    def _fetch_all_pages(self, channels, last):
        """Fetch the notifications of ``channels`` page by page, as a client does."""
        channels = [channel_with_db(self.env.cr.dbname, channel) for channel in channels]
        pages = []
        has_more = True
        with patch.object(bus_notifications, "BUS_FETCH_MAX_BYTES", self.PAGE_BUDGET):
            while has_more:
                notifications_by_channel, has_more = fetch_bus_notifications(
                    self.env.cr, {last: channels},
                )
                pages.append({
                    channel[1]: [notif["message"]["type"] for notif in notifs]
                    for channel, notifs in notifications_by_channel.items()
                })
                last = max(n["id"] for notifs in notifications_by_channel.values() for n in notifs)
        return pages

    def test_fetch_is_cut_by_bytes(self):
        last = self.env["bus.bus"]._bus_last_id()
        self._send_notifications([
            ("channel_A", "A1"), ("channel_B", "B1"), ("channel_A", "A2"), ("channel_A", "A3"),
            ("channel_A", "A4"), ("channel_A", "A5"), ("channel_C", "C1"),
        ])
        pages = self._fetch_all_pages(["channel_A", "channel_B", "channel_C"], last)
        # Every channel is complete up to the cut-off. The small ones are not delayed by
        # the large one.
        self.assertEqual(pages, [
            {"channel_A": ["A1", "A2"], "channel_B": ["B1"]},
            {"channel_A": ["A3", "A4", "A5"]},
            {"channel_C": ["C1"]},
        ])

    def test_fetch_row_larger_than_budget(self):
        last = self.env["bus.bus"]._bus_last_id()
        self._send_notifications([("channel_A", "large")], size=self.PAGE_BUDGET * 2)
        self._send_notifications([("channel_A", "small_1"), ("channel_A", "small_2")])
        pages = self._fetch_all_pages(["channel_A"], last)
        self.assertEqual(pages, [
            {"channel_A": ["large"]},
            {"channel_A": ["small_1", "small_2"]},
        ])

    def test_paged_catch_up(self):
        client = self.websocket_connect()
        self._send_notifications([("dummy", "dummy")])  # Subscribing with 0 would fallback to last id.
        last = self.env["bus.bus"]._bus_last_id()
        expected = [f"A{i}" for i in range(10)]
        self._send_notifications([("channel_A", type_) for type_ in expected])
        with patch.object(bus_notifications, "BUS_FETCH_MAX_BYTES", self.PAGE_BUDGET):
            self.subscribe(client, ["channel_A"], last=last)
            notifications, frame_count = self._recv_notifications(client, len(expected))
        self.assertEqual([n["message"]["type"] for n in notifications], expected)
        self.assertGreater(frame_count, 1)

    def test_paged_catch_up_mixed_channels(self):
        client = self.websocket_connect()
        self._send_notifications([("dummy", "dummy")])  # Subscribing with 0 would fallback to last id.
        last = self.env["bus.bus"]._bus_last_id()
        sent = [("channel_A", f"A{i}") for i in range(10)]
        sent[2:2] = [("channel_B", "B1"), ("channel_C", "C1")]
        sent.append(("channel_B", "B2"))
        self._send_notifications(sent)
        with patch.object(bus_notifications, "BUS_FETCH_MAX_BYTES", self.PAGE_BUDGET):
            self.subscribe(client, ["channel_A", "channel_B", "channel_C"], last=last)
            notifications, _frame_count = self._recv_notifications(client, len(sent))
        received_types = [n["message"]["type"] for n in notifications]
        for channel in ("channel_A", "channel_B", "channel_C"):
            expected_types = [type_ for c, type_ in sent if c == channel]
            self.assertEqual([t for t in received_types if t in expected_types], expected_types)

    def test_subscribe_during_paged_catch_up(self):
        client_1 = self.websocket_connect()
        client_2 = self.websocket_connect(cookie=f"session_id={self.session.sid}")
        self._send_notifications([("dummy", "dummy")])  # Subscribing with 0 would fallback to last id.
        last = self.env["bus.bus"]._bus_last_id()
        old = [f"old_{i}" for i in range(10)]
        self._send_notifications([("channel_A", type_) for type_ in old])
        with patch.object(bus_notifications, "BUS_FETCH_MAX_BYTES", self.PAGE_BUDGET):
            self.subscribe(client_1, ["channel_A"], last=last)
            self.subscribe(client_2, ["channel_A"], last=last, wait_for_dispatch=False)
            self._send_notifications([("channel_A", "new")])
            for client in (client_1, client_2):
                notifications, _frame_count = self._recv_notifications(client, len(old) + 1)
                self.assertEqual([n["message"]["type"] for n in notifications], [*old, "new"])

    def test_release_claims_after_cut_fetch(self):
        dispatcher = BusDispatcher()
        dbname = self.env.cr.dbname
        for ws_last_id, topic_last_id, history_ids, cutoff_id, expected_waiting_id in [
            (10, 40, [60], None, None),  # Complete fetch, promoted.
            (10, 40, [], 50, None),  # Websocket and topic caught up, promoted.
            (10, 40, [60], 50, 50),  # Subscribers got more than the cut-off.
            (10, 100, [], 50, 50),  # Topic ahead of the cut-off.
            (80, 40, [], 50, 80),  # Websocket ahead of the cut-off.
        ]:
            websocket = object()
            topic = ChannelTopic((dbname, secrets.token_hex(4)), topic_last_id)
            topic._history = [(notif_id, 0) for notif_id in history_ids]
            dispatcher._topic_by_channel[topic._channel] = topic
            dispatcher._topics_by_websocket[websocket] = {topic}
            topic._state = DispatchState.IN_FLIGHT
            topic._waiting_room_snapshot = {websocket: ws_last_id}
            dispatcher._release_claims(dbname, {topic}, cutoff_id=cutoff_id)
            if expected_waiting_id is None:
                self.assertEqual(topic._websockets, {websocket})
                self.assertFalse(topic._waiting_room)
                self.assertFalse(topic._waiting_after_cut)
            else:
                self.assertFalse(topic._websockets)
                self.assertEqual(topic._waiting_room, {websocket: expected_waiting_id})
                self.assertEqual(topic._waiting_after_cut, {websocket})
            # A cut fetch queues its topics for the next page.
            self.assertIs(
                topic._state,
                DispatchState.IDLE if cutoff_id is None else DispatchState.QUEUED,
            )

    def test_waiting_websocket_gets_late_notifications(self):
        sent = []

        class FakeWebsocket:
            def send(self, payload, opcode):
                sent.append([n["id"] for n in json.loads(payload)])

        topic = ChannelTopic((self.env.cr.dbname, "channel_A"), 40)
        topic._history = [(60, time.monotonic())]
        cut_websocket = FakeWebsocket()
        topic._waiting_after_cut.add(cut_websocket)
        # Both wait at 50. One was kept there by a cut fetch, one subscribed from there.
        topic._waiting_room_snapshot = {cut_websocket: 50, FakeWebsocket(): 50}
        # 45 is committed late, 60 was already sent to the subscribers.
        topic.dispatch_notifications([{"id": 45}, {"id": 55}, {"id": 60}])
        # The client of the other one has everything up to its last id.
        self.assertEqual(sent, [[45, 55, 60], [55, 60]])
