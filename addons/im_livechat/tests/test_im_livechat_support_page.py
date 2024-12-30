# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon

@odoo.tests.tagged("-at_install", "post_install")
class TestImLivechatSupportPage(TestGetOperatorCommon):
    def test_load_modules(self):
        operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Support Channel", "user_ids": [operator.id]}
        )
        self.start_tour(f"/im_livechat/support/{livechat_channel.id}", "im_livechat.basic_tour")
