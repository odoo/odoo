# Part of Odoo. See LICENSE file for full copyright and licensing details.
try:
    import websocket as ws
except ImportError:
    ws = None

from odoo.tests import tagged
from .common import WebsocketCase


@tagged("-at_install", "post_install")
class TestIrWebsocket(WebsocketCase):
    def test_only_allow_string_channels_from_frontend(self):
        with self.assertRaises(ValueError):
            self.env['ir.websocket']._subscribe({
                'inactivity_period': 1000,
                'last': 0,
                'channels': [('odoo', 'discuss.channel', 5)],
            })
