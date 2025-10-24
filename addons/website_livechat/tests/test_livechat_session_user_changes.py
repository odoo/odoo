# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.website_livechat.tests.common import TestLivechatCommon


class TestLivechatSessionUserChanges(tests.HttpCase, TestLivechatCommon):
    def test_livechat_logout_after_chat_start(self):
        self.start_tour("/", "website_livechat_logout_after_chat_start", login="admin")
