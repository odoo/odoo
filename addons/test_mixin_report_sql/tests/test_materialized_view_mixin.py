import datetime as dt
from unittest.mock import patch

import psycopg

from odoo.exceptions import UserError
from odoo.libs.sql import SQL
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.mixin_report_sql.models import mixin_materialized_view


class MaterializedCase(TransactionCase):
    """Shared fixture: a real materialized report over a real source table."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["mixin.report.sql.test.mv"]
        cls.Source = cls.env["mixin.report.sql.test.source"]
        cls.table = cls.report._table

    def _seed(self, grain, value):
        record = self.Source.create({"grain": grain, "value": value})
        self.env.flush_all()
        return record

    def _indexes(self):
        """``{index_name: [columns]}`` for the report's relation."""
        self.env.cr.execute(
            """
            SELECT ic.relname, array_agg(a.attname ORDER BY array_position(i.indkey, a.attnum))
              FROM pg_index i
              JOIN pg_class ic ON ic.oid = i.indexrelid
              JOIN pg_class tc ON tc.oid = i.indrelid
              JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
             WHERE tc.relname = %s
               AND tc.relnamespace = current_schema::regnamespace
             GROUP BY ic.relname
            """,
            (self.table,),
        )
        return dict(self.env.cr.fetchall())

    def _oid(self):
        self.env.cr.execute(
            "SELECT oid FROM pg_class WHERE relname = %s "
            "AND relnamespace = current_schema::regnamespace",
            (self.table,),
        )
        row = self.env.cr.fetchone()
        return row[0] if row else None


class TestIntrospection(MaterializedCase):
    """Schema-scoped pg_class lookups."""

    def setUp(self):
        super().setUp()
        self.env.cr.execute("CREATE SCHEMA IF NOT EXISTS test_bsr_schema")
        self.env.cr.execute(
            "CREATE MATERIALIZED VIEW test_bsr_schema.test_bsr_mv AS SELECT 1 AS id"
        )
        self.addCleanup(
            lambda: self.env.cr.execute("DROP SCHEMA IF EXISTS test_bsr_schema CASCADE")
        )

    def test_relation_exists_is_schema_scoped(self):
        self.assertFalse(self.report._relation_exists("test_bsr_mv"))

    def test_relation_exists_finds_its_own(self):
        self.assertTrue(self.report._relation_exists(self.table))

    def test_relation_exists_is_kind_scoped(self):
        self.assertFalse(
            self.report._relation_exists("mixin_report_sql_test_source")  # a table
        )

    def test_is_populated_returns_bool_for_missing(self):
        result = self.report._is_populated("obviously_missing_relation_xyz")
        self.assertIs(type(result), bool)
        self.assertFalse(result)

    def test_relkind(self):
        self.assertEqual(self.report._relkind(self.table), "m")
        self.assertEqual(self.report._relkind("mixin_report_sql_test_source"), "r")
        self.assertIsNone(self.report._relkind("obviously_missing_relation_xyz"))

    def test_dependent_relations_listed(self):
        self.env.cr.execute(
            f"CREATE VIEW test_bsr_dep_child AS SELECT * FROM {self.table}"
        )
        self.addCleanup(
            lambda: self.env.cr.execute("DROP VIEW IF EXISTS test_bsr_dep_child")
        )
        names = {row[0] for row in self.report._dependent_relations(self.table)}
        self.assertIn("test_bsr_dep_child", names)


