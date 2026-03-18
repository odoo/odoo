# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.http.session import SESSION_ROTATION_INTERVAL
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.bus.models.bus import channel_with_db, json_dump


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWebsocketController(HttpCaseWithUserDemo):
    def test_im_status_offline_on_websocket_closed(self):
        self.authenticate("demo", "demo")
        self.env["mail.presence"]._update_presence(self.user_demo)
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.env["bus.bus"].search([]).unlink()
        self.make_jsonrpc_request("/websocket/on_closed", {})
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        presence_notif, self_notif = self.make_jsonrpc_request(
            "/websocket/peek_notifications",
            {
                "channels": [f"odoo-presence-res.partner_{self.partner_demo.id}"],
                "last": 0,
                "is_first_poll": True,
            },
        )["notifications"]
        self.assertEqual(presence_notif["message"]["type"], "mail.record/insert")
        self.assertEqual(presence_notif["message"]["payload"]["res.partner"][0]["id"], self.partner_demo.id)
        self.assertEqual(presence_notif["message"]["payload"]["res.partner"][0]["im_status"], "offline")
        self.assertEqual(self_notif["message"]["type"], "mail.record/insert")
        self.assertEqual(self_notif["message"]["payload"]["res.partner"][0]["id"], self.partner_demo.id)
        self.assertEqual(self_notif["message"]["payload"]["res.partner"][0]["presence_status"], "offline")

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
        notif = self.make_jsonrpc_request(
            "/websocket/peek_notifications",
            {
                "channels": [f"odoo-presence-res.partner_{self.partner_demo.id}"],
                "last": last_id,
                "is_first_poll": True,
            },
        )["notifications"][0]
        bus_record = self.env["bus.bus"].search([("id", "=", int(notif["id"]))])
        self.assertEqual(
            bus_record.channel, json_dump(channel_with_db(self.env.cr.dbname, self.user_demo)),
        )
        self.assertEqual(notif["message"]["type"], "mail.record/insert")
        self.assertEqual(notif["message"]["payload"]["res.partner"][0]["id"], self.partner_demo.id)
        self.assertEqual(notif["message"]["payload"]["res.partner"][0]["im_status"], "online")

    @freeze_time("2026-03-03", as_kwarg='clock')
    def test_do_not_rotate_session_when_updating_presence(self, clock):
        self.authenticate('admin', 'admin')
        self.url_open('/odoo').raise_for_status()
        original_session = self.opener.cookies['session_id']

        clock.tick(SESSION_ROTATION_INTERVAL + 1)
        self.make_jsonrpc_request('/websocket/peek_notifications', {
            'channels': [],
            'last': 0,
            'is_first_poll': True,
        })
        self.make_jsonrpc_request('/websocket/update_bus_presence', {
            'inactivity_period': 0,
        })
        self.assertEqual(self.opener.cookies['session_id'], original_session,
            "Session rotation must not occur at the websocket routes "
            "that are re-exposed on HTTP for convenience.")

        self.url_open('/odoo').raise_for_status()
        self.assertNotEqual(self.opener.cookies['session_id'], original_session,
            "Session rotation should occur with other URLs.")
