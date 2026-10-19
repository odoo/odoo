# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website.tests.test_performance import TestWebsitePerformanceCommon


@tagged("post_install", "-at_install")
class TestWebsiteLivechatPerformance(TestWebsitePerformanceCommon):
    def test_cached_page_queries(self):
        self.assertEqual(self._get_url_hot_query(self.page.url), 4)
        operator = self.env["res.users"].create({
            "name": "Operator",
            "login": "operator",
            "group_ids": [(4, self.env.ref("im_livechat.im_livechat_group_user").id)],
        })
        self.env["mail.presence"]._update_presence(operator)
        self.env.ref("website.default_website").channel_id = self.env["im_livechat.channel"].create({
            "name": "Channel",
            "user_ids": [(6, 0, operator.ids)],
        })
        # fresh livechat info: rule count, channel, operators, users, presences
        self.assertEqual(self._get_url_hot_query(self.page.url), 10)
