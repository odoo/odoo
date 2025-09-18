from datetime import UTC, datetime, timezone
from unittest.mock import patch

from werkzeug.datastructures import ResponseCacheControl
from werkzeug.http import parse_cache_control_header

import odoo
from odoo.http import Session
from odoo.tools import config, reset_cached_properties

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.test_http.utils import MemoryGeoipResolver, MemorySessionStore

HTTP_DATETIME_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


class TestHttpBase(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        geoip_resolver = MemoryGeoipResolver()
        session_store = MemorySessionStore(session_class=Session)

        reset_cached_properties(odoo.http.root)
        cls.addClassCleanup(reset_cached_properties, odoo.http.root)
        cls.classPatch(
            config,
            "options",
            config.options.new_child(
                {"server_wide_modules": ["base", "web", "rpc", "test_http"]}
            ),
        )
        cls.classPatch(odoo.http.Application, "session_store", session_store)
        cls.classPatch(odoo.http.Application, "geoip_city_db", geoip_resolver)
        cls.classPatch(odoo.http.Application, "geoip_country_db", geoip_resolver)

    def setUp(self):
        super().setUp()
        odoo.http.root.session_store.store.clear()

    def db_url_open(self, url, *args, allow_redirects=False, **kwargs):
        return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def nodb_url_open(self, url, *args, allow_redirects=False, **kwargs):
        # Patch at multiple levels for code accessing via different import paths
        with (
            patch("odoo.http.db_list") as db_list1,
            patch("odoo.http.db_filter") as db_filter1,
            patch("odoo.http.request_class.db_list") as db_list2,
            patch("odoo.http.request_class.db_filter") as db_filter2,
        ):
            for db_list in (db_list1, db_list2):
                db_list.return_value = []
            for db_filter in (db_filter1, db_filter2):
                db_filter.return_value = []
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def multidb_url_open(self, url, *args, allow_redirects=False, dblist=(), **kwargs):
        dblist = dblist or self.db_list
        assert len(dblist) >= 2, "There should be at least 2 databases"
        # Patch at multiple levels:
        # - odoo.http.* for code accessing via module (e.g., web.controllers.utils uses http.db_filter)
        # - odoo.http.request_class.* for code importing from helpers
        with (
            patch("odoo.http.db_list") as db_list1,
            patch("odoo.http.db_filter") as db_filter1,
            patch("odoo.http.request_class.db_list") as db_list2,
            patch("odoo.http.request_class.db_filter") as db_filter2,
            patch("odoo.http.request_class.Registry") as Registry,
        ):
            for db_list in (db_list1, db_list2):
                db_list.return_value = dblist
            for db_filter in (db_filter1, db_filter2):
                db_filter.side_effect = lambda dbs, host=None: [
                    db for db in dbs if db in dblist
                ]
            Registry.return_value = self.registry
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def parse_http_cache_control(self, cache_control):
        return parse_cache_control_header(cache_control, None, ResponseCacheControl)

    def assertCacheControl(self, response, cache_control):
        self.assertEqual(
            self.parse_http_cache_control(response.headers["Cache-Control"]),
            self.parse_http_cache_control(cache_control),
        )

    def parse_http_expires(self, expires):
        return datetime.strptime(expires, HTTP_DATETIME_FORMAT).replace(tzinfo=UTC)
