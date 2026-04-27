# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.social.tests import common
from odoo.addons.social.tests.tools import mock_void_external_calls
from odoo.tests import Form, users


class TestSocialCrmConvert(common.SocialCase):
    @classmethod
    def setUpClass(cls):
        with mock_void_external_calls():
            super(TestSocialCrmConvert, cls).setUpClass()

            cls.user_social_crm = mail_new_test_user(
                cls.env, login='user_social_crm',
                name='Christine SocialUser', email='christine.socialuser@test.example.com',
                tz='Europe/Brussels', notification_type='inbox',
                company_id=cls.env.ref("base.main_company").id,
                groups='base.group_user,social.group_social_user,base.group_partner_manager',
            )

            cls.utm_campaign_id = cls.env['utm.campaign'].create({
                'name': 'Social Campaign'
            })

            cls.social_stream = cls.env['social.stream'].create({
                'name': 'Social Stream',
                'stream_type_id': cls.env.ref('social_facebook.stream_type_page_posts').id,
                'media_id': cls._get_social_media().id,
                'account_id': cls.social_account.id
            })

            cls.social_post.write({
                'utm_campaign_id': cls.utm_campaign_id.id,
            })

            cls.social_live_post = cls.env['social.live.post'].create({
                'post_id': cls.social_post.id,
                'account_id': cls.social_account.id,
                'facebook_post_id': 'abc123'
            })

            cls.social_stream_post = cls.env['social.stream.post'].create({
                'author_name': 'John Doe',
                'stream_id': cls.social_stream.id,
            })

    @classmethod
    def _get_social_media(cls):
        return cls.env.ref('social_facebook.social_media_facebook')

    @users('user_social_crm')
    @mock_void_external_calls()
    def test_social_crm_convert_from_post(self):
        """ When converting from a stream.post with a matching social.post, the wizard will be
        initialized with the data from the stream.post and the resulting lead after conversion will
        have as UTMs: the same campaign as the social.post, the medium from the related
        social.account and the source as the social.post's source.

        Since we found a perfect match on a single partner, the action will be set to 'exist' and
        the partner_id will be initialized with this partner. """

        self.social_stream_post.write({'facebook_post_id': 'abc123'})
        john_doe = self.env['res.partner'].sudo().create({'name': 'John Doe'})
        # <form string="Convert Post to Lead">
        #     ...
        #             <field name="conversion_source" invisible="1"/>
        #             <field name="post_content" invisible="1"/>
        #             ...
        #             <field name="social_account_id" invisible="1"/>
        #             <field name="social_stream_post_id" invisible="1"/>
        #     ...
        # </form>
        convert_wizard_form = Form(self.env['social.post.to.lead'].with_context(
            default_social_account_id=self.social_account,
            default_social_stream_post_id=self.social_stream_post,
            default_conversion_source='stream_post',
            default_post_content='Hello',
        ))

        convert_wizard = convert_wizard_form.save()
        self.assertEqual(convert_wizard.post_datetime, self.social_stream_post.published_date)
        self.assertEqual(convert_wizard.post_link, self.social_stream_post.post_link)
        self.assertEqual(convert_wizard.partner_id, john_doe)
        self.assertEqual(convert_wizard.author_name, 'John Doe')
        self.assertEqual(convert_wizard.action, 'exist')

        convert_wizard.action_convert_to_lead()
        created_lead = self.env['crm.lead'].sudo().search([('partner_id', '=', john_doe.id)])
        self.assertEqual(len(created_lead), 1)
        self.assertEqual(created_lead.campaign_id, self.utm_campaign_id)
        self.assertEqual(created_lead.medium_id, self.social_account.utm_medium_id)
        self.assertEqual(created_lead.source_id, self.social_post.source_id)

    @users('user_social_crm')
    @mock_void_external_calls()
    def test_social_crm_convert_from_comment(self):
        """ When converting from a comment the resulting lead after conversion will have as UTMs:
        no campaign, the medium from the related social.account and source set to our master data. """

        self.env['res.partner'].sudo().create({'name': 'Doug'})
        convert_wizard_form = Form(self.env['social.post.to.lead'].with_context(
            default_social_account_id=self.social_account.id,
            default_social_stream_post_id=self.social_stream_post.id,
            default_conversion_source='comment',
            default_post_content='Hello',
            default_author_name='Jack',
            default_post_link='https://www.facebook.com/1',
        ))
        convert_wizard = convert_wizard_form.save()
        self.assertEqual(convert_wizard.action, 'create')
        self.assertFalse(convert_wizard.partner_id)

        convert_wizard.action_convert_to_lead()
        created_lead = self.env['crm.lead'].sudo().search([('partner_id', '=', convert_wizard.partner_id.id)])
        self.assertEqual(len(created_lead), 1)
        self.assertFalse(created_lead.campaign_id)
        self.assertEqual(created_lead.medium_id, self.social_account.utm_medium_id)
        self.assertEqual(created_lead.source_id, self.env.ref('social_crm.utm_source_social_post'))
