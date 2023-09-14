# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests.common import users
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_blog.tests.common import TestWebsiteBlogCommon
from odoo.addons.mail.controllers.thread import ThreadController


class TestWebsiteBlogFlow(TestWebsiteBlogCommon):
    def setUp(self):
        super(TestWebsiteBlogFlow, self).setUp()
        group_portal = self.env.ref('base.group_portal')
        self.user_portal = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Dorian Portal',
            'login': 'portal_user',
            'email': 'portal_user@example.com',
            'notification_type': 'email',
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
        self.test_blog_post.with_user(self.user_employee).message_post(
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
            ThreadController().mail_message_post(
                'blog.post',
                self.test_blog_post.id,
                {'body': 'Test message blog post', 'attachment_ids': [attachment.id]},
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
            ThreadController().mail_message_post(
                'blog.post',
                self.test_blog_post.id,
                {'body': 'Test message blog post', 'attachment_ids': [second_attachment.id]},
                attachment_tokens=['wrong_token']
            )

        self.assertFalse(self.env['mail.message'].sudo().search(
            [('model', '=', 'blog.post'), ('attachment_ids', 'in', second_attachment.ids)]))

    def test_website_blog_teaser_content(self):
        """ Make sure that the content of the post is correctly rendered in
            proper plain text. """

        self.test_blog_post.content = "<h2>Test Content</h2>"

        self.assertEqual(self.test_blog_post.teaser, "Test Content...")


class TestWebsiteBlogTranslationFlow(TestWebsiteBlogCommon):
    def setUp(self):
        self.parseltongue = self.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        self.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [self.parseltongue.id])],
        }).lang_install()

    def test_teaser_manual(self):
        super().setUp()
        blog_post_parseltongue = self.test_blog_post.with_context(lang=self.parseltongue.code)

        # No manual teaser, ensure everything works as expected in multi langs
        self.test_blog_post.content = "English Content"
        self.test_blog_post.update_field_translations('content', {
            self.parseltongue.code: {
                "English Content": "Parseltongue Content",
            }
        })
        self.assertEqual(self.test_blog_post.teaser, "English Content...")
        self.assertEqual(blog_post_parseltongue.teaser, "Parseltongue Content...")
        self.assertFalse(self.test_blog_post.teaser_manual)
        self.assertFalse(blog_post_parseltongue.teaser_manual)

        # Manual teaser in translation but not in main lang
        blog_post_parseltongue.teaser = "Parseltongue Teaser Manual"
        self.assertEqual(self.test_blog_post.teaser, "English Content...")
        self.assertEqual(blog_post_parseltongue.teaser, "Parseltongue Teaser Manual")
        self.assertFalse(self.test_blog_post.teaser_manual)
        self.assertEqual(blog_post_parseltongue.teaser_manual, "Parseltongue Teaser Manual")

        # Manual teaser in both langs
        self.test_blog_post.teaser = "English Teaser Manual"
        self.assertEqual(self.test_blog_post.teaser, "English Teaser Manual")
        self.assertEqual(blog_post_parseltongue.teaser, "Parseltongue Teaser Manual")
        self.assertEqual(self.test_blog_post.teaser_manual, "English Teaser Manual")
        self.assertEqual(blog_post_parseltongue.teaser_manual, "Parseltongue Teaser Manual")

        # Empty manual teaser in translation, english one should remain
        blog_post_parseltongue.teaser = ""
        self.assertEqual(self.test_blog_post.teaser, "English Teaser Manual")
        self.assertEqual(blog_post_parseltongue.teaser, "Parseltongue Content...", "Should fallback again to content")
        self.assertEqual(self.test_blog_post.teaser_manual, "English Teaser Manual")
        self.assertFalse(blog_post_parseltongue.teaser_manual, "Should have been emptied")

        # Modifying content should be reflected in teaser if not manually set
        blog_post_parseltongue.content = "New Parseltongue Content"
        self.assertEqual(self.test_blog_post.teaser, "English Teaser Manual")
        self.assertEqual(blog_post_parseltongue.teaser, "New Parseltongue Content...", "Should still fallback to content")
        self.assertEqual(self.test_blog_post.teaser_manual, "English Teaser Manual")
        self.assertFalse(blog_post_parseltongue.teaser_manual, "Should still be empty")
