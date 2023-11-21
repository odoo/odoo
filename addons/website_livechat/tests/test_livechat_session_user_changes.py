# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_livechat.tests.common import TestLivechatCommon
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestLivechatSessionUserChanges(HttpCase, TestLivechatCommon):
    def test_livechat_login_after_chat_start(self):
        self.start_tour("/", "website_livechat_login_after_chat_start")

    def test_livechat_logout_after_chat_start(self):
        self.start_tour("/", "website_livechat_logout_after_chat_start", login="admin")
