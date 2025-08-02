# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os
import unittest

from unittest.mock import MagicMock, patch

from odoo.tests import new_test_user, tagged
from .common import WebsocketCase


@tagged("-at_install", "post_install")
@unittest.skipIf(os.getenv("ODOO_FAKETIME_TEST_MODE"), "This test cannot work with faketime")
class TestIrWebsocket(WebsocketCase):
    def test_only_allow_string_channels_from_frontend(self):
        with self.assertLogs("odoo.addons.bus.websocket", level="ERROR") as log:
            ws = self.websocket_connect()
            self.subscribe(ws, [("odoo", "discuss.channel", 5)], self.env["bus.bus"]._bus_last_id())
        self.assertIn("bus.Bus only string channels are allowed.", log.output[0])

    def test_build_bus_channel_list(self):
        test_user = new_test_user(
            self.env, login="test_user", password="Password!1", groups="base.group_system"
        )
        mock_wsrequest = MagicMock()
        mock_wsrequest.session.uid = test_user.id
        with patch("odoo.addons.bus.models.ir_websocket.wsrequest", new=mock_wsrequest):
            ir_websocket_model = self.env["ir.websocket"].with_user(test_user)
            channels = set(ir_websocket_model._build_bus_channel_list(["test_channel"]))
        expected_channels = {
            "test_channel",
            test_user.partner_id,
            self.env.ref("base.group_system"),
            self.env.ref("base.group_user"),
        }
        self.assertTrue(
            expected_channels.issubset(channels),
            f"The channels list is missing some expected values: {expected_channels - channels}.",
        )
