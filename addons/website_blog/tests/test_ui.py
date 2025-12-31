# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
import re
from odoo.addons.website_blog.tests.common import TestWebsiteBlogCommon
from datetime import datetime


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

    def test_blog_context_and_social_media(self):
        self.env.ref('website.default_website').write({
            'social_facebook': "https://www.facebook.com/Odoo",
            'social_twitter': 'https://twitter.com/Odoo',
            'social_linkedin': 'https://www.linkedin.com/company/odoo',
            'social_youtube': 'https://www.youtube.com/user/OpenERPonline',
            'social_github': 'https://github.com/odoo',
            'social_instagram': 'https://www.instagram.com/explore/tags/odoo/',
            'social_tiktok': 'https://www.tiktok.com/@odoo',
            'social_discord': 'https://discord.com/servers/discord-town-hall-169256939211980800',
        })
        self.env.ref('website_blog.opt_blog_sidebar_show').active = True
        self.start_tour("/blog", "blog_context_and_social_media", login="admin")

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
        self.assertEqual(response.headers.get('Content-Type'), 'image/svg+xml; charset=utf-8')
        self.assertRegex(response.headers.get('Content-Disposition', ''), r'mail_message-\d+-author_avatar\.svg')

    def test_sidebar_with_date_and_tag(self):
        Blog = self.env['blog.blog']
        Post = self.env['blog.post']

        Blog1 = Blog.create({'name': 'Nature'})
        Blog2 = Blog.create({'name': 'Space'})

        # Create first blog post (Feb 2025)
        blog_post_1 = Post.create({
            'name': 'First Blog Post',
            'blog_id': Blog1.id,
            'author_id': self.env.user.id,
            'is_published': True,
            'published_date': datetime(2025, 2, 10, 12, 0, 0),
        })

        # Create second blog post (Jan 2025)
        blog_post_2 = Post.create({
            'name': 'Second Blog Post',
            'blog_id': Blog2.id,
            'author_id': self.env.user.id,
            'is_published': True,
            'published_date': datetime(2025, 1, 15, 14, 30, 0),
        })

        self.env.ref("website_blog.opt_blog_sidebar_show").active = True
        self.env.ref("website_blog.opt_blog_post_sidebar").active = True
        self.start_tour("/blog", "blog_sidebar_with_date_and_tag", login="admin")

        blog_tag = self.env.ref('website_blog.blog_tag_5', raise_if_not_found=False)
        if not blog_tag:
            blog_tag = self.env['blog.tag'].create({'name': "discovery"})
        blog_post_1.write({'tag_ids': [(4, blog_tag.id)]})
        blog_post_2.write({'tag_ids': [(4, blog_tag.id)]})

        self.start_tour("/blog", "blog_tags_with_date", login="admin")

    def test_blog_posts_dynamic_snippet_options(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'blog_posts_dynamic_snippet_options', login='admin')

    def test_blog_posts_dynamic_snippet_visibility(self):
        # Checks snippets visibility with or without content.
        def start_visibility_tour(blog_posts, publish):
            url = self.env['website'].get_client_action_url('/')
            tour_before, tour_after = ('empty', 'visible') if publish else ('visible', 'empty')
            self.start_tour(url, f'blog_posts_dynamic_snippet_{tour_before}', login='admin')
            blog_posts.write({'website_published': publish})
            self.start_tour(url, f'blog_posts_dynamic_snippet_{tour_after}', login='admin')

        # 1. Visibility for new snippets created starting from `19.0` (`o_dynamic_snippet_loading`):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'blog_posts_dynamic_snippet_edit', login='admin')
        homepage_view = self.env['ir.ui.view'].search([
            ('website_id', '=', self.env.ref('website.default_website').id),
            ('key', '=', 'website.homepage'),
        ])
        # Unpublish blog posts so the dynamic snippet can't show content.
        blog_posts = self.env['blog.post'].search([])
        blog_posts.write({'website_published': False})
        self.start_tour(self.env['website'].get_client_action_url('/'), 'blog_posts_dynamic_snippet_empty', login='admin')

        # 2. Compatibility for snippets created in `18.2` (`s_dynamic_empty`):
        homepage_view_arch_1 = homepage_view.arch_db.replace('o_dynamic_snippet_loading', 's_dynamic_empty')
        homepage_view.write({'arch': homepage_view_arch_1})
        start_visibility_tour(blog_posts, True)

        # 3. Compatibility for snippets before `18.0` and never edited (`o_dynamic_empty`):
        homepage_view_arch_2 = homepage_view.arch_db.replace('s_dynamic_empty', 'o_dynamic_empty')
        homepage_view.write({'arch': homepage_view_arch_2})
        start_visibility_tour(blog_posts, False)

        # 4. Compatibility for snippets from before `18.0` and edited in `18.0` (`o_dynamic_empty` & `o_dynamic_snippet_empty`).
        homepage_view_arch_3 = homepage_view.arch_db.replace('o_dynamic_empty', 'o_dynamic_empty o_dynamic_snippet_empty')
        homepage_view.write({'arch': homepage_view_arch_3})
        start_visibility_tour(blog_posts, True)

        # 5. Compatibility for snippets created in `18.0` and never edited (`s_dynamic_empty` & `o_dynamic_snippet_empty`).
        homepage_view_arch_4 = homepage_view.arch_db.replace('o_dynamic_empty', 's_dynamic_empty')
        homepage_view.write({'arch': homepage_view_arch_4})
        start_visibility_tour(blog_posts, False)

        # 6. Compatibility for snippets created in `19.0` and never edited (no visibility class).
        homepage_view_arch_5 = homepage_view.arch_db.replace('s_dynamic_empty o_dynamic_snippet_empty', '')
        homepage_view.write({'arch': homepage_view_arch_5})
        start_visibility_tour(blog_posts, True)

        # Visibility for misconfigured snippets.
        homepage_view_arch_misconfigured = re.sub(r'data-filter-id="\d+"', 'data-filter-id="-1"', homepage_view.arch_db)
        homepage_view.write({'arch': homepage_view_arch_misconfigured})
        self.start_tour(self.env['website'].get_client_action_url('/'), 'blog_posts_dynamic_snippet_misconfigured', login='admin')
