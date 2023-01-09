# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon


class SlidesCase(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(SlidesCase, cls).setUpClass()

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
            'mobile': '0456001122',
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
            'karma_gen_slide_vote': 5,
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
