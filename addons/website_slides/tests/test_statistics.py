# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.website_slides.tests import common
from odoo.exceptions import UserError
from odoo.tests import HttpCase, tagged
from odoo.tests.common import users
from odoo.tools import mute_logger, float_compare


@tagged('functional')
class TestChannelStatistics(common.SlidesCase):

    @mute_logger('odoo.models')
    def test_channel_new_content(self):
        (self.slide | self.slide_2).write({'date_published': fields.Datetime.now() + relativedelta(days=-6)})
        self.slide_3.write({'date_published': fields.Datetime.now() + relativedelta(days=-8)})
        self.assertTrue(all(slide.is_new_slide for slide in (self.slide | self.slide_2)))
        self.assertFalse(self.slide_3.is_new_slide)

        channel_aspublisher = self.channel.with_user(self.user_officer)
        self.assertTrue(channel_aspublisher.partner_has_new_content)
        (self.slide | self.slide_2).with_user(self.user_officer).action_mark_completed()
        self.assertFalse(channel_aspublisher.partner_has_new_content)

        channel_aspublisher._action_add_members(self.user_portal.partner_id)
        channel_asportal = self.channel.with_user(self.user_portal)
        self.assertTrue(channel_asportal.partner_has_new_content)

        (self.slide | self.slide_2).write({'date_published': fields.Datetime.now() + relativedelta(days=-8)})
        channel_asportal.invalidate_recordset(['partner_has_new_content'])
        self.assertFalse(channel_asportal.partner_has_new_content)

    @mute_logger('odoo.models')
    def test_channel_statistics(self):
        channel_publisher = self.channel.with_user(self.user_officer)
        # slide category computation
        self.assertEqual(channel_publisher.total_slides, len(channel_publisher.slide_content_ids))
        self.assertEqual(channel_publisher.nbr_infographic, len(channel_publisher.slide_content_ids.filtered(lambda s: s.slide_category == 'infographic')))
        self.assertEqual(channel_publisher.nbr_document, len(channel_publisher.slide_content_ids.filtered(lambda s: s.slide_category == 'document')))
        self.assertEqual(channel_publisher.nbr_video, len(channel_publisher.slide_content_ids.filtered(lambda s: s.slide_category == 'video')))
        # slide statistics computation
        self.assertEqual(float_compare(channel_publisher.total_time, sum(s.completion_time for s in channel_publisher.slide_content_ids), 3), 0)
        # members computation
        self.assertEqual(channel_publisher.members_count, 1)
        channel_publisher.action_add_member()
        self.assertEqual(channel_publisher.members_count, 1)
        channel_publisher._action_add_members(self.user_emp.partner_id)
        channel_publisher.invalidate_recordset(['partner_ids'])
        self.assertEqual(channel_publisher.members_count, 2)
        self.assertEqual(channel_publisher.partner_ids, self.user_officer.partner_id | self.user_emp.partner_id)

    @mute_logger('odoo.models')
    def test_channel_user_statistics(self):
        channel_publisher = self.channel.with_user(self.user_officer)
        channel_publisher.write({
            'enroll': 'invite',
        })
        channel_publisher._action_add_members(self.user_emp.partner_id)
        channel_emp = self.channel.with_user(self.user_emp)

        members = self.env['slide.channel.partner'].search([('channel_id', '=', self.channel.id)])
        member_emp = members.filtered(lambda m: m.partner_id == self.user_emp.partner_id)
        member_publisher = members.filtered(lambda m: m.partner_id == self.user_officer.partner_id)

        slides_emp = (self.slide | self.slide_2).with_user(self.user_emp)
        slides_emp.action_set_viewed()
        self.assertEqual(member_emp.completion, 0)
        self.assertEqual(channel_emp.completion, 0)

        slides_emp.action_mark_completed()
        channel_emp.invalidate_recordset()
        self.assertEqual(
            channel_emp.completion,
            math.ceil(100.0 * len(slides_emp) / len(channel_publisher.slide_content_ids)))
        self.assertFalse(channel_emp.completed)

        self.slide_3.with_user(self.user_emp)._action_mark_completed()
        self.assertEqual(member_emp.completion, 100)
        self.assertEqual(channel_emp.completion, 100)
        self.assertTrue(channel_emp.completed)

        # The following tests should not update the completion for users that has already completed the course

        self.slide_3.is_published = False
        self.assertEqual(member_emp.completion, 100)
        self.assertEqual(channel_emp.completion, 100)
        self.assertTrue(channel_emp.completed)

        self.slide_3.is_published = True
        self.slide_3.active = False
        self.assertEqual(member_emp.completion, 100)
        self.assertEqual(channel_emp.completion, 100)
        self.assertTrue(channel_emp.completed)

        # Should update completion when slide is marked as completed

        self.assertEqual(member_publisher.completion, 0)
        self.assertEqual(channel_publisher.completion, 0)
        self.slide.with_user(self.user_officer).action_mark_completed()
        self.assertEqual(member_publisher.completion, 50)
        self.assertEqual(channel_publisher.completion, 50)

        # Should update completion when slide is (un)archived
        self.slide_3.active = True
        self.assertEqual(member_emp.completion, 100)
        self.assertEqual(channel_emp.completion, 100)
        self.assertEqual(member_publisher.completion, 33)
        self.assertEqual(channel_publisher.completion, 33)

        # Should update completion when a new published slide is created
        self.slide_4 = self.slide_3.copy({'is_published': True})
        self.assertEqual(member_emp.completion, 100)
        self.assertEqual(channel_emp.completion, 100)
        self.assertEqual(member_publisher.completion, 25)
        self.assertEqual(channel_publisher.completion, 25)

        # Should update completion when slide is (un)published
        self.slide_4.is_published = False
        self.assertEqual(member_emp.completion, 100)
        self.assertEqual(channel_emp.completion, 100)
        self.assertEqual(member_publisher.completion, 33)
        self.assertEqual(channel_publisher.completion, 33)

        # Should update completion when slide is marked as uncompleted
        self.slide.with_user(self.user_emp).action_mark_uncompleted()
        self.assertEqual(member_emp.completion, 67)
        self.assertEqual(channel_emp.completion, 67)
        self.assertEqual(member_publisher.completion, 33)
        self.assertEqual(channel_publisher.completion, 33)

        # Should update completion when a slide is unlinked
        self.slide.with_user(self.user_manager).unlink()
        self.assertEqual(member_emp.completion, 100)
        self.assertEqual(channel_emp.completion, 100)
        self.assertEqual(member_publisher.completion, 0)
        self.assertEqual(channel_publisher.completion, 0)

    @mute_logger('odoo.models')
    def test_channel_user_statistics_complete_check_member(self):
        slides = (self.slide | self.slide_2)
        slides.write({'is_preview': True})
        slides.flush_model()
        slides_emp = slides.with_user(self.user_emp)
        slides_emp.read(['name'])
        with self.assertRaises(UserError):
            slides_emp.action_mark_completed()

    @mute_logger('odoo.models')
    def test_channel_user_statistics_view_check_member(self):
        slides = (self.slide | self.slide_2)
        slides.write({'is_preview': True})
        slides.flush_model()
        slides_emp = slides.with_user(self.user_emp)
        slides_emp.read(['name'])
        with self.assertRaises(UserError):
            slides_emp.action_set_viewed()


