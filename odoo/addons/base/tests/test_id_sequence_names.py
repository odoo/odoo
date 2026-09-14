import importlib.util
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import SQL

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


def _load(version, name):
    spec = importlib.util.spec_from_file_location(
        f"base_migration_{name.replace('-', '_')}", MIGRATIONS / version / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("post_install", "-at_install")
class TestIdSequenceNames(TransactionCase):
    def _sequence_of(self, table):
        self.env.cr.execute("SELECT pg_get_serial_sequence(%s, 'id')", [table])
        return self.env.cr.fetchone()[0].rpartition(".")[2]

    def _probe_table(self, table):
        self.env.cr.execute(
            SQL("CREATE TABLE %s (id serial PRIMARY KEY)", SQL.identifier(table))
        )

    def test_a_model_rename_takes_the_id_sequence_with_the_table(self):
        for version, name in (
            ("1.34", "pre-migrate_document_family_rename"),
            ("1.51", "pre-migrate_integration_rename"),
        ):
            with self.subTest(migration=version):
                old, new = f"probe_old_{version[2:]}", f"probe_new_{version[2:]}"
                self._probe_table(old)

                _load(version, name)._rename_table(self.env.cr, old, new)

                self.assertEqual(self._sequence_of(new), f"{new}_id_seq")

    def test_a_sequence_left_behind_by_an_earlier_rename_takes_its_tables_name(self):
        self._probe_table("probe_renamed")
        self.env.cr.execute(
            "ALTER SEQUENCE probe_renamed_id_seq RENAME TO probe_original_id_seq"
        )

        _load("1.52", "pre-migrate_id_sequence_names").migrate(self.env.cr, "1.51")

        self.assertEqual(self._sequence_of("probe_renamed"), "probe_renamed_id_seq")

    def test_a_sequence_whose_canonical_name_is_taken_is_left_alone(self):
        self._probe_table("probe_clash")
        self.env.cr.execute(
            "ALTER SEQUENCE probe_clash_id_seq RENAME TO probe_elsewhere_id_seq"
        )
        self.env.cr.execute("CREATE SEQUENCE probe_clash_id_seq")

        _load("1.52", "pre-migrate_id_sequence_names").migrate(self.env.cr, "1.51")

        self.assertEqual(self._sequence_of("probe_clash"), "probe_elsewhere_id_seq")
