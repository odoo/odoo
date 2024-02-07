# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import new_test_user, HttpCase, tagged
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon


@tagged("-at_install", "post_install")
class TestImLivechatSessionHistory(HttpCase, TestImLivechatCommon):
    def test_session_history_navigation_back_and_forth(self):
        operator = new_test_user(self.env, login="operator", groups="base.group_user,im_livechat.im_livechat_group_manager")
        self.env["bus.presence"].create({"user_id": operator.id, "status": "online"})
        self.livechat_channel.user_ids |= operator
        infos = self.livechat_channel.with_user(self.env.ref("base.public_user"))._open_livechat_discuss_channel(
            anonymous_name="Visitor", previous_operator_id=operator.partner_id.id
        )
        channel = self.env["discuss.channel"].browse(infos["id"])
        channel.with_user(operator).message_post(body="Hello, how can I help you?")
        self.start_tour("/web", "im_livechat_history_back_and_forth_tour", login="operator")
