# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager
from unittest.mock import patch

from decorator import decorator

import odoo
from odoo.addons.test_http.utils import MemoryGeoipResolver, MemorySessionStore
from odoo.http import Session
from odoo.tools.func import lazy_property


@contextmanager
def nodb():
    with patch('odoo.http.db_list', return_value=[]),\
         patch('odoo.http.db_filter', return_value=[]):
        yield

def multidb(dblist):
    assert len(dblist) >= 2
    @decorator
    def _multidb(func, self, *args, **kwargs):
        with multidb_(dblist, self.registry):
            return func(self, *args, **kwargs)
    return _multidb
@contextmanager
def multidb_(dblist, registry):
    with patch('odoo.http.db_list', return_value=dblist),\
         patch('odoo.http.db_filter', side_effect=lambda dbs, host=None: [
             db for db in dbs if db in dblist
         ]),\
         patch('odoo.http.Registry', return_value=registry):
        yield


class HttpTestMixin:
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
