# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.tests import TransactionCase

from odoo.addons.bus.models.bus import FETCH_MAX_BYTES
from odoo.addons.bus.tests.common import WebsocketCase


class TestBusFetchLimit(TransactionCase):
    def test_split_notifications_according_to_max_bytes(self):
        last = self.env["bus.bus"]._bus_last_id()
        for x in range(4):
            self.env["bus.bus"]._sendone("foo", "notification_type", f"{x}{'*' * int(FETCH_MAX_BYTES * 0.4)}")
        self.env.cr.precommit.run()
        notifications, has_more_notifications = self.env["bus.bus"]._poll_batch(["foo"], last, max_bytes=None)
        self.assertEqual(len(notifications), 4)
        self.assertFalse(has_more_notifications)
        notifications, has_more_notifications = self.env["bus.bus"]._poll_batch(["foo"], last)
        self.assertEqual(len(notifications), 2)
        self.assertTrue(notifications[0]["message"]["payload"].startswith("0"))
        self.assertTrue(notifications[1]["message"]["payload"].startswith("1"))
        self.assertTrue(has_more_notifications)
        notifications, has_more_notifications = self.env["bus.bus"]._poll_batch(["foo"], notifications[-1]["id"])
        self.assertEqual(len(notifications), 2)
        self.assertTrue(notifications[0]["message"]["payload"].startswith("2"))
        self.assertTrue(notifications[1]["message"]["payload"].startswith("3"))
        self.assertFalse(has_more_notifications)

    def test_oversized_first_notification_is_returned_alone(self):
        last = self.env["bus.bus"]._bus_last_id()
        self.env["bus.bus"]._sendone("foo", "notification_type", f"0{'*' * FETCH_MAX_BYTES}")
        self.env["bus.bus"]._sendone("foo", "notification_type", "1")
        self.env.cr.precommit.run()
        notifications, has_more_notifications = self.env["bus.bus"]._poll_batch(["foo"], last)
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]["message"]["payload"].startswith("0"))
        self.assertTrue(has_more_notifications)
        notifications, has_more_notifications = self.env["bus.bus"]._poll_batch(["foo"], notifications[-1]["id"])
        self.assertEqual([n["message"]["payload"] for n in notifications], ["1"])
        self.assertFalse(has_more_notifications)

    def test_split_notifications_according_to_max_rows(self):
        last = self.env["bus.bus"]._bus_last_id()
        for x in range(4):
            self.env["bus.bus"]._sendone("foo", "notification_type", str(x))
        self.env.cr.precommit.run()
        notifications, has_more_notifications = self.env["bus.bus"]._poll_batch(["foo"], last, max_rows=3)
        self.assertEqual([n["message"]["payload"] for n in notifications], ["0", "1", "2"])
        self.assertTrue(has_more_notifications)
        notifications, has_more_notifications = self.env["bus.bus"]._poll_batch(
            ["foo"], last, [n["id"] for n in notifications], max_rows=3
        )
        self.assertEqual([n["message"]["payload"] for n in notifications], ["3"])
        self.assertFalse(has_more_notifications)


class TestBusFetchLimitWebsocket(WebsocketCase):
    def test_backlog_above_max_bytes_arrives_in_full(self):
        websocket = self.websocket_connect()
        last = self.env["bus.bus"]._bus_last_id()
        for x in range(3):
            self.env["bus.bus"]._sendone("foo", "notification_type", f"{x}{'*' * int(FETCH_MAX_BYTES * 0.4)}")
        self.env.cr.precommit.run()
        self.subscribe(websocket, ["foo"], last, wait_for_dispatch=False)
        pages = [json.loads(websocket.recv()) for _ in range(2)]
        self.assertEqual(
            [[n["message"]["payload"][0] for n in page] for page in pages],
            [["0", "1"], ["2"]],
        )
