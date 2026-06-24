# Part of Odoo. See LICENSE file for full copyright and licensing details.

import functools
from unittest.mock import patch

from lxml import html

from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.website.models.ir_http import sitemap_group
from odoo.addons.website.tests.common import all_sitemap_urls


@tagged('-at_install', 'post_install')
class TestWebsiteSitemap(TransactionCase):
    def test_sitemap_page_lastmod(self):
        website = self.env.ref('base.default_website')
        website = website.with_context(website_id=website.id)

        page_url = '/test-page'
        Page = self.env['website.page']
        page = Page.create({
            'name': 'Test Page',
            'website_id': website.id,
            'url': page_url,
            'type': 'qweb',
            'arch': '<t t-call="website.layout"/>',
            'is_published': True,
        })
        View = self.env['ir.ui.view']

        def set_write_dates(page_date, view_date):
            self.env.cr.execute(
                "UPDATE website_page SET write_date = %s WHERE id = %s",
                (page_date, page.id)
            )
            self.env.cr.execute(
                "UPDATE ir_ui_view SET write_date = %s WHERE id = %s",
                (view_date, page.view_id.id)
            )
            View.invalidate_model(['write_date'])
            Page.invalidate_model(['write_date', 'view_write_date'])
            self.assertEqual(str(page.write_date), page_date)
            self.assertEqual(str(page.view_id.write_date), view_date)

        def get_sitemap_lastmod():
            pages = website._enumerate_pages()
            return next(p['lastmod'] for p in pages if p['loc'] == page_url)

        old_date = "2002-05-06 12:00:00"

        new_date = "2014-05-15 12:00:00"
        set_write_dates(new_date, old_date)
        self.assertEqual(str(get_sitemap_lastmod()), new_date[:10])

        new_date2 = "2015-10-01 12:00:00"
        set_write_dates(old_date, new_date2)
        self.assertEqual(str(get_sitemap_lastmod()), new_date2[:10])

    def test_sitemap_dedup_overridden_controllers(self):
        website = self.env['website'].search([], limit=1)

        # Fake router and rule to simulate two sitemap entries with and without trailing slash
        def fake_sitemap_callable(env, rule, qs):
            yield {'loc': '/dupe'}
            yield {'loc': '/dupe/'}

        class FakeEndpoint:
            routing = {'sitemap': fake_sitemap_callable}

        class FakeRule:
            endpoint = FakeEndpoint()
            _converters = {}

        class FakeRouter:
            def iter_rules(self):
                return [FakeRule()]

        # Patch routing_map to return our fake router so only our fake rules are considered
        with patch('odoo.addons.website.models.ir_http.IrHttp.routing_map', autospec=True, return_value=FakeRouter()):
            locs = list(website.with_user(website.user_id)._enumerate_pages())

        dupes = [l['loc'] for l in locs if l['loc'].startswith('/dupe')]
        # Only one entry should remain, normalized to '/dupe'
        self.assertEqual(dupes, ['/dupe'])

    def test_sitemap_callable_dedup_with_partial_and_bound(self):
        # Some routes are duplicated at runtime (e.g., when a redirect
        # is configured). The framework may clone an existing endpoint for the
        # extra rule, and 3rd-party modules sometimes wrap callables using
        # `functools.partial` to adapt them.
        # As a result, the very same sitemap generator can be referenced in two
        # different ways: once as a classic bound method (self.sitemap) and once
        # as a `functools.partial(self.sitemap)` wrapper.
        # If we were deduplicating based on the callable object identity only,
        # those two references would look different and the sitemap code could
        # run twice.
        website = self.env['website'].search([], limit=1)

        call_count = {'n': 0}  # mutable object to be used in CallableHolder.

        class CallableHolder:
            def sitemap(self, env, rule, qs):
                call_count['n'] += 1
                yield {'loc': '/once'}

        holder = CallableHolder()

        # First rule uses the bound method directly
        class EndpointBound:
            routing = {'sitemap': holder.sitemap}

        class RuleBound:
            endpoint = EndpointBound()
            _converters = {}

        # Second rule uses a partial wrapping the same bound method
        class EndpointPartial:
            routing = {'sitemap': functools.partial(holder.sitemap)}

        class RulePartial:
            endpoint = EndpointPartial()
            _converters = {}

        class FakeRouter:
            def iter_rules(self):
                return [RuleBound(), RulePartial()]

        with patch('odoo.addons.website.models.ir_http.IrHttp.routing_map', autospec=True, return_value=FakeRouter()):
            locs = list(website.with_user(website.user_id)._enumerate_pages())

        # The sitemap callable should have been executed only once
        self.assertEqual(call_count['n'], 1)
        # And the returned loc should be present (normalized already)
        self.assertIn('/once', [loc['loc'] for loc in locs])

    def test_sitemap_group_tagging(self):
        website = self.env.ref('base.default_website')
        page = self.env['website.page'].create({
            'name': 'Grouped Page',
            'website_id': website.id,
            'url': '/grp-test',
            'type': 'qweb',
            'arch': '<t t-call="website.layout"/>',
            'is_published': True,
        })
        locs = list(website.with_user(website.user_id)._enumerate_pages())
        # Every entry must be tagged with a group so the controller can split.
        self.assertTrue(all('group' in loc for loc in locs))
        # CMS pages are website-core content, bucketed under 'pages'.
        page_loc = next(loc for loc in locs if loc['loc'] == page.url)
        self.assertEqual(page_loc['group'], 'pages')

    def test_sitemap_group_explicit_name(self):
        # @sitemap_group must win over the module-derived default.
        website = self.env['website'].search([], limit=1)

        @sitemap_group('my-section')
        def fake_sitemap_callable(env, rule, qs):
            yield {'loc': '/named'}

        class FakeEndpoint:
            routing = {'sitemap': fake_sitemap_callable}

        class FakeRule:
            endpoint = FakeEndpoint()
            _converters = {}

        class FakeRouter:
            def iter_rules(self):
                return [FakeRule()]

        with patch('odoo.addons.website.models.ir_http.IrHttp.routing_map', autospec=True, return_value=FakeRouter()):
            locs = list(website.with_user(website.user_id)._enumerate_pages())

        loc = next(l for l in locs if l['loc'] == '/named')
        self.assertEqual(loc['group'], 'my-section', "@sitemap_group must set the sitemap group")

    def test_enumerate_pages_homepage_filtering(self):
        website = self.env.ref('base.default_website')
        homepage_url = '/custom-homepage'
        self.env['website.page'].create({
            'name': 'Custom Homepage',
            'website_id': website.id,
            'url': homepage_url,
            'type': 'qweb',
            'arch': '<t t-call="website.layout"/>',
            'is_published': True,
        })
        website.homepage_url = homepage_url

        locs_with_homepage = list(website.with_user(website.user_id)._enumerate_pages())
        locs_with_homepage_urls = [page['loc'] for page in locs_with_homepage]
        self.assertIn('/', locs_with_homepage_urls)
        self.assertIn(homepage_url, locs_with_homepage_urls)

        locs_without_homepage = list(website.with_user(website.user_id)._enumerate_pages(ignore_custom_homepage=True))
        locs_without_homepage_urls = [page['loc'] for page in locs_without_homepage]
        self.assertIn('/', locs_without_homepage_urls)
        self.assertNotIn(homepage_url, locs_without_homepage_urls)

    def test_sitemap_group_invalid_name(self):
        with self.assertRaises(ValueError):
            sitemap_group('My Section!')(lambda env, rule, qs: None)


