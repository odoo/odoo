import odoo
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.tests import new_test_user


@odoo.tests.tagged("-at_install", "post_install")
class TestImLivechatSessions(TestImLivechatCommon):
    def test_livechat_session_open(self):
        new_test_user(
            self.env,
            login="operator",
            groups="base.group_user,im_livechat.im_livechat_group_manager",
        )
        self.make_jsonrpc_request(
            "/im_livechat/get_session", {"channel_id": self.livechat_channel.id}
        )
        action = self.env.ref("im_livechat.discuss_channel_action_from_livechat_channel")
        self.start_tour(
            f"/odoo/livechat/{self.livechat_channel.id}/action-{action.id}", "im_livechat_session_open",
            login="operator"
        )
