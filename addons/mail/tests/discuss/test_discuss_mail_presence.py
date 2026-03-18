# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

try:
    import websocket as ws
except ImportError:
    ws = None

from itertools import product

from odoo.tests import new_test_user
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.mail.tests.common import MailCommon, freeze_all_time
from odoo.addons.bus.models.bus import channel_with_db, json_dump


class TestMailPresence(WebsocketCase, MailCommon):
    def _receive_presence(self, requested_by, target, has_token=False):
        self.env["mail.presence"].search([]).unlink()
        target_user = isinstance(target, self.env.registry["res.users"])
        if isinstance(requested_by, self.env.registry["res.users"]):
            session = self.authenticate(requested_by.login, requested_by.login)
            auth_cookie = f"session_id={session.sid};"
        else:
            self.authenticate(None, None)
            auth_cookie = f"{requested_by._cookie_name}={requested_by._format_auth_cookie()};"
        websocket = self.websocket_connect(cookie=auth_cookie)
        target_channel = target.partner_id if target_user else target
        channel_parts = ["odoo-presence", f"{target_channel._name}_{target_channel.id}"]
        if has_token:
            channel_parts.append(target_channel._get_im_status_access_token())
        self.subscribe(websocket, ["-".join(channel_parts)], self.env["bus.bus"]._bus_last_id())
        self.env["mail.presence"]._update_presence(target)
        self.trigger_notification_dispatching([(target, "presence")])
        notifications = json.loads(websocket.recv())
        self._close_websockets()
        bus_record = self.env["bus.bus"].search([("id", "=", int(notifications[0]["id"]))])
        self.assertEqual(
            bus_record.channel,
            json_dump(channel_with_db(self.env.cr.dbname, (target, "presence"))),
        )
        self.assertEqual(notifications[0]["message"]["type"], "mail.record/insert")
        self.assertEqual(
            notifications[0]["message"]["payload"][target_channel._name][0]["im_status"],
            "online",
        )
        self.assertEqual(
            notifications[0]["message"]["payload"][target_channel._name][0]["id"],
            target_channel.id,
        )

    @freeze_all_time()
    def test_presence_access(self):
        internal = new_test_user(self.env, login="internal_user", groups="base.group_user")
        other_internal = new_test_user(
            self.env, login="other_internal_user", groups="base.group_user"
        )
        portal = new_test_user(self.env, login="portal_user", groups="base.group_portal")
        other_portal = new_test_user(
            self.env, login="other_portal_user", groups="base.group_portal"
        )
        guest = self.env["mail.guest"].create({"name": "Guest"})
        other_guest = self.env["mail.guest"].create({"name": "Other Guest"})
        for requested_by, target, has_token, allowed in [
            *product([internal], [guest, other_internal, portal], [True, False], [True]),
            *product([guest, portal], [internal, other_guest, other_portal], [False], [False]),
            *product([guest, portal], [internal, other_guest, other_portal], [True], [True]),
        ]:
            with self.subTest(
                f"test presence access, requested_by={requested_by.name}, target={target.name}, has_token={has_token}, allowed={allowed}"
            ):
                if allowed:
                    self._receive_presence(requested_by, target, has_token=has_token)
                else:
                    with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
                        self._receive_presence(requested_by, target, has_token=has_token)

    def test_manual_im_status(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        session = self.authenticate(bob.login, bob.login)
        with self.assertBus(
            [(bob, "presence")],
            [
                {
                    "type": "mail.record/insert",
                    "payload": {
                        "res.partner": [{"id": bob.partner_id.id, "im_status": "offline"}],
                    },
                },
            ],
        ):
            self.make_jsonrpc_request(
                "/mail/set_manual_im_status",
                {"status": "offline"},
                cookies={"session_id": session.sid},
            )

    def test_presence_status_only_sent_to_self(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        self._reset_bus()
        self.env["mail.presence"].with_user(bob)._update_presence(bob)
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        presence_channel_notif, self_channel_notif = self.env["bus.bus"].search([])
        self.assertEqual(presence_channel_notif.channel, json_dump(channel_with_db(self.env.cr.dbname, (bob, "presence"))))
        self.assertEqual(self_channel_notif.channel, json_dump(channel_with_db(self.env.cr.dbname, bob)))
        presence_payload = json.loads(presence_channel_notif.message)["payload"]
        self.assertEqual(
            presence_payload,
            {"res.partner": [{"id": bob.partner_id.id, "im_status": "online"}]},
        )
        self_payload = json.loads(self_channel_notif.message)["payload"]
        self.assertEqual(
            self_payload,
            {"res.partner": [{"id": bob.partner_id.id, "presence_status": "online"}]},
        )
        other_user = new_test_user(self.env, login="other_user", groups="base.group_user")
        self._reset_bus()
        bob_presence = self.env["mail.presence"].search([("user_id", "=", bob.id)])
        bob_presence._send_presence(bus_target=other_user)
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        notifications = self.env["bus.bus"].search([])
        self.assertEqual(len(notifications), 1)  # Only im_status notification was dispatched, and only for bus_target.
        self.assertEqual(
            notifications.channel,
            json_dump(channel_with_db(self.env.cr.dbname, other_user)),
        )
        self.assertEqual(
           json.loads(notifications.message)["payload"],
            {"res.partner": [{"id": bob.partner_id.id, "im_status": "online"}]},
        )
