# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.addons.bus.tests.common import WebsocketCase


class TestWebsocketDispatching(WebsocketCase):
    def test_single_channel_sequential_commit(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["channel_A"])
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification").commit()
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification")
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification_2").commit()
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification_3").commit()
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_3")

    def test_only_deliver_to_subscribed_channels(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["channel_A"])
        with self.bus_tx_mock.tx(self.env.cr) as tx:
            tx.send("channel_A", "channel_a_notification")
            tx.send("channel_B", "channel_b_notification")
        notifications = json.loads(websocket.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification")

    def test_new_channel_catch_up_from_older_position(self):
        client = self.websocket_connect()
        initial_snapshot = self.bus_tx_mock.snapshot()
        self.subscribe(client, ["channel_A"])
        with self.bus_tx_mock.tx(self.env.cr) as tx:
            tx.send("channel_B", "channel_b_notification")
            tx.send("channel_A", "channel_a_notification")
        self.assertEqual(len(json.loads(client.recv())["notifications"]), 1)
        self.subscribe(client, ["channel_A", "channel_B"], stream_position=initial_snapshot)
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification")

    def test_new_channel_with_higher_position_do_not_recv_past_notifications(self):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"])
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification_1").commit()
        self.assertEqual(len(json.loads(client.recv())["notifications"]), 1)
        # Commit channel_b_notification_OLD *before* re-subscribing so that channel_B's
        # starting position (taken after this commit) excludes it.
        self.bus_tx_mock.tx(self.env.cr).send("channel_B", "channel_b_notification_OLD").commit()
        self.subscribe(client, ["channel_A", "channel_B"])
        message = json.loads(client.recv())
        self.assertEqual(message["stream_position"], self.bus_tx_mock.snapshot())
        self.assertFalse(message["notifications"])
        # B subscribed with a higher stream position. This means that the next
        # dispatching *must* include A and *must not* include
        # `channel_b_notification_OLD`.
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification_2").commit()
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
        self.bus_tx_mock.tx(self.env.cr).send("channel_B", "channel_b_notification_NEW").commit()
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_b_notification_NEW")

    def test_low_tx_notification_not_lost_when_higher_tx_commits_first(self):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"])
        low_tx = self.bus_tx_mock.tx(self.env.cr)
        low_tx.send("channel_A", "low_tx_notification")
        high_tx = self.bus_tx_mock.tx(self.env.cr)
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
        self.assertGreater(high_bus_record.create_tx_id, low_bus_record.create_tx_id)

    def test_no_delivery_before_subscribe(self):
        client = self.websocket_connect()
        with self.bus_tx_mock.tx(self.env.cr) as tx:
            tx.send("channel_A", "channel_a_notification_1")
            tx.send("channel_A", "channel_a_notification_2")
        self.subscribe(client, ["channel_A"])
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification_3").commit()
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_3")

    def test_stuck_tx_does_not_block_dispatching(self):
        client = self.websocket_connect()
        self.subscribe(client, ["channel_A"])
        self.bus_tx_mock.tx(self.env.cr)  # First TX is stuck.
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification_1").commit()
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_1")
        self.bus_tx_mock.tx(self.env.cr).send("channel_A", "channel_a_notification_2").commit()
        notifications = json.loads(client.recv())["notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["message"]["type"], "channel_a_notification_2")
