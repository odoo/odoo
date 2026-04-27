# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.social.tests import common
from odoo.addons.social.tests.tools import mock_void_external_calls
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import users


class TestSocialMultiCompany(common.SocialCase):
    @classmethod
    def setUpClass(cls):
        super(TestSocialMultiCompany, cls).setUpClass()

        with mock_void_external_calls():
            cls.media_id = cls.env['social.media'].create({'name': 'Social Media'})

            cls.company_1 = cls.social_manager.company_id
            cls.company_2 = cls.env['res.company'].create({'name': 'Company 2'})

            cls.account_1, cls.account_2 = cls.social_accounts
            cls.account_1.company_id = cls.company_1
            cls.account_2.company_id = cls.company_2

            cls.account_3 = cls.env['social.account'].create({
                'name': 'Account 3',
                'media_id': cls.media_id.id,
                'company_id': False,
            })

            cls.stream_type_id = cls.env['social.stream.type'].create({
                'name': 'Stream Type',
                'stream_type': 'stream_type',
                'media_id': cls.media_id.id,
            })

            cls.stream_1 = cls.env['social.stream'].create({
                'name': 'Stream 1',
                'media_id': cls.media_id.id,
                'account_id': cls.account_1.id,
                'stream_type_id': cls.stream_type_id.id,
            })
            cls.stream_2 = cls.env['social.stream'].create({
                'name': 'Stream 2',
                'media_id': cls.media_id.id,
                'account_id': cls.account_2.id,
                'stream_type_id': cls.stream_type_id.id,
            })

            cls.stream_post_1 = cls.env['social.stream.post'].create({
                'stream_id': cls.stream_1.id,
            })

            cls.stream_post_2 = cls.env['social.stream.post'].create({
                'stream_id': cls.stream_2.id,
            })

            cls.social_manager.company_ids |= cls.company_1 | cls.company_2

            cls.social_manager_2 = cls.social_manager.copy()
            cls.social_manager_2.company_id = cls.company_2
            cls.social_manager_2.company_ids = cls.company_2

            cls.social_user.company_ids |= cls.company_1

    @classmethod
    def _get_social_media(cls):
        return cls.env['social.media'].create({'name': 'Social Media'})

    @users('social_manager')
    @mock_void_external_calls()
    def test_allowed_company_ids(self):
        """If no company is set on the post, we should see the social accounts based on
        the ACLs (so the social manager should be able to see all social accounts).

        If a company is set, we should be able to see only account in this company or
        without a company.
        """
        post_1 = self.env['social.post'].create({
            'message': 'test',
            'company_id': False,
        })
        self.assertEqual(self.account_1 | self.account_2 | self.account_3, post_1.account_allowed_ids)

        post_2 = self.env['social.post'].create({
            'message': 'test',
            'company_id': self.company_1.id,
        })
        self.assertEqual(self.account_1 | self.account_3, post_2.account_allowed_ids)

        with self.assertRaises(ValidationError, msg='Should not be able to add a social account of an other company'):
            post_2.account_ids |= self.account_2

    @users('social_user')
    @mock_void_external_calls()
    def test_social_account_acls(self):
        """Test the company based ACLs of the <social.account>."""
        self.assertEqual(self.account_1.company_id, self.company_1)
        self.assertEqual(self.account_2.company_id, self.company_2)

        result = self.env['social.account'].search([])

        # The social user is in the company 1 but not in the company 2
        self.assertEqual(self.account_1 | self.account_3, result)

        self.assertEqual(
            self.env['social.account'].browse(self.account_1.id).name,
            'Social Account 1',
            'Should be able to read the account of the company',
        )

        self.env.invalidate_all()
        with self.assertRaises(AccessError, msg='Should not be able to read the account of an other company'):
            self.env['social.account'].browse(self.account_2.id).name

    @users('social_manager')
    @mock_void_external_calls()
    def test_social_post_acls(self):
        # Create a social post with a message on 2 different accounts
        # In 2 different companies
        post = self.env['social.post'].create({
            'message': 'Test message',
            'account_ids': (self.account_1 | self.account_2).ids,
            'company_id': False,
        })

        self.assertFalse(post.company_id)

        post.action_post()

        self.env.invalidate_all()

        self.assertEqual(
            len(post.with_user(self.social_manager_2).live_post_ids),
            1,
            'The post is read by the social user who is in the company 2. '
            'He should not see the live post which belongs to the company 1.'
        )

        self.env.invalidate_all()

        self.assertEqual(
            len(post.live_post_ids),
            2,
            'The post is read by the social user who is in both companies. '
            'He should see the live post of both companies.'
        )

    @users('social_manager')
    @mock_void_external_calls()
    def test_social_post_click_count(self):
        # An UTM medium is created for each social account
        # That's how we can compute the click based on the current company
        self.assertTrue(self.account_1.utm_medium_id)
        self.assertTrue(self.account_2.utm_medium_id)
        self.assertNotEqual(self.account_1.utm_medium_id, self.account_2.utm_medium_id)

        url = 'https://odoo.com/test/click/count/computation'
        message = f"""
            Hi social users :)
            Visit {url}
        """

        post = self.env['social.post'].create({
            'message': message,
            'account_ids': (self.account_1 | self.account_2).ids,
            'company_id': False,
        })

        self.assertFalse(post.company_id)

        post.action_post()

        live_post_1 = post.live_post_ids.filtered(lambda l: l.company_id == self.company_1)
        live_post_2 = post.live_post_ids.filtered(lambda l: l.company_id == self.company_2)

        self.assertEqual(len(live_post_1), 1)
        self.assertEqual(len(live_post_2), 1)

        self.env['mail.render.mixin'].sudo()._shorten_links_text(post.message, live_post_1._get_utm_values())
        link_tracker_1 = self.env['link.tracker'].search([('url', '=', url), ('medium_id', '=', self.account_1.utm_medium_id.id)])

        self.env['mail.render.mixin'].sudo()._shorten_links_text(post.message, live_post_2._get_utm_values())
        link_tracker_2 = self.env['link.tracker'].search([('url', '=', url), ('medium_id', '=', self.account_2.utm_medium_id.id)])

        self.assertEqual(len(link_tracker_1), 1)
        self.assertEqual(len(link_tracker_2), 1)

        # 13 clicks on the first account, in the first company
        self.env['link.tracker.click'].sudo().create([{'link_id': link_tracker_1.id} for _ in range(13)])
        # 7 clicks on the first account, in the first company
        self.env['link.tracker.click'].sudo().create([{'link_id': link_tracker_2.id} for _ in range(7)])

        self.assertEqual(link_tracker_1.count, 13)
        self.assertEqual(link_tracker_2.count, 7)

        self.env.invalidate_all()
        self.assertEqual(post.click_count, 20, 'There should be 20 clicks across all the companies')
        self.env.invalidate_all()
        self.assertEqual(post.with_company(self.company_1).click_count, 13, 'There should be 13 clicks for a user who is only in the first company')
        self.env.invalidate_all()
        self.assertEqual(post.with_company(self.company_2).click_count, 7, 'There should be 7 clicks for a user who is only in the second company')

    @users('social_user')
    @mock_void_external_calls()
    def test_social_stream_post_acls(self):
        self.env.invalidate_all()

        result = self.env['social.stream.post'].search([])
        self.assertEqual(self.stream_post_1, result)

        self.env.invalidate_all()

        result = self.env['social.stream.post'].with_user(self.social_manager).search([])
        self.assertEqual(self.stream_post_1 | self.stream_post_2, result)
