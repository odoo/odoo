# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.addons.mail.tests.common import mail_new_test_user


class SlidesCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(SlidesCase, cls).setUpClass()

        cls.user_officer = mail_new_test_user(
            cls.env, name='Ophélie Officer', login='user_officer', email='officer@example.com',
            groups='base.group_user,website_slides.group_website_slides_officer'
        )

        cls.user_manager = mail_new_test_user(
            cls.env, name='Manuel Manager', login='user_manager', email='manager@example.com',
            groups='base.group_user,website_slides.group_website_slides_manager'
        )

        cls.user_emp = mail_new_test_user(
            cls.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user'
        )

        cls.user_portal = mail_new_test_user(
            cls.env, name='Patrick Portal', login='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

        cls.user_public = mail_new_test_user(
            cls.env, name='Pauline Public', login='user_public', email='public@example.com',
            groups='base.group_public'
        )

        cls.customer = cls.env['res.partner'].create({
            'name': 'Caroline Customer',
            'email': 'customer@example.com',
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
            'slide_type': 'presentation',
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
            'slide_type': 'presentation',
            'is_published': True,
            'completion_time': 3.0,
            'sequence': 3,
        })
        cls.slide_3 = cls.env['slide.slide'].with_user(cls.user_officer).create({
            'name': 'How To Cook Humans For Humans',
            'channel_id': cls.channel.id,
            'slide_type': 'document',
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
