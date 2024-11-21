# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo.addons.base.tests.common import HttpCaseWithUserPortal, HttpCaseWithUserDemo

from contextlib import nullcontext

from odoo.sql_db import categorize_query
from odoo.tools import mute_logger
from odoo.tests.common import HttpCase, tagged


_logger = logging.getLogger(__name__)


class UtilPerf(HttpCaseWithUserPortal, HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # remove menu containing a slug url (only website_helpdesk normally), to
        # avoid the menu cache being disabled, which would increase sql queries
        cls.env['website.menu'].search([
            ('url', '=like', '/%/%-%'),
        ]).unlink()
        # if website_livechat is installed before another module, the
        # get_livechat_channel_info add unrelated query for the current test.
        # So we disable it.
        if 'channel_id' in cls.env['website']:
            cls.env['website'].search([]).channel_id = False

    def _get_url_hot_query(self, url, cache=True, query_list=False):
        """ This method returns the number of SQL Queries used inside a request.
        The returned query number will be the same as a "real" (outside of test
        mode) case: the method takes care of removing the extra queries related
        to the testing mode and to add the missing one from "real" use case.

        The goal is to ease the code reading and debugging of those perf testing
        methods, as one will have the same query count written in the test than
        it shows in "real" case logs.

        eg: if a page is taking X SQL query count to be loaded outside test mode
            in "real" case, the test is expected to also use X as query count
            value to be asserted/checked.

        :param str url: url to be checked
        :param bool cache: whether the QWeb `t-cache` should be disabled or not
        :param bool query_list: whether the method should also return list of
            queries (without test cursor savepoint queries)
        :return: the query count plus the list of queries if ``query_list``
            is ``True``
        :rtype: int|tuple(int, list)
        """
        url += ('?' not in url and '?' or '')
        if cache:
            url += '&debug='
        else:
            url += '&debug=disable-t-cache'

        # ensure worker is in hot state
        self.url_open(url)
        self.url_open(url)
        self.url_open(url)

        nested_profiler = self.profile(collectors=['sql'], db=False)
        with nested_profiler:
            self.registry.get_sequences(self.cr)
            self.url_open(url)

        profiler = nested_profiler.profiler
        self.assertEqual(len(profiler.sub_profilers), 1, "we expect to have only one accessed url") # if not adapt the code below
        route_profiler = profiler.sub_profilers[0]
        route_entries = route_profiler.collectors[0].entries
        entries = profiler.collectors[0].entries + route_entries
        sql_queries = [entry['full_query'].strip() for entry in entries]
        sql_count = len(sql_queries)
        if not query_list:
            return sql_count
        return sql_count, sql_queries

    def _check_url_hot_query(self, url, expected_query_count, select_tables_perf=None, insert_tables_perf=None):
        query_count, sql_queries = self._get_url_hot_query(url, query_list=True)

        sql_from_tables = {}
        sql_into_tables = {}

        query_separator = '\n' + '-' * 100 + '\n'
        queries = query_separator.join(sql_queries)

        for query in sql_queries:
            query_type, table = categorize_query(query)
            if query_type == 'into':
                log_target = sql_into_tables
            elif query_type == 'from':
                log_target = sql_from_tables
            else:
                _logger.warning("Query type %s for query %s is not supported by _check_url_hot_query", query_type, query)
            log_target.setdefault(table, 0)
            log_target[table] = log_target[table] + 1
        if query_count != expected_query_count:
            msq = f"Expected {expected_query_count} queries but {query_count} where ran: {query_separator}{queries}{query_separator}"
            self.fail(msq)
        self.assertEqual(sql_from_tables, select_tables_perf or {}, f'Select queries does not match: {query_separator}{queries}{query_separator}')
        self.assertEqual(sql_into_tables, insert_tables_perf or {}, f'Insert queries does not match: {query_separator}{queries}{query_separator}')


class TestStandardPerformance(UtilPerf):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.users'].browse(2).image_1920 = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'

    @mute_logger('odoo.http')
    def test_10_perf_sql_img_controller(self):
        self.authenticate('demo', 'demo')
        # not published user, get the not found image placeholder
        self.assertEqual(self.env['res.users'].sudo().browse(2).website_published, False)
        url = '/web/image/res.users/2/image_256'
        self.assertEqual(self._get_url_hot_query(url), 8)
        self.assertEqual(self._get_url_hot_query(url, cache=False), 8)

    @mute_logger('odoo.http')
    def test_11_perf_sql_img_controller(self):
        self.authenticate('demo', 'demo')
        self.env['res.users'].sudo().browse(2).website_published = True
        url = '/web/image/res.users/2/image_256'
        select_tables_perf = {
            'base_registry_signaling': 1,
            'res_users': 2,
            'res_partner': 1,
            'ir_attachment': 2,
        }
        self._check_url_hot_query(url, 6, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(url, cache=False), 6)

    @mute_logger('odoo.http')
    def test_20_perf_sql_img_controller_bis(self):
        url = '/web/image/website/1/favicon'
        select_tables_perf = {
            'base_registry_signaling': 1,
            'website': 2,
            # 1. `_find_record()` performs an access right check through
            #    `exists()` which perform a request on the website.
            # 2. `_get_stream_from` ends up reading the requested record to
            #    give a name to the file (downloaded_name)
            'ir_attachment': 2,
            # 1. `_record_to_stream()` does a `search()`..
            # 2. ..followed by a `_read()`
        }
        self._check_url_hot_query(url, 5, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(url, cache=False), 5)

        self.authenticate('portal', 'portal')
        self._check_url_hot_query(url, 5, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(url, cache=False), 5)


class TestWebsitePerformanceCommon(UtilPerf):

    def setUp(self):
        super().setUp()
        self.page, self.menu = self._create_page_with_menu('/sql_page')

    def _create_page_with_menu(self, url):
        name = url[1:]
        website = self.env['website'].browse(1)
        page = self.env['website.page'].create({
            'url': url,
            'name': name,
            'type': 'qweb',
            'arch': '<t name="%s" t-name="website.page_test_%s"> \
                       <t t-call="website.layout"> \
                         <div id="wrap"><div class="oe_structure"/></div> \
                       </t> \
                     </t>' % (name, name),
            'key': 'website.page_test_%s' % name,
            'is_published': True,
            'website_id': website.id,
            'track': False,
        })
        menu = self.env['website.menu'].create({
            'name': name,
            'url': url,
            'page_id': page.id,
            'website_id': website.id,
            'parent_id': website.menu_id.id
        })
        return (page, menu)


class TestWebsitePerformance(TestWebsitePerformanceCommon):

    def test_10_perf_sql_queries_page(self):
        # standard untracked website.page
        for readonly_enabled in (True, False):
            self.env.registry.test_readonly_enabled = readonly_enabled
            with self.subTest(readonly_enabled=readonly_enabled), self.env.cr.savepoint() as savepoint:
                select_tables_perf = {
                    'base_registry_signaling': 1,
                    'ir_attachment': 1,
                    # `_get_serve_attachment` dispatcher fallback
                    'website_page': 2,
                    # 1. `_serve_page` search page matching URL..
                    # 2. ..then reads it (`is_visible`)
                    'website': 1,
                }
                expected_query_count = 5
                if not readonly_enabled:
                    select_tables_perf['ir_ui_view'] = 1 # Check if `view.track` to track visitor or not
                    expected_query_count += 1
                self._check_url_hot_query(self.page.url, expected_query_count, select_tables_perf)
                self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 10)
                self.menu.unlink()  # page being or not in menu shouldn't add queries
                self._check_url_hot_query(self.page.url, expected_query_count, select_tables_perf)
                self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 10)
                savepoint.rollback()

    def test_15_perf_sql_queries_page(self):
        # standard tracked website.page
        for readonly_enabled in (True, False):
            self.env.registry.test_readonly_enabled = readonly_enabled
            with self.subTest(readonly_enabled=readonly_enabled), self.env.cr.savepoint() as savepoint:
                select_tables_perf = {
                    'base_registry_signaling': 1,
                    'ir_attachment': 1,
                    # `_get_serve_attachment` dispatcher fallback
                    'website_page': 2,
                    # 1. `_serve_page` search page matching URL..
                    # 2. ..then reads it (`is_visible`)
                    'website': 1,
                }
                expected_query_count = 5
                expected_query_count_no_cache = 10
                insert_tables_perf = {}
                if not readonly_enabled:
                    select_tables_perf['ir_ui_view'] = 1 # Check if `view.track` to track visitor or not
                    insert_tables_perf = {
                        'website_visitor': 1,
                        # Visitor upsert
                    }
                    expected_query_count += 2
                    expected_query_count_no_cache += 1
                self.page.track = True
                self._check_url_hot_query(self.page.url, expected_query_count, select_tables_perf, insert_tables_perf)
                self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), expected_query_count_no_cache)

                self.menu.unlink()  # page being or not in menu shouldn't add queries
                self._check_url_hot_query(self.page.url, expected_query_count, select_tables_perf, insert_tables_perf)
                self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), expected_query_count_no_cache)
                savepoint.rollback()

    def test_20_perf_sql_queries_homepage(self):
        # homepage "/" has its own controller
        for readonly_enabled in (True, False):
            self.env.registry.test_readonly_enabled = readonly_enabled
            with self.subTest(readonly=readonly_enabled), self.env.cr.savepoint() as savepoint:
                select_tables_perf = {
                    'base_registry_signaling': 1,
                    'website_menu': 1,
                    # homepage controller is prefetching all menus for perf in one go
                    'website_page': 2,
                    # 1. the menu prefetching is also prefetching all menu's pages
                    # 2. find page matching the `/` url
                    'website': 1,
                }
                expected_query_count = 5
                expected_query_count_no_cache = 8
                insert_tables_perf = {}
                if not readonly_enabled:
                    select_tables_perf['ir_ui_view'] = 1 # Check if `view.track` to track visitor or not
                    insert_tables_perf = {
                        'website_visitor': 1,
                        # Visitor upsert
                    }
                    expected_query_count += 2
                    expected_query_count_no_cache += 1
                self._check_url_hot_query('/', expected_query_count, select_tables_perf, insert_tables_perf)
                self.assertEqual(self._get_url_hot_query('/', cache=False), expected_query_count_no_cache)
                savepoint.rollback()

    def test_30_perf_sql_queries_page_no_layout(self):
        # untrack website.page with no call to layout templates
        self.page.arch = '<div>I am a blank page</div>'
        select_tables_perf = {
            'base_registry_signaling': 1,
            'ir_attachment': 1,
            # `_get_serve_attachment` dispatcher fallback
            'website_page': 2,
            # 1. `_serve_page` search page matching URL..
            # 2. ..then reads it (`is_visible`)
            'website': 1,
            # Check if website.cookies_bar is active
            'ir_ui_view': 1,
            # Check if `view.track` to track visitor or not
        }
        self._check_url_hot_query(self.page.url, 6, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 6)

    def test_40_perf_sql_queries_page_multi_level_menu(self):
        # menu structure should not impact SQL requests
        _, menu_a = self._create_page_with_menu('/a')
        _, menu_aa = self._create_page_with_menu('/aa')
        _, menu_b = self._create_page_with_menu('/b')
        _, menu_bb = self._create_page_with_menu('/bb')
        _, menu_bbb = self._create_page_with_menu('/bbb')
        _, menu_bbbb = self._create_page_with_menu('/bbbb')
        _, menu_bbbbb = self._create_page_with_menu('/bbbbb')
        self._create_page_with_menu('c')
        menu_bbbbb.parent_id = menu_bbbb
        menu_bbbb.parent_id = menu_bbb
        menu_bbb.parent_id = menu_bb
        menu_bb.parent_id = menu_b
        menu_aa.parent_id = menu_a

        select_tables_perf = {
            'base_registry_signaling': 1,
            'ir_attachment': 1,
            # `_get_serve_attachment` dispatcher fallback
            'website_page': 2,
            # 1. `_serve_page` search page matching URL..
            # 2. ..then reads it (`is_visible`)
            'website': 1,
            'ir_ui_view': 1,
            # Check if `view.track` to track visitor or not
        }
        self._check_url_hot_query(self.page.url, 6, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 10)

@tagged('-at_install', 'post_install')
class TestWebsitePerformancePost(UtilPerf):
    @mute_logger('odoo.http')
    def test_50_perf_sql_web_assets(self):
        # assets route /web/assets/..
        assets_url = self.env['ir.qweb']._get_asset_bundle('web.assets_frontend_lazy', css=False, js=True).get_links()[0]
        self.assertIn('web.assets_frontend_lazy.min.js', assets_url)
        select_tables_perf = {
            'base_registry_signaling': 1,
            'ir_attachment': 2,
            # All 2 coming from the /web/assets and ir.binary stack
            # 1. `search() the attachment`
            # 2. `_record_to_stream` reads the other attachment fields
        }
        self._check_url_hot_query(assets_url, 3, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(assets_url, cache=False), 3)
