# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from unittest.mock import patch


@tagged('-at_install', 'post_install')
class TestRedirect(HttpCase):

    def setUp(self):
        super(TestRedirect, self).setUp()

        self.user_portal = self.env['res.users'].with_context({'no_reset_password': True}).create({
            'name': 'Test Website Portal User',
            'login': 'portal_user',
            'password': 'portal_user',
            'email': 'portal_user@mail.com',
            'group_ids': [(6, 0, [self.env.ref('base.group_portal').id])]
        })

    def test_01_redirect_308_model_converter(self):

        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '308',
            'url_from': '/test_website/country/<model("res.country"):country>',
            'url_to': '/redirected/country/<model("res.country"):country>',
        })
        country_ad = self.env.ref('base.ad')

        """ Ensure 308 redirect with model converter works fine, including:
                - Correct & working redirect as public user
                - Correct & working redirect as logged in user
                - Correct replace of url_for() URLs in DOM
        """
        url = '/test_website/country/' + self.env['ir.http']._slug(country_ad)
        redirect_url = url.replace('test_website', 'redirected')

        # [Public User] Open the original url and check redirect OK
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith(redirect_url), "Ensure URL got redirected")
        self.assertTrue(country_ad.name in r.text, "Ensure the controller returned the expected value")
        self.assertTrue(redirect_url in r.text, "Ensure the url_for has replaced the href URL in the DOM")

        # [Logged In User] Open the original url and check redirect OK
        self.authenticate("portal_user", "portal_user")
        r = self.url_open(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.url.endswith(redirect_url), "Ensure URL got redirected (2)")
        self.assertTrue('Logged In' in r.text, "Ensure logged in")
        self.assertTrue(country_ad.name in r.text, "Ensure the controller returned the expected value (2)")
        self.assertTrue(redirect_url in r.text, "Ensure the url_for has replaced the href URL in the DOM")

    def test_redirect_308_by_method_url_rewrite(self):
        self.env['website.rewrite'].create([{
            'name': 'Test Website Redirect',
            'redirect_type': '308',
            'url_from': url_from,
            'url_to': f'{url_from}_new',
        } for url_from in ('/get', '/post', '/get_post')])

        self.env.ref('test_website.test_view').arch = '''
            <t>
                <a href="/get"></a><a href="/post"></a><a href="/get_post"></a>
            </t>
        '''

        # [Public User] Open the /test_view url and ensure urls are rewritten
        r = self.url_open('/test_view')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.content.strip(),
            b'<a href="/get_new"></a><a href="/post_new"></a><a href="/get_post_new"></a>'
        )

    @mute_logger('odoo.http')  # mute 403 warning
    def test_02_redirect_308_RequestUID(self):
        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '308',
            'url_from': '/test_website/200/<model("test.model"):rec>',
            'url_to': '/test_website/308/<model("test.model"):rec>',
        })

        rec_published = self.env['test.model'].create({'name': 'name', 'website_published': True})
        rec_unpublished = self.env['test.model'].create({'name': 'name', 'website_published': False})

        WebsiteHttp = odoo.addons.website.models.ir_http.IrHttp

        def _get_error_html(env, code, value):
            return str(code).split('_')[-1], f"CUSTOM {code}"

        with patch.object(WebsiteHttp, '_get_error_html', _get_error_html):
            # Patch will avoid to display real 404 page and regenerate assets each time and unlink old one.
            # And it allow to be sur that exception id handled by handle_exception and return a "managed error" page.

            # published
            resp = self.url_open(f"/test_website/200/name-{rec_published.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), f"/test_website/308/name-{rec_published.id}")

            resp = self.url_open(f"/test_website/308/name-{rec_published.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 200)

            resp = self.url_open(f"/test_website/200/xx-{rec_published.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), f"/test_website/308/xx-{rec_published.id}")

            resp = self.url_open(f"/test_website/308/xx-{rec_published.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 301)
            self.assertURLEqual(resp.headers.get('Location'), f"/test_website/308/name-{rec_published.id}")

            resp = self.url_open(f"/test_website/200/xx-{rec_published.id}", allow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertURLEqual(resp.url, f"/test_website/308/name-{rec_published.id}")

            # unexisting
            resp = self.url_open("/test_website/200/name-100", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), "/test_website/308/name-100")

            resp = self.url_open("/test_website/308/name-100", allow_redirects=False)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.text, "CUSTOM 404")

            resp = self.url_open("/test_website/200/xx-100", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), "/test_website/308/xx-100")

            resp = self.url_open("/test_website/308/xx-100", allow_redirects=False)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.text, "CUSTOM 404")

            # unpublish
            resp = self.url_open(f"/test_website/200/name-{rec_unpublished.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), f"/test_website/308/name-{rec_unpublished.id}")

            resp = self.url_open(f"/test_website/308/name-{rec_unpublished.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.text, "CUSTOM 404")

            resp = self.url_open(f"/test_website/200/xx-{rec_unpublished.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), f"/test_website/308/xx-{rec_unpublished.id}")

            resp = self.url_open(f"/test_website/308/xx-{rec_unpublished.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.text, "CUSTOM 404")

            # with seo_name as slug
            rec_published.seo_name = "seo_name"
            rec_unpublished.seo_name = "seo_name"

            resp = self.url_open(f"/test_website/200/seo-name-{rec_published.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), f"/test_website/308/seo-name-{rec_published.id}")

            resp = self.url_open(f"/test_website/308/seo-name-{rec_published.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 200)

            resp = self.url_open(f"/test_website/200/xx-{rec_unpublished.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), f"/test_website/308/xx-{rec_unpublished.id}")

            resp = self.url_open(f"/test_website/308/xx-{rec_unpublished.id}", allow_redirects=False)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.text, "CUSTOM 404")

            resp = self.url_open("/test_website/200/xx-100", allow_redirects=False)
            self.assertEqual(resp.status_code, 308)
            self.assertURLEqual(resp.headers.get('Location'), "/test_website/308/xx-100")

            resp = self.url_open("/test_website/308/xx-100", allow_redirects=False)
            self.assertEqual(resp.status_code, 404)
            self.assertEqual(resp.text, "CUSTOM 404")

    def test_03_redirect_308_qs(self):
        self.env['website.rewrite'].create({
            'name': 'Test QS Redirect',
            'redirect_type': '308',
            'url_from': '/empty_controller_test',
            'url_to': '/empty_controller_test_redirected',
        })
        r = self.url_open('/test_website/test_redirect_view_qs?a=a')
        self.assertEqual(r.status_code, 200)
        self.assertIn(
            'href="/empty_controller_test_redirected?a=a"', r.text,
            "Redirection should have been applied, and query string should not have been duplicated.",
        )

    @mute_logger('odoo.http')  # mute 403 warning
    def test_04_redirect_301_route_unpublished_record(self):
        # 1. Accessing published record: Normal case, expecting 200
        rec1 = self.env['test.model'].create({
            'name': '301 test record',
            'is_published': True,
        })
        url_rec1 = '/test_website/200/' + self.env['ir.http']._slug(rec1)
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 200)

        # 2. Accessing unpublished record: expecting 404 for public users
        rec1.is_published = False
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 404)

        # 3. Accessing unpublished record with redirect to a 404: expecting 404
        redirect = self.env['website.rewrite'].create({
            'name': 'Test 301 Redirect route unpublished record',
            'redirect_type': '301',
            'url_from': url_rec1,
            'url_to': '/404',
        })
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 404)

        # 4. Accessing unpublished record with redirect to another published
        # record: expecting redirect to that record
        rec2 = rec1.copy({'is_published': True})
        url_rec2 = '/test_website/200/' + self.env['ir.http']._slug(rec2)
        redirect.url_to = url_rec2
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            r.url.endswith(url_rec2),
            "Unpublished record should redirect to published record set in redirect")

    @mute_logger('odoo.http')
    def test_05_redirect_404_notfound_record(self):
        # 1. Accessing unexisting record: raise 404
        url_rec1 = '/test_website/200/unexisting-100000'
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 404)

        # 2. Accessing unexisting/unpublished record with redirect to a new url: expecting 301
        redirect = self.env['website.rewrite'].create({
            'name': 'Test 301 Redirect route unexisting record',
            'redirect_type': '301',
            'url_from': url_rec1,
            'url_to': '/get',
        })
        r = self.url_open(url_rec1, allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertURLEqual(r.headers.get('Location'), redirect.url_to)

        r = self.url_open(url_rec1, allow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, redirect.url_to)

    @mute_logger('odoo.http')
    def test_06_redirect_404_unslug_record(self):
        # 1. Accessing nonexisting record: raise 404
        url_rec1 = '/test_website/200/an-old-slug-100000'
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 404)

        redirect = self.env['website.rewrite'].create({
            'name': 'Test 301 Redirect route nonexisting record',
            'redirect_type': '301',
            'url_from': '/test_website/200/100000',
            'url_to': '/get',
        })

        # 2. Accessing nonexisting record (without exact slug matching) with redirect to a new url: expecting 301
        r = self.url_open(url_rec1, allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertURLEqual(r.headers.get('Location'), redirect.url_to)

        r = self.url_open(url_rec1, allow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, redirect.url_to)

    @mute_logger('odoo.http')
    def test_07_redirect_404_unslug2slug_record(self):
        rec_unpublished = self.env['test.model'].create({'name': 'name-unpub', 'website_published': False})
        rec_published = self.env['test.model'].create({'name': 'name-pub', 'website_published': True})

        # 1. Accessing nonexisting record: raise 404
        url_rec1 = '/test_website/200/a-random-slug-%d' % rec_unpublished.id
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 404)

        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '301',
            'url_from': '/test_website/200/%d' % rec_unpublished.id,
            'url_to': '/test_website/200/%d' % rec_published.id,
        })

        # 2. Accessing nonexisting record (without exact slug matching) with redirect to an unslugified url:
        # expecting 301 to slugified record. E.g. /shop/1 => /shop/2 ==> /shop/old-prod-1 -> /shop/new-prod-2
        r = self.url_open(url_rec1, allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertURLEqual(r.headers.get('Location'), '/test_website/200/name-pub-%d' % rec_published.id)

        r = self.url_open(url_rec1, allow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, '/test_website/200/name-pub-%d' % rec_published.id)

    @mute_logger('odoo.http')
    def test_08_redirect_404_unslug_translated_record(self):
        lang_fr = self.env['res.lang']._activate_lang('fr_FR')
        self.env['website'].search([]).language_ids = self.env.ref('base.lang_en') + lang_fr
        rec_unpublished = self.env['test.model'].create({'name': 'name-unpub', 'website_published': False})
        rec_published = self.env['test.model'].create({'name': 'name-pub', 'website_published': True})
        rec_published.with_context(lang='fr_FR').name = 'nom-publié'

        # 1. Accessing nonexisting record: raise 404
        url_rec1 = '/test_website/200/another-random-slug-%d' % rec_unpublished.id
        r = self.url_open(url_rec1)
        self.assertEqual(r.status_code, 404)

        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '301',
            'url_from': '/test_website/200/%d' % rec_unpublished.id,
            'url_to': '/test_website/200/%d' % rec_published.id,
        })

        # 2. Accessing nonexisting record (without exact slug matching) with redirect to an unslugified url:
        # expecting 301 to slugified record. E.g. /shop/1 => /shop/2 ==> /shop/old-prod-1 -> /shop/new-prod-2
        r = self.url_open(url_rec1, allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertURLEqual(r.headers.get('Location'), '/test_website/200/name-pub-%d' % rec_published.id)

        # 3. Accessing translated nonexisting record (without exact slug matching) with redirect to an unslugified url:
        # expecting 301 to slugified record. E.g. /shop/1 => /shop/2 ==> /shop/old-prod-1 -> /shop/new-prod-2
        r = self.url_open('/fr' + url_rec1, allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertURLEqual(r.headers.get('Location'), '/fr/test_website/200/nom-publie-%d' % rec_published.id)

        r = self.url_open('/fr' + url_rec1, allow_redirects=True)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, '/fr/test_website/200/nom-publie-%d' % rec_published.id)

    @mute_logger('odoo.http')
    def test_09_redirect_absolute_url(self):
        urlfrom = '/test_website/200/a-new-job-20019'
        r = self.url_open(urlfrom, allow_redirects=True)
        self.assertEqual(r.status_code, 404)

        urlto = 'https://example.com/a-job'
        self.env['website.rewrite'].create({
            'name': 'Test Website Redirect',
            'redirect_type': '301',
            'url_from': urlfrom,
            'url_to': urlto,
        })

        r = self.url_open(urlfrom, allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertURLEqual(r.headers.get('Location'), urlto)

    @mute_logger('odoo.http')
    def test_10_redirect_unslug_multi_segment(self):
        # A single redirect stored in the fully-unslugged form should match a
        # slugged URL that has *several* record segments, e.g. a blog post
        # /blog/<blog>/<post>. Every record segment must be unslugged, not only
        # every other one, otherwise the redirect never matches.
        url_slugged = '/test_website/200/blog-2/post-7'
        r = self.url_open(url_slugged)
        self.assertEqual(r.status_code, 404)

        redirect = self.env['website.rewrite'].create({
            'name': 'Test 301 Redirect multi-segment unslug',
            'redirect_type': '301',
            'url_from': '/test_website/200/2/7',
            'url_to': '/get',
        })

        r = self.url_open(url_slugged, allow_redirects=False)
        self.assertEqual(r.status_code, 301)
        self.assertURLEqual(r.headers.get('Location'), redirect.url_to)

    @mute_logger('odoo.http')
    def test_redirect_308_multiple_url_endpoint(self):
        self.env['website.rewrite'].create({
            'name': 'Test Multi URL 308',
            'redirect_type': '308',
            'url_from': '/test_countries_308',
            'url_to': '/test_countries_308_redirected',
        })
        rec1 = self.env['test.model'].create({
            'name': '301 test record',
            'is_published': True,
        })
        url_rec1 = f"/test_countries_308/{self.env['ir.http']._slug(rec1)}"

        resp = self.url_open("/test_countries_308", allow_redirects=False)
        self.assertEqual(resp.status_code, 308)
        self.assertURLEqual(resp.headers.get('Location'), "/test_countries_308_redirected")

        resp = self.url_open(url_rec1)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.url.endswith(url_rec1))

    def test_redirect_with_qs(self):
        self.env['website.rewrite'].create({
            'name': 'Test 301 Redirect with qs',
            'redirect_type': '301',
            'url_from': '/foo?bar=1',
            'url_to': '/new-page-01',
        })
        self.env['website.rewrite'].create({
            'name': 'Test 301 Redirect with qs',
            'redirect_type': '301',
            'url_from': '/foo?bar=2',
            'url_to': '/new-page-10?qux=2',
        })
        self.env['website.rewrite'].create({
            'name': 'Test 301 Redirect without qs',
            'redirect_type': '301',
            'url_from': '/foo',
            'url_to': '/new-page-11',
        })

        # should match qs first
        resp = self.url_open("/foo?bar=1", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertURLEqual(resp.headers.get('Location'), "/new-page-01?bar=1")

        # should match qs first
        resp = self.url_open("/foo?bar=2", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertURLEqual(resp.headers.get('Location'), "/new-page-10?qux=2&bar=2")

        # should match no qs
        resp = self.url_open("/foo?bar=3", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertURLEqual(resp.headers.get('Location'), "/new-page-11?bar=3")

        resp = self.url_open("/foo", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertURLEqual(resp.headers.get('Location'), "/new-page-11")

        # we dont support wrong get order
        # purpose is to support simple case like content.asp?id=xx
        resp = self.url_open("/foo?oups=1&bar=2", allow_redirects=False)
        self.assertEqual(resp.status_code, 301)
        self.assertURLEqual(resp.headers.get('Location'), "/new-page-11?oups=1&bar=2")
