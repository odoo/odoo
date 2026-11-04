# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteModels(HttpCase):
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
        post.write({'is_published': True})
        rule = self.env.ref('website_blog.website_blog_post_public')
        rule.domain_force = "[('website_id', '=', website.id)]"
        res = self.url_open(post.website_url, allow_redirects=False)
        res.raise_for_status()
