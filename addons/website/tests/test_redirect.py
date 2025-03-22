# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tools import MockRequest
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteRedirect(TransactionCase):
    def test_sitemap_with_redirect(self):
        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '308',
            'url_from': '/website/info',
            'url_to': '/test',
        })
        website = self.env.ref('website.default_website')
        with MockRequest(self.env, website=website):
            pages = self.env.ref('website.default_website')._enumerate_pages()
            urls = [url['loc'] for url in pages]
            self.assertIn('/website/info', urls)
            self.assertNotIn('/test', urls)
