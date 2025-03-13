# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.addons.im_livechat.controllers.main import LivechatController
from odoo.addons.im_livechat.tests.common import TestGetOperatorCommon

@odoo.tests.tagged("-at_install", "post_install")
class TestImLivechatSupportPage(TestGetOperatorCommon):
    def test_load_modules(self):
        operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Support Channel", "user_ids": [operator.id]}
        )
        self.start_tour(f"/im_livechat/support/{livechat_channel.id}", "im_livechat.basic_tour")

    def test_load_modules_cors(self):
        operator = self._create_operator()
        livechat_channel = self.env["im_livechat.channel"].create(
            {"name": "Support Channel", "user_ids": [operator.id]}
        )
        with patch.object(LivechatController, "_is_cors_request", return_value=True):
            self.start_tour(f"/im_livechat/support/{livechat_channel.id}", "im_livechat.basic_tour")
