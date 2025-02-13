# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.website_blog.tests.common import TestWebsiteBlogCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestWebsiteBlogUi(odoo.tests.HttpCase, TestWebsiteBlogCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        blog = cls.env['blog.blog'].create({
            "name": 'aaa Blog Test',
            "subtitle": 'Blog Test Subtitle',
            "cover_properties": """{"background-image": "url('/website_blog/static/src/img/blog_1.jpeg')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0.4"}""",
        })

        blog_tag = cls.env.ref('website_blog.blog_tag_2', raise_if_not_found=False)
        if not blog_tag:
            blog_tag = cls.env['blog.tag'].create({'name': 'adventure'})
        cls.env['blog.post'].create({
            "name": "Post Test",
            "subtitle": "Subtitle Test",
            "blog_id": blog.id,
            "author_id": cls.env.user.id,
            "tag_ids": [(4, blog_tag.id)],
            "is_published": True,
            "cover_properties": """{"background-image": "url('/website_blog/static/src/img/cover_1.jpg')", "resize_class": "o_record_has_cover o_half_screen_height", "opacity": "0"}""",
        })

    def test_admin(self):
        self.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })
        # Ensure at least two blogs exist for the step asking to select a blog
        self.env['blog.blog'].create({'name': 'Travel'})

        # Ensure at least one image exists for the step that chooses one
        self.env['ir.attachment'].create({
            'public': True,
            'type': 'url',
            'url': '/web/image/123/transparent.png',
            'name': 'transparent.png',
            'mimetype': 'image/png',
        })

        self.start_tour(self.env['website'].get_client_action_url('/'), 'blog', login='admin')

    def test_blog_post_tags(self):
        self.start_tour(self.env['website'].get_client_action_url('/blog'), 'blog_tags', login='admin')

    def test_autocomplete_with_date(self):
        self.env.ref('website_blog.opt_blog_sidebar_show').active = True
        self.env.ref('website_blog.opt_sidebar_blog_index_follow_us').active = False
        self.start_tour("/blog", 'blog_autocomplete_with_date')

    def test_avatar_comment(self):
        mail_message = self.env['mail.message'].create({
            'author_id': self.user_public.partner_id.id,
            'model': self.test_blog_post._name,
            'res_id': self.test_blog_post.id,
            'subtype_id': self.ref('mail.mt_comment'),
        })
        portal_message = mail_message.portal_message_format()
        response = self.url_open(portal_message[0]['author_avatar_url'])
        # Ensure that the avatar is visible
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'image/png')
        self.assertRegex(response.headers.get('Content-Disposition', ''), r'mail_message-\d+-author_avatar\.png')

    def test_blog_access_rights(self):
        group_website_blog_manager_id = self.ref("website_blog.group_website_blog_manager")
        group_website_designer_id = self.ref("website.group_website_designer")
        group_employee_id = self.ref("base.group_user")
        self.env["res.users"].with_context({"no_reset_password": True}).create({
            "name": "Adam Blog Manager",
            "login": "adam",
            "email": "adam.manager@example.com",
            "groups_id": [(6, 0, [group_website_blog_manager_id, group_employee_id])],
        })
        self.start_tour(self.env["website"].get_client_action_url("/blog"), "blog_manager", login="adam")
        self.env["res.users"].with_context({"no_reset_password": True}).create({
            "name": "Eve Employee",
            "login": "eve",
            "email": "eve.employee@example.com",
            "groups_id": [(6, 0, [group_website_designer_id, group_employee_id])],
        })
        self.start_tour(self.env["website"].get_client_action_url("/blog"), "blog_no_manager", login="eve")