@tagged('-at_install', 'post_install')
class TestSitemapIndex(HttpCase):
    """/sitemap.xml is an index; check it splits URLs into per-group sub-sitemaps."""

    def _open_sitemap_index(self):
        # Drop cached sitemaps so each test regenerates from the current state.
        self.env['ir.attachment'].search([('url', '=like', '/sitemap%')]).unlink()
        return html.fromstring(self.url_open('/sitemap.xml').content)

    def test_sitemap_index_splits_by_group(self):
        website = self.env.ref('base.default_website')
        page_url = '/index-split-test'
        self.env['website.page'].create({
            'name': 'Index Split Test',
            'website_id': website.id,
            'url': page_url,
            'type': 'qweb',
            'arch': '<t t-call="website.layout"/>',
            'is_published': True,
        })

        index = self._open_sitemap_index()
        locs = index.xpath('//loc/text()')
        self.assertTrue(locs, "/sitemap.xml must be an index listing sub-sitemaps")
        self.assertTrue(all(loc.endswith('.xml') for loc in locs),
                        "The index must only list sub-sitemaps, not page URLs")
        self.assertTrue(any('-pages-' in loc for loc in locs),
                        "CMS pages must be listed in a 'pages' group sub-sitemap")

        # The page URL itself lives in a sub-sitemap, not the index.
        self.assertIn(page_url, all_sitemap_urls(self))

    def test_sitemap_group_chunking(self):
        # A group over LOC_PER_SITEMAP is split into several indexed chunks.
        with patch('odoo.addons.website.controllers.main.LOC_PER_SITEMAP', 1):
            index = self._open_sitemap_index()
        chunks = [loc for loc in index.xpath('//loc/text()') if '-pages-' in loc]
        self.assertGreater(len(chunks), 1,
                           "The 'pages' group must be split into multiple sub-sitemaps")
