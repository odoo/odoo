from odoo.addons.mail.tests.common import Store
from odoo.tests.common import tagged
from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon


@tagged("post_install", "-at_install")
class TestUserLivechatUsername(TestGetOperatorCommon):
    def test_user_livechat_username_channel_invite_notification(self):
        john = self._create_operator("fr_FR")
        bob = self._create_operator("fr_FR")
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "Livechat Channel",
                "user_ids": [bob.id],
            }
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "anonymous_name": "Visitor",
                "channel_id": livechat_channel.id,
                "persisted": True,
            },
        )
        john.partner_id.user_livechat_username = "ELOPERADOR"
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        channel.add_members(partner_ids=john.partner_id.ids)
        john_data = next(
            (
                p
                for p in Store(channel.message_ids[-1]).get_result()["res.partner"]
                if p["id"] == john.partner_id.id
            ),
            {},
        )
        self.assertEqual(john_data.get("user_livechat_username"), "ELOPERADOR")