class TestIndexPlan(MaterializedCase):
    """``id`` is always indexed, whatever the unique key is."""

    def test_unique_index_is_on_the_declared_column(self):
        self.assertEqual(self.report._relation_index_field, "grain")
        self.assertIn(["grain"], self._indexes().values())

    def test_id_is_indexed_even_though_the_unique_key_is_not_id(self):
        """Every ORM read ends in WHERE id IN (...); without this it seq-scans."""
        self.assertIn(["id"], self._indexes().values())

    def test_index_names_say_what_they_index(self):
        indexes = self._indexes()
        self.assertIn(f"{self.table}__grain_uidx", indexes)
        self.assertIn(f"{self.table}__id_idx", indexes)

    def test_the_legacy_id_prefixed_name_is_retired(self):
        self.assertNotIn(f"id_{self.table}", self._indexes())

    def test_ensure_indexes_is_idempotent(self):
        before = self._indexes()
        self.report._relation_create_indexes()
        self.assertEqual(self._indexes(), before)

    def test_ensure_indexes_drops_a_legacy_index_left_by_an_older_version(self):
        self.env.cr.execute(
            SQL(
                "CREATE UNIQUE INDEX %s ON %s (grain)",
                SQL.identifier(f"id_{self.table}"),
                SQL.identifier(self.table),
            )
        )
        self.assertIn(f"id_{self.table}", self._indexes())
        self.report._relation_create_indexes()
        self.assertNotIn(f"id_{self.table}", self._indexes())
        self.assertIn(f"{self.table}__grain_uidx", self._indexes())

    def test_index_names_stay_within_the_identifier_limit(self):
        cls = type(self.report)
        with patch.object(cls, "_table", "z" * 70, create=True):
            name = self.report._relation_index_name("some_column_uidx")
        self.assertLessEqual(len(name.encode()), 63)
        with patch.object(cls, "_table", "z" * 70, create=True):
            self.assertEqual(name, self.report._relation_index_name("some_column_uidx"))

    def test_empty_index_field_raises(self):
        with self.assertRaises(ValueError):
            self.report._create_relation(index_field=[])

    def test_composite_index_field(self):
        self.report._create_relation(index_field=["grain", "id"])
        self.assertIn(["grain", "id"], self._indexes().values())
        # a composite unique index still satisfies REFRESH ... CONCURRENTLY
        self.assertTrue(self.report.refresh())


class TestRefresh(MaterializedCase):
    """``refresh()``: contents, self-healing, and transaction hygiene."""

    def test_refresh_picks_up_new_source_rows(self):
        self._seed("a", 1.0)
        self.assertTrue(self.report.refresh())
        self.assertEqual(self.report.search([("grain", "=", "a")]).total, 1.0)
        self._seed("a", 4.0)
        self.assertTrue(self.report.refresh())
        self.assertEqual(self.report.search([("grain", "=", "a")]).total, 5.0)

    def test_refresh_recreates_a_missing_relation(self):
        self._seed("a", 1.0)
        self.env.cr.execute(
            SQL("DROP MATERIALIZED VIEW %s", SQL.identifier(self.table))
        )
        self.assertIsNone(self.report._relkind(self.table))
        self.assertTrue(self.report.refresh())
        self.assertEqual(self.report._relkind(self.table), "m")
        self.assertEqual(self.report.search([("grain", "=", "a")]).total, 1.0)

    def test_refresh_rebuilds_when_a_bound_parameter_moved(self):
        """A materialized definition inlines its parameters as literals.

        `SQL("s.date <= %s", a_date)` freezes that date at CREATE time and
        REFRESH re-runs the frozen definition forever, so the check has to live
        where the cron can reach it.
        """
        cls = type(self.report)
        self.Source.create({"date": "2020-01-01", "grain": "old", "value": 1.0})
        self.Source.create({"date": "2020-01-02", "grain": "new", "value": 1.0})
        self.env.flush_all()

        def cutoff(day):
            return lambda self: [SQL("s.date <= %s", dt.date(2020, 1, day))]

        with patch.object(cls, "_get_where_conditions", cutoff(1)):
            self.report._create_relation()
            self.assertEqual(self.report.search([]).mapped("grain"), ["old"])

        with patch.object(cls, "_get_where_conditions", cutoff(2)):
            self.assertTrue(self.report._relation_definition_changed())
            self.assertTrue(self.report.refresh())
            self.assertEqual(
                sorted(self.report.search([]).mapped("grain")), ["new", "old"]
            )

    def test_refresh_leaves_an_unchanged_relation_in_place(self):
        self._seed("a", 1.0)
        self.report.refresh()
        oid = self._oid()
        self.assertTrue(self.report.refresh())
        self.assertEqual(self._oid(), oid, "an unchanged definition must not rebuild")

    def test_refresh_propagates_programming_errors(self):
        with patch.object(type(self.report), "_is_populated", side_effect=KeyError):
            with self.assertRaises(KeyError):
                self.report.refresh()

    def test_a_propagating_error_leaves_the_cursor_usable(self):
        """ir.cron writes its bookkeeping after the callback, on the same cursor.

        Without the SAVEPOINT that write dies in InFailedSqlTransaction and the
        failure is never recorded.
        """
        self.env.cr.execute(
            SQL("DROP INDEX %s", SQL.identifier(f"{self.table}__grain_uidx"))
        )
        self._seed("a", 1.0)
        self.env.cr.execute(
            SQL("REFRESH MATERIALIZED VIEW %s", SQL.identifier(self.table))
        )
        with self.assertRaises(psycopg.errors.ObjectNotInPrerequisiteState):
            self.report.refresh()
        self.env["ir.config_parameter"].sudo().set_param("mixin_report_sql.probe", "1")
        self.env.flush_all()

    def test_a_failing_rebuild_also_leaves_the_cursor_usable(self):
        """The rebuild branch is DDL and fails as readily as the refresh.

        Covering only the refresh would leave the same hole open on the path
        that self-heals a changed definition.
        """

        def broken(self):
            return [SQL("s.no_such_column = %s", 1)]

        with patch.object(type(self.report), "_get_where_conditions", broken):
            self.assertTrue(self.report._relation_definition_changed())
            with self.assertRaises(psycopg.errors.UndefinedColumn):
                self.report.refresh()
        self.env["ir.config_parameter"].sudo().set_param("mixin_report_sql.reb", "1")
        self.env.flush_all()

    def test_transient_errors_return_false_and_keep_the_cursor(self):
        self.env.cr.execute(
            SQL("DROP INDEX %s", SQL.identifier(f"{self.table}__grain_uidx"))
        )
        self._seed("a", 1.0)
        self.env.cr.execute(
            SQL("REFRESH MATERIALIZED VIEW %s", SQL.identifier(self.table))
        )
        with patch.object(
            mixin_materialized_view,
            "_TRANSIENT_REFRESH_ERRORS",
            (psycopg.errors.ObjectNotInPrerequisiteState,),
        ):
            self.assertFalse(self.report.refresh())
        self.env.cr.execute("SELECT 1")
        self.assertEqual(self.env.cr.fetchone()[0], 1)

    def test_cron_entry_point_is_still_named_for_the_stored_ir_cron_code(self):
        # agromarin/remote/data/ir_cron_data.xml is noupdate="1": the stored
        # ir.cron.code names this method and no upgrade rewrites it.
        self.assertTrue(self.report.refresh.__self__ is not None)
        self.assertTrue(self.report._cron_refresh_materialized_view())


