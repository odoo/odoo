import unittest
from dataclasses import replace
from typing import Any

import psycopg

from odoo.db import settings as pool_settings
from odoo.db import utils as db_utils
from odoo.db.settings import PoolSettings
from odoo.db.utils import (
    _HEALTH_PARAMS,
    get_connection_info_for_database,
    is_maintenance_db,
)

_BASE = PoolSettings(
    app_name="odoo-{pid}",
    host="primary.example",
    port=5432,
    user="odoo",
    password="secret",
    sslmode="require",
    template="template0",
)


def _settings(**overrides: Any) -> PoolSettings:
    return replace(_BASE, **overrides)


class TestIsMaintenanceDb(unittest.TestCase):
    def test_system_and_template_databases(self):
        for name in ("postgres", "template0", "template1"):
            with self.subTest(name=name):
                self.assertTrue(is_maintenance_db(name, _settings()))

    def test_the_configured_template_is_included(self):
        self.assertTrue(
            is_maintenance_db("tpl_custom", _settings(template="tpl_custom"))
        )

    def test_the_default_reads_the_installed_settings_per_call(self):
        with pool_settings.installed(_settings(template="tpl_a")):
            self.assertTrue(is_maintenance_db("tpl_a"))
        with pool_settings.installed(_settings(template="tpl_b")):
            self.assertFalse(is_maintenance_db("tpl_a"))
            self.assertTrue(is_maintenance_db("tpl_b"))

    def test_ordinary_databases_are_not_maintenance(self):
        for name in ("prod", "template_of_mine", "postgres_backup"):
            with self.subTest(name=name):
                self.assertFalse(is_maintenance_db(name, _settings()))

    def test_system_dbs_has_one_definition(self):
        self.assertEqual(
            db_utils.SYSTEM_DBS, frozenset({"postgres", "template0", "template1"})
        )
        import odoo.db

        self.assertIs(odoo.db.SYSTEM_DBS, db_utils.SYSTEM_DBS)


class TestConnectionInfoForKeywords(unittest.TestCase):
    def _info(self, name="mydb", readonly=False, **overrides):
        return get_connection_info_for_database(name, readonly, _settings(**overrides))

    def test_returns_the_database_name_unchanged(self):
        db, info = self._info("mydb")
        self.assertEqual(db, "mydb")
        self.assertEqual(info["dbname"], "mydb")

    def test_carries_the_configured_credentials(self):
        _, info = self._info()
        self.assertEqual(info["host"], "primary.example")
        self.assertEqual(info["user"], "odoo")
        self.assertEqual(info["password"], "secret")
        self.assertEqual(info["sslmode"], "require")

    def test_unset_values_are_omitted_not_sent_empty(self):
        _, info = self._info(host=None, password=None)
        self.assertNotIn("host", info)
        self.assertNotIn("password", info)

    def test_health_parameters_are_applied(self):
        _, info = self._info()
        for key, value in _HEALTH_PARAMS.items():
            with self.subTest(key=key):
                self.assertEqual(info[key], value)

    def test_health_parameters_are_accepted_by_every_supported_libpq(self):
        # tcp_user_timeout (libpq 12) is the youngest of these; the wheel a
        # deployment installs picks its own libpq, and a keyword libpq does not
        # know fails the connect outright ("invalid connection option").
        # min_protocol_version arrived with libpq 18 and, at its default of
        # 3.0, negotiated exactly what its absence does.
        self.assertLessEqual(
            set(_HEALTH_PARAMS),
            {
                "connect_timeout",
                "tcp_user_timeout",
                "keepalives",
                "keepalives_idle",
                "keepalives_interval",
                "keepalives_count",
            },
        )

    def test_application_name_interpolates_the_pid_and_is_truncated(self):
        import os

        _, info = self._info()
        self.assertEqual(info["application_name"], f"odoo-{os.getpid()}")
        _, long_info = self._info(app_name="x" * 200)
        self.assertEqual(len(long_info["application_name"]), 63)

    def test_the_default_is_the_installed_settings(self):
        with pool_settings.installed(_settings(host="installed.example")):
            _, info = get_connection_info_for_database("mydb")
        self.assertEqual(info["host"], "installed.example")


