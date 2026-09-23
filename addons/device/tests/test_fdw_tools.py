from datetime import timedelta
from unittest.mock import patch

import psycopg

from odoo import fields
from odoo.db import schema as sql
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.device.tests.common import DeviceTransactionCase
from odoo.addons.device.tools import fdw

LOG_TABLE = "device_data_log"


class TestFdwHelpers(DeviceTransactionCase):
    def test_a_regular_table_is_not_foreign(self):
        self.assertFalse(fdw.is_foreign(self.env.cr, LOG_TABLE))
        self.assertIsNone(fdw.foreign_server(self.env.cr, LOG_TABLE))

    def test_an_installed_model_misses_no_column(self):
        model = self.env["device.data.log"]
        existing = sql.get_table_columns(self.env.cr, LOG_TABLE)
        self.assertEqual(fdw.missing_columns(model, existing), [])

    def test_missing_columns_names_the_column_with_its_sql_type(self):
        model = self.env["device.data.log"]
        existing = sql.get_table_columns(self.env.cr, LOG_TABLE)
        existing.pop("raw_payload")
        self.assertEqual(
            fdw.missing_columns(model, existing), [("raw_payload", "text")]
        )

    def test_checked_references_resolve_to_tables(self):
        model = self.env["device.data.log"]
        self.assertEqual(
            fdw.checked_references(model),
            [("device_id", "device_device", True)],
        )

    def test_trigger_statements_carry_the_three_guards_and_no_placeholder(self):
        stmts = fdw.trigger_statements(
            LOG_TABLE,
            [("device_id", "device_device", True)],
            [("device_device", "log_last_id")],
        )
        joined = "\n".join(stmts)
        self.assertIn("trg_device_data_log_fdw_fk_check BEFORE INSERT", joined)
        self.assertIn("trg_device_data_log_fdw_unlink_pointer AFTER DELETE", joined)
        self.assertIn(
            "trg_device_device_fdw_no_delete_device_data_log BEFORE DELETE", joined
        )
        # "%" would be read as a parameter placeholder by the cursor.
        self.assertNotIn("%", joined)


