# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestIrWebsocket(common.HttpCase):
    def test_only_allow_string_channels_from_frontend(self):
        with self.assertRaises(ValueError):
            self.env['ir.websocket']._subscribe({
                'inactivity_period': 1000,
                'last': 0,
                'channels': [('odoo', 'discuss.channel', 5)],
            })
