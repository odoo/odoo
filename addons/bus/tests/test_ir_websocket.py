# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os
import unittest

from odoo.tests import tagged
from .common import WebsocketCase


@tagged("-at_install", "post_install")
@unittest.skipIf(os.getenv("ODOO_FAKETIME_TEST_MODE"), "This test cannot work with faketime")
class TestIrWebsocket(WebsocketCase):
    def test_only_allow_string_channels_from_frontend(self):
        with self.assertLogs("odoo.addons.bus.websocket", level="ERROR") as log:
            ws = self.websocket_connect()
            self.subscribe(ws, [("odoo", "discuss.channel", 5)], self.env["bus.bus"]._bus_last_id())
        self.assertIn("bus.Bus only string channels are allowed.", log.output[0])