class TestFdwGuardsOnARegularTable(DeviceTransactionCase):
    """The triggers behave like the foreign keys they replace.

    Installed here on the regular ``device_data_log`` table, inside the test
    transaction, so what is verified is the trigger logic itself and not the
    FK Postgres still enforces on this table.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="FDW Config")
        cls.device = cls._create_device_device(config=cls.config, identifier="FDW-1")
        model = cls.env["device.data.log"]
        for statement in fdw.trigger_statements(
            LOG_TABLE,
            fdw.checked_references(model),
            [("device_device", "log_last_id")],
        ):
            cls.env.cr.execute(statement)

    def _log(self, **vals):
        vals.setdefault("device_id", self.device.id)
        vals.setdefault("timestamp", fields.Datetime.now())
        return self.env["device.data.log"].create(vals)

    @mute_logger("odoo.sql_db")
    def test_a_device_with_history_cannot_be_deleted(self):
        self._log()
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.env.cr.savepoint():
                self.env.cr.execute(
                    "DELETE FROM device_device WHERE id = %s", [self.device.id]
                )

    def test_a_device_without_history_can_be_deleted(self):
        spare = self._create_device_device(config=self.config, identifier="FDW-2")
        with self.env.cr.savepoint():
            self.env.cr.execute("DELETE FROM device_device WHERE id = %s", [spare.id])
            self.assertEqual(self.env.cr.rowcount, 1)

    def test_deleting_a_log_clears_the_pointer(self):
        log = self._log()
        self.device.log_last_id = log
        self.env.flush_all()
        self.env.cr.execute("DELETE FROM device_data_log WHERE id = %s", [log.id])
        self.env.cr.execute(
            "SELECT log_last_id FROM device_device WHERE id = %s", [self.device.id]
        )
        self.assertIsNone(self.env.cr.fetchone()[0])

    def test_pointer_constraints_are_found_and_dropped(self):
        # rolled back, so the constraint is there for the tests that follow
        savepoint = self.env.cr.savepoint()
        try:
            dropped = fdw.drop_pointer_foreign_keys(
                self.env.cr, [("device_device", "log_last_id")]
            )
            self.assertEqual(len(dropped), 1)
            self.assertIn("log_last_id", dropped[0])
        finally:
            savepoint.close(rollback=True)

    def test_an_installed_guard_is_not_dropped_and_recreated(self):
        statements = fdw.trigger_statements(
            LOG_TABLE,
            fdw.checked_references(self.env["device.data.log"]),
            [("device_device", "log_last_id")],
        )
        table_ddl = [s for s in statements if "TRIGGER" in s.split("(")[0]]
        functions = [s for s in statements if s.startswith("CREATE OR REPLACE")]
        self.assertTrue(table_ddl)
        self.assertTrue(
            all(fdw._installs_existing_trigger(self.env.cr, s) for s in table_ddl)
        )
        # a function body may change, and replacing it locks no table
        self.assertFalse(
            any(fdw._installs_existing_trigger(self.env.cr, s) for s in functions)
        )

    def test_a_guard_for_a_reference_no_longer_checked_is_stale(self):
        self.env.cr.execute(
            f"""
            CREATE FUNCTION res_company_fdw_no_delete_{LOG_TABLE}() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RETURN OLD; END $$;
            CREATE TRIGGER trg_res_company_fdw_no_delete_{LOG_TABLE} BEFORE DELETE
            ON res_company FOR EACH ROW
            EXECUTE FUNCTION res_company_fdw_no_delete_{LOG_TABLE}();
            """
        )
        references = fdw.checked_references(self.env["device.data.log"])
        self.assertEqual(
            fdw.stale_guard_triggers(self.env.cr, LOG_TABLE, references),
            [(f"trg_res_company_fdw_no_delete_{LOG_TABLE}", "res_company")],
        )

    def test_guards_left_by_a_rename_of_the_log_table_are_stale(self):
        # A rename carries the log's guards along under the old name, and a
        # referenced table keeps a guard naming a log table that is gone.
        self.env.cr.execute(
            f"""
            CREATE FUNCTION old_log_fdw_fk_check() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$;
            CREATE TRIGGER trg_old_log_fdw_fk_check BEFORE INSERT
            ON {LOG_TABLE} FOR EACH ROW EXECUTE FUNCTION old_log_fdw_fk_check();
            CREATE FUNCTION device_device_fdw_no_delete_old_log() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN RETURN OLD; END $$;
            CREATE TRIGGER trg_device_device_fdw_no_delete_old_log BEFORE DELETE
            ON device_device FOR EACH ROW
            EXECUTE FUNCTION device_device_fdw_no_delete_old_log();
            """
        )
        references = fdw.checked_references(self.env["device.data.log"])
        self.assertCountEqual(
            fdw.stale_guard_triggers(self.env.cr, LOG_TABLE, references),
            [
                ("trg_old_log_fdw_fk_check", LOG_TABLE),
                ("trg_device_device_fdw_no_delete_old_log", "device_device"),
            ],
        )


class TestGcOrdersLocalWritesFirst(DeviceTransactionCase):
    """Pointers are cleared before the rows go, never after.

    On a foreign table the two writes commit in different databases, so the
    order is what keeps a crash in between from leaving a dangling pointer.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="GC Config")
        cls.device = cls._create_device_device(config=cls.config, identifier="GC-1")

    def test_the_pointer_is_null_by_the_time_unlink_runs(self):
        old = self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "timestamp": fields.Datetime.now() - timedelta(days=400),
            }
        )
        self.device.log_last_id = old
        self.env.flush_all()
        seen = []
        model_cls = type(self.env["device.data.log"])
        original_unlink = model_cls.unlink

        def unlink_spy(records):
            records.env.cr.execute(
                "SELECT log_last_id FROM device_device WHERE id = %s",
                [self.device.id],
            )
            seen.append(records.env.cr.fetchone()[0])
            return original_unlink(records)

        with patch.object(
            model_cls, "_fdw_pointer_columns", (("device_device", "log_last_id"),)
        ):
            with patch.object(model_cls, "unlink", unlink_spy):
                deleted = self.env["device.data.log"]._gc_old_logs(
                    fields.Datetime.now() - timedelta(days=30)
                )
        self.assertEqual(deleted, 1)
        self.assertEqual(seen, [None])
        self.assertFalse(old.exists())


@tagged("post_install", "-at_install")
class TestRawPayloadGcBatches(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Batch Config")
        cls.device = cls._create_device_device(config=cls.config, identifier="BATCH-1")

    def test_every_batch_is_bounded_by_id_and_all_rows_are_reached(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "device.raw_payload_retention_days", "30"
        )
        logs = self.env["device.data.log"].create(
            [
                {
                    "device_id": self.device.id,
                    "timestamp": fields.Datetime.now() - timedelta(days=90),
                    "raw_payload": f'{{"n": {n}}}',
                }
                for n in range(3)
            ]
        )
        model_cls = type(self.env["device.data.log"])
        with patch.object(model_cls, "_RAW_PAYLOAD_BATCH_SIZE", 1):
            cleared = self.env["device.data.log"]._gc_old_raw_payloads()
        self.assertEqual(cleared, 3)
        self.assertFalse(any(logs.mapped("raw_payload")))
