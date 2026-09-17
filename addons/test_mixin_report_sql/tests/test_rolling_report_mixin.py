import datetime as dt
from unittest.mock import patch

from odoo.libs.sql import SQL
from odoo.tests.common import TransactionCase


class RollingCase(TransactionCase):
    """A real rolling report over a real, date-grained source table.

    The consumer suite in ``agromarin/remote_gps`` covers the same semantics
    against production shapes, but it lives in another repository that this
    one's CI never checks out — so the mixin needs its own fence here.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["mixin.report.sql.test.rolling"]
        cls.Source = cls.env["mixin.report.sql.test.source"]
        cls.table = cls.report._table
        cls.today = dt.date.today()

    def _seed(self, days_ago, grain="a", value=1.0):
        record = self.Source.create(
            {
                "date": self.today - dt.timedelta(days=days_ago),
                "grain": grain,
                "value": value,
            }
        )
        self.env.flush_all()
        return record

    def _rows(self):
        self.env.cr.execute(
            SQL(
                "SELECT date, grain, total FROM %s ORDER BY date, grain",
                SQL.identifier(self.table),
            )
        )
        return self.env.cr.fetchall()


class TestStorageKind(RollingCase):
    def test_the_report_is_a_table_not_a_materialized_view(self):
        """The window refresh DELETEs and INSERTs, which REFRESH cannot express."""
        self.assertEqual(self.report._relation_kind, "r")
        self.assertEqual(self.report._relkind(self.table), "r")

    def test_the_orm_reads_the_table(self):
        self.assertIsNone(self.report._table_query)
        self.assertEqual(self.report._table_sql.code, f'"{self.table}"')

    def test_the_grain_column_is_indexed(self):
        self.env.cr.execute(
            "SELECT ic.relname FROM pg_index i "
            "JOIN pg_class ic ON ic.oid = i.indexrelid "
            "JOIN pg_class tc ON tc.oid = i.indrelid "
            "WHERE tc.relname = %s",
            (self.table,),
        )
        names = {row[0] for row in self.env.cr.fetchall()}
        self.assertIn(f"{self.table}__date_idx", names)
        self.assertIn(f"{self.table}__id_uidx", names)

    def test_the_column_list_comes_from_the_registry(self):
        self.assertEqual(
            self.report._rolling_columns(), ["id", "date", "grain", "total"]
        )

    def test_a_report_without_the_registry_is_refused_at_create_time(self):
        """mixin.sql.report is required and cannot be declared as a parent.

        Consumers write `_inherit = ["mixin.sql.report", "mixin.rolling.report"]`
        -- naming it a parent here makes that order impossible and the registry
        refuses the model. So the requirement is checked instead, and checked
        early: the column list is only reached by a *window* refresh, so a
        mis-composed report used to install cleanly, tick once against an empty
        table, and fail on the second tick.
        """
        with patch.object(type(self.report), "_get_fields_select", None):
            with self.assertRaises(NotImplementedError) as cm:
                self.report._rolling_columns()
            self.assertIn("mixin.sql.report", str(cm.exception))
            with self.assertRaises(NotImplementedError):
                self.report._create_relation()


class TestWindowRefresh(RollingCase):
    def test_a_window_refresh_matches_a_full_rebuild(self):
        for day in range(12):
            self._seed(day, value=float(day + 1))
        self.report.refresh(full=True)
        full = self._rows()
        self.assertTrue(self.report.refresh())
        self.assertEqual(self._rows(), full, "the window disagreed with a full rebuild")

    def test_a_window_refresh_picks_up_new_rows_in_the_window(self):
        self._seed(10, value=5.0)
        self._seed(0, value=1.0)
        self.report.refresh(full=True)
        self._seed(0, value=2.0)
        self.assertTrue(self.report.refresh())
        by_date = {row[0]: row[2] for row in self._rows()}
        self.assertEqual(by_date[self.today], 3.0)

    def test_periods_before_the_window_are_left_alone(self):
        self._seed(10, value=5.0)
        self.report.refresh(full=True)
        # A late-arriving row outside the window must NOT appear: the window
        # refresh never revisits settled periods. That is the contract, and
        # _rolling_mark_stale is how a caller asks for the exception.
        self._seed(10, value=7.0)
        self.assertTrue(self.report.refresh())
        by_date = {row[0]: row[2] for row in self._rows()}
        self.assertEqual(by_date[self.today - dt.timedelta(days=10)], 5.0)

    def test_a_full_rebuild_picks_up_settled_periods(self):
        self._seed(10, value=5.0)
        self.report.refresh(full=True)
        self._seed(10, value=7.0)
        self.assertTrue(self.report.refresh(full=True))
        by_date = {row[0]: row[2] for row in self._rows()}
        self.assertEqual(by_date[self.today - dt.timedelta(days=10)], 12.0)

    def test_the_cutoff_lands_on_a_grain_boundary(self):
        cutoff = self.today - dt.timedelta(days=self.report._rolling_window_days)
        self.env.cr.execute(SQL("SELECT %s", self.report._rolling_cutoff_sql()))
        self.assertEqual(self.env.cr.fetchone()[0], cutoff)

    def test_an_empty_source_is_not_a_reason_to_rebuild(self):
        """The parent rebuilds an empty relation; a table that is empty because
        the source is empty is simply correct."""
        self.assertFalse(self.report._relation_rebuild_when_empty)
        self.assertFalse(self.report._is_populated(self.table))
        self.assertFalse(self.report._relation_needs_rebuild())


class TestSelfHealing(RollingCase):
    def test_refresh_recreates_a_missing_table(self):
        self._seed(0, value=3.0)
        self.env.cr.execute(SQL("DROP TABLE %s", SQL.identifier(self.table)))
        self.assertIsNone(self.report._relkind(self.table))
        self.assertTrue(self.report.refresh())
        self.assertEqual(self.report._relkind(self.table), "r")
        self.assertEqual(self._rows()[0][2], 3.0)

    def test_refresh_rebuilds_when_the_definition_changed(self):
        self._seed(0, value=3.0)
        self.report.refresh(full=True)
        with patch.object(
            type(self.report),
            "_get_where_conditions",
            lambda self: ["s.value > 100"],
        ):
            self.assertTrue(self.report._relation_definition_changed())
            self.assertTrue(self.report.refresh())
            self.assertEqual(self._rows(), [])

    def test_a_failing_window_refresh_leaves_the_cursor_usable(self):
        """Without the parent's SAVEPOINT the cron's own bookkeeping write dies.

        ir.cron runs _resolve_attempt() and commits on the same cursor in its
        `finally`, so an aborted transaction loses the record of the failure
        along with the refresh.
        """
        self._seed(0, value=1.0)
        self.report.refresh(full=True)
        self.env.cr.execute(
            SQL("ALTER TABLE %s DROP COLUMN total", SQL.identifier(self.table))
        )
        with self.assertRaises(Exception):
            self.report.refresh()
        self.env["ir.config_parameter"].sudo().set_param("mixin_report_sql.roll", "1")
        self.env.flush_all()


class TestStaleness(RollingCase):
    def test_the_flag_round_trips(self):
        self.assertFalse(self.report._rolling_pop_stale())
        self.report._rolling_mark_stale()
        self.assertTrue(self.report._rolling_pop_stale())
        self.assertFalse(self.report._rolling_pop_stale())

    def test_a_settings_change_that_rewrites_history_forces_a_full_rebuild(self):
        self._seed(10, value=5.0)
        self.report.refresh(full=True)
        self._seed(10, value=7.0)
        self.report._rolling_mark_stale()
        self.assertTrue(self.report.refresh())
        by_date = {row[0]: row[2] for row in self._rows()}
        self.assertEqual(
            by_date[self.today - dt.timedelta(days=10)],
            12.0,
            "a stale report must rebuild every period, not just the window",
        )
        self.assertFalse(
            self.report._rolling_pop_stale(), "the flag is consumed by the rebuild"
        )


class TestConcurrency(RollingCase):
    """A slow refresh must cost one tick, never a connection per tick.

    Every cron-running instance ticks the same refresh; the GPS daily report
    once queued ninety of them behind a five-hour statement and exhausted
    max_connections.
    """

    def test_a_refresh_already_running_elsewhere_is_skipped(self):
        self._seed(0, value=1.0)
        other = self.registry.cursor()
        self.addCleanup(other.close)
        other.execute(SQL("SELECT pg_advisory_xact_lock(hashtext(%s))", self.table))
        with self.assertLogs(
            "odoo.addons.mixin_report_sql.models.mixin_materialized_view",
            level="WARNING",
        ) as logs:
            self.assertFalse(self.report.refresh())
        self.assertIn("skipped", logs.output[0])
        other.rollback()
        self.assertTrue(self.report.refresh(), "released lock, refresh proceeds")

    def test_a_refresh_that_overruns_its_timeout_is_a_transient_failure(self):
        self._seed(0, value=1.0)
        self.report.refresh(full=True)

        def sleep_past_the_bound(report):
            report.env.cr.execute(SQL("SELECT pg_sleep(1)"))

        with (
            patch.object(type(self.report), "_refresh_statement_timeout", "100ms"),
            patch.object(type(self.report), "_refresh_contents", sleep_past_the_bound),
        ):
            self.assertFalse(self.report.refresh())
        self.env.cr.execute(SQL("SELECT 1"))
        self.assertEqual(self.env.cr.fetchone()[0], 1, "cursor still usable")
