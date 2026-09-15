import unittest

import psycopg

from odoo.db.dsn import (
    _LOCALE_INDEPENDENT_AUTH_MARKERS,
    _expand_conninfo,
    _get_dsn_key,
    _get_key_dbname,
    _resolve_connect_error,
)


class TestNormalizeDsnKey(unittest.TestCase):
    def test_dbname_keeps_its_libpq_name(self):
        key_dict = dict(_get_dsn_key({"dbname": "test", "host": "localhost"}))
        self.assertEqual(key_dict["dbname"], "test")
        self.assertNotIn("database", key_dict)

    def test_key_dbname_reads_the_one_field_the_pool_files_by(self):
        self.assertEqual(
            _get_key_dbname(_get_dsn_key({"dbname": "test", "host": "h"})), "test"
        )
        self.assertEqual(_get_key_dbname(_get_dsn_key({"host": "h"})), "")
        self.assertEqual(_get_key_dbname(frozenset()), "")

    def test_password_excluded(self):
        key_dict = dict(_get_dsn_key({"dbname": "test", "password": "secret"}))
        self.assertNotIn("password", key_dict)

    def test_none_values_excluded(self):
        key_dict = dict(_get_dsn_key({"dbname": "test", "host": None}))
        self.assertNotIn("host", key_dict)

    def test_string_dsn(self):
        key_dict = dict(_get_dsn_key("dbname=test host=localhost"))
        self.assertEqual(key_dict["dbname"], "test")
        self.assertEqual(key_dict["host"], "localhost")

    def test_same_dsn_same_key(self):
        key1 = _get_dsn_key({"dbname": "test", "host": "localhost"})
        key2 = _get_dsn_key("dbname=test host=localhost")
        self.assertEqual(key1, key2)


class TestExpandConninfo(unittest.TestCase):
    def test_the_dsn_key_never_survives_expansion(self):
        self.assertEqual(
            _expand_conninfo({"dsn": "", "dbname": "x", "autocommit": True}),
            {"dbname": "x", "autocommit": True},
        )
        self.assertEqual(
            _expand_conninfo({"dsn": "host=h", "dbname": "x"}),
            {"host": "h", "dbname": "x"},
        )

    def test_keywords_override_what_the_dsn_spells(self):
        self.assertEqual(
            _expand_conninfo({"dsn": "dbname=a host=h", "dbname": "b"})["dbname"], "b"
        )


class TestNormalizeDsnKeyPassword(unittest.TestCase):
    def test_password_rotation_yields_different_key(self):
        base = {"dbname": "x", "host": "h", "user": "u"}
        k0 = _get_dsn_key({**base, "password": "old"})
        k1 = _get_dsn_key({**base, "password": "new"})
        self.assertNotEqual(
            k0, k1, "different passwords must yield different pool keys"
        )

    def test_password_not_leaked_in_key(self):
        key = _get_dsn_key(
            {"dbname": "x", "host": "h", "user": "u", "password": "s3cr3t"}
        )
        for _k, v in key:
            self.assertNotIn(
                "s3cr3t", v, "raw password must not appear in the pool key"
            )


class TestNormalizeDsnKeyUriExpansion(unittest.TestCase):
    def test_uri_password_not_in_key(self):
        key = _get_dsn_key(
            {"dsn": "postgresql://u:s3cret@h:5433/dbz", "application_name": "x"}
        )
        self.assertNotIn("s3cret", str(sorted(key)))
        kd = dict(key)
        self.assertEqual(kd.get("dbname"), "dbz")
        self.assertEqual(kd.get("host"), "h")

    def test_uri_password_rotation_changes_key(self):
        k1 = _get_dsn_key({"dsn": "postgresql://u:old@h/dbz"})
        k2 = _get_dsn_key({"dsn": "postgresql://u:new@h/dbz"})
        self.assertNotEqual(k1, k2)

    def test_kwargs_override_uri_components(self):
        key = dict(
            _get_dsn_key(
                {
                    "dsn": "postgresql://h/dbz?application_name=uriapp",
                    "application_name": "kwapp",
                }
            )
        )
        self.assertEqual(key.get("application_name"), "kwapp")


