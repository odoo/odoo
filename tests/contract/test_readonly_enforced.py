import psycopg
import pytest

from .conftest import requires_pg


@requires_pg
class TestEnforceReadonlyIsATransactionProperty:
    def test_an_idle_primary_cursor_becomes_read_only(self, scratch_cursor):
        cr = scratch_cursor
        assert cr.readonly is False
        cr.enforce_readonly()
        assert cr.readonly is True
        cr.execute("SELECT 1")
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            cr.execute("CREATE TABLE probe_ro (id int)")

    def test_a_cursor_already_in_a_transaction_refuses(self, scratch_cursor):
        cr = scratch_cursor
        cr.execute("SELECT 1")
        with pytest.raises(psycopg.ProgrammingError):
            cr.enforce_readonly()
        assert cr.readonly is False

    def test_enforcing_twice_is_idempotent(self, scratch_cursor):
        cr = scratch_cursor
        cr.enforce_readonly()
        cr.execute("SELECT 1")
        cr.enforce_readonly()
        assert cr.readonly is True
