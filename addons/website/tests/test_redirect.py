# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tools import MockRequest
from odoo.models import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestWebsiteRedirect(TransactionCase):
    def test_01_website_redirect_validation(self):
        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/',
            })
        self.assertIn('homepage', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/favicon.ico',
            })
        self.assertIn('existing page', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '308',
                'url_from': '/website/info',
                'url_to': '/favicon.ico/',  # trailing slash on purpose
            })
        self.assertIn('existing page', str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '301',
                'url_from': '/website/info',
                'url_to': '#',
            })
        self.assertIn("must not start with '#'", str(error.exception))

        with self.assertRaises(ValidationError) as error:
            self.env['website.rewrite'].create({
                'name': 'Test Website Redirect',
                'redirect_type': '301',
                'url_from': '/website/info',
                'url_to': '/website/info',
            })
        self.assertIn("should not be same", str(error.exception))

    def test_sitemap_with_redirect(self):
        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '308',
            'url_from': '/website/info',
            'url_to': '/test',
        })
        website = self.env.ref('website.default_website')
        with MockRequest(self.env, website=website):
            self.env['website.rewrite'].refresh_routes()
            pages = self.env.ref('website.default_website')._enumerate_pages()
            urls = [url['loc'] for url in pages]
            self.assertIn('/website/info', urls)
            self.assertNotIn('/test', urls)
