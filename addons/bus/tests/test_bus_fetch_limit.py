# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch

from odoo.tests import TransactionCase

from odoo.addons.bus.models.bus import channel_with_db
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.tools import notifications
from odoo.addons.bus.tools.notifications import FETCH_MAX_BYTES, fetch_bus_notification_batches


class TestBusFetchLimit(TransactionCase):
    def test_fetch_batches(self):
        channel = channel_with_db(self.env.cr.dbname, "foo")
        last = self.env["bus.bus"]._bus_last_id()
        for payload in ("0", "1", f"2{'*' * FETCH_MAX_BYTES}", "3", "4", "5", "6"):
            self.env["bus.bus"]._sendone("foo", "notification_type", payload)
        self.env.cr.precommit.run()
        with patch.object(notifications, "FETCH_MAX_ROWS", 3):
            batches = [
                (
                    [n["message"]["payload"][0] for n in batch.notifications_by_channel[channel]],
                    batch.has_more,
                )
                for batch in fetch_bus_notification_batches(self.env.cr, {last: [channel]})
            ]
        self.assertEqual(
            batches,
            [(["0", "1"], True), (["2"], True), (["3", "4", "5"], True), (["6"], False)],
        )


class TestBusFetchLimitWebsocket(WebsocketCase):
    def _receive_frames(self, websocket, count):
        return [
            [notification["message"]["payload"] for notification in json.loads(websocket.recv())]
            for _ in range(count)
        ]

    def test_notifications_arrive_batch_by_batch(self):
        websocket = self.websocket_connect()
        self.subscribe(websocket, ["foo", "bar"], self.env["bus.bus"]._bus_last_id())
        for payload in ("0", "1"):
            self.env["bus.bus"]._sendone("foo", "notification_type", f"foo{payload}")
            self.env["bus.bus"]._sendone("bar", "notification_type", f"bar{payload}")
        with patch.object(notifications, "FETCH_MAX_ROWS", 2):
            self.trigger_notification_dispatching()
            frames = self._receive_frames(websocket, 4)
        self.assertEqual(sorted(frames[:2]), [["bar0"], ["foo0"]])
        self.assertEqual(sorted(frames[2:]), [["bar1"], ["foo1"]])
