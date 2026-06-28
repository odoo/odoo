# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import users, HttpCase, tagged, TransactionCase
from odoo.addons.http_routing.tests.common import MockRequest
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
            'group_ids': [(6, 0, [group_portal.id])]
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

        # Publish the blog post at a future date
        self.test_blog_post.write({"website_published": False, "publish_on": '2050-01-01 00:00:00', "published_date": False})

        publish_message = next((m for m in self.test_blog_post.blog_id.message_ids if m.subtype_id.id == self.ref('website_blog.mt_blog_blog_published')), None)
        self.assertTrue(
            not publish_message or publish_message.notified_partner_ids != (self.user_employee.partner_id | self.user_public.partner_id),
            'website_blog: people following a blog should not be notified of a post that will be published in the future')

        # Publish the blog post now
        self.test_blog_post.write({"website_published": True, "publish_on": False, "published_date": False})

        # Check publish message has been sent to blog followers
        publish_message = next((m for m in self.test_blog_post.blog_id.message_ids if m.subtype_id.id == self.ref('website_blog.mt_blog_blog_published')), None)
        self.assertTrue(publish_message)
        self.assertEqual(
            publish_message.notified_partner_ids,
            self.user_employee.partner_id | self.user_public.partner_id,
            'website_blog: people following a blog should be notified of a published post')

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
            'raw': b'test',
            'type': 'binary',
        })

        with MockRequest(self.env):
            ThreadController().mail_message_post(
                "blog.post",
                self.test_blog_post.id,
                {
                    "body": "Test message blog post",
                    "attachment_ids": [attachment.id],
                    "attachment_tokens": [attachment._get_ownership_token()],
                },
            )

        self.assertTrue(self.env['mail.message'].sudo().search(
            [('model', '=', 'blog.post'), ('attachment_ids', 'in', attachment.ids)]))

        second_attachment = self.env['ir.attachment'].sudo().create({
            'name': 'some_attachment.pdf',
            'res_model': 'mail.compose.message',
            'raw': b'test',
            'type': 'binary',
        })

        with self.assertRaises(UserError), MockRequest(self.env):
            ThreadController().mail_message_post(
                "blog.post",
                self.test_blog_post.id,
                {
                    "body": "Test message blog post",
                    "attachment_ids": [second_attachment.id],
                    "attachment_tokens": ["wrong_token"],
                },
            )

        self.assertFalse(self.env['mail.message'].sudo().search(
            [('model', '=', 'blog.post'), ('attachment_ids', 'in', second_attachment.ids)]))

    def test_blog_notification_website_domain(self):
        backend_domain = 'https://backend.example'
        self.env['ir.config_parameter'].sudo().set_str('web.base.url', backend_domain)
        rendered_html = self.env['ir.qweb']._render(
            'website_blog.blog_post_template_new_post',
            {
                'post': self.test_blog_post,
                'object': self.test_blog,
            }
        )
        self.assertIn(f'href="{backend_domain}/blog/', rendered_html)

        frontend_domain = 'https://frontend.example'
        website = self.env['website'].search([], limit=1)
        website.domain = frontend_domain
        self.test_blog.website_id = website
        rendered_html = self.env['ir.qweb']._render(
            'website_blog.blog_post_template_new_post',
            {
                'post': self.test_blog_post,
                'object': self.test_blog,
            }
        )
        self.assertIn(f'href="{frontend_domain}/blog/', rendered_html)

    def test_website_blog_teaser_content(self):
        """ Make sure that the content of the post is correctly rendered in
            proper plain text. """

        self.test_blog_post.content = "<h2>Test Content</h2>"

        self.assertEqual(self.test_blog_post.teaser, "Test Content...")


