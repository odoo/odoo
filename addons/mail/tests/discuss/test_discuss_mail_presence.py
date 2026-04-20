# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

try:
    import websocket as ws
except ImportError:
    ws = None

from itertools import product

from odoo.tests import new_test_user
from odoo.addons.bus.tests.common import WebsocketCase, BusResult
from odoo.addons.mail.tests.common import MailCommon, freeze_all_time
from odoo.addons.bus.models.bus import channel_with_db, json_dump


class TestMailPresence(WebsocketCase, MailCommon):
    def _receive_presence(self, requested_by, target, has_token=False):
        self.env["mail.presence"].search([]).unlink()
        if isinstance(requested_by, self.env.registry["res.users"]):
            session = self.authenticate(requested_by.login, requested_by.login)
            auth_cookie = f"session_id={session.sid};"
        else:
            self.authenticate(None, None)
            auth_cookie = f"{requested_by._cookie_name}={requested_by._format_auth_cookie()};"
        websocket = self.websocket_connect(cookie=auth_cookie)
        channel_parts = ["odoo-presence", f"{target._name}_{target.id}"]
        if has_token:
            channel_parts.append(target._get_im_status_access_token())
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
            notifications[0]["message"]["payload"][target._name][0]["im_status"],
            "online",
        )
        self.assertEqual(notifications[0]["message"]["payload"][target._name][0]["id"], target.id)

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
        expected_payload = {}
        if "has_active_call" in self.env["res.users"]._fields:
            expected_payload["res.users"] = [
                {
                    "should_display_in_call_im_status": False,
                    "id": bob.id,
                    "im_status": "offline",
                },
            ]
        else:
            expected_payload["res.users"] = [{"id": bob.id, "im_status": "offline"}]

        with self.assertBus(
            BusResult((bob, "presence"), "mail.record/insert", expected_payload),
        ):
            self.make_jsonrpc_request(
                "/mail/set_manual_im_status",
                {"status": "offline"},
                cookies={"session_id": session.sid},
            )

    def test_presence_status_only_sent_to_self(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        with self.assertBus(
            [
                BusResult(
                    (bob, "presence"),
                    "mail.record/insert",
                    {"res.users": [{"id": bob.id, "im_status": "online"}]},
                ),
                BusResult(
                    bob,
                    "mail.record/insert",
                    {"res.users": [{"id": bob.id, "presence_status": "online"}]},
                ),
            ],
        ):
            self.env["mail.presence"].with_user(bob)._update_presence(bob)
