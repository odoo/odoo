# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

from psycopg2 import OperationalError

from odoo.tests import TransactionCase

from odoo.addons.bus import bus_dispatcher
from odoo.addons.bus.models.bus import channel_with_db
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.tools import notifications as notifications_tools
from odoo.addons.bus.tools.notifications import FETCH_MAX_BYTES, fetch_bus_notifications


class TestBusFetchLimit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.channels = [channel_with_db(cls.env.cr.dbname, "foo")]

    def test_split_notifications_according_to_max_bytes(self):
        last = self.env["bus.bus"]._bus_last_id()
        for x in range(4):
            self.env["bus.bus"]._sendone("foo", "notification_type", f"{x}{'*' * int(FETCH_MAX_BYTES * 0.4)}")
        self.env.cr.precommit.run()
        notifications = self.env["bus.bus"]._poll(self.channels, last)
        self.assertEqual([n["message"]["payload"][0] for n in notifications], ["0", "1", "2", "3"])
        notifications, has_more = self.env["bus.bus"]._poll_batch(self.channels, last)
        self.assertEqual(len(notifications), 2)
        self.assertTrue(notifications[0]["message"]["payload"].startswith("0"))
        self.assertTrue(notifications[1]["message"]["payload"].startswith("1"))
        self.assertTrue(has_more)
        notifications, has_more = self.env["bus.bus"]._poll_batch(self.channels, notifications[-1]["id"])
        self.assertEqual(len(notifications), 2)
        self.assertTrue(notifications[0]["message"]["payload"].startswith("2"))
        self.assertTrue(notifications[1]["message"]["payload"].startswith("3"))
        self.assertFalse(has_more)

    def test_oversized_first_notification_is_returned_alone(self):
        last = self.env["bus.bus"]._bus_last_id()
        self.env["bus.bus"]._sendone("foo", "notification_type", f"0{'*' * FETCH_MAX_BYTES}")
        self.env["bus.bus"]._sendone("foo", "notification_type", "1")
        self.env.cr.precommit.run()
        notifications, has_more = self.env["bus.bus"]._poll_batch(self.channels, last)
        self.assertEqual(len(notifications), 1)
        self.assertTrue(notifications[0]["message"]["payload"].startswith("0"))
        self.assertTrue(has_more)
        notifications, has_more = self.env["bus.bus"]._poll_batch(self.channels, notifications[-1]["id"])
        self.assertEqual([n["message"]["payload"] for n in notifications], ["1"])
        self.assertFalse(has_more)

    def test_split_notifications_according_to_max_rows(self):
        last = self.env["bus.bus"]._bus_last_id()
        for x in range(4):
            self.env["bus.bus"]._sendone("foo", "notification_type", str(x))
        self.env.cr.precommit.run()
        with patch.object(notifications_tools, "FETCH_MAX_ROWS", 3):
            notifications, has_more = self.env["bus.bus"]._poll_batch(self.channels, last)
            self.assertEqual([n["message"]["payload"] for n in notifications], ["0", "1", "2"])
            self.assertTrue(has_more)
            notifications, has_more = self.env["bus.bus"]._poll_batch(
                self.channels, last, [n["id"] for n in notifications],
            )
            self.assertEqual([n["message"]["payload"] for n in notifications], ["3"])
            self.assertFalse(has_more)

    def test_last_id_out_of_the_id_range(self):
        self.env["bus.bus"]._sendone("foo", "notification_type", "0")
        self.env.cr.precommit.run()
        notifications = self.env["bus.bus"]._poll(self.channels, -(2**64))
        self.assertEqual(notifications[-1]["message"]["payload"], "0")
        self.assertEqual(self.env["bus.bus"]._poll(self.channels, 2**64), [])


class TestBusFetchLimitWebsocket(WebsocketCase):
    def _send_large_notifications(self, count):
        for x in range(count):
            self.env["bus.bus"]._sendone("foo", "notification_type", f"{x}{'*' * int(FETCH_MAX_BYTES * 0.4)}")

    def _receive_frames(self, websocket, count):
        return [
            [
                notification["message"]["payload"].rstrip("*")
                for notification in json.loads(websocket.recv())
            ]
            for _ in range(count)
        ]

    def test_backlog_above_max_bytes_arrives_in_full(self):
        websocket = self.websocket_connect()
        last = self.env["bus.bus"]._bus_last_id()
        self._send_large_notifications(3)
        self.env.cr.precommit.run()
        self.subscribe(websocket, ["foo"], last, wait_for_dispatch=False)
        self.assertEqual(self._receive_frames(websocket, 2), [["0", "1"], ["2"]])

    def test_notifications_above_max_bytes_arrive_in_full(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["foo"], self.env["bus.bus"]._bus_last_id())
        self._send_large_notifications(3)
        self.trigger_notification_dispatching()
        self.assertEqual(self._receive_frames(websocket, 2), [["0", "1"], ["2"]])

    def test_pages_cover_the_channels_of_a_batch(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["foo", "bar"], self.env["bus.bus"]._bus_last_id())
        for payload in ("0", "1"):
            self.env["bus.bus"]._sendone("foo", "notification_type", f"foo{payload}")
            self.env["bus.bus"]._sendone("bar", "notification_type", f"bar{payload}")
        with patch.object(notifications_tools, "FETCH_MAX_ROWS", 2):
            self.trigger_notification_dispatching()
            # Each page holds one notification of each channel, sent channel by channel.
            frames = self._receive_frames(websocket, 4)
        self.assertEqual(sorted(frames[:2]), [["bar0"], ["foo0"]])
        self.assertEqual(sorted(frames[2:]), [["bar1"], ["foo1"]])

    def test_backlog_of_several_channels_arrives_in_one_frame_per_page(self):
        websocket = self.websocket_connect()
        last = self.env["bus.bus"]._bus_last_id()
        for payload in ("0", "1"):
            self.env["bus.bus"]._sendone("foo", "notification_type", f"foo{payload}")
            self.env["bus.bus"]._sendone("bar", "notification_type", f"bar{payload}")
        self.env.cr.precommit.run()
        with patch.object(notifications_tools, "FETCH_MAX_ROWS", 2):
            self.subscribe(websocket, ["foo", "bar"], last, wait_for_dispatch=False)
            frames = self._receive_frames(websocket, 2)
        self.assertEqual(frames, [["foo0", "bar0"], ["foo1", "bar1"]])

    def test_no_duplicate_when_a_page_fails(self):
        websocket = self.websocket_connect()
        last = self.env["bus.bus"]._bus_last_id()
        self._send_large_notifications(3)
        self.env.cr.precommit.run()
        failed = []

        def _fail_on_second_page(*args):
            pages = fetch_bus_notifications(*args)
            if failed:
                return pages

            def _first_page_then_fail():
                yield next(pages)
                failed.append(True)
                e = "connection lost"
                raise OperationalError(e)

            return _first_page_then_fail()

        with (
            self.assertLogs("odoo.addons.bus.bus_dispatcher", "ERROR"),
            patch.object(bus_dispatcher, "BATCH_RETRY_DELAY", 0),
            patch.object(bus_dispatcher, "fetch_bus_notifications", _fail_on_second_page),
        ):
            self.subscribe(websocket, ["foo"], last, wait_for_dispatch=False)
            frames = self._receive_frames(websocket, 2)
        self.assertTrue(failed)
        self.assertEqual(frames, [["0", "1"], ["2"]])
