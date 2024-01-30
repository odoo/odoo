# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo.http import Session
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.tools.func import lazy_property
from odoo.addons.test_http.utils import MemoryGeoipResolver, MemorySessionStore


class TestHttpBase(HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(lazy_property.reset_all, odoo.http.root)
        cls.classPatch(odoo.conf, 'server_wide_modules', ['base', 'web', 'test_http'])
        lazy_property.reset_all(odoo.http.root)
        cls.classPatch(odoo.http.root, 'session_store', MemorySessionStore(session_class=Session))
        cls.classPatch(odoo.http.root, 'geoip_resolver', MemoryGeoipResolver())

    def setUp(self):
        super().setUp()
        odoo.http.root.session_store.store.clear()

    def db_url_open(self, url, *args, allow_redirects=False, **kwargs):
        return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def nodb_url_open(self, url, *args, allow_redirects=False, **kwargs):
        with patch('odoo.http.db_list') as db_list, \
             patch('odoo.http.db_filter') as db_filter:
            db_list.return_value = []
            db_filter.return_value = []
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)

    def multidb_url_open(self, url, *args, allow_redirects=False, dblist=(), **kwargs):
        dblist = dblist or self.db_list
        assert len(dblist) >= 2, "There should be at least 2 databases"
        with patch('odoo.http.db_list') as db_list, \
             patch('odoo.http.db_filter') as db_filter, \
             patch('odoo.http.Registry') as Registry:
            db_list.return_value = dblist
            db_filter.side_effect = lambda dbs, host=None: [db for db in dbs if db in dblist]
            Registry.return_value = self.registry
            return self.url_open(url, *args, allow_redirects=allow_redirects, **kwargs)
