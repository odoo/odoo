from psycopg.errors import UniqueViolation

from odoo.db import schema as sql
from odoo.orm.models.table_objects import Constraint, UniqueIndex
from odoo.tests import TransactionCase, tagged

_TABLE = "test_table_object_conversion"
_NAME = f"{_TABLE}_name_uniq"


class _Pool:
    def post_constraint(self, cr, apply_it, name):
        apply_it(cr)


class _Model:
    _table = _TABLE

    def __init__(self, env):
        self.env = env
        self.pool = _Pool()


@tagged("post_install", "-at_install")
class TestTableObjectConversion(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.cr.execute(
            f"CREATE TABLE {_TABLE} (id serial PRIMARY KEY, name varchar)"
        )
        self.model = _Model(self.env)

    def _named(self, table_object):
        table_object.name = "name_uniq"
        return table_object

    def _constraint_exists(self):
        return bool(sql.get_constraint_definition(self.env.cr, _TABLE, _NAME))

    def _index_definition(self):
        return sql.get_index_definition(self.env.cr, _NAME)[0]

    def test_a_constraints_backing_index_is_attributed_to_it(self):
        self._named(Constraint("UNIQUE(name)")).apply_to_database(self.model)

        self.assertTrue(
            self._index_definition(),
            "pg_indexes does not list a UNIQUE constraint's index, so reading "
            "it as a plain index was never ambiguous and this fix is moot",
        )
        self.assertEqual(sql.get_index_constraint(self.env.cr, _NAME), _NAME)

    def test_a_plain_index_is_attributed_to_nothing(self):
        self._named(UniqueIndex("(lower(name))")).apply_to_database(self.model)

        self.assertTrue(self._index_definition())
        self.assertIsNone(sql.get_index_constraint(self.env.cr, _NAME))

    def test_a_constraint_becomes_an_index(self):
        self._named(Constraint("UNIQUE(name)")).apply_to_database(self.model)
        self._named(UniqueIndex("(lower(name))")).apply_to_database(self.model)

        self.assertFalse(
            self._constraint_exists(),
            "the constraint outlived the declaration that produced it",
        )
        self.assertIn(
            "lower",
            self._index_definition(),
            "the index still enforces the old rule, so a case-insensitive "
            "declaration reads as applied while nothing changed",
        )
        self.assertIsNone(sql.get_index_constraint(self.env.cr, _NAME))

    def test_an_index_becomes_a_constraint(self):
        self._named(UniqueIndex("(lower(name))")).apply_to_database(self.model)
        self._named(Constraint("UNIQUE(name)")).apply_to_database(self.model)

        self.assertTrue(self._constraint_exists())
        self.assertEqual(sql.get_index_constraint(self.env.cr, _NAME), _NAME)

    def test_reapplying_an_unchanged_index_is_not_a_rebuild(self):
        self._named(UniqueIndex("(lower(name))")).apply_to_database(self.model)
        self.env.cr.execute("SELECT oid FROM pg_class WHERE relname = %s", (_NAME,))
        before = self.env.cr.fetchone()

        self._named(UniqueIndex("(lower(name))")).apply_to_database(self.model)
        self.env.cr.execute("SELECT oid FROM pg_class WHERE relname = %s", (_NAME,))

        self.assertEqual(self.env.cr.fetchone(), before)

    def test_the_rule_each_kind_enforces_actually_applies(self):
        self._named(UniqueIndex("(lower(name))")).apply_to_database(self.model)
        self.env.cr.execute(f"INSERT INTO {_TABLE} (name) VALUES ('Casing')")
        with self.assertRaises(UniqueViolation):
            with self.env.cr.savepoint():
                self.env.cr.execute(f"INSERT INTO {_TABLE} (name) VALUES ('casing')")

        self._named(Constraint("UNIQUE(name)")).apply_to_database(self.model)
        self.env.cr.execute(f"INSERT INTO {_TABLE} (name) VALUES ('casing')")
        with self.assertRaises(UniqueViolation):
            with self.env.cr.savepoint():
                self.env.cr.execute(f"INSERT INTO {_TABLE} (name) VALUES ('casing')")


@tagged("post_install", "-at_install")
class TestIrModelConstraintUnlink(TransactionCase):
    def setUp(self):
        super().setUp()
        self.env.cr.execute(
            f"CREATE TABLE {_TABLE} (id serial PRIMARY KEY, name varchar)"
        )

    def _record(self, recorded_type):
        return self.env["ir.model.constraint"].create(
            {
                "name": _NAME,
                "model": self.env["ir.model"]._get_id("res.partner"),
                "module": self.env["ir.module.module"]
                .search([("name", "=", "base")], limit=1)
                .id,
                "type": recorded_type,
            }
        )

    def test_a_constraint_recorded_as_an_index_is_still_dropped(self):
        self.env.cr.execute(
            f"ALTER TABLE {_TABLE} ADD CONSTRAINT {_NAME} UNIQUE (name)"
        )

        self._record("i").unlink()

        self.assertIsNone(
            sql.get_constraint_definition(self.env.cr, _TABLE, _NAME),
            "DROP INDEX cannot release a constraint's backing index, and the "
            "upgrade that tried it left the registry unable to load",
        )
        self.assertIsNone(sql.get_index_definition(self.env.cr, _NAME)[0])

    def test_an_index_recorded_as_a_constraint_is_still_dropped(self):
        self.env.cr.execute(f"CREATE UNIQUE INDEX {_NAME} ON {_TABLE} (name)")

        self._record("u").unlink()

        self.assertIsNone(
            sql.get_index_definition(self.env.cr, _NAME)[0],
            "the drop matched on constraint type and found nothing, so the "
            "index survived its own declaration with no error raised",
        )
