# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):
    def test_admin(self):
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
