import logging
from contextlib import closing
from unittest.mock import patch
from urllib.parse import urljoin, urlsplit

import requests

import odoo
from odoo.modules.registry import Registry
from odoo.sql_db import close_db, db_connect
from odoo.tests import HOST, BaseCase, Like, get_db_name, tagged
from odoo.tools import lazy_property, mute_logger, SQL


"""
RCO:
The other "what could go wrong" I can think about:

* you cannot connect to PostgreSQL
* the database does not exists
* the database is corrupted:
* + table ir_module_module does not exist or misses some columns
* + the "sequences" don't exist
* the database version doesn't match the server version (version is inferred from module base, I think)
* you cannot import some modules (in the Python sense)
* some modules are marked to be installed/upgraded/uninstalled and that fails (that's part of Registry.new)
"""
# TODO: write some tests for those too


def duplicate_db(db_source, db_dest):
    query = SQL("CREATE DATABASE %s ENCODING 'unicode' TEMPLATE %s", SQL.identifier(db_dest), SQL.identifier(db_source))
    with closing(db_connect('postgres').cursor()) as cr:
        cr._cnx.autocommit = True
        cr.execute(query)


def drop_db(db):
    query = SQL("DROP DATABASE IF EXISTS %s", SQL.identifier(db))
    with closing(db_connect('postgres').cursor()) as cr:
        cr._cnx.autocommit = True
        cr.execute(query)


