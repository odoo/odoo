# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timezone
from unittest.mock import patch

from werkzeug.datastructures import ResponseCacheControl
from werkzeug.http import parse_cache_control_header

import odoo.http.geoip
from odoo.http.router import Application, root
from odoo.http.session import Session
from odoo.tools import config, reset_cached_properties

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.test_http.utils import MemoryGeoipResolver, MemorySessionStore

HTTP_DATETIME_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'


class TestHttpBase(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        geoip_resolver = MemoryGeoipResolver()
        session_store = MemorySessionStore(session_cls=Session)

        reset_cached_properties(root)
        cls.addClassCleanup(reset_cached_properties, root)
        cls.classPatch(config, 'options', config.options.new_child({
            'server_wide_modules': ['base', 'web', 'rpc', 'test_http'],
        }))
        cls.classPatch(Application, 'session_store', session_store)
        cls.classPatch(odoo.http.geoip, '_geoip_city_db', lambda: geoip_resolver)
        cls.classPatch(odoo.http.geoip, '_geoip_country_db', lambda: geoip_resolver)

    def setUp(self):
        super().setUp()
        root.session_store.store.clear()

    def db_url_open(self, url, *args, allow_redirects=False, **kwargs):
        return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def nodb_url_open(self, url, *args, allow_redirects=False, **kwargs):
        with patch('odoo.http.router.db_list') as db_list, \
             patch('odoo.http.router.db_filter') as db_filter:
            db_list.return_value = []
            db_filter.return_value = []
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def multidb_url_open(self, url, *args, allow_redirects=False, dblist=(), **kwargs):
        dblist = dblist or self.db_list
        assert len(dblist) >= 2, "There should be at least 2 databases"
        with patch('odoo.http.router.db_list') as db_list, \
             patch('odoo.http.router.db_filter') as db_filter, \
             patch('odoo.http.requestlib.Registry') as Registry:  # TODO @juc: router
            db_list.return_value = dblist
            db_filter.side_effect = lambda dbs, host=None: [db for db in dbs if db in dblist]
            Registry.return_value = self.registry
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def parse_http_cache_control(self, cache_control):
        return parse_cache_control_header(cache_control, None, ResponseCacheControl)

    def assertCacheControl(self, response, cache_control):
        self.assertEqual(
           self.parse_http_cache_control(response.headers['Cache-Control']),
           self.parse_http_cache_control(cache_control),
        )

    def parse_http_expires(self, expires):
        return datetime.strptime(expires, HTTP_DATETIME_FORMAT).replace(tzinfo=timezone.utc)
