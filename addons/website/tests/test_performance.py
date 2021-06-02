# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase

EXTRA_REQUEST = 5
""" During tests, the query on 'base_registry_signaling, base_cache_signaling'
    won't be executed on hot state, but 6 new queries related to the test cursor
    will be added:
        SAVEPOINT "test_cursor_4"
        SAVEPOINT "test_cursor_4"
        ROLLBACK TO SAVEPOINT "test_cursor_4"
        SAVEPOINT "test_cursor_5"
        [.. usual SQL Queries .. ]
        SAVEPOINT "test_cursor_5"
        ROLLBACK TO SAVEPOINT "test_cursor_5"
"""


class TestWebsitePerformance(HttpCase):

    def setUp(self):
        super().setUp()

        self.page = self.env['website.page'].create({
            'url': '/sql_page',
            'name': 'Page Test SQL Perf',
            'type': 'qweb',
            'arch': '<t name="Contact Us" t-name="website.contactus"> \
                       <t t-call="website.layout"> \
                         <div id="wrap"><div class="oe_structure"/></div> \
                       </t> \
                     </t>',
            'key': 'website.page_test_perf_sql',
            'is_published': True,
        })

    def _get_url_hot_query(self, url):
        # ensure worker is in hot state
        self.url_open(url)
        self.url_open(url)

        sql_count = self.registry.test_cr.sql_log_count
        self.url_open(url)
        return self.registry.test_cr.sql_log_count - sql_count

    def test_10_perf_sql_queries_page(self):
        # standard website.page
        expected_sql = 12 + EXTRA_REQUEST
        self.assertEqual(self._get_url_hot_query(self.page.url), expected_sql)

    def test_20_perf_sql_queries_homepage(self):
        # homepage "/" has its own controller
        # add 5 queries for test environment (RELEASE/SAVEPOINT/ROLLBACK test_cursor)
        expected_sql = 21 + EXTRA_REQUEST
        self.assertEqual(self._get_url_hot_query('/'), expected_sql)

    def test_30_perf_sql_queries_page_no_layout(self):
        # website.page with no call to layout templates
        self.page.arch = '<div>I am a blank page</div>'
        expected_sql = 8 + EXTRA_REQUEST
        self.assertEqual(self._get_url_hot_query(self.page.url), expected_sql)
