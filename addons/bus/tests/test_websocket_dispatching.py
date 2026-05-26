# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.bus.tests.common import WebsocketCase


class TestWebsocketDispatching(WebsocketCase):
    def test_single_channel_sequential_commit(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["channel_A"])
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification")
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification")
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_2")
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_3")
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_3")

    def test_only_deliver_to_subscribed_channels(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["channel_A"])
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification")
            self.env["bus.bus"]._sendone("channel_B", "channel_b_notification")
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification")

    def test_new_channel_catch_up_from_older_snapshot(self):
        client = self.websocket_connect()
        initial_snapshot = self.bus_db_mock.snapshot()
        self.subscribe(client, ["channel_A"])
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_B", "channel_b_notification")
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification")
        self.assertEqual(len(json.loads(client.recv())["notifications"]), 1)
        self.subscribe(client, ["channel_A", "channel_B"], from_snapshot=initial_snapshot)
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification")

    def test_new_channel_with_higher_from_snapshot_do_not_recv_past_notifications(self):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"])
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_1")
        self.assertEqual(len(json.loads(client.recv())["notifications"]), 1)
        # Commit channel_b_notification_OLD *before* re-subscribing so that channel_B's
        # from snapshot (taken after this commit) excludes it.
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_B", "channel_b_notification_OLD")
        self.subscribe(client, ["channel_A", "channel_B"])
        message = json.loads(client.recv())
        self.assertEqual(message["last_fetch_snapshot"], self.bus_db_mock.snapshot())
        self.assertFalse(message["notifications"])
        # B subscribed with a higher from_snapshot. This means that the next
        # dispatching *must* include A and *must not* include
        # `channel_b_notification_OLD`.
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_2")
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_B", "channel_b_notification_NEW")
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification_NEW")

    def test_low_tx_notification_not_lost_when_higher_tx_commits_first(self):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"])
        low_tx = self.bus_db_mock.tx()
        low_tx.send("channel_A", "low_tx_notification")
        high_tx = self.bus_db_mock.tx()
        high_tx.send("channel_A", "high_tx_notification").commit()
        high_tx_notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(high_tx_notifications), 1)
        self.assertEqual(high_tx_notifications[0]["message"]["type"], "high_tx_notification")
        low_tx.commit()
        low_tx_notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(low_tx_notifications), 1)
        self.assertEqual(low_tx_notifications[0]["message"]["type"], "low_tx_notification")
        low_bus_record = self.env["bus.bus"].browse(low_tx_notifications[0]["id"])
        high_bus_record = self.env["bus.bus"].browse(high_tx_notifications[0]["id"])
        self.assertGreater(high_bus_record.create_xid, low_bus_record.create_xid)

    def test_no_delivery_before_subscribe(self):
        client = self.websocket_connect()
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_1")
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_2")
        self.subscribe(client, ["channel_A"])
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_3")
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_3")

    def test_stuck_tx_does_not_block_dispatching(self):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"])
        self.bus_db_mock.tx()  # First TX is stuck.
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_1")
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_1")
        with self.bus_db_mock.tx():
            self.env["bus.bus"]._sendone("channel_A", "channel_a_notification_2")
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
