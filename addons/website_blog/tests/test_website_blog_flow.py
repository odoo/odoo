# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_blog.tests.common import TestWebsiteBlogCommon


class TestWebsiteBlogFlow(TestWebsiteBlogCommon):

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
        test_blog = self.env['blog.blog'].sudo(self.user_blogmanager).create({
            'name': 'New Blog',
        })
        self.assertIn(
            self.user_blogmanager.partner_id, test_blog.message_partner_ids,
            'website_blog: blog create should be in the blog followers')
        test_blog.message_subscribe([self.user_employee.partner_id.id, self.user_public.partner_id.id])

        # Create a new post, blog followers should not follow the post
        test_blog_post = self.env['blog.post'].sudo(self.user_blogmanager).create({
            'name': 'New Post',
            'blog_id': test_blog.id,
        })
        self.assertNotIn(
            self.user_employee.partner_id, test_blog_post.message_partner_ids,
            'website_blog: subscribing to a blog should not subscribe to its posts')
        self.assertNotIn(
            self.user_public.partner_id, test_blog_post.message_partner_ids,
            'website_blog: subscribing to a blog should not subscribe to its posts')

        # Publish the blog
        test_blog_post.write({'website_published': True})

        # Check publish message has been sent to blog followers
        publish_message = next((m for m in test_blog_post.blog_id.message_ids if m.subtype_id.id == self.ref('website_blog.mt_blog_blog_published')), None)
        self.assertEqual(
            publish_message.needaction_partner_ids,
            self.user_employee.partner_id | self.user_public.partner_id,
            'website_blog: peuple following a blog should be notified of a published post')

        # Armand posts a message -> becomes follower
        test_blog_post.sudo().message_post(
            body='Armande BlogUser Commented',
            message_type='comment',
            author_id=self.user_employee.partner_id.id,
            subtype='mt_comment',
        )
        self.assertIn(
            self.user_employee.partner_id, test_blog_post.message_partner_ids,
            'website_blog: people commenting a post should follow it afterwards')
