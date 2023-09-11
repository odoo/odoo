# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy

from contextlib import nullcontext

from odoo.tools import mute_logger
from odoo.tests.common import HttpCase, tagged

EXTRA_REQUEST = 2 - 1
""" During tests, the query on 'base_registry_signaling, base_cache_signaling'
won't be executed on hot state, but new queries related to the test cursor will
be added:

    cr = Cursor() # SAVEPOINT
    cr.execute(...)
    cr.commit() # RELEASE
    cr.close()
"""


class UtilPerf(HttpCase):
    def _get_url_hot_query(self, url, cache=True, table_count=False):
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
        :param bool table_count: whether the method should also return data
            about the queried table
        :return: the query count plus the queried table data if ``table_count``
            is ``True``
        :rtype: int|tuple(int, dict)
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
        sql_count_before = self.cr.sql_log_count

        with (self.cr._enable_table_tracking() if table_count else nullcontext()):
            if table_count:
                sql_from_log_before = copy.deepcopy(self.cr.sql_from_log)
                sql_into_log_before = copy.deepcopy(self.cr.sql_into_log)

            self.url_open(url)
            sql_count = self.cr.sql_log_count - sql_count_before - EXTRA_REQUEST
            if table_count:
                sql_from_tables = {'base_registry_signaling': 1}  # see EXTRA_REQUEST
                sql_into_tables = {}
                for table, stats in self.cr.sql_from_log.items():
                    query_count = stats[0] - sql_from_log_before.get(table, [0])[0]
                    if query_count:
                        sql_from_tables[table] = query_count
                for table, stats in self.cr.sql_into_log.items():
                    query_count = stats[0] - sql_into_log_before.get(table, [0])[0]
                    if query_count:
                        sql_into_tables[table] = query_count
                return sql_count, sql_from_tables, sql_into_tables

            return sql_count

    def _check_url_hot_query(self, url, expected_query_count, select_tables_perf=None, insert_tables_perf=None):
        query_count, select_tables, insert_tables = self._get_url_hot_query(url, table_count=True)
        self.assertEqual(query_count, expected_query_count)
        self.assertEqual(select_tables, select_tables_perf or {})
        self.assertEqual(insert_tables, insert_tables_perf or {})


class TestStandardPerformance(UtilPerf):
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


class TestWebsitePerformance(UtilPerf):

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

    def test_10_perf_sql_queries_page(self):
        # standard untracked website.page
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
        self.menu.unlink()  # page being or not in menu shouldn't add queries
        self._check_url_hot_query(self.page.url, 6, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 10)

    def test_15_perf_sql_queries_page(self):
        # standard tracked website.page
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
        insert_tables_perf = {
            'website_visitor': 1,
            # Visitor upsert
        }
        self.page.track = True
        self._check_url_hot_query(self.page.url, 7, select_tables_perf, insert_tables_perf)
        self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 11)

        self.menu.unlink()  # page being or not in menu shouldn't add queries
        self._check_url_hot_query(self.page.url, 7, select_tables_perf, insert_tables_perf)
        self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 11)

    def test_20_perf_sql_queries_homepage(self):
        # homepage "/" has its own controller
        select_tables_perf = {
            'base_registry_signaling': 1,
            'website_menu': 1,
            # homepage controller is prefetching all menus for perf in one go
            'website_page': 2,
            # 1. the menu prefetching is also prefetching all menu's pages
            # 2. find page matching the `/` url
            'website': 1,
            'ir_ui_view': 1,
            # Check if `view.track` to track visitor or not
        }
        insert_tables_perf = {
            'website_visitor': 1,
            # Visitor upsert
        }
        self._check_url_hot_query('/', 7, select_tables_perf, insert_tables_perf)
        self.assertEqual(self._get_url_hot_query('/', cache=False), 9)

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
            'ir_ui_view': 1,
            # Check if `view.track` to track visitor or not
        }
        self._check_url_hot_query(self.page.url, 5, select_tables_perf)
        self.assertEqual(self._get_url_hot_query(self.page.url, cache=False), 5)

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
