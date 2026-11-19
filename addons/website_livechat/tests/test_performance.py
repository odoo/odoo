# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import new_test_user, tagged

from odoo.addons.website.tests.test_performance import TestWebsitePerformanceCommon


@tagged("post_install", "-at_install")
class TestWebsiteLivechatPerformance(TestWebsitePerformanceCommon):
    def test_cached_page_queries(self):
        query_count_without_livechat = self._get_url_hot_query(self.page.url)
        operator = new_test_user(self.env, "operator", groups="im_livechat.im_livechat_group_user")
        self.env["mail.presence"]._update_presence(operator)
        self.env.ref("website.default_website").channel_id = self.env["im_livechat.channel"].create({
            "name": "Channel",
            "user_ids": [(6, 0, operator.ids)],
        })
        # writing `channel_id` doesn't invalidate the cached page
        self.env.registry.clear_cache()
        # fresh livechat info: website, rule count, channel, operators, users, presences
        self.assertEqual(self._get_url_hot_query(self.page.url), query_count_without_livechat + 7)
