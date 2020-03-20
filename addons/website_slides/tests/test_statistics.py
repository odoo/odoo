# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import math

from odoo.addons.website_slides.tests import common
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger, float_compare


@tagged('functional')
class TestChannelStatistics(common.SlidesCase):

    @mute_logger('odoo.models')
    def test_channel_statistics(self):
        channel_publisher = self.channel.with_user(self.user_publisher)
        # slide type computation
        self.assertEqual(channel_publisher.total_slides, len(channel_publisher.slide_content_ids))
        self.assertEqual(channel_publisher.nbr_infographic, len(channel_publisher.slide_content_ids.filtered(lambda s: s.slide_type == 'infographic')))
        self.assertEqual(channel_publisher.nbr_presentation, len(channel_publisher.slide_content_ids.filtered(lambda s: s.slide_type == 'presentation')))
        self.assertEqual(channel_publisher.nbr_document, len(channel_publisher.slide_content_ids.filtered(lambda s: s.slide_type == 'document')))
        self.assertEqual(channel_publisher.nbr_video, len(channel_publisher.slide_content_ids.filtered(lambda s: s.slide_type == 'video')))
        # slide statistics computation
        self.assertEqual(float_compare(channel_publisher.total_time, sum(s.completion_time for s in channel_publisher.slide_content_ids), 3), 0)
        # members computation
        self.assertEqual(channel_publisher.members_count, 1)
        channel_publisher.action_add_member()
        self.assertEqual(channel_publisher.members_count, 1)
        channel_publisher._action_add_members(self.user_emp.partner_id)
        channel_publisher.invalidate_cache(['partner_ids'])
        self.assertEqual(channel_publisher.members_count, 2)
        self.assertEqual(channel_publisher.partner_ids, self.user_publisher.partner_id | self.user_emp.partner_id)

    @mute_logger('odoo.models')
    def test_channel_user_statistics(self):
        channel_publisher = self.channel.with_user(self.user_publisher)
        channel_publisher.write({
            'enroll': 'invite',
        })
        channel_publisher._action_add_members(self.user_emp.partner_id)
        channel_emp = self.channel.with_user(self.user_emp)

        slides_emp = (self.slide | self.slide_2).with_user(self.user_emp)
        slides_emp.action_set_viewed()
        self.assertEqual(channel_emp.completion, 0)

        slides_emp.action_set_completed()
        channel_emp.invalidate_cache()
        self.assertEqual(
            channel_emp.completion,
            math.ceil(100.0 * len(slides_emp) / len(channel_publisher.slide_content_ids)))
        self.assertFalse(channel_emp.completed)

        self.slide_3.with_user(self.user_emp).action_set_completed()
        self.assertEqual(channel_emp.completion, 100)
        self.assertTrue(channel_emp.completed)

        self.slide_3.is_published = False
        self.assertEqual(channel_emp.completion, 100)
        self.assertTrue(channel_emp.completed)

        self.slide_3.is_published = True
        self.slide_3.active = False
        self.assertEqual(channel_emp.completion, 100)
        self.assertTrue(channel_emp.completed)

    @mute_logger('odoo.models')
    def test_channel_user_statistics_complete_check_member(self):
        slides = (self.slide | self.slide_2)
        slides.write({'is_preview': True})
        slides.flush(['is_preview'])
        slides_emp = slides.with_user(self.user_emp)
        slides_emp.read(['name'])
        with self.assertRaises(UserError):
            slides_emp.action_set_completed()

    @mute_logger('odoo.models')
    def test_channel_user_statistics_view_check_member(self):
        slides = (self.slide | self.slide_2)
        slides.write({'is_preview': True})
        slides.flush(['is_preview'])
        slides_emp = slides.with_user(self.user_emp)
        slides_emp.read(['name'])
        with self.assertRaises(UserError):
            slides_emp.action_set_viewed()


@tagged('functional')
class TestSlideStatistics(common.SlidesCase):

    def test_slide_user_statistics(self):
        channel_publisher = self.channel.with_user(self.user_publisher)
        channel_publisher._action_add_members(self.user_emp.partner_id)
        channel_publisher.invalidate_cache(['partner_ids'])

        slide_emp = self.slide.with_user(self.user_emp)
        self.assertEqual(slide_emp.likes, 0)
        self.assertEqual(slide_emp.dislikes, 0)
        self.assertEqual(slide_emp.user_vote, 0)
        slide_emp.action_like()
        self.assertEqual(slide_emp.likes, 1)
        self.assertEqual(slide_emp.dislikes, 0)
        self.assertEqual(slide_emp.user_vote, 1)
        slide_emp.action_dislike()
        self.assertEqual(slide_emp.likes, 0)
        self.assertEqual(slide_emp.dislikes, 0)
        self.assertEqual(slide_emp.user_vote, 0)
        slide_emp.action_dislike()
        self.assertEqual(slide_emp.likes, 0)
        self.assertEqual(slide_emp.dislikes, 1)
        self.assertEqual(slide_emp.user_vote, -1)

    def test_slide_statistics_views(self):
        channel_publisher = self.channel.with_user(self.user_publisher)
        channel_publisher._action_add_members(self.user_emp.partner_id)

        self.assertEqual(self.slide.slide_views, 0)
        self.assertEqual(self.slide.public_views, 0)

        self.slide.write({'public_views': 4})

        self.assertEqual(self.slide.slide_views, 0)
        self.assertEqual(self.slide.public_views, 4)
        self.assertEqual(self.slide.total_views, 4)

        slide_emp = self.slide.with_user(self.user_emp)
        slide_emp.action_set_viewed()

        self.assertEqual(slide_emp.slide_views, 1)
        self.assertEqual(slide_emp.public_views, 4)
        self.assertEqual(slide_emp.total_views, 5)

    @users('user_publisher')
    def test_slide_statistics_types(self):
        category = self.category.with_user(self.env.user)
        self.assertEqual(
            category.nbr_presentation,
            len(category.channel_id.slide_ids.filtered(lambda s: s.category_id == category and s.slide_type == 'presentation')))
        self.assertEqual(
            category.nbr_document,
            len(category.channel_id.slide_ids.filtered(lambda s: s.category_id == category and s.slide_type == 'document')))

        self.assertEqual(self.channel.total_slides, 3, 'The channel should contain 3 slides')
        self.assertEqual(category.total_slides, 2, 'The first category should contain 2 slides')
        other_category = self.env['slide.slide'].with_user(self.user_publisher).create({
            'name': 'Other Category',
            'channel_id': self.channel.id,
            'is_category': True,
            'is_published': True,
            'sequence': 5,
        })
        self.assertEqual(other_category.total_slides, 0, 'The other category should not contain any slide yet')

        # move one of the slide to the other category
        self.slide_3.write({'sequence': 6})
        self.assertEqual(category.total_slides, 1, 'The first category should contain 1 slide')
        self.assertEqual(other_category.total_slides, 1, 'The other category should contain 1 slide')
        self.assertEqual(self.channel.total_slides, 3, 'The channel should still contain 3 slides')
