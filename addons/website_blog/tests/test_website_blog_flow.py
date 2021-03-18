# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import users
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_blog.tests.common import TestWebsiteBlogCommon
from odoo.addons.portal.controllers.mail import PortalChatter


class TestWebsiteBlogFlow(TestWebsiteBlogCommon):
    def setUp(self):
        super(TestWebsiteBlogFlow, self).setUp()
        group_portal = self.env.ref('base.group_portal')
        self.user_portal = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Dorian Portal',
            'login': 'portal_user',
            'email': 'portal_user@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [group_portal.id])]
        })

    def test_website_blog_followers(self):
        """ Test the flow of followers and notifications for blogs. Intended
        flow :

         - people subscribe to a blog
         - when creating a new post, nobody except the creator follows it
         - people subscribed to the blog does not receive comments on posts
         - when published, a notification is sent to all blog followers
         - if someone subscribe to the post or comment it, it become follower
           and receive notification for future comments. """

        # Create a new blog, subscribe the employee to the blog
        self.assertIn(
            self.user_blogmanager.partner_id, self.test_blog.message_partner_ids,
            'website_blog: blog create should be in the blog followers')
        self.test_blog.message_subscribe([self.user_employee.partner_id.id, self.user_public.partner_id.id])

        # Create a new post, blog followers should not follow the post
        self.assertNotIn(
            self.user_employee.partner_id, self.test_blog_post.message_partner_ids,
            'website_blog: subscribing to a blog should not subscribe to its posts')
        self.assertNotIn(
            self.user_public.partner_id, self.test_blog_post.message_partner_ids,
            'website_blog: subscribing to a blog should not subscribe to its posts')

        # Publish the blog
        self.test_blog_post.write({'website_published': True})

        # Check publish message has been sent to blog followers
        publish_message = next((m for m in self.test_blog_post.blog_id.message_ids if m.subtype_id.id == self.ref('website_blog.mt_blog_blog_published')), None)
        self.assertEqual(
            publish_message.notified_partner_ids,
            self.user_employee.partner_id | self.user_public.partner_id,
            'website_blog: peuple following a blog should be notified of a published post')

        # Armand posts a message -> becomes follower
        self.test_blog_post.sudo().message_post(
            body='Armande BlogUser Commented',
            message_type='comment',
            author_id=self.user_employee.partner_id.id,
            subtype_xmlid='mail.mt_comment',
        )
        self.assertIn(
            self.user_employee.partner_id, self.test_blog_post.message_partner_ids,
            'website_blog: people commenting a post should follow it afterwards')

    @users('portal_user')
    def test_blog_comment(self):
        """Test comment on blog post with attachment."""
        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'some_attachment.pdf',
            'res_model': 'mail.compose.message',
            'datas': 'test',
            'type': 'binary',
            'access_token': 'azerty',
        })

        with MockRequest(self.env):
            PortalChatter().portal_chatter_post(
                'blog.post',
                self.test_blog_post.id,
                'Test message blog post',
                attachment_ids=[attachment.id],
                attachment_tokens=[attachment.access_token]
            )

        self.assertTrue(self.env['mail.message'].sudo().search(
            [('model', '=', 'blog.post'), ('attachment_ids', 'in', attachment.ids)]))

        second_attachment = self.env['ir.attachment'].sudo().create({
            'name': 'some_attachment.pdf',
            'res_model': 'mail.compose.message',
            'datas': 'test',
            'type': 'binary',
            'access_token': 'azerty',
        })

        with self.assertRaises(UserError), MockRequest(self.env):
            PortalChatter().portal_chatter_post(
                'blog.post',
                self.test_blog_post.id,
                'Test message blog post',
                attachment_ids=[second_attachment.id],
                attachment_tokens=['wrong_token']
            )

        self.assertFalse(self.env['mail.message'].sudo().search(
            [('model', '=', 'blog.post'), ('attachment_ids', 'in', second_attachment.ids)]))
