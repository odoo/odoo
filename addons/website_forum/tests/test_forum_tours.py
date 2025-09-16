# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.gamification.tests.common import HttpCaseGamification
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCaseGamification):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['forum.post'].create({
            'name': 'Very Smart Question',
            'forum_id': cls.env.ref('website_forum.forum_help').id,
        })

    def test_01_admin_forum_tour(self):
        self.start_tour("/", 'question', login="admin")

    def test_02_demo_question(self):
        forum = self.env.ref('website_forum.forum_help')
        demo = self.user_demo
        demo.karma = forum.karma_post + 1
        self.start_tour("/", 'forum_question', login="demo")
        tags = self.env['forum.tag'].search([('name', 'in', ['Tag', 'tag', 'test tag'])])
        self.assertEqual(len(tags), 3)
