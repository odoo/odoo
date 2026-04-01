from odoo import fields
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
            "/im_livechat/get_session", {"channel_id": livechat_channel.id, "persisted": True}
        )
        john.partner_id.user_livechat_username = "ELOPERADOR"
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        channel._add_members(users=john)
        self.assertEqual(
            channel.message_ids[-1].body,
            f'<div class="o_mail_notification" data-oe-type="channel-joined">invited <a href="#" data-oe-model="res.partner" data-oe-id="{john.partner_id.id}">@ELOPERADOR</a> to the channel</div>',
        )

    def test_user_livechat_username_reactions(self):
        john = self._create_operator("fr_FR")
        john.livechat_username = "ELOPERADOR"
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Livechat Channel", "user_ids": [john.id]}
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": livechat_channel.id}
        )
        channel = self.env["discuss.channel"].browse(data["channel_id"])
        message = channel.message_post(body="Hello, How can I help you?")
        session = self.authenticate(john.login, john.login)
        data = self.make_jsonrpc_request(
            "/mail/message/reaction",
            {"action": "add", "content": "👍", "message_id": message.id},
            cookies={"session_id": session.sid},
        )
        self.assertEqual(
            data["res.partner"][0],
            {
                "avatar_128_access_token": john.partner_id._get_avatar_128_access_token(),
                "id": john.partner_id.id,
                "user_livechat_username": "ELOPERADOR",
                "write_date": fields.Datetime.to_string(john.partner_id.write_date),
            },
        )

    def test_user_livechat_username_in_store(self):
        john = self._create_operator("fr_FR")
        operator = self._create_operator("en_US")
        john.livechat_username = "ELOPERADOR"
        operator.group_ids = [
            fields.Command.link(self.env.ref("im_livechat.im_livechat_group_user").id),
        ]
        livechat_channel = self.env["im_livechat.channel"].create(
            {
                "name": "The channel",
                "user_ids": [fields.Command.link(john.id), fields.Command.link(operator.id)],
            }
        )
        channel = self.env["discuss.channel"].with_user(operator).create(
            {
                "name": "Livechat session",
                "channel_type": "livechat",
                "livechat_operator_id": operator.partner_id.id,
                "livechat_channel_id": livechat_channel.id,
            }
        )
        data = operator.partner_id.with_user(operator).search_for_channel_invite("fr_FR", channel.id)["store_data"]
        john_data = next(filter(lambda partner: partner["id"] == john.partner_id.id, data["res.partner"]))
        self.assertEqual(
            john_data["user_livechat_username"],
            "ELOPERADOR",
        )
