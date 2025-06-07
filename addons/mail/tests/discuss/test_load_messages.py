
import odoo.tests
from odoo import Command
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@odoo.tests.tagged('post_install', '-at_install')
class TestLoadMessages(HttpCaseWithUserDemo):
    def test_01_mail_message_load_order_tour(self):
        partner_admin = self.env.ref('base.partner_admin')
        channel_id = self.env["discuss.channel"].create({
            "name": "MyTestChannel",
            "channel_member_ids": [Command.create({"partner_id": partner_admin.id})],
        })
        self.env["mail.message"].create([{
            "body": str(n),
            "model": "discuss.channel",
            "pinned_at": odoo.fields.Datetime.now() if n == 1 else None,
            "res_id": channel_id.id,
            "author_id": partner_admin.id,
            "message_type": "comment",
        } for n in range(1, 61)])
        channel_id.channel_member_ids.filtered(
            lambda m: m.partner_id == partner_admin
        )._mark_as_read(channel_id.message_ids[0].id)
        self.start_tour("/odoo/action-mail.action_discuss", "mail_message_load_order_tour", login="admin")
