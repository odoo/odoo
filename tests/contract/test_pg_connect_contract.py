import psycopg
import pytest

from .conftest import requires_pg

MISSING_DB = "odoo_contract_no_such_db_xyzzy"


class TestPoolConnectFailureTranslation:
    @requires_pg
    def test_absent_database_raises_invalid_catalog_name(self):
        import odoo.db

        with pytest.raises(psycopg.errors.InvalidCatalogName):
            with odoo.db.db_connect(MISSING_DB).cursor():
                pass

    @requires_pg
    def test_that_type_would_escape_an_operational_error_catch(self):
        import odoo.db

        escaped = None
        try:
            with odoo.db.db_connect(MISSING_DB).cursor():
                pass
        except psycopg.OperationalError:
            escaped = False
        except Exception:
            escaped = True
        assert escaped is True, (
            "a missing database is now caught by `except psycopg.OperationalError`. "
            "If odoo.db.pool changed its connect-failure translation, revisit "
            "odoo.service.common._EXPECTED_CONNECT_FAILURES and the comments "
            "explaining why the catch is the broad psycopg.Error tree."
        )

    @requires_pg
    def test_authenticate_against_a_missing_database_returns_false(self):
        from odoo.service.common import exp_authenticate

        assert exp_authenticate(MISSING_DB, "admin", "x", None) is False, (
            "authenticate against a non-existent database no longer returns "
            "False -- /xmlrpc/common is auth=none, so a "
            "distinguishable answer here is a database existence oracle"
        )

    @requires_pg
    def test_reachable_non_odoo_database_does_not_raise(self, scratch_db):
        import odoo.db

        with odoo.db.db_connect(scratch_db).cursor() as cr:
            cr.execute("SELECT 1")
            assert cr.fetchone()[0] == 1
        odoo.db.close_db(scratch_db)