class TestConnectErrorTranslation(unittest.TestCase):
    def _op_error(self, message):
        return psycopg.OperationalError(message)

    def test_missing_database_translates_to_invalid_catalog_name(self):
        exc = self._op_error(
            'connection failed: FATAL:  database "nope" does not exist'
        )
        self.assertIsInstance(
            _resolve_connect_error(exc), psycopg.errors.InvalidCatalogName
        )

    def test_missing_role_translates_to_auth_error(self):
        exc = self._op_error('connection failed: FATAL:  role "nobody" does not exist')
        self.assertIsInstance(
            _resolve_connect_error(exc),
            psycopg.errors.InvalidAuthorizationSpecification,
        )

    def test_bad_password_translates_to_auth_error(self):
        exc = self._op_error('FATAL:  password authentication failed for user "x"')
        self.assertIsInstance(
            _resolve_connect_error(exc),
            psycopg.errors.InvalidAuthorizationSpecification,
        )

    def test_no_pg_hba_entry_translates_to_auth_error(self):
        exc = self._op_error('FATAL:  no pg_hba.conf entry for host "1.2.3.4"')
        self.assertIsInstance(
            _resolve_connect_error(exc),
            psycopg.errors.InvalidAuthorizationSpecification,
        )

    def test_transient_errors_return_none(self):
        for msg in (
            "connection refused",
            "connection timeout",
            "could not connect to server: Connection refused",
            "server closed the connection unexpectedly",
            "FATAL:  the database system is starting up",
        ):
            with self.subTest(msg=msg):
                self.assertIsNone(_resolve_connect_error(self._op_error(msg)))


if __name__ == "__main__":
    unittest.main()


class TestConnectErrorTranslationIsLocaleAware(unittest.TestCase):
    PG_HBA_IN_FOUR_LANGUAGES = (
        ('FATAL:  no pg_hba.conf entry for host "1.2.3.4"'),
        (
            "FATAL:  no hay una l\u00ednea en pg_hba.conf para el servidor \u00ab1.2.3.4\u00bb"
        ),
        (
            "FATAL:  aucune entr\u00e9e dans pg_hba.conf pour l'h\u00f4te \u00ab 1.2.3.4 \u00bb"
        ),
        ("FATAL:  keine pg_hba.conf-Eintrag f\u00fcr Host \u00bb1.2.3.4\u00ab"),
    )

    def test_pg_hba_is_recognised_in_every_language(self):
        for msg in self.PG_HBA_IN_FOUR_LANGUAGES:
            with self.subTest(msg=msg[:40]):
                self.assertIsInstance(
                    _resolve_connect_error(psycopg.OperationalError(msg)),
                    psycopg.errors.InvalidAuthorizationSpecification,
                    "pg_hba.conf is a filename; no catalogue translates it, so "
                    "this one must not depend on lc_messages",
                )

    def test_the_locale_proof_markers_contain_no_prose(self):
        for marker in _LOCALE_INDEPENDENT_AUTH_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(
                    " ",
                    marker,
                    "a marker with a space in it is a phrase, and phrases are "
                    "translated -- keep this list to identifiers and filenames",
                )

    def test_a_transient_failure_is_still_transient(self):
        for msg in (
            "could not connect to server: Connection refused",
            "server closed the connection unexpectedly",
            "FATAL:  the database system is starting up",
        ):
            with self.subTest(msg=msg[:40]):
                self.assertIsNone(
                    _resolve_connect_error(psycopg.OperationalError(msg)),
                    "classifying a restart as permanent would make the pool "
                    "give up on a server that is about to come back",
                )

    def test_english_auth_messages_are_still_recognised(self):
        for msg in (
            'FATAL:  password authentication failed for user "x"',
            'FATAL:  role "x" does not exist',
            'FATAL:  role "x" is not permitted to log in',
        ):
            with self.subTest(msg=msg[:40]):
                self.assertIsInstance(
                    _resolve_connect_error(psycopg.OperationalError(msg)),
                    psycopg.errors.InvalidAuthorizationSpecification,
                )

    def test_a_localised_password_failure_is_a_known_gap(self):
        localised = (
            "FATAL:  la autentificaci\u00f3n password fall\u00f3 para el usuario "
            "\u00abx\u00bb"
        )
        self.assertIsNone(
            _resolve_connect_error(psycopg.OperationalError(localised)),
            "This is the documented residual, pinned so it is not mistaken for "
            "a regression: a localised password failure is NOT recognised, and "
            "costs db_borrow_timeout. There is no client-side fix -- psycopg "
            "exposes no SQLSTATE for connect errors, and `-c lc_messages=C` "
            "cannot help because authentication precedes options processing. "
            "If this ever starts passing, the fix is real and this test should "
            "be inverted.",
        )
