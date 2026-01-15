# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.bus.models.bus import channel_with_db, json_dump


class TestWebsocketController(HttpCaseWithUserDemo):
    def test_im_status_offline_on_websocket_closed(self):
        self.authenticate("demo", "demo")
        self.env["mail.presence"]._update_presence(self.user_demo)
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.env["bus.bus"].search([]).unlink()
        self.make_jsonrpc_request("/websocket/on_closed", {})
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        message = self.make_jsonrpc_request(
            "/websocket/peek_notifications",
            {
                "channels": [f"odoo-presence-res.partner_{self.partner_demo.id}"],
                "last": 0,
                "is_first_poll": True,
            },
        )["notifications"][0]["message"]
        self.assertEqual(message["type"], "bus.bus/im_status_updated")
        self.assertEqual(message["payload"]["partner_id"], self.partner_demo.id)
        self.assertEqual(message["payload"]["im_status"], "offline")
        self.assertEqual(message["payload"]["presence_status"], "offline")

    def test_receive_missed_presences_on_peek_notifications(self):
        self.authenticate("demo", "demo")
        self.env["mail.presence"]._update_presence(self.user_demo)
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        # First request will get notifications and trigger the creation
        # of the missed presences one.
        last_id = self.env["bus.bus"]._bus_last_id()
        self.make_jsonrpc_request(
            "/websocket/peek_notifications",
            {
                "channels": [f"odoo-presence-res.partner_{self.partner_demo.id}"],
                "last": last_id,
                "is_first_poll": True,
            },
        )
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        notification = self.make_jsonrpc_request(
            "/websocket/peek_notifications",
            {
                "channels": [f"odoo-presence-res.partner_{self.partner_demo.id}"],
                "last": last_id,
                "is_first_poll": True,
            },
        )["notifications"][0]
        bus_record = self.env["bus.bus"].search([("id", "=", int(notification["id"]))])
        self.assertEqual(
            bus_record.channel, json_dump(channel_with_db(self.env.cr.dbname, self.partner_demo))
        )
        self.assertEqual(notification["message"]["type"], "bus.bus/im_status_updated")
        self.assertEqual(notification["message"]["payload"]["partner_id"], self.partner_demo.id)
        self.assertEqual(notification["message"]["payload"]["im_status"], "online")
        self.assertEqual(notification["message"]["payload"]["presence_status"], "online")
