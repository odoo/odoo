# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from freezegun import freeze_time

from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.websocket import Websocket


class TestWebsocketDispatching(WebsocketCase):
    def test_receive_notifications_on_subscribed_channels(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["channel_A"], last=0)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification", None)
        self.trigger_notification_dispatching(["channel_A", "channel_B"])
        notifications = json.loads(websocket.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification")

    @freeze_time("2026-04-02", as_kwarg="clock")
    def test_dispatch_notifications_for_new_channels(self, clock):
        client = self.websocket_connect()
        initial_min_id = self.env["bus.bus"]._bus_last_id()
        self.subscribe(client, ["channel_A"], last=initial_min_id)
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification", None)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.trigger_notification_dispatching(["channel_A"])
        self.assertEqual(len(json.loads(client.recv())), 1)
        # Make sure the min_id kept by the server advances in order to ensure the server
        # will fetch oldest notifications for the new channel and not retrieve them by
        # luck.
        clock.tick(Websocket.MAX_NOTIFICATION_HISTORY_SEC + 1)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.trigger_notification_dispatching(["channel_A"])
        self.assertEqual(len(json.loads(client.recv())), 1)
        self.subscribe(client, ["channel_A", "channel_B"], last=initial_min_id)
        notifications = json.loads(client.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification")

    @freeze_time("2026-04-02", as_kwarg="clock")
    def test_subscribe_to_new_channel_with_higher_id(self, clock):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"], last=0)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_1", None)
        self.trigger_notification_dispatching(["channel_A"])
        self.assertEqual(len(json.loads(client.recv())), 1)
        # Ensure the server state advances in order to avoid fresh state luck.
        clock.tick(Websocket.MAX_NOTIFICATION_HISTORY_SEC + 1)
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification", None)
        self.trigger_notification_dispatching(["channel_A"])
        self.assertEqual(len(json.loads(client.recv())), 1)
        # At this point, the min_id for A is equal or below the last notification. B will
        # subscribe with an higher id. This means that the next dispatching *must* include
        # A and *must not* include `channel_b_notification_OLD`.
        self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_2", None)
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification_OLD", None)
        for _ in range(200):
            self.env["bus.bus"]._sendone("channel_C", "channel_c_notification", None)
        self.trigger_notification_dispatching(["channel_C"])
        # The client has an higher id. This is common since the server min_id is held
        # back for the out-of-order commit case.
        self.subscribe(client, ["channel_A", "channel_B"], last=self.env["bus.bus"]._bus_last_id())
        self.trigger_notification_dispatching(["channel_A", "channel_B"])
        notifications = json.loads(client.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
        self.env["bus.bus"]._sendone("channel_B", "channel_b_notification_NEW", None)
        self.trigger_notification_dispatching(["channel_A", "channel_B"])
        notifications = json.loads(client.recv())
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification_NEW")