class TestConnectionInfoForReplica(unittest.TestCase):
    def _info(self, readonly, **overrides):
        return get_connection_info_for_database(
            "mydb", readonly, _settings(**overrides)
        )

    def test_replica_overrides_host_and_port_only(self):
        _, info = self._info(
            readonly=True, replica_host="replica.example", replica_port=5433
        )
        self.assertEqual(info["host"], "replica.example")
        self.assertEqual(info["port"], 5433)
        self.assertEqual(info["user"], "odoo")
        self.assertEqual(info["password"], "secret")

    def test_without_a_replica_host_readonly_targets_the_primary(self):
        _, info = self._info(readonly=True)
        self.assertEqual(info["host"], "primary.example")

    def test_readonly_false_ignores_replica_settings(self):
        _, info = self._info(readonly=False, replica_host="replica.example")
        self.assertEqual(info["host"], "primary.example")


class TestConnectionInfoForUri(unittest.TestCase):
    def _info(self, uri):
        return get_connection_info_for_database(uri, settings=_settings())

    def test_database_is_taken_from_the_uri_path(self):
        db, info = self._info("postgresql://user@host:5432/thedb")
        self.assertEqual(db, "thedb")
        self.assertEqual(info["dsn"], "postgresql://user@host:5432/thedb")

    def test_username_is_the_fallback_database_name(self):
        db, _ = self._info("postgresql://theuser@host")
        self.assertEqual(db, "theuser")

    def test_malformed_uri_warns_instead_of_silently_guessing(self):
        with self.assertWarns(RuntimeWarning):
            db, _ = self._info("postgresql://host.example")
        self.assertEqual(db, "host.example")

    def test_a_uri_with_no_path_user_or_host_still_returns_a_string(self):
        for uri in ("postgresql:///", "postgresql://?connect_timeout=1"):
            with self.subTest(uri=uri), self.assertWarns(RuntimeWarning):
                db, info = self._info(uri)
            self.assertEqual(db, "")
            self.assertEqual(info["dsn"], uri)

    def test_health_params_do_not_override_the_uri_query_string(self):
        _, info = self._info("postgresql://h/db?connect_timeout=60&keepalives=0")
        self.assertNotIn("connect_timeout", info)
        self.assertNotIn("keepalives", info)
        self.assertEqual(info["keepalives_idle"], _HEALTH_PARAMS["keepalives_idle"])

    def test_uri_application_name_is_respected(self):
        _, info = self._info("postgresql://h/db?application_name=mine")
        self.assertNotIn("application_name", info)

    def test_application_name_is_added_when_the_uri_omits_it(self):
        _, info = self._info("postgresql://h/db")
        self.assertIn("application_name", info)

    def test_postgres_scheme_is_accepted_too(self):
        db, _ = self._info("postgres://user@host/thedb")
        self.assertEqual(db, "thedb")


if __name__ == "__main__":
    unittest.main()


class _SeedCursor:
    def __init__(self, *, blocked=False):
        self.statements: list[tuple[str, tuple]] = []
        self.blocked = blocked
        self.rolled_back = 0
        self._row = None

    def execute(self, query, params=None, log_exceptions=True):
        self.statements.append((" ".join(query.split()), tuple(params or ())))
        if query.startswith("SELECT current_setting"):
            self._row = ("5min",)
        elif "pg_restore_relation_stats" in query:
            if self.blocked:
                raise psycopg.errors.LockNotAvailable(
                    "canceling statement due to lock timeout"
                )
            self._row = (7,)

    def fetchone(self):
        return self._row

    def savepoint(self, flush=True):
        cursor = self

        class _Savepoint:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                if exc_type is not None:
                    cursor.rolled_back += 1
                return False

        return _Savepoint()


class TestPlannerStatsSeedNeverWaitsWithoutBound(unittest.TestCase):
    def test_the_seed_runs_under_a_lock_timeout_and_puts_the_old_value_back(self):
        from odoo.db.utils import update_planner_stats

        cr = _SeedCursor()
        self.assertEqual(update_planner_stats(cr, lock_timeout=2.0), 7)
        sets = [p for q, p in cr.statements if q.startswith("SET LOCAL lock_timeout")]
        self.assertEqual(sets, [("2000ms",), ("5min",)])
        self.assertEqual(cr.rolled_back, 0)

    def test_a_relation_locked_by_another_session_skips_the_seed(self):
        from odoo.db.utils import update_planner_stats

        cr = _SeedCursor(blocked=True)
        with self.assertLogs("odoo.db.utils", level="WARNING") as cm:
            self.assertEqual(update_planner_stats(cr, lock_timeout=2.0), 0)
        self.assertIn("not seeded", cm.output[0])
        self.assertEqual(
            cr.rolled_back,
            1,
            "the timeout and the failed statement leave with the savepoint, "
            "so the caller's transaction is usable and its lock_timeout is "
            "what it was",
        )