class TestCreation(MaterializedCase):
    """``_create_relation``, its guards and its hooks."""

    def test_query_must_return_sql(self):
        with patch.object(type(self.report), "_query", lambda self: "SELECT 1"):
            with self.assertRaises(TypeError):
                self.report._create_relation()

    def test_a_model_that_sets_table_query_is_refused(self):
        """The ORM inlines _table_query and ignores _materialized.

        A model setting it gets a relation built, indexed and refreshed by this
        mixin that nothing ever reads. That used to be silent.
        """
        cls = type(self.report)
        with patch.object(cls, "_table_query", SQL("SELECT 1 AS id"), create=True):
            with self.assertRaises(UserError) as cm:
                self.report._create_relation()
        self.assertIn("_query()", str(cm.exception))

    def test_prepare_schema_hook_runs_on_every_init(self):
        """A schema object has its own lifetime; an edit to it moves no hash.

        Running the hook only before a CREATE would mean a changed function
        body never reached a deployment whose relation was already current.
        """
        calls = []
        with patch.object(
            type(self.report),
            "_relation_prepare_schema",
            lambda self: calls.append(1),
        ):
            self.report.init()  # definition unchanged: no rebuild
        self.assertEqual(len(calls), 1)

    def test_prepare_schema_hook_runs_before_the_create(self):
        """A model needing its own DDL uses this instead of overriding init()."""
        calls = []

        def prepare(self):
            self.env.cr.execute("SELECT 1")
            calls.append(self._relkind(self._table))

        with patch.object(type(self.report), "_relation_prepare_schema", prepare):
            self.report._create_relation()
        # the hook saw the *old* relation, i.e. it ran before the drop/create
        self.assertEqual(calls, ["m"])

    def test_refuses_a_relation_kind_it_does_not_own(self):
        cls = type(self.report)
        self.env.cr.execute("CREATE TABLE test_bsr_owned_table (id integer)")
        self.addCleanup(
            lambda: self.env.cr.execute("DROP TABLE IF EXISTS test_bsr_owned_table")
        )
        with patch.object(cls, "_table", "test_bsr_owned_table", create=True):
            with self.assertRaises(UserError) as cm:
                self.report._drop_existing_relation()
        self.assertIn("does not own", str(cm.exception))

    def test_with_no_data_creates_an_unpopulated_view(self):
        self.report._create_relation(with_data=False)
        self.assertFalse(self.report._is_populated(self.table))
        self.assertTrue(self.report._relation_needs_rebuild())
        # and refresh() populates it without a full rebuild
        oid = self._oid()
        self.assertTrue(self.report.refresh())
        self.assertTrue(self.report._is_populated(self.table))
        self.assertEqual(self._oid(), oid)

    def test_init_noop_on_the_abstract_mixin(self):
        mixin = self.env["mixin.materialized.view"]
        self.assertTrue(mixin._abstract)
        mixin.init()  # must not raise


