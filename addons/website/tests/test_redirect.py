# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.exceptions import ValidationError
from odoo.http import request
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
        website = self.env.ref('base.default_website')
        with MockRequest(self.env, website=website) as request:
            request.env['website.rewrite'].refresh_routes()
            pages = request.env.ref('base.default_website')._enumerate_pages()
            urls = [url['loc'] for url in pages]
            self.assertNotIn('/test', urls)

    def test_url_from_exist_warning(self):
        page = self.env['website.page'].create({
            'name': 'Test Redirect Warning',
            'type': 'qweb',
            'key': 'test.redirect_warning',
            'arch': '<div>Test</div>',
            'url': '/test_redirect_warning',
            'is_published': True,
        })

        def is_url_from_exist(url_from, website=None):
            return self.env['website.rewrite'].new({
                'redirect_type': '301',
                'url_from': url_from,
                'url_to': '/website/info',
                'website_id': website.id if website else False,
            }).is_url_from_exist

        with MockRequest(self.env, website=self.env.ref('base.default_website')):
            # the warning is computed by an onchange, i.e. during a POST rpc
            request.httprequest.environ['REQUEST_METHOD'] = 'POST'

            self.assertTrue(is_url_from_exist(page.url))
            page.is_published = False
            self.assertFalse(is_url_from_exist(page.url), "unpublished page: the redirection is served")

            self.assertFalse(is_url_from_exist('/website/unknown_route'))
            self.assertTrue(is_url_from_exist('/website/info'))

            # frontend route: a missing record ends up in a 404, hence served
            country_url = '/website/country_infos/%s'
            self.assertTrue(is_url_from_exist(country_url % self.env.ref('base.be').id))
            self.assertFalse(is_url_from_exist(country_url % 999999))

            # a page of another website does not shadow a bound rewrite
            page.write({'is_published': True, 'website_id': self.env.ref('base.default_website').id})
            other_website = self.env['website'].create({'name': 'Other Website'})
            self.assertFalse(is_url_from_exist(page.url, other_website))
            self.assertTrue(is_url_from_exist(page.url, self.env.ref('base.default_website')))
