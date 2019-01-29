# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from functools import partial

from odoo.tests import common, new_test_user

slides_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class SlidesCase(common.SavepointCase):

    def setUp(self):
        super(SlidesCase, self).setUp()

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

        # self.survey = self.env['survey.survey'].sudo(self.survey_manager).create({
        #     'title': 'Test Survey',
        #     'access_mode': 'public',
        #     'users_login_required': True,
        #     'users_can_go_back': False,
        # })
        # self.page_0 = self.env['survey.page'].sudo(self.survey_manager).create({
        #     'title': 'First page',
        #     'survey_id': self.survey.id,
        # })
        # self.question_ft = self.env['survey.question'].sudo(self.survey_manager).create({
        #     'question': 'Test Free Text',
        #     'page_id': self.page_0.id,
        #     'question_type': 'free_text',
        # })
        # self.question_num = self.env['survey.question'].sudo(self.survey_manager).create({
        #     'question': 'Test NUmerical Box',
        #     'page_id': self.page_0.id,
        #     'question_type': 'numerical_box',
        # })

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
