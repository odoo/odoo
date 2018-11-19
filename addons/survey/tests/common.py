# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

from odoo.tests import common, new_test_user

survey_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class SurveyCase(common.SavepointCase):

    def setUp(self):
        super(SurveyCase, self).setUp()

        self.survey_manager = survey_new_test_user(
            self.env, name='Gustave Doré', login='survey_manager', email='survey.manager@example.com',
            groups='survey.group_survey_manager,base.group_user'
        )

        self.survey_user = survey_new_test_user(
            self.env, name='Lukas Peeters', login='survey_user', email='survey.user@example.com',
            groups='survey.group_survey_user,base.group_user'
        )

        self.user_portal = survey_new_test_user(
            self.env, name='Patrick Portal', login='portal_user', email='portal@example.com',
            groups='base.group_portal'
        )

        self.user_public = survey_new_test_user(
            self.env, name='Pauline Public', login='public_user', email='public@example.com',
            groups='base.group_public'
        )
