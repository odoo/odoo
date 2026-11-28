# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.exceptions import ValidationError
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
        default_website = self.env.ref('base.default_website')
        page = self.env['website.page'].create({
            'type': 'qweb',
            'url': '/test_redirect_warning',
            'is_published': True,
        })

        with MockRequest(self.env, website=default_website) as mock_request:
            # the warning is computed by an onchange, i.e. during a POST rpc
            mock_request.httprequest.environ['REQUEST_METHOD'] = 'POST'

            def is_url_from_exist(url_from, website=None):
                return mock_request.env['website.rewrite'].new({
                    'redirect_type': '301',
                    'url_from': url_from,
                    'url_to': '/website/info',
                    'website_id': website.id if website else False,
                }).is_url_from_exist

            self.assertTrue(is_url_from_exist(page.url))
            self.assertTrue(is_url_from_exist(page.url.upper()), "pages are matched case-insensitively")
            self.assertTrue(is_url_from_exist(f'{page.url}/'), "the trailing slash does not change the page")

            # the visitors of a website get its own copy of a generic page
            page_copy = self.env['website.page'].create({
                'type': 'qweb',
                'url': page.url,
                'key': page.key,
                'website_id': default_website.id,
            })
            self.assertFalse(is_url_from_exist(page.url, default_website), "the copy is unpublished")
            page_copy.is_published = True
            self.assertTrue(is_url_from_exist(page.url, default_website), "the copy is published")
            page_copy.unlink()

            page.is_published = False
            self.assertFalse(is_url_from_exist(page.url), "unpublished page: the redirection is served")

            self.assertFalse(is_url_from_exist('/website/unknown_route'))
            self.assertTrue(is_url_from_exist('/website/info'))
            self.assertTrue(is_url_from_exist('/website/info?a=1'), "the query string does not change the page")
            self.assertTrue(is_url_from_exist('/my/address'), "GET-only route, matched during the POST onchange")
            self.assertTrue(is_url_from_exist('/odoo'), "not a website route")

            # the routes are the ones of the rewrite's website
            other_website = self.env['website'].create({'name': 'Other Website'})
            self.env['website.rewrite'].create({
                'redirect_type': '404',
                'url_from': '/website/info',
                'website_id': other_website.id,
            })
            self.assertFalse(is_url_from_exist('/website/info', other_website))
            self.assertTrue(is_url_from_exist('/website/info', default_website))

            # a page of another website does not shadow a bound rewrite
            page.write({'is_published': True, 'website_id': default_website.id})
            self.assertTrue(is_url_from_exist(page.url), "a redirection without website: the page is served on one of the websites")
            rewrite = self.env['website.rewrite'].create({
                'redirect_type': '301',
                'url_from': page.url,
                'url_to': '/website/info',
                'website_id': default_website.id,
            })
            self.assertTrue(rewrite.is_url_from_exist)
            rewrite.website_id = other_website
            self.assertFalse(rewrite.is_url_from_exist, "changing the website recomputes the warning")
