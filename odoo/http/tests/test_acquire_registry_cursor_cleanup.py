import typing
import unittest
from types import SimpleNamespace
from unittest import mock

import psycopg

from odoo.http import _serve
from odoo.http.exceptions import RegistryError


class _TrackingCursor:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def _acquire(this: typing.Any) -> typing.Any:
    return _serve._RequestServeMixin._acquire_registry_cursor(this)


def _call(check_signaling):
    cursor = _TrackingCursor()
    registry: typing.Any = SimpleNamespace(
        cursor=lambda readonly=False, pin_key=None: cursor,
        check_signaling=check_signaling,
    )
    this = SimpleNamespace(
        db="testdb", registry=None, session=SimpleNamespace(sid="S" * 84)
    )
    with mock.patch.object(_serve, "Registry", lambda db: registry):
        raised = None
        try:
            _acquire(this)
        except BaseException as e:
            raised = e
    return raised, cursor


class TestAcquireRegistryCursorCleanup(unittest.TestCase):
    def test_success_returns_the_open_cursor(self):
        cursor = _TrackingCursor()
        registry: typing.Any = SimpleNamespace(
            cursor=lambda readonly=False, pin_key=None: cursor,
            check_signaling=lambda cr: registry,
        )
        this = SimpleNamespace(
            db="testdb", registry=None, session=SimpleNamespace(sid="S" * 84)
        )
        with mock.patch.object(_serve, "Registry", lambda db: registry):
            got = _acquire(this)
        self.assertIs(got, cursor)
        self.assertFalse(cursor.closed)
        self.assertIs(this.registry, registry)

    def test_typed_error_translates_and_closes(self):
        def boom(cr):
            raise psycopg.ProgrammingError("no such column")

        raised, cursor = _call(boom)
        self.assertIsInstance(raised, RegistryError)
        self.assertTrue(cursor.closed, "typed path must close the cursor")

    def test_unexpected_error_closes_and_reraises_unchanged(self):
        sentinel = psycopg.InternalError("catalog is being rebuilt")

        def boom(cr):
            raise sentinel

        raised, cursor = _call(boom)
        self.assertIs(raised, sentinel)
        self.assertTrue(cursor.closed, "cursor leaked on an unexpected error")

    def test_base_exception_also_closes(self):
        def boom(cr):
            raise KeyboardInterrupt

        raised, cursor = _call(boom)
        self.assertIsInstance(raised, KeyboardInterrupt)
        self.assertTrue(cursor.closed)


if __name__ == "__main__":
    unittest.main()


class _ReadonlyCursor(_TrackingCursor):
    readonly = True

    def rollback(self):
        pass


class TestOpenReadWriteCursorRefusal(unittest.TestCase):
    def test_a_refused_readonly_replacement_is_closed_before_the_raise(self):
        initial, fresh = _ReadonlyCursor(), _ReadonlyCursor()

        class _Host:
            _require_env = _serve._RequestServeMixin._require_env
            _open_read_write_cursor = _serve._RequestServeMixin._open_read_write_cursor

        host = _Host()
        host.env = SimpleNamespace(
            registry=SimpleNamespace(
                db_name="testdb", cursor=lambda pin_key=None: fresh
            )
        )
        host.httprequest = SimpleNamespace(method="POST", path="/x")
        host.session = SimpleNamespace(sid="S" * 84)
        with self.assertRaises(RuntimeError):
            host._open_read_write_cursor(initial)
        self.assertTrue(initial.closed)
        self.assertTrue(fresh.closed, "the refused replacement cursor must not leak")