@tagged('functional')
class TestSlideStatistics(common.SlidesCase):

    def test_slide_user_statistics(self):
        channel_publisher = self.channel.with_user(self.user_officer)
        channel_publisher._action_add_members(self.user_emp.partner_id)
        channel_publisher.invalidate_recordset(['partner_ids'])

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
        self.assertEqual(slide_emp.dislikes, 1)
        self.assertEqual(slide_emp.user_vote, -1)
        slide_emp.action_dislike()
        self.assertEqual(slide_emp.likes, 0)
        self.assertEqual(slide_emp.dislikes, 0)
        self.assertEqual(slide_emp.user_vote, 0)

    def test_slide_statistics_views(self):
        channel_publisher = self.channel.with_user(self.user_officer)
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

    @users('user_officer')
    def test_slide_statistics_categories(self):
        category = self.category.with_user(self.env.user)
        self.assertEqual(
            category.nbr_document,
            len(category.channel_id.slide_ids.filtered(lambda s: s.category_id == category and s.slide_category == 'document')))

        self.assertEqual(self.channel.total_slides, 3, 'The channel should contain 3 slides')
        self.assertEqual(category.total_slides, 2, 'The first category should contain 2 slides')
        other_category = self.env['slide.slide'].with_user(self.user_officer).create({
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

@tagged('functional')
class TestHttpSlideStatistics(HttpCase, common.SlidesCase):
    @classmethod
    def setUpClass(cls):
        super(TestHttpSlideStatistics, cls).setUpClass()
        cls.slide.is_preview = True

    def test_slide_statistics_views(self):
        self.assertEqual(self.slide.public_views, 0)
        self.assertEqual(self.slide.total_views, 0)
        # Open the slide a first time. Must increase the views by 1
        self.url_open(f'/slides/slide/{self.slide.id}')
        self.assertEqual(self.slide.public_views, 1)
        self.assertEqual(self.slide.total_views, 1)
        # Open the slide a second time.
        # As it's the same session, it must not increase the views anymore
        self.url_open(f'/slides/slide/{self.slide.id}')
        self.assertEqual(self.slide.public_views, 1)
        self.assertEqual(self.slide.total_views, 1)
