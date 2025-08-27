# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged
import functools
from unittest.mock import patch


@tagged('-at_install', 'post_install')
class TestWebsiteSitemap(TransactionCase):
    def test_sitemap_page_lastmod(self):
        website = self.env['website'].search([], limit=1)
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
