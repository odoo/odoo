# Part of Odoo. See LICENSE file for full copyright and licensing details.
from uuid import uuid4

from odoo.addons.bus.models.bus import channel_with_db, dispatch, hashable
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.tests import tagged


@tagged("-at_install", "post_install")
class TestWebEditorWebsocket(WebsocketCase):
    def test_subscribe_collab_channel_as_public(self):
        channel = str(uuid4())
        ws = self.websocket_connect()  # no cookie: public session
        self.subscribe(
            ws,
            ["editor_collaboration:res.partner:name:1", channel],
            self.env["bus.bus"]._bus_last_id(),
        )
        # The subscription itself must have succeeded: the other requested
        # channels are registered for dispatch
        self.assertIn(
            hashable(channel_with_db(self.registry.db_name, channel)),
            dispatch._channels_to_ws,
        )
        # The collaboration channel must not be joined by the public user
        self.assertNotIn(
            hashable((self.registry.db_name, "editor_collaboration", "res.partner", "name", 1)),
            dispatch._channels_to_ws,
        )
