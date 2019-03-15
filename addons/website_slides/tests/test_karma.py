# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_slides.tests import common
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('functional')
class TestKarmaGain(common.SlidesCase):

    def setUp(self):
        super(TestKarmaGain, self).setUp()

        self.channel_2 = self.env['slide.channel'].sudo(self.user_publisher).create({
            'name': 'Test Channel 2',
            'channel_type': 'training',
            'promote_strategy': 'most_voted',
            'enroll': 'public',
            'visibility': 'public',
            'website_published': True,
            'karma_gen_channel_finish': 100,
        })

        self.slide_2 = self.env['slide.slide'].sudo(self.user_publisher).create({
            'name': 'How to travel through space and time',
            'channel_id': self.channel_2.id,
            'slide_type': 'presentation',
            'website_published': True,
            'completion_time': 2.0,
        })

        self.channel_3 = self.env['slide.channel'].sudo(self.user_publisher).create({
            'name': 'Test Channel 3',
            'channel_type': 'training',
            'promote_strategy': 'most_voted',
            'enroll': 'public',
            'visibility': 'public',
            'website_published': True,
            'karma_gen_channel_finish': 50,
        })

        self.slide_3 = self.env['slide.slide'].sudo(self.user_publisher).create({
            'name': 'How to duplicate yourself',
            'channel_id': self.channel_3.id,
            'slide_type': 'presentation',
            'website_published': True,
            'completion_time': 2.0,
        })

    def karma_gain_test(self, user):
        # Add the user to the course
        self.channel.sudo()._action_add_members(user.partner_id)

        # Init user env
        channel = self.channel.sudo(user)
        slide = self.slide.sudo(user)
        self.assertEqual(user.karma, 0)

        # Finish the Course
        karma = channel.karma_gen_channel_finish
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

        # Finish two course at the same time (should not ever happen but hey, we never know)
        self.channel_2.sudo()._action_add_members(user.partner_id)
        self.channel_3.sudo()._action_add_members(user.partner_id)

        karma = karma + self.channel_2.karma_gen_channel_finish + self.channel_3.karma_gen_channel_finish
        slides = self.slide_2.sudo(user) | self.slide_3.sudo(user)
        slides.action_set_completed()
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