@tagged('-at_install', 'post_install')
class TestWebsiteBlogTranslationFlow(HttpCase, TestWebsiteBlogCommon):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parseltongue = cls.env['res.lang'].create({
            'name': 'Parseltongue',
            'code': 'pa_GB',
            'iso_code': 'pa_GB',
            'url_code': 'pa_GB',
        })
        cls.env["base.language.install"].create({
            'overwrite': True,
            'lang_ids': [(6, 0, [cls.parseltongue.id])],
        }).lang_install()
        cls.headers = {"Content-Type": "application/json"}

    def test_teaser_manual(self):
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

    def test_update_field_translation(self):
        """Test updating the translated text when default lang isn't en_US"""
        self.authenticate('admin', 'admin')

        # Setup
        br_lang = self.env['res.lang']._activate_lang('pt_BR')
        en_lang = self.env['res.lang']._activate_lang('en_US')

        website = self.env.ref('base.default_website')
        website.language_ids += br_lang
        website.default_lang_id = br_lang

        blog_post = self.env['blog.post'].with_context(lang=br_lang.code).create({
            'name':'Test Blog',
            'content':'Todos os blogs', 
        })
        # sha256 encoding of 'Todos os blogs'
        sha = 'c10cb3d9aeec6fe03ed86f24efb262c65ed9de7e9263db1605e3196c343de7a3'

        # Ensure that initial translations for 'en_US' and 'pt_BR' are different
        blog_post.update_field_translations('content', {
            en_lang.code: {'Todos os blogs' : 'All blogs'}
        })
        self.assertEqual('Todos os blogs', blog_post.with_context(lang=br_lang.code).content)
        self.assertEqual('All blogs', blog_post.with_context(lang=en_lang.code).content)

        # Test updating translation
        payload = self.build_rpc_payload({
            'model': blog_post._name,
            'record_id': blog_post.id,
            'field_name': 'content',
            'translations': {en_lang.code: {sha: 'Updated blogs'}},
        })
        self.url_open('/website/field/translation/update', data=json.dumps(payload), headers=self.headers)
        self.assertEqual('Todos os blogs', blog_post.with_context(lang=br_lang.code).content)
        self.assertEqual('Updated blogs', blog_post.with_context(lang=en_lang.code).content)

    def test_url_with_falsy_value(self):
        """Test that accessing a tag without id in the url does not crash."""
        blog = self.env['blog.blog'].create({'name': 'Test Blog'})
        blog_tag = self.env['blog.tag'].create({'name': 'demo'})
        self.env['blog.post'].create({
            'name': 'Test Blog Post',
            'blog_id': blog.id,
            'tag_ids': [(6, 0, [blog_tag.id])],
            'author_id': self.env.user.partner_id.id,
            'is_published': True,
        })
        response = self.url_open('/blog/tag/demo')
        self.assertEqual(response.status_code, 200)

    def test_cannot_delete_field_used_in_website_blog(self):
        self.partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')])
        self.test_field = self.env['ir.model.fields'].create({
            'name': 'x_test_field',
            'model_id': self.partner_model.id,
            'ttype': 'char',
            'field_description': 'test',
        })
        self.env['blog.post'].create({
            'name': 'Test Blog',
            'content': f'''
                <form data-model_name="res.partner">
                    <input name="{self.test_field.name}">
                </form>
            ''',
        })
        with self.assertRaisesRegex(ValidationError, f"The field '{self.test_field.name}' cannot be deleted because it is referenced in a website view."):
            self.test_field.unlink()

        self.assertTrue(self.test_field.exists())


@tagged("-at_install", "post_install")
class TestBlogSearch(TransactionCase):

    def setUp(self):
        super().setUp()
        self.website = self.env.ref("base.default_website")
        # Blog
        self.blog = self.env['blog.blog'].create({
            'name': 'Test Blog',
        })
        # Categories
        self.cat_a = self.env['blog.tag.category'].create({'name': 'Cat A'})
        self.cat_b = self.env['blog.tag.category'].create({'name': 'Cat B'})
        # Tags
        self.tag_a1 = self.env['blog.tag'].create({
            'name': 'A1',
            'category_id': self.cat_a.id,
        })
        self.tag_a2 = self.env['blog.tag'].create({
            'name': 'A2',
            'category_id': self.cat_a.id,
        })
        self.tag_b1 = self.env['blog.tag'].create({
            'name': 'B1',
            'category_id': self.cat_b.id,
        })
        # Posts
        self.post_a1 = self.env['blog.post'].create({
            'name': 'Post A1',
            'blog_id': self.blog.id,
            'tag_ids': [(6, 0, [self.tag_a1.id])],
            'website_published': True,
        })
        self.post_a2 = self.env['blog.post'].create({
            'name': 'Post A2',
            'blog_id': self.blog.id,
            'tag_ids': [(6, 0, [self.tag_a2.id])],
            'website_published': True,
        })
        self.post_a1_b1 = self.env['blog.post'].create({
            'name': 'Post A1 B1',
            'blog_id': self.blog.id,
            'tag_ids': [(6, 0, [self.tag_a1.id, self.tag_b1.id])],
            'website_published': True,
        })

    def test_tag_same_category_or(self):
        """A1 + A2 => OR logic"""
        options = {
            "tag": f"{self.tag_a1.id},{self.tag_a2.id}",
        }
        results_count, details, _ = self.website._search_with_fuzzy(
            "blog_post", "", 0, 10, "name asc", options
        )
        results = details[0].get('results', [])
        self.assertEqual(results_count, 3, "Should return all posts with A1 or A2")
        self.assertIn(self.post_a1, results)
        self.assertIn(self.post_a2, results)
        self.assertIn(self.post_a1_b1, results)

    def test_tag_cross_category_and(self):
        """A1 + B1 => AND logic"""
        options = {
            "tag": f"{self.tag_a1.id},{self.tag_b1.id}",
        }
        results_count, details, _ = self.website._search_with_fuzzy(
            "blog_post", "", 0, 10, "name asc", options
        )
        results = details[0].get('results', [])
        self.assertEqual(results_count, 1, "Should return only posts matching both categories")
        self.assertNotIn(self.post_a1, results)
        self.assertNotIn(self.post_a2, results)
        self.assertIn(self.post_a1_b1, results)

    def test_tag_single(self):
        options = {
            "tag": f"{self.tag_a1.id}",
        }
        results_count, details, _ = self.website._search_with_fuzzy(
            "blog_post", "", 0, 10, "name asc", options
        )
        results = details[0].get('results', [])
        self.assertEqual(results_count, 2)
        self.assertIn(self.post_a1, results)
        self.assertNotIn(self.post_a2, results)
        self.assertIn(self.post_a1_b1, results)
