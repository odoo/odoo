# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

@tagged("post_install", "-at_install")
class TestGuestFeature(HttpCase):
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
