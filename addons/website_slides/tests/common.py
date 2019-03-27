# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from functools import partial

from odoo.tests import common, new_test_user

slides_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class SlidesCase(common.SavepointCase):

    def setUp(self):
        super(SlidesCase, self).setUp()

        self.user_publisher = slides_new_test_user(
            self.env, name='Paul Publisher', login='user_publisher', email='publisher@example.com',
            groups='base.group_user,website.group_website_publisher'
        )

        self.user_emp = slides_new_test_user(
            self.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
            groups='base.group_user'
        )

        self.user_portal = slides_new_test_user(
            self.env, name='Patrick Portal', login='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

        self.user_public = slides_new_test_user(
            self.env, name='Pauline Public', login='user_public', email='public@example.com',
            groups='base.group_public'
        )

        self.customer = self.env['res.partner'].create({
            'name': 'Caroline Customer',
            'email': 'customer@example.com',
            'customer': True,
        })

        self.channel = self.env['slide.channel'].sudo(self.user_publisher).create({
            'name': 'Test Channel',
            'channel_type': 'documentation',
            'promote_strategy': 'most_voted',
            'enroll': 'public',
            'visibility': 'public',
            'website_published': True,
            'karma_gen_channel_finish': 100,
            'karma_gen_slide_vote': 5,
            'karma_gen_channel_rank': 10,
        })
        self.slide = self.env['slide.slide'].sudo(self.user_publisher).create({
            'name': 'How To Cook Humans',
            'channel_id': self.channel.id,
            'slide_type': 'presentation',
            'website_published': True,
            'completion_time': 2.0,
        })

    @contextmanager
    def sudo(self, user):
        """ Quick sudo environment """
        old_uid = self.uid
        try:
            self.uid = user.id
            self.env = self.env(user=self.uid)
            yield
        finally:
            # back
            self.uid = old_uid
            self.env = self.env(user=self.uid)