@tagged("post_install", "-at_install")
class TestRebuildSkipAndDeferral(MaterializedCase):
    """``init()`` rebuild policy: hash-based skip and end-of-load deferral.

    post_install because ``init()`` branches on ``registry.loaded``: at_install
    runs inside module loading, where it is still False and every call takes the
    deferral branch. Testing the ready path at_install measures the deferral.
    """

    def test_init_skips_rebuild_when_definition_unchanged(self):
        self.report.init()
        oid = self._oid()
        self.assertIsNotNone(oid)
        self.report.init()
        self.assertEqual(self._oid(), oid)

    def test_init_rebuilds_when_the_query_changes(self):
        oid = self._oid()
        with patch.object(
            type(self.report),
            "_get_where_conditions",
            lambda self: ["s.value > 0"],
        ):
            self.report.init()
            self.assertNotEqual(self._oid(), oid)

    def test_a_relation_without_a_hash_is_rebuilt(self):
        self.env.cr.execute(
            SQL("COMMENT ON MATERIALIZED VIEW %s IS NULL", SQL.identifier(self.table))
        )
        self.assertTrue(self.report._relation_definition_changed())
        oid = self._oid()
        self.report.init()
        self.assertNotEqual(self._oid(), oid)
        # the rebuilt relation is stamped, so a second init() now skips
        oid = self._oid()
        self.report.init()
        self.assertEqual(self._oid(), oid)

    def test_init_defers_to_register_hook_while_loading(self):
        registry = self.env.registry
        oid = self._oid()
        changed = patch.object(
            type(self.report), "_get_where_conditions", lambda self: ["s.value > 0"]
        )
        with (
            registry.loading_window() as phase,
            patch.object(registry, "ready", False),
        ):
            pending = phase.state(mixin_materialized_view._PENDING_REBUILDS, dict)
            with changed, patch.object(registry, "loaded", False):
                self.report.init()
                self.assertEqual(self._oid(), oid, "nothing rebuilt during load")
                self.assertIn(self.report._name, pending)
            with changed:
                self.report._register_hook()
                self.assertNotEqual(self._oid(), oid)
                self.assertNotIn(self.report._name, pending)
                # the hook is idempotent once consumed
                oid = self._oid()
                self.report._register_hook()
                self.assertEqual(self._oid(), oid)

    def test_a_ready_registry_setup_runs_the_hook_outside_any_load(self):
        registry = self.env.registry
        self.assertTrue(registry.ready)
        oid = self._oid()
        registry.setup_models(self.env.cr)
        self.assertEqual(self._oid(), oid)

    def test_init_reconciles_indexes_without_rebuilding(self):
        """An index plan that changed between versions must still land."""
        self.env.cr.execute(
            SQL("DROP INDEX %s", SQL.identifier(f"{self.table}__id_idx"))
        )
        self.assertNotIn(f"{self.table}__id_idx", self._indexes())
        oid = self._oid()
        self.report.init()
        self.assertEqual(self._oid(), oid, "reconciling indexes must not rebuild")
        self.assertIn(f"{self.table}__id_idx", self._indexes())


class TestQueryResolution(MaterializedCase):
    """``_query()`` resolves through the mixins in either ``_inherit`` order."""

    def test_composed_model_resolves_to_the_registry_builder(self):
        self.assertIsInstance(self.report._query(), SQL)
        self.assertIn("mixin_report_sql_test_source", self.report._query().code)

    def test_standalone_mixin_raises_a_directive_error(self):
        mixin = self.env["mixin.materialized.view"]
        with self.assertRaises(NotImplementedError) as cm:
            mixin._query()
        self.assertIn("mixin.sql.report", str(cm.exception))
        self.assertIn("_query()", str(cm.exception))
