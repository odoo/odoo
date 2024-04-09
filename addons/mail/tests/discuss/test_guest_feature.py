# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from odoo.tests import tagged
from odoo.addons.bus.tests.common import WebsocketCase


@tagged("post_install", "-at_install")
class TestGuestFeature(WebsocketCase):
    def test_channel_seen_as_guest(self):
        guest = self.env["mail.guest"].create({"name": "Guest"})
        partner = self.env["res.partner"].create({"name": "John"})
        channel = self.env["discuss.channel"].channel_create(
            group_id=None, name="General"
        )
        channel.add_members(guest_ids=[guest.id], partner_ids=[partner.id])
        channel.message_post(
            body="Hello World!", message_type="comment", subtype_xmlid="mail.mt_comment"
        )
        guest_member = channel.channel_member_ids.filtered(
            lambda m: m.guest_id == guest
        )
        self.assertEqual(guest_member.seen_message_id, self.env["mail.message"])
        self.make_jsonrpc_request(
            "/discuss/channel/set_last_seen_message",
            {
                "channel_id": channel.id,
                "last_message_id": channel.message_ids[0].id,
            },
            headers={
                "Cookie": f"{guest._cookie_name}={guest._format_auth_cookie()};"
            },
        )
        self.assertEqual(guest_member.seen_message_id, channel.message_ids[0])

    def test_subscribe_to_guest_channel(self):
        self.env["bus.bus"].search([]).unlink()
        guest = self.env["mail.guest"].create({"name": "Guest"})
        guest_websocket = self.websocket_connect()
        self.subscribe(guest_websocket, [f"mail.guest_{guest._format_auth_cookie()}"], guest.id)
        self.env["bus.bus"]._sendone(guest, "lambda", {"foo": "bar"})
        self.trigger_notification_dispatching([guest])
        notifications = json.loads(guest_websocket.recv())
        self.assertEqual(1, len(notifications))
        self.assertEqual(notifications[0]["message"]["type"], "lambda")
        self.assertEqual(notifications[0]["message"]["payload"], {"foo": "bar"})

    def test_subscribe_to_discuss_channel(self):
        guest = self.env["mail.guest"].create({"name": "Guest"})
        channel = self.env["discuss.channel"].channel_create(
            group_id=None, name="General"
        )
        channel.add_members(guest_ids=[guest.id])
        self.env["bus.bus"].search([]).unlink()
        guest_websocket = self.websocket_connect()
        self.subscribe(guest_websocket, [f"mail.guest_{guest._format_auth_cookie()}"], guest.id)
        self.env["bus.bus"]._sendone(channel, "lambda", {"foo": "bar"})
        self.trigger_notification_dispatching([channel])
        notifications = json.loads(guest_websocket.recv())
        self.assertEqual(1, len(notifications))
        self.assertEqual(notifications[0]["message"]["type"], "lambda")
        self.assertEqual(notifications[0]["message"]["payload"], {"foo": "bar"})


@tagged("mail_guest", "post_install", "-at_install")
class TestGuestInternals(WebsocketCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_guest = cls.env["mail.guest"].create({
            "access_token": "test_token",
            "country_id": cls.env.ref("base.be").id,
            "lang": "en_US",
            "timezone": "Europe/Brussels",
            "name": "Guest",
        })

    def _make_jsonrpc_request_with_guest(self, route, parameters, guest, headers=None):
        """ Helper hiding cookie management for guest """
        headers = dict((headers or {}), Cookie=f"{guest._cookie_name}={guest._format_auth_cookie()};")
        return self.make_jsonrpc_request(route, parameters, headers=headers)

    def test_controller_guest_update_name(self):
        """ Test for '/mail/guest/update_name' """
        _res = self._make_jsonrpc_request_with_guest(
            "/mail/guest/update_name",
            {
                "guest_id": self.test_guest.id,
                "name": "New Name",
            },
            self.test_guest,
        )
        self.assertEqual(self.test_guest.name, "New Name")
