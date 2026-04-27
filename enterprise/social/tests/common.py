# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.social.tests.tools import mock_void_external_calls
from odoo.tests import common


class SocialCase(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(SocialCase, cls).setUpClass()

        with mock_void_external_calls():
            cls.social_media = cls._get_social_media()
            cls.social_account = cls._get_social_account()

            attachments = [{
                'name': 'first.png',
                'datas': 'ABCDEFG='
            }, {
                'name': 'second.png',
                'datas': 'GFEDCBA='
            }]

            cls.social_accounts = cls._get_post_social_accounts()

            cls.social_post = cls.env['social.post'].create({
                'message': 'A message',
                'image_ids': [(0, 0, attachment) for attachment in attachments],
                'post_method': 'now',
                'account_ids': [(4, account.id) for account in cls.social_accounts]
            })

            cls.social_manager = mail_new_test_user(
                cls.env, name='Gustave Doré', login='social_manager', email='social.manager@example.com',
                groups='social.group_social_manager,base.group_user'
            )

            cls.social_user = mail_new_test_user(
                cls.env, name='Lukas Peeters', login='social_user', email='social.user@example.com',
                groups='social.group_social_user,base.group_user'
            )

            cls.user_emp = mail_new_test_user(
                cls.env, name='Eglantine Employee', login='user_emp', email='employee@example.com',
                groups='base.group_user', password='user_emp'
            )

    @classmethod
    def _get_social_media(cls):
        return None

    @classmethod
    def _get_social_account(cls):
        return cls.env['social.account'].create({
            'media_id': cls._get_social_media().id,
            'name': 'Social Account 1'
        })

    @classmethod
    def _get_post_social_accounts(cls):
        return cls.social_account | cls.env['social.account'].create({
            'media_id': cls._get_social_media().id,
            'name': 'Social Account 2'
        })

    def _checkPostedStatus(self, success):
        live_posts = self.env['social.live.post'].search([('post_id', '=', self.social_post.id)])

        self.assertEqual(len(live_posts), 2)
        self.assertTrue(all(live_post.state == 'posted' if success else 'failed' for live_post in live_posts))
        self.assertEqual(self.social_post.state, 'posted')
