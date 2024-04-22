# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import new_test_user
from odoo.addons.im_livechat.tests.common import TestImLivechatCommon
from odoo.tests.common import users, tagged


@tagged("-at_install", "post_install")
class TestImLivechatSessionHistoryOpen(TestImLivechatCommon):
    @users('admin')
    def test_session_history_open(self):
        operator = new_test_user(self.env, login="operator", groups="base.group_user,im_livechat.im_livechat_group_manager")
        [user_1, user_2] = self.env['res.partner'].create(
        [{
                'name': 'test 1',
            },
            {
                'name': 'test 2',
            }
        ])
        self.env["discuss.channel"].create(
            [{
                "name": "test 1",
                "channel_type": "livechat",
                "livechat_channel_id": 1,
                "livechat_operator_id": operator.partner_id.id,
                "channel_member_ids": [Command.create({"partner_id": user_1.id})],
            },
            {
                "name": "test 2",
                "channel_type": "livechat",
                "livechat_channel_id": 1,
                "livechat_operator_id": operator.partner_id.id,
                "channel_member_ids": [Command.create({"partner_id": user_2.id})],
            }]
        )
        self.start_tour("/web", "im_livechat_session_history_open", login="operator", step_delay=25)
