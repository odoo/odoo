# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from functools import partial

from odoo.tests import common, new_test_user

slides_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class SlidesCase(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(SlidesCase, cls).setUpClass()

        cls.user_publisher = slides_new_test_user(
            cls.env, name='Paul Publisher', login='user_publisher', email='publisher@example.com',
            groups='base.group_user,website.group_website_publisher'
        )

        cls.user_emp = slides_new_test_user(
            cls.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user'
        )

        cls.user_portal = slides_new_test_user(
            cls.env, name='Patrick Portal', login='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

        cls.user_public = slides_new_test_user(
            cls.env, name='Pauline Public', login='user_public', email='public@example.com',
            groups='base.group_public'
        )

        cls.customer = cls.env['res.partner'].create({
            'name': 'Caroline Customer',
            'email': 'customer@example.com',
        })

        cls.channel = cls.env['slide.channel'].with_user(cls.user_publisher).create({
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
        cls.slide = cls.env['slide.slide'].with_user(cls.user_publisher).create({
            'name': 'How To Cook Humans',
            'channel_id': cls.channel.id,
            'slide_type': 'presentation',
            'is_published': True,
            'completion_time': 2.0,
            'sequence': 1,
        })
        cls.category = cls.env['slide.slide'].with_user(cls.user_publisher).create({
            'name': 'Cooking Tips for Humans',
            'channel_id': cls.channel.id,
            'is_category': True,
            'is_published': True,
            'sequence': 2,
        })
        cls.slide_2 = cls.env['slide.slide'].with_user(cls.user_publisher).create({
            'name': 'How To Cook For Humans',
            'channel_id': cls.channel.id,
            'slide_type': 'presentation',
            'is_published': True,
            'completion_time': 3.0,
            'sequence': 3,
        })
        cls.slide_3 = cls.env['slide.slide'].with_user(cls.user_publisher).create({
            'name': 'How To Cook Humans For Humans',
            'channel_id': cls.channel.id,
            'slide_type': 'document',
            'is_published': True,
            'completion_time': 1.5,
            'sequence': 4,
        })
