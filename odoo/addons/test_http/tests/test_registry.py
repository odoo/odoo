import logging
from contextlib import closing
from unittest.mock import patch
from urllib.parse import urlsplit

import psycopg
import requests

import odoo
from odoo.db import PoolError, close_db, db_connect
from odoo.libs.web import urljoin
from odoo.modules.registry import Registry
from odoo.service.db.lifecycle import _retry_terminate_then_ddl
from odoo.tests import HOST, BaseCase, Like, get_db_name, tagged
from odoo.tools import SQL, config, mute_logger, reset_cached_properties

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


def duplicate_db(db_source, db_dest):
    query = SQL(
        "CREATE DATABASE %s ENCODING 'unicode' TEMPLATE %s",
        SQL.identifier(db_dest),
        SQL.identifier(db_source),
    )
    with closing(db_connect("postgres").cursor()) as cr:
        cr.connection.autocommit = True
        cr.execute(query)


def drop_db(db):
    with closing(db_connect("postgres").cursor()) as cr:
        cr.connection.autocommit = True
        _retry_terminate_then_ddl(
            cr,
            db,
            f"test_http DROP DB: {db}",
            lambda: cr.execute(SQL("DROP DATABASE IF EXISTS %s", SQL.identifier(db))),
        )


@tagged("-standard", "-at_install", "post_install", "database_breaking")
class TestHttpRegistry(BaseCase):
    @classmethod
    def setUpClass(cls):
        reset_cached_properties(odoo.http.root)
        cls.addClassCleanup(reset_cached_properties, odoo.http.root)
        cls.classPatch(
            config,
            "options",
            config.options.new_child(
                {"server_wide_modules": ["base", "web", "rpc", "test_http"]}
            ),
        )
        cls.classPatch(
            odoo.http.constants,
            "SELECT_DB_PATHS",
            odoo.http.constants.SELECT_DB_PATHS | {"/test_http/ensure_db"},
        )

        cls._db_list = cls.startClassPatcher(patch("odoo.http.Application.get_dbs_served"))
        cls._db_list.return_value = ["postgres", get_db_name()]

        def fake_db_filter(dbs, host=None):
            return [db for db in dbs if db in cls._db_list()]

        cls.startClassPatcher(
            patch("odoo.http.Application.filter_dbs_served", side_effect=fake_db_filter)
        )

    def setUp(self):
        super().setUp()
        self.opener = requests.Session()
        Registry.remove(get_db_name())
        close_db(get_db_name())
        odoo.http.invalidate_db_catalog_cache()
        self.addCleanup(odoo.http.invalidate_db_catalog_cache)

    def duplicate_current_db(self, db_suffix):
        db_duplicate = f"{get_db_name()}-test-http-registry-{db_suffix}"

        duplicate_db(db_source=get_db_name(), db_dest=db_duplicate)
        self.addCleanup(drop_db, db_duplicate)
        self.addCleanup(close_db, db_duplicate)
        self._db_list.return_value.append(db_duplicate)
        self.addCleanup(self._db_list.return_value.remove, db_duplicate)

        return db_duplicate

    def authenticate(self, *, db=None):
        session = odoo.http.root.session_store.new()
        session.update(odoo.http.prepare_default_session(), db=db or get_db_name())
        session.context["lang"] = odoo.http.DEFAULT_LANG
        odoo.http.root.session_store.save(session)
        self.opener.cookies.set("session_id", session.sid, domain=HOST)
        return session

    def url_open(self, path, *, allow_redirects=False):
        if not path.startswith("/"):
            raise ValueError("can only request a relative url")
        url = urljoin(f"http://{HOST}:{odoo.tools.config['http_port']}", path)
        return self.opener.get(url, allow_redirects=allow_redirects)

    def test_signaling(self):
        self.authenticate()
        res = self.url_open("/test_http/ensure_db")
        self.assertEqual(res.status_code, 200)

        with Registry(get_db_name()).cursor() as cr:
            cr.execute("INSERT INTO orm_signaling_registry default values")

        with self.assertLogs("odoo.registry", logging.INFO) as capture:
            res = self.url_open("/test_http/ensure_db")
            self.assertEqual(res.status_code, 200)
        self.assertEqual(
            capture.output,
            [
                "INFO:odoo.registry:Reloading the model registry after database signaling.",
                Like("INFO:odoo.registry:Registry loaded in ...s"),
            ],
        )

    def test_missing_db(self):
        db_duplicate = self.duplicate_current_db("drop")

        session = self.authenticate(db=db_duplicate)
        res = self.url_open("/test_http/ensure_db")
        self.assertEqual(res.status_code, 200)

        close_db(db_duplicate)
        drop_db(db_duplicate)
        self.assertIn(db_duplicate, Registry.registries)

        with self.assertLogs("odoo.http.application", logging.WARNING) as capture:
            res = self.url_open("/test_http/ensure_db")
            res.raise_for_status()
            self.assertFalse(
                odoo.http.root.session_store.get(session.sid).db,
                "A session on a dropped database must be durably logged out.",
            )
            self.authenticate(db=db_duplicate)
            res_query = self.url_open(f"/test_http/ensure_db?db={db_duplicate}")
            res_query.raise_for_status()

        self.assertEqual(
            [
                (
                    res.status_code,
                    urlsplit(res.headers.get("Location", "")).path,
                ),
                (
                    res_query.status_code,
                    urlsplit(res_query.headers.get("Location", "")).path,
                ),
            ],
            [(303, "/web/database/selector")] * 2,
            "It should not redirect back on /test_http/ensure_db.",
        )
        self.assertEqual(
            capture.output,
            [
                Like(
                    "WARNING:odoo.http.application:Database or registry unusable, trying without\n"
                    f'Traceback...database "{db_duplicate}" does not exist...'
                )
            ]
            * 2,
        )

    def test_catalog_unreachable_keeps_session(self):
        session = self.authenticate()
        boom = psycopg.OperationalError("server closed the connection unexpectedly")
        with (
            patch("odoo.http._serve.Registry", side_effect=boom),
            patch("odoo.service.db.list_dbs", side_effect=boom),
            self.assertLogs("odoo.http.application", logging.WARNING) as capture,
        ):
            res = self.url_open("/test_http/ensure_db")
        self.assertEqual(
            capture.output,
            [
                Like(
                    "WARNING:odoo.http.application:Database or registry "
                    "unusable, trying without\nTraceback...server closed the "
                    "connection unexpectedly..."
                )
            ],
        )
        self.assertEqual(
            (res.status_code, urlsplit(res.headers.get("Location", "")).path),
            (303, "/web/database/selector"),
            "The request itself degrades to db-less serving.",
        )
        persisted = odoo.http.root.session_store.get(session.sid)
        self.assertEqual(
            persisted.db,
            get_db_name(),
            "A catalog-unreachable blip must not log the session out.",
        )

    def test_pool_error_keeps_session(self):
        session = self.authenticate()
        with (
            patch("odoo.http._serve.Registry") as registry_cls,
            self.assertLogs("odoo.http.application", logging.WARNING),
        ):
            registry_cls.return_value.cursor.side_effect = PoolError(
                "couldn't get a connection after 30.00 sec"
            )
            res = self.url_open("/test_http/ensure_db")
        self.assertEqual(
            (res.status_code, urlsplit(res.headers.get("Location", "")).path),
            (303, "/web/database/selector"),
            "The request itself degrades to db-less serving.",
        )
        persisted = odoo.http.root.session_store.get(session.sid)
        self.assertEqual(
            persisted.db,
            get_db_name(),
            "A transient pool failure must not log the session out.",
        )

    @mute_logger("odoo.db")
    def test_corrupt_ir_module_module_table(self):
        db_duplicate = self.duplicate_current_db("corrupt-irmodule")

        with db_connect(db_duplicate).cursor() as cr:
            cr.execute("""
                ALTER TABLE "ir_module_module" DROP COLUMN "state"
            """)

        self.authenticate(db=db_duplicate)

        with (
            self.assertLogs("odoo.registry", logging.ERROR) as capture1,
            self.assertLogs("odoo.http.application", logging.WARNING) as capture2,
        ):
            res = self.url_open("/test_http/greeting-public")
            self.assertEqual(res.status_code, 404)
        self.assertEqual(
            capture1.output,
            [
                "ERROR:odoo.registry:Failed to load registry",
            ],
        )
        self.assertEqual(
            capture2.output,
            [
                Like(
                    "WARNING:odoo.http.application:Database or registry unusable, trying without\n"
                    'Traceback...column "state" does not exist...'
                )
            ],
        )

    @mute_logger("odoo.db")
    def test_corrupt_signaling(self):
        db_duplicate = self.duplicate_current_db("corrupt-sequence")

        self.authenticate(db=db_duplicate)
        res = self.url_open("/test_http/ensure_db")
        self.assertEqual(res.status_code, 200)

        with db_connect(db_duplicate).cursor() as cr:
            cr.execute("""
                DROP table "orm_signaling_registry"
            """)

        with self.subTest(name="existing registry"):
            with self.assertLogs("odoo.http.application", logging.WARNING) as capture:
                res = self.url_open("/test_http/greeting-public")
                self.assertEqual(res.status_code, 404)
            self.assertEqual(
                capture.output,
                [
                    Like(
                        "WARNING:odoo.http.application:Database or registry unusable, trying without\n"
                        'Traceback...relation "orm_signaling_registry_id_seq" does not exist...'
                    )
                ],
            )

        with self.subTest(name="new registry"):
            self.authenticate(db=db_duplicate)
            Registry.remove(db_duplicate)
            res = self.url_open("/test_http/greeting-public")
            self.assertEqual(res.status_code, 200)