@tagged('-standard', '-at_install', 'post_install', 'database_breaking')
class TestHttpRegistry(BaseCase):
    @classmethod
    def setUpClass(cls):
        lazy_property.reset_all(odoo.http.root)
        cls.addClassCleanup(lazy_property.reset_all, odoo.http.root)
        cls.classPatch(odoo.conf, 'server_wide_modules', ['base', 'web', 'test_http'])

        # make sure there are always many databases, to break monodb
        cls._db_list = cls.startClassPatcher(patch('odoo.http.db_list'))
        cls._db_list.return_value = ['postgres', get_db_name()]
        cls.startClassPatcher(patch('odoo.http.db_filter',
            side_effect=lambda dbs, host=None: [db for db in dbs if db in cls._db_list()]))

    def setUp(self):
        super().setUp()
        self.opener = requests.Session()
        Registry.delete(get_db_name())
        close_db(get_db_name())

    def duplicate_current_db(self, db_suffix):
        db_duplicate = f'{get_db_name()}-test-http-registry-{db_suffix}'

        # duplicate the current database
        duplicate_db(db_source=get_db_name(), db_dest=db_duplicate)
        self.addCleanup(drop_db, db_duplicate)
        self.addCleanup(close_db, db_duplicate)
        self._db_list.return_value.append(db_duplicate)
        self.addCleanup(self._db_list.return_value.remove, db_duplicate)

        return db_duplicate

    def authenticate(self, *, db=None):
        session = odoo.http.root.session_store.new()
        session.update(odoo.http.get_default_session(), db=db or get_db_name())
        session.context['lang'] = odoo.http.DEFAULT_LANG
        odoo.http.root.session_store.save(session)
        self.opener.cookies['session_id'] = session.sid
        return session

    def url_open(self, path, *, allow_redirects=False):
        if not path.startswith('/'):
            raise ValueError("can only request a relative url")
        url = urljoin(f"http://{HOST}:{odoo.tools.config['http_port']}", path)
        return self.opener.get(url, allow_redirects=allow_redirects)

    def test_signaling(self):
        # open a registry + session on the current db
        self.authenticate()
        res = self.url_open('/test_http/ensure_db')
        self.assertEqual(res.status_code, 200)

        # invalidate the registry of the current db
        with Registry(get_db_name()).cursor() as cr:
            cr.execute("select nextval('base_registry_signaling')")

        # the registry should rebuild itself just fine
        with self.assertLogs('odoo.modules.registry', logging.INFO) as capture:
            res = self.url_open('/test_http/ensure_db')
            self.assertEqual(res.status_code, 200)
        self.assertEqual(capture.output, [
            "INFO:odoo.modules.registry:Reloading the model registry after database signaling.",
            Like("INFO:odoo.modules.registry:Registry loaded in ...s"),
        ])

    def test_missing_db(self):
        db_duplicate = self.duplicate_current_db('drop')

        # open a registry + session on the duplicated db
        self.authenticate(db=db_duplicate)
        res = self.url_open('/test_http/ensure_db')
        self.assertEqual(res.status_code, 200)

        # drop the duplicate, leave the session and registry dangling
        close_db(db_duplicate)
        drop_db(db_duplicate)
        self.assertIn(db_duplicate, Registry.registries)  # dangling

        # the registry is unusable, make sure the system recovers fine
        with self.assertLogs('odoo.http', logging.WARNING) as capture:
            res = self.url_open('/test_http/ensure_db')
            res.raise_for_status()
            self.authenticate(db=db_duplicate)  # session was drop
            res_query = self.url_open(f'/test_http/ensure_db?db={db_duplicate}')
            res_query.raise_for_status()

        self.assertEqual(
            [(res.status_code, urlsplit(res.headers.get('Location', '')).path),
             (res_query.status_code, urlsplit(res_query.headers.get('Location', '')).path)],
            [(303, '/web/database/selector')] * 2,
            "It should not redirect back on /test_http/ensure_db.",
        )
        self.assertEqual(capture.output, [
            Like("WARNING:odoo.http:Database or registry unusable, trying without\n"
                 f'Traceback...database "{db_duplicate}" does not exist...')
        ] * 2)

    @mute_logger('odoo.sql_db')
    def test_corrupt_ir_module_module_table(self):
        db_duplicate = self.duplicate_current_db('corrupt-irmodule')

        # corrupt the ir_module_module table
        with db_connect(db_duplicate).cursor() as cr:
            cr.execute('''
                ALTER TABLE "ir_module_module" DROP COLUMN "state"
            ''')

        # we have a session on that database but no registry
        self.authenticate(db=db_duplicate)

        # impossible to build a registry, make sure the system recovers
        with self.assertLogs('odoo.modules.registry', logging.ERROR) as capture1, \
             self.assertLogs('odoo.http', logging.WARNING) as capture2:
            res = self.url_open('/test_http/greeting-public')
            self.assertEqual(res.status_code, 404)
        self.assertEqual(capture1.output, [
            "ERROR:odoo.modules.registry:Failed to load registry",
        ])
        self.assertEqual(capture2.output, [
            Like("WARNING:odoo.http:Database or registry unusable, trying without\n"
                 'Traceback...column "state" does not exist...')
        ])

    @mute_logger('odoo.sql_db')
    def test_corrupt_sequences(self):
        db_duplicate = self.duplicate_current_db('corrupt-sequence')

        # open a registry + session on the current db (for first subtest)
        self.authenticate(db=db_duplicate)
        res = self.url_open('/test_http/ensure_db')
        self.assertEqual(res.status_code, 200)

        # drop the signaling sequence
        with db_connect(db_duplicate).cursor() as cr:
            cr.execute('''
                DROP SEQUENCE "base_registry_signaling"
            ''')

        with self.subTest(name="existing registry"):
            # attempt to reuse the registry, make sure the system recover
            with self.assertLogs('odoo.http', logging.WARNING) as capture:
                res = self.url_open('/test_http/greeting-public')
                self.assertEqual(res.status_code, 404)
            self.assertEqual(capture.output, [
                Like("WARNING:odoo.http:Database or registry unusable, trying without\n"
                     'Traceback...relation "base_registry_signaling" does not exist...')
            ])

        with self.subTest(name="new registry"):
            self.authenticate(db=db_duplicate)
            Registry.delete(db_duplicate)
            # attempt to create a new registry, it should create the
            # missing sequences and go on just fine
            res = self.url_open('/test_http/greeting-public')
            self.assertEqual(res.status_code, 200)
