# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo):

    def test_01_admin_forum_tour(self):
        with self.assertQueryCount(__system__=1507):
            self.start_tour("/", 'question', login="admin", step_delay=100)

    def test_02_demo_question(self):
        forum = self.env.ref('website_forum.forum_help')
        demo = self.user_demo
        demo.karma = forum.karma_post + 1
        with self.assertQueryCount(__system__=1472):
            self.start_tour("/", 'forum_question', login="demo")
