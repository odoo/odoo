from datetime import UTC, datetime
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
        odoo.http.root.session_store.clear()
        odoo.http.invalidate_db_catalog_cache()
        self.addCleanup(odoo.http.invalidate_db_catalog_cache)

    def db_url_open(self, url, *args, allow_redirects=False, **kwargs):
        odoo.http.invalidate_db_catalog_cache()
        return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def nodb_url_open(self, url, *args, allow_redirects=False, **kwargs):
        with (
            patch("odoo.http.Application.get_dbs_served", return_value=[]),
            patch("odoo.http.Application.filter_dbs_served", return_value=[]),
        ):
            odoo.http.invalidate_db_catalog_cache()
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def multidb_url_open(self, url, *args, allow_redirects=False, dblist=(), **kwargs):
        dblist = dblist or self.dbs_served
        assert len(dblist) >= 2, "There should be at least 2 databases"
        with (
            patch("odoo.http.Application.get_dbs_served", return_value=list(dblist)),
            patch(
                "odoo.http.Application.filter_dbs_served",
                side_effect=lambda dbs, host=None: [db for db in dbs if db in dblist],
            ),
            patch("odoo.http.request_class.Registry") as Registry,
            patch("odoo.http._serve.Registry") as ServeRegistry,
        ):
            Registry.return_value = self.registry
            ServeRegistry.return_value = self.registry
            odoo.http.invalidate_db_catalog_cache()
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
