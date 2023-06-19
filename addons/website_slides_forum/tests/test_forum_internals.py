# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_forum.tests.common import KARMA, TestForumPostCommon
from odoo.addons.website_slides.tests.common import SlidesCase
from odoo.tests import tagged


@tagged('forum_internals')
class TestPostInternalsSlidesForum(TestForumPostCommon, SlidesCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.forum.slide_channel_id = cls.channel
        cls.channel._action_add_members((cls.user_employee_2 | cls.user_emp | cls.user_portal_2).partner_id)

    def test_posts_can_view(self):
        """Check that website_officers have access to all records with can_view.

        For other users, belonging to the course is part of ir.rule records.
        See also ``TestPostInternals.test_can_view``.
        """
        self.env['forum.post'].search([]).unlink()

        portal_posts = self._generate_posts(self.user_portal)
        self.user_portal.karma = 0
        no_post = self.env['forum.post']
        self.user_employee_2.karma = KARMA['close_all']
        self.user_portal_2.karma = KARMA['moderate']
        self._check_post_can_view_cases(
            [
                (self.user_officer, portal_posts),
                (self.user_portal_2, portal_posts),  # fellow member with moderate rights.
                (self.user_emp, no_post),  # fellow member of the course but portal has 0 karma.
                (self.user_employee_2,  # member with close_all right
                 portal_posts.filtered(lambda p: p.state in ('active', 'flagged', 'close'))),
            ],
            portal_posts,
        )
