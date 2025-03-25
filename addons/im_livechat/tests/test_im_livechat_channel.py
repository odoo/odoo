from odoo.tests import new_test_user, tagged
from odoo.exceptions import AccessError
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("-at_install", "post_install")
class TestImLivechatChannel(TestImLivechatCommon):
    def test_user_cant_join_livechat_channel(self):
        bob_user = new_test_user(self.env, "bob_user", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.livechat_channel.with_user(bob_user).action_join()

    def test_operator_join_leave_livechat_channel(self):
        bob_operator = new_test_user(
            self.env, "bob_user", groups="base.group_user,im_livechat.im_livechat_group_user"
        )
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_join()
        self.assertIn(bob_operator, self.livechat_channel.user_ids)
        self.livechat_channel.with_user(bob_operator).action_quit()
        self.assertNotIn(bob_operator, self.livechat_channel.user_ids)
