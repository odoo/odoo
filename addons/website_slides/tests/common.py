# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user, MailCase
from odoo.tests import HttpCase


class SlidesCase(MailCase, HttpCase):

    @classmethod
    def setUpClass(cls):
        # Test Data
        # ------------------------------------------------------------
        # CHANNEL   Test Channel, documentation, public
        # 1 slide (doc), 1 category with 2 slides (doc), everything published
        # SLIDE3 has a question
        super().setUpClass()

        cls.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })

        cls.user_officer = mail_new_test_user(
            cls.env,
            email='officer@example.com',
            groups='base.group_user,website_slides.group_website_slides_officer',
            login='user_officer',
            name='Ophélie Officer',
            notification_type='email',
        )

        cls.user_manager = mail_new_test_user(
            cls.env,
            email='manager@example.com',
            login='user_manager',
            groups='base.group_user,website_slides.group_website_slides_manager',
            name='Manuel Manager',
            notification_type='email',
        )

        cls.user_emp = mail_new_test_user(
            cls.env,
            email='employee@example.com',
            groups='base.group_user',
            login='user_emp',
            name='Eglantine Employee',
            notification_type='email',
        )

        cls.user_portal = mail_new_test_user(
            cls.env,
            email='portal@example.com',
            groups='base.group_portal',
            login='user_portal',
            name='Patrick Portal',
            notification_type='email',
        )
        cls.user_portal_2 = mail_new_test_user(
            cls.env,
            email='portal.2@example.com',
            groups='base.group_portal',
            login='user_portal_2',
            name='Paulette Portalle',
            notification_type='email',
        )

        cls.user_public = mail_new_test_user(
            cls.env,
            email='public@example.com',
            groups='base.group_public',
            login='user_public',
            name='Pauline Public',
            notification_type='email',
        )

        cls.customer = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.be').id,
            'email': 'customer@customer.example.com',
            'phone': '0456001122',
            'name': 'Caroline Customer',
        })

        cls.channel = cls.env['slide.channel'].with_user(cls.user_officer).create({
            'name': 'Test Channel',
            'channel_type': 'documentation',
            'promote_strategy': 'most_voted',
            'enroll': 'public',
            'visibility': 'public',
            'is_published': True,
            'karma_gen_channel_finish': 100,
            'karma_gen_channel_rank': 10,
        })
        cls.slide = cls.env['slide.slide'].with_user(cls.user_officer).create({
            'name': 'How To Cook Humans',
            'channel_id': cls.channel.id,
            'slide_category': 'document',
            'is_published': True,
            'completion_time': 2.0,
            'sequence': 1,
        })
        cls.category = cls.env['slide.slide'].with_user(cls.user_officer).create({
            'name': 'Cooking Tips for Humans',
            'channel_id': cls.channel.id,
            'is_category': True,
            'is_published': True,
            'sequence': 2,
        })
        cls.slide_2 = cls.env['slide.slide'].with_user(cls.user_officer).create({
            'name': 'How To Cook For Humans',
            'channel_id': cls.channel.id,
            'slide_category': 'document',
            'is_published': True,
            'completion_time': 3.0,
            'sequence': 3,
        })
        cls.slide_3 = cls.env['slide.slide'].with_user(cls.user_officer).create({
            'name': 'How To Cook Humans For Humans',
            'channel_id': cls.channel.id,
            'slide_category': 'document',
            'is_published': True,
            'completion_time': 1.5,
            'sequence': 4,
            'quiz_first_attempt_reward': 42,
        })
        cls.question_1 = cls.env['slide.question'].with_user(cls.user_officer).create({
            'question': 'How long should be cooked a human?',
            'slide_id': cls.slide_3.id,
        })
        cls.answer_1 = cls.env['slide.answer'].with_user(cls.user_officer).create({
            'question_id': cls.question_1.id,
            'text_value': "25' at 180°C",
            'is_correct': True,
        })
        cls.answer_2 = cls.env['slide.answer'].with_user(cls.user_officer).create({
            'question_id': cls.question_1.id,
            'text_value': "Raw",
            'is_correct': False,
        })

    def _add_member(self, channels, partner, add_vals=None):
        return self.env['slide.channel.partner'].create([
            {
                'channel_id': channel.id,
                'member_status': 'joined',
                'partner_id': partner.id,
                **(add_vals or {}),
            } for channel in channels
        ])

    def _add_slide(self, channels, add_vals=None):
        return self.env['slide.slide'].create([
            {
                'channel_id': self.channel.id,
                'completion_time': 2.0,
                'is_published': True,
                'name': f'TestSlide {len(channel.slide_ids)} on {channel.name}',
                'sequence': 10,
                'slide_category': 'document',
                **(add_vals or {}),
            } for channel in channels
        ])

    def assertAttendeeStatus(
            self, attendee, member_status='ongoing', completion=100, active=True,
            channel_completion=100, channel_completed=True, channel_is_member=True,
        ):
        """ Check that the course completion is still accounted for, with given
        member_status. Note that channel completion values may differ from
        attendee status (less often updated, channel is more for display).
        """
        # attendee values
        self.assertEqual(attendee.active, active)
        self.assertEqual(attendee.member_status, member_status)
        self.assertEqual(attendee.completion, completion)

        # channel display values
        attendee_user = attendee.partner_id.user_ids[0]
        self.assertTrue(attendee_user)
        channel = attendee.channel_id.with_user(attendee_user)
        self.assertEqual(channel.completed, channel_completed)
        self.assertEqual(channel.completion, channel_completion)
        self.assertEqual(channel.is_member, channel_is_member)
        self.assertEqual(channel.is_member_invited, member_status == 'invited')
        if active:
            self.assertIn(attendee, channel.sudo().channel_partner_all_ids)
        else:
            self.assertNotIn(attendee, channel.sudo().channel_partner_all_ids)
        if member_status == 'invited' or not channel_is_member:
            self.assertNotIn(attendee, channel.sudo().channel_partner_ids)
        else:
            self.assertIn(attendee, channel.sudo().channel_partner_ids)
