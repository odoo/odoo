# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('functional')
class TestStatistics(common.SlidesCase):

    def karma_gain_test(self, user):
        # Add the user to the course
        self.channel.sudo()._action_add_members(user.partner_id)

        # Init user env
        channel = self.channel.sudo(user)
        slide = self.slide.sudo(user)
        self.assertEqual(user.karma, 0)

        # Finish the Course
        karma = channel.karma_gen_channel_finish
        if user == self.user_public:
            with self.assertRaises(AccessError):
                slide.action_set_completed()
        else:
            slide.action_set_completed()
            self.assertEqual(user.karma, karma)

            # Vote for a slide
            karma = karma + channel.karma_gen_slide_vote
            slide.action_like()
            self.assertEqual(user.karma, karma)
            slide.action_dislike()
            self.assertEqual(user.karma, karma - channel.karma_gen_slide_vote)
            slide.action_dislike()
            self.assertEqual(user.karma, karma)

    @mute_logger('odoo.models')
    def test_users_karma_gain(self):
        self.karma_gain_test(self.user_emp)

    @mute_logger('odoo.models')
    def test_user_publisher_karma_gain(self):
        self.karma_gain_test(self.user_publisher)

    @mute_logger('odoo.models')
    def test_user_portal_karma_gain(self):
        self.karma_gain_test(self.user_portal)

    @mute_logger('odoo.models')
    def test_user_public_karma_gain(self):
        self.karma_gain_test(self.user_public)
