# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

try:
    import websocket as ws
except ImportError:
    ws = None

from odoo.tests import tagged, new_test_user
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.models.bus import channel_with_db, json_dump
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install", "-at_install")
class TestBusPresence(WebsocketCase, MailCommon):
    def _receive_presence(self, sender, recipient):
        self._reset_bus()
        sent_from_user = isinstance(sender, self.env.registry["res.users"])
        receive_to_user = isinstance(recipient, self.env.registry["res.users"])
        if receive_to_user:
            session = self.authenticate(recipient.login, recipient.login)
            auth_cookie = f"session_id={session.sid};"
        else:
            self.authenticate(None, None)
            auth_cookie = f"{recipient._cookie_name}={recipient._format_auth_cookie()};"
        websocket = self.websocket_connect(cookie=auth_cookie, timeout=1)
        sender_bus_target = sender.partner_id if sent_from_user else sender
        self.subscribe(
            websocket,
            [f"odoo-presence-{sender_bus_target._name}_{sender_bus_target.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        self.env["bus.presence"].create(
            {"user_id" if sent_from_user else "guest_id": sender.id, "status": "online"}
        )
        self.trigger_notification_dispatching([(sender_bus_target, "presence")])
        notifications = json.loads(websocket.recv())
        self._close_websockets()
        bus_record = self.env["bus.bus"].search([("id", "=", int(notifications[0]["id"]))])
        self.assertEqual(
            bus_record.channel,
            json_dump(channel_with_db(self.env.cr.dbname, (sender_bus_target, "presence"))),
        )
        self.assertEqual(notifications[0]["message"]["type"], "bus.bus/im_status_updated")
        self.assertEqual(notifications[0]["message"]["payload"]["im_status"], "online")
        self.assertEqual(
            notifications[0]["message"]["payload"]["partner_id" if sent_from_user else "guest_id"],
            sender_bus_target.id,
        )

    def test_receive_presences_as_guest(self):
        guest = self.env["mail.guest"].create({"name": "Guest"})
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        # Guest should not receive users's presence: no common channel.
        with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
            self._receive_presence(sender=bob, recipient=guest)
        channel = self.env["discuss.channel"].channel_create(group_id=None, name="General")
        channel.add_members(guest_ids=[guest.id], partner_ids=[bob.partner_id.id])
        # Now that they share a channel, guest should receive users's presence.
        self._receive_presence(sender=bob, recipient=guest)

        other_guest = self.env["mail.guest"].create({"name": "OtherGuest"})
        # Guest should not receive guest's presence: no common channel.
        with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
            self._receive_presence(sender=other_guest, recipient=guest)
        channel.add_members(guest_ids=[other_guest.id])
        # Now that they share a channel, guest should receive guest's presence.
        self._receive_presence(sender=other_guest, recipient=guest)

    def test_receive_presences_as_portal(self):
        portal = new_test_user(self.env, login="portal_user", groups="base.group_portal")
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        # Portal should not receive users's presence: no common channel.
        with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
            self._receive_presence(sender=bob, recipient=portal)
        channel = self.env["discuss.channel"].channel_create(group_id=None, name="General")
        channel.add_members(partner_ids=[portal.partner_id.id, bob.partner_id.id])
        # Now that they share a channel, portal should receive users's presence.
        self._receive_presence(sender=bob, recipient=portal)

        guest = self.env["mail.guest"].create({"name": "Guest"})
        # Portal should not receive guest's presence: no common channel.
        with self.assertRaises(ws._exceptions.WebSocketTimeoutException):
            self._receive_presence(sender=guest, recipient=portal)
        channel.add_members(guest_ids=[guest.id])
        # Now that they share a channel, portal should receive guest's presence.
        self._receive_presence(sender=guest, recipient=portal)

    def test_receive_presences_as_internal(self):
        internal = new_test_user(self.env, login="internal_user", groups="base.group_user")
        guest = self.env["mail.guest"].create({"name": "Guest"})
        # Internal can access guest's presence regardless of their channels.
        self._receive_presence(sender=guest, recipient=internal)
        # Internal can access users's presence regardless of their channels.
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        self._receive_presence(sender=bob, recipient=internal)
