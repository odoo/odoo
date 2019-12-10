# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('functional')
class TestKarmaGain(common.SlidesCase):

    def setUp(self):
        super(TestKarmaGain, self).setUp()

        self.channel_2 = self.env['slide.channel'].with_user(self.user_publisher).create({
            'name': 'Test Channel 2',
            'channel_type': 'training',
            'promote_strategy': 'most_voted',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
            'karma_gen_channel_finish': 100,
            'karma_gen_slide_vote': 5,
            'karma_gen_channel_rank': 10,
        })

        self.slide_2_0 = self.env['slide.slide'].with_user(self.user_publisher).create({
            'name': 'How to travel through space and time',
            'channel_id': self.channel_2.id,
            'slide_type': 'presentation',
            'is_published': True,
            'completion_time': 2.0,
        })
        self.slide_2_1 = self.env['slide.slide'].with_user(self.user_publisher).create({
            'name': 'How to duplicate yourself',
            'channel_id': self.channel_2.id,
            'slide_type': 'presentation',
            'is_published': True,
            'completion_time': 2.0,
        })

    @mute_logger('odoo.models')
    @users('user_emp', 'user_portal', 'user_publisher')
    def test_karma_gain(self):
        user = self.env.user
        user.write({'karma': 0})
        computed_karma = 0

        # Add the user to the course
        (self.channel | self.channel_2)._action_add_members(user.partner_id)
        self.assertEqual(user.karma, 0)

        # Finish the Course
        self.slide.with_user(user).action_set_completed()
        self.assertFalse(self.channel.with_user(user).completed)
        (self.slide_2 | self.slide_3).with_user(user).action_set_completed()
        self.assertTrue(self.channel.with_user(user).completed)
        computed_karma += self.channel.karma_gen_channel_finish
        self.assertEqual(user.karma, computed_karma)

        # Begin then finish the second Course
        self.slide_2_0.with_user(user).action_set_completed()
        self.assertFalse(self.channel_2.with_user(user).completed)
        self.assertEqual(user.karma, computed_karma)

        self.slide_2_1.with_user(user).action_set_completed()
        self.assertTrue(self.channel_2.with_user(user).completed)
        computed_karma += self.channel_2.karma_gen_channel_finish
        self.assertEqual(user.karma, computed_karma)

        # Vote for a slide
        slide_user = self.slide.with_user(user)
        slide_user.action_like()
        computed_karma += self.channel.karma_gen_slide_vote
        self.assertEqual(user.karma, computed_karma)
        slide_user.action_like()  # re-like something already liked should not add karma again
        self.assertEqual(user.karma, computed_karma)
        slide_user.action_dislike()
        computed_karma -= self.channel.karma_gen_slide_vote
        self.assertEqual(user.karma, computed_karma)
        slide_user.action_dislike()
        computed_karma -= self.channel.karma_gen_slide_vote
        self.assertEqual(user.karma, computed_karma)
        slide_user.action_dislike()  # dislike again something already disliked should not remove karma again
        self.assertEqual(user.karma, computed_karma)

    @mute_logger('odoo.models')
    @users('user_emp', 'user_portal', 'user_publisher')
    def test_karma_gain_multiple_course(self):
        user = self.env.user
        user.write({'karma': 0})
        computed_karma = 0

        # Finish two course at the same time (should not ever happen but hey, we never know)
        (self.channel | self.channel_2)._action_add_members(user.partner_id)

        computed_karma += self.channel.karma_gen_channel_finish + self.channel_2.karma_gen_channel_finish
        (self.slide | self.slide_2 | self.slide_3 | self.slide_2_0 | self.slide_2_1).with_user(user).action_set_completed()
        self.assertEqual(user.karma, computed_karma)
