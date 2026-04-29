# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.models.website import Website as WebsiteModel
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteModels(HttpCase):
    def test_access_with_website_record_rule(self):
        blog = self.env['blog.blog'].create({
            'name': 'test blog',
            'website_id': self.ref('base.default_website'),
        })
        post = self.env['blog.post'].create({
            'name': 'test post',
            'blog_id': blog.id,
        })
        post.write({'is_published': True})
        rule = self.env.ref('website_blog.website_blog_post_public')
        rule.domain = "[('website_id', '=', website.id)]"
        res = self.url_open(post.website_url, allow_redirects=False)
        res.raise_for_status()

    def test_highest_priority_cta_button_candidate_wins(self):
        self.patch(WebsiteModel, '_get_cta_candidates', lambda website, website_type: [
            (999, {'cta_btn_text': "Test CTA", 'cta_btn_href': '/test_cta'}),
        ])
        cta_data = self.env.ref('base.default_website').get_cta_data('blog')
        self.assertEqual(cta_data['cta_btn_text'], "Test CTA")
        self.assertEqual(cta_data['cta_btn_href'], '/test_cta')
        self.assertEqual(cta_data['shop_btn_href'], '/shop')
