# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged
import functools
from unittest.mock import patch

from odoo.addons.website.sitemap import registry as sitemap_registry


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

        # Second rule uses a partial wrapping the same bound method
        class EndpointPartial:
            routing = {'sitemap': functools.partial(holder.sitemap)}

        class RulePartial:
            endpoint = EndpointPartial()

        class FakeRouter:
            def iter_rules(self):
                return [RuleBound(), RulePartial()]

        with patch('odoo.addons.website.models.ir_http.IrHttp.routing_map', autospec=True, return_value=FakeRouter()):
            locs = list(website.with_user(website.user_id)._enumerate_pages())

        # The sitemap callable should have been executed only once
        self.assertEqual(call_count['n'], 1)
        # And the returned loc should be present (normalized already)
        self.assertIn({'loc': '/once'}, locs)

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


@tagged('-at_install', 'post_install')
class TestSitemapRegistry(TransactionCase):

    def _register(self, group, func, route_prefixes=()):
        sitemap_registry.register(group, func, route_prefixes)
        self.addCleanup(sitemap_registry._groups.pop, group, None)

    def test_register_validates_group_name(self):
        def group_func(env, query_string=None):
            yield from ()

        for name in ('Blog', 'blog-x', '42', '_blog', ''):
            with self.assertRaises(ValueError):
                sitemap_registry.register(name, group_func)

    def test_register_idempotent(self):
        def group_func(env, query_string=None):
            yield from ()

        self._register('test_idem', group_func)
        sitemap_registry.register('test_idem', group_func)
        self.assertEqual(len(sitemap_registry._groups['test_idem']), 1)

    def test_get_groups_filters_unloaded_addons(self):
        def group_func(env, query_string=None):
            yield from ()

        self._register('test_loaded', group_func)
        # declared in odoo.addons.website.* -> visible when website is loaded
        self.assertIn('test_loaded', sitemap_registry.get_groups({'website'}))
        self.assertNotIn('test_loaded', sitemap_registry.get_groups({'base'}))

    def test_enumerate_group_pages_normalization(self):
        """Lock the URL normalization/dedup contract of _enumerate_group_pages."""
        website = self.env['website'].search([], limit=1)

        def group_func(env, query_string=None):
            yield {'loc': '/norm/'}
            yield {'loc': '/norm'}
            yield {'loc': '/'}

        self._register('test_norm', group_func)

        locs = [loc['loc'] for loc in website._enumerate_group_pages('test_norm')]
        # TODO(human): assert the expected normalized/deduplicated locs

    def test_prefix_skips_unmarked_routes_only(self):
        website = self.env['website'].search([], limit=1)

        def group_func(env, query_string=None):
            yield {'loc': '/covered/from-group'}

        self._register('test_covered', group_func, route_prefixes=('/covered',))

        def covered_page(self):
            pass

        def custom_sitemap(env, rule, qs):
            yield {'loc': '/covered/custom'}

        # Route under a registered prefix WITHOUT a `sitemap` kwarg:
        # must be skipped (its URLs belong to the group generators)
        class UnmarkedEndpoint:
            routing = {'type': 'http', 'auth': 'public', 'website': True,
                       'routes': ['/covered/page']}
            original_endpoint = staticmethod(covered_page)

        class UnmarkedRule:
            rule = '/covered/page'
            endpoint = UnmarkedEndpoint()
            _converters = {}

            def build(self, value, append_unknown=False):
                return '', '/covered/page'

        # Route under the same prefix WITH an explicit `sitemap` kwarg:
        # must keep its legacy behavior
        class MarkedEndpoint:
            routing = {'sitemap': custom_sitemap}

        class MarkedRule:
            rule = '/covered/custom'
            endpoint = MarkedEndpoint()

        class FakeRouter:
            def iter_rules(self):
                return [UnmarkedRule(), MarkedRule()]

        with patch('odoo.addons.website.models.ir_http.IrHttp.routing_map', autospec=True, return_value=FakeRouter()):
            locs = [l['loc'] for l in website.with_user(website.user_id)._enumerate_pages()]
            locs_excluded = [
                l['loc'] for l in website.with_user(website.user_id)._enumerate_pages(
                    exclude_registry_groups=True)]

        self.assertNotIn('/covered/page', locs, "kwarg-less route under a registered prefix must be skipped")
        self.assertIn('/covered/custom', locs, "explicit sitemap kwarg must bypass the prefix skip")
        self.assertIn('/covered/from-group', locs, "group URLs must stay available to generic consumers")
        self.assertNotIn('/covered/from-group', locs_excluded, "sitemap controller path must exclude group URLs")
