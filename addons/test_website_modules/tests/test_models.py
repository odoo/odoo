# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests


@tests.tagged('-at_install', 'post_install')
class TestWebsiteModels(tests.HttpCase):
    def test_access_with_website_record_rule(self):
        website = self.env['website'].get_current_website()
        blog = self.env['blog.blog'].create({
            'name': 'test blog',
            'website_id': website.id,
        })
        post = self.env['blog.post'].create({
            'name': 'test post',
            'blog_id': blog.id,
        })
        rule = self.env.ref('website_blog.website_blog_post_public')
        rule.domain_force = "[('website_id', '=', website.id)]"
        res = self.url_open(f'{post.website_url}')
        self.assertEqual(res.status_code, 200, "Should have access to the blog post")
