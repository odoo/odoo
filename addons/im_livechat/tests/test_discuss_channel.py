from odoo.tests import new_test_user, tagged
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("-at_install", "post_install")
class TestDiscussChannel(TestImLivechatCommon):
    def test_unfollow_from_non_member_does_not_close_livechat(self):
        bob_user = new_test_user(
            self.env, "bob_user", groups="base.group_user,im_livechat.im_livechat_group_manager"
        )
        data = self.make_jsonrpc_request(
            "/im_livechat/get_session",
            {
                "channel_id": self.livechat_channel.id,
                "anonymous_name": "Visitor",
            },
        )
        chat = self.env["discuss.channel"].browse(data["channel_id"])
        self.assertTrue(chat.livechat_active)
        chat.with_user(bob_user).action_unfollow()
        self.assertTrue(chat.livechat_active)
        chat.with_user(chat.livechat_operator_id.user_ids[0]).action_unfollow()
        self.assertFalse(chat.livechat_active)
