from unittest.mock import patch

import psycopg
import pytest

from .conftest import fake_pg_cursor


@pytest.fixture
def lifecycle():
    from odoo.service.db import lifecycle

    return lifecycle


def _statements(cr):
    return [c.args[0] for c in cr.execute.call_args_list]


def _status(lifecycle, name):
    import odoo.db

    return patch.object(
        odoo.db, "get_unaccent_status", return_value=odoo.db.FunctionStatus[name]
    )


class TestUnaccentFollowsPresenceNotTheOption:
    def test_a_template_shipped_unaccent_is_made_immutable(self, lifecycle):
        cr = fake_pg_cursor()
        with _status(lifecycle, "PRESENT"):
            lifecycle._create_extensions(cr, "db", unaccent=False)
        statements = _statements(cr)
        assert "CREATE EXTENSION IF NOT EXISTS unaccent" not in statements
        assert "ALTER FUNCTION unaccent(text) IMMUTABLE" in statements

    def test_the_option_still_creates_the_extension(self, lifecycle):
        cr = fake_pg_cursor()
        with _status(lifecycle, "PRESENT"):
            lifecycle._create_extensions(cr, "db", unaccent=True)
        statements = _statements(cr)
        assert statements.index(
            "CREATE EXTENSION IF NOT EXISTS unaccent"
        ) < statements.index("ALTER FUNCTION unaccent(text) IMMUTABLE")

    @pytest.mark.parametrize("status", ["MISSING", "INDEXABLE"])
    def test_nothing_to_alter(self, lifecycle, status):
        cr = fake_pg_cursor()
        with _status(lifecycle, status):
            lifecycle._create_extensions(cr, "db", unaccent=False)
        assert "ALTER FUNCTION unaccent(text) IMMUTABLE" not in _statements(cr)

    def test_a_refused_alter_keeps_the_extensions(self, lifecycle, caplog):
        def execute(statement, *args, **kwargs):
            if statement.startswith("ALTER FUNCTION"):
                raise psycopg.errors.InsufficientPrivilege("must be owner")

        cr = fake_pg_cursor(execute=execute)
        with _status(lifecycle, "PRESENT"), caplog.at_level("WARNING"):
            lifecycle._create_extensions(cr, "db", unaccent=False)
        assert "cannot be made immutable" in caplog.text
        assert "Unable to create PostgreSQL extensions" not in caplog.text
