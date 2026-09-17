import hashlib
import logging

import psycopg

from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.sql import SQL

_PENDING_REBUILDS = "mixin_report_sql.pending_materialized_view_rebuilds"

_logger = logging.getLogger(__name__)

# Marker prefix for the definition hash stored as the COMMENT of every
# relation managed by this mixin (see _relation_definition_hash).
_MV_COMMENT_PREFIX = "odoo-mv:v1:"

_RELKIND_LABELS = {"v": "view", "m": "materialized view", "r": "table"}

# PostgreSQL truncates identifiers at NAMEDATALEN-1. Two generated index names
# sharing a 63-byte prefix would collide silently under CREATE ... IF NOT
# EXISTS, so _relation_index_name folds the overflow into a digest instead.
_MAX_IDENTIFIER = 63


# Transient Postgres errors that are safe to surface as "retry on next cron".
# Anything else (programming errors, auth, corruption) must propagate so the
# cron's error log actually records it.
#
# All four are psycopg OperationalError subclasses, which means the cron's own
# `retrying()` wrapper would also roll back and retry them. The savepoint in
# refresh() is not for these: it is for the errors that DO propagate, so a
# programming error leaves the cursor usable and ir.cron can still write its
# bookkeeping instead of dying in InFailedSqlTransaction.
# QueryCanceled is what _refresh_statement_timeout raises on overrun.
_TRANSIENT_REFRESH_ERRORS = (
    psycopg.errors.SerializationFailure,
    psycopg.errors.LockNotAvailable,
    psycopg.errors.DeadlockDetected,
    psycopg.errors.QueryCanceled,
)


# Provides idempotent ``_create_relation()``, self-healing ``refresh()``, and a
# cron entry point.  Introspection queries are scoped to ``current_schema`` so
# multi-schema databases are handled correctly.
#
# Vocabulary: everything here is spelled ``_relation_*`` rather than ``_mv_*``
# because ``_relation_kind`` lets one implementation own both storage kinds --
# ``mixin.rolling.report`` sets it to ``'r'`` and gets a real table from these
# same methods.  ``_cron_refresh_materialized_view`` is the exception and keeps
# its name: it is referenced from ``ir.cron.code`` in a ``noupdate="1"`` data
# file, so renaming it would break already-installed crons with no upgrade path.
class MixinMaterializedView(models.AbstractModel):
    """Abstract mixin for models backed by a PostgreSQL relation this mixin owns."""

    _name = "mixin.materialized.view"
    _description = "Materialized View Mixin"

    # Composition marker for `_inherit = ["mixin.sql.report",
    # "mixin.materialized.view"]`.  Consumed by mixin.sql.report._table_query:
    # True makes the ORM read the physical relation at self._table (fast)
    # instead of re-inlining the analytical query as a subquery (slow).
    # _create_relation still populates it from _query().  Stand-alone (no
    # mixin.sql.report) requires overriding _query() -- and, because the ORM
    # consults _table_query and not this marker, must NOT set _table_query.
    _materialized = True

    # Column (or list of columns) for the UNIQUE index that REFRESH ...
    # CONCURRENTLY requires.  A concrete model normally overrides only this.
    _relation_index_field = "id"

    # pg_class.relkind this model owns at self._table.  'm' (materialized view)
    # here; mixin.rolling.report sets 'r' because a rolling window has to
    # DELETE and INSERT rows, which REFRESH MATERIALIZED VIEW cannot express.
    _relation_kind = "m"

    # Whether an empty relation is itself a reason to rebuild.  True here: an
    # unpopulated materialized view cannot be SELECTed at all.  A rolling
    # report sets False -- a table that is empty because the source is empty is
    # simply correct, and rebuilding to rediscover that is a scan for nothing.
    _relation_rebuild_when_empty = True

    # Upper bound on any single statement of a refresh, as a PostgreSQL
    # interval.  A refresh that overruns is cancelled and reported as
    # transient, so a degraded query costs one failed tick instead of a
    # connection held for hours: the GPS daily report ran 5h per tick once its
    # source moved behind postgres_fdw, and the hourly ticks queueing behind it
    # exhausted max_connections.  None disables the bound.
    _refresh_statement_timeout = "30min"

    # ------------------------------------------------------------------
    # QUERY ACCESSOR
    # ------------------------------------------------------------------

    def _query(self) -> SQL:
        """Return the defining ``SQL`` for this relation.

        Cooperative: resolves to ``mixin.sql.report._query`` whenever that mixin
        is composed in, in either ``_inherit`` order.  A stand-alone subclass
        overrides this method.

        It deliberately does NOT fall back to ``_table_query``.  Setting that
        attribute makes the ORM inline the query as a subquery, so the relation
        this mixin builds and refreshes would never be read — see the guard in
        ``_create_relation``.
        """
        inherited = getattr(super(), "_query", None)
        if inherited is not None:
            return inherited()
        raise NotImplementedError(
            f"{self._name}: inherit 'mixin.sql.report' for the registry pattern, "
            "or override _query() to return a non-empty SQL object."
        )

    # ------------------------------------------------------------------
    # POSTGRES INTROSPECTION (schema-scoped)
    # ------------------------------------------------------------------

    def _relation_exists(self, table) -> bool:
        """True if a relation of kind ``self._relation_kind`` named ``table`` exists here."""
        self.env.cr.execute(
            SQL(
                "SELECT 1 FROM pg_class "
                "WHERE relname = %s "
                "AND relkind = %s "
                "AND relnamespace = current_schema::regnamespace",
                table,
                self._relation_kind,
            )
        )
        return bool(self.env.cr.fetchone())

    def _is_populated(self, table) -> bool:
        """True if the materialized view ``table`` has been populated with data."""
        self.env.cr.execute(
            SQL(
                "SELECT relispopulated FROM pg_class "
                "WHERE relname = %s "
                "AND relkind = 'm' "
                "AND relnamespace = current_schema::regnamespace",
                table,
            )
        )
        row = self.env.cr.fetchone()
        return bool(row and row[0])

    def _relkind(self, table):
        """Return ``pg_class.relkind`` for ``table`` in the current schema, or None."""
        self.env.cr.execute(
            SQL(
                "SELECT relkind FROM pg_class "
                "WHERE relname = %s "
                "AND relnamespace = current_schema::regnamespace",
                table,
            )
        )
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def _dependent_relations(self, table) -> list:
        """List views / matviews that depend on ``table`` (would be dropped by CASCADE)."""
        self.env.cr.execute(
            SQL(
                """
            SELECT DISTINCT c2.relname, c2.relkind
            FROM pg_depend d
            JOIN pg_class c1 ON d.refobjid = c1.oid
            JOIN pg_rewrite r ON d.objid = r.oid
            JOIN pg_class c2 ON r.ev_class = c2.oid
            WHERE c1.relname = %s
              AND c1.relnamespace = current_schema::regnamespace
              AND c2.relname != c1.relname
            """,
                table,
            )
        )
        return list(self.env.cr.fetchall())

    # ------------------------------------------------------------------
    # REFRESH
    # ------------------------------------------------------------------

    def refresh(self, force_rebuild=False) -> bool:
        """Bring the relation's contents up to date, rebuilding it if it must.

        Self-healing: a missing relation, a relation of the wrong kind, or one
        whose stored definition no longer matches ``_query()`` is rebuilt here
        rather than reported and left broken.  That matters because the
        definition of a materialized view is frozen at CREATE — a parameter
        bound into ``_get_where_conditions`` becomes a literal, and only a
        rebuild can move it.  The cron is the only thing that runs regularly,
        so the cron is where the check belongs.

        :param force_rebuild: rebuild from the source regardless of the hash.
        :return: True on success; False if a transient error occurred or another
            transaction is already refreshing this relation.  Errors that are
            not transient propagate so the cron's log records them — the
            SAVEPOINT is what keeps the cursor usable when they do.
        """
        # Skip, never queue. Every instance that runs crons ticks this refresh,
        # and a tick that waits behind a slow one holds a connection for as
        # long as the slow one runs; ninety of those is how the GPS report took
        # production down. The lock is transaction-scoped so a dead worker
        # releases it with its rollback.
        if not self._refresh_try_lock():
            _logger.warning(
                "Refresh of %s skipped: another transaction is refreshing it",
                self._table,
            )
            return False
        try:
            # Both branches inside the SAVEPOINT: a failed statement aborts the
            # whole transaction, so without this a propagating error would leave
            # the cursor in InFailedSqlTransaction and ir.cron's own bookkeeping
            # write (_resolve_attempt, then commit, in its `finally`) would fail
            # too -- losing the record of the failure along with the refresh.
            # The rebuild is DDL and can fail just as readily as the refresh, so
            # covering only the latter would leave the same hole open.
            # flush=False: the relation is defined over committed data, so
            # pending ORM writes are intentionally not flushed here; callers
            # needing them reflected must flush explicitly beforehand.
            with self.env.cr.savepoint(flush=False):
                if self._refresh_statement_timeout:
                    # set_config(..., true) is transaction-local, like SET LOCAL,
                    # but takes a bound value.
                    self.env.cr.execute(
                        SQL(
                            "SELECT set_config('statement_timeout', %s, true)",
                            self._refresh_statement_timeout,
                        )
                    )
                if force_rebuild or self._relation_definition_changed():
                    self._create_relation()
                else:
                    self._refresh_contents()
        except _TRANSIENT_REFRESH_ERRORS as exc:
            _logger.warning(
                "Transient refresh failure on %s: %s. Cron will retry.",
                self._table,
                exc,
            )
            return False
        # Every row was just replaced behind the ORM. Anything this transaction
        # had already read stays in cache otherwise, reading as current.
        self.invalidate_model()
        return True

    def _refresh_try_lock(self) -> bool:
        """Take the transaction-scoped advisory lock for this relation.

        :return: False when another transaction already holds it.
        """
        self.env.cr.execute(
            SQL("SELECT pg_try_advisory_xact_lock(hashtext(%s))", self._table)
        )
        return bool(self.env.cr.fetchone()[0])

    def _refresh_contents(self) -> None:
        """Replace the relation's rows in place.  Runs inside ``refresh``'s savepoint."""
        table_name = SQL.identifier(self._table)
        # First refresh must be blocking: PostgreSQL rejects REFRESH ...
        # CONCURRENTLY on an unpopulated MV with ObjectNotInPrerequisiteState.
        if self._is_populated(self._table):
            _logger.info("Refreshing %s (CONCURRENTLY)", self._table)
            self.env.cr.execute(
                SQL("REFRESH MATERIALIZED VIEW CONCURRENTLY %s", table_name),
            )
        else:
            _logger.info("Refreshing %s (blocking, first refresh)", self._table)
            self.env.cr.execute(SQL("REFRESH MATERIALIZED VIEW %s", table_name))

    def _cron_refresh_materialized_view(self) -> bool:
        """Cron entry point.

        Referenced by name from ``ir.cron.code`` in ``noupdate="1"`` data, so
        the name is a stored contract — rename it and installed crons break
        with no upgrade path.
        """
        return self.refresh()

    # ------------------------------------------------------------------
    # CREATION
    # ------------------------------------------------------------------

    def init(self):
        """Default schema hook: (re)create the relation on install / upgrade.

        Reads ``with_data`` from context (default True) and uses
        ``_relation_index_field`` for the unique index.  A concrete model
        normally sets only that attribute, and puts any DDL of its own in
        ``_relation_prepare_schema()`` — overriding ``init()`` forfeits the
        hash-skip and the end-of-load deferral below.
        """
        # registry.init_models calls init() on every model, including this
        # abstract mixin, which has no table.
        if self._abstract:
            return
        # Unconditionally, before any early return: a schema object this report
        # depends on has its own lifetime, and an edit to it does not move the
        # relation's definition hash. Running it only before a CREATE would mean
        # a changed function body never reached a deployment whose relation was
        # already up to date. It is idempotent, so _create_relation runs it
        # again on the paths that do not come through here (refresh's self-heal).
        self._relation_prepare_schema()
        with_data = self.env.context.get("with_data", True)
        # Relation missing: create immediately — data loading and at_install
        # tests may SELECT it before the end-of-load hook runs.
        if not self._relation_exists(self._table):
            self._create_relation(with_data=with_data)
            return
        # Registry still loading: defer to _register_hook (end of load), where
        # the final model definition builds the query exactly once.  init() runs
        # once per upgraded module in the closure, so on `-u base` it fires many
        # times per load, each a full CREATE ... WITH DATA (minutes on prod).
        if not self.pool.loaded:
            self.pool.loading.state(_PENDING_REBUILDS, dict)[self._name] = with_data
            return
        # Ready registry (e.g. reload_schema on a running server).
        self._sync_existing_relation(with_data)

    def _register_hook(self) -> None:
        """Process a rebuild deferred by ``init()`` during module loading.

        Called once per registry load after all modules are in, and again on
        every incremental setup of a ready registry. The deferred rebuilds live
        in the loading phase, which closes before the registry becomes ready,
        so a ready registry has nothing pending and no phase to ask.
        """
        super()._register_hook()
        if self._abstract or self.pool.ready:
            return
        pending = self.pool.loading.state(_PENDING_REBUILDS, dict)
        if self._name not in pending:
            return
        self._sync_existing_relation(pending.pop(self._name))

    def _sync_existing_relation(self, with_data=True) -> None:
        """Rebuild the existing relation if stale, else just reconcile its indexes.

        The index reconciliation is the reason this is not simply an ``if``:
        an index plan that changed between versions must land on deployments
        whose definition hash still matches, and ``CREATE INDEX IF NOT EXISTS``
        is cheap enough to run on every load.
        """
        if self._relation_needs_rebuild(with_data=with_data):
            self._create_relation(with_data=with_data)
        else:
            self._relation_create_indexes()

    def _relation_prepare_schema(self) -> None:
        """Hook for DDL this relation depends on — functions, types, extensions.

        Runs on every ``init()`` and again immediately before every CREATE, so
        it **must be idempotent** (``CREATE OR REPLACE``, ``IF NOT EXISTS``).
        Exists so a model needing such DDL does not have to override ``init()``
        and lose the definition-hash skip and the end-of-load deferral with it.
        """

    def _relation_index_cols(self, index_field=None) -> list:
        """Normalize ``_relation_index_field`` (or an explicit value) to a list."""
        if index_field is None:
            index_field = self._relation_index_field
        return [index_field] if isinstance(index_field, str) else list(index_field)

    def _relation_index_name(self, suffix) -> str:
        """Deterministic index name for ``self._table``, within PostgreSQL's limit."""
        name = f"{self._table}__{suffix}"
        if len(name.encode()) <= _MAX_IDENTIFIER:
            return name
        digest = hashlib.sha256(name.encode()).hexdigest()[:8]
        keep = _MAX_IDENTIFIER - len(digest) - 1
        return f"{name.encode()[:keep].decode(errors='ignore')}_{digest}"

    def _relation_extra_indexes(self) -> list:
        """Secondary indexes as ``(name_suffix, [columns])``.  None by default."""
        return []

    def _relation_definition_hash(self, query_sql: SQL, index_cols: list) -> str:
        """Return the marker comment identifying this relation's definition.

        Hashes the defining SQL (code *and* parameters) and the unique-index
        columns; stored as a relation COMMENT by ``_create_relation`` and
        compared by ``_relation_definition_changed``.  Parameters are in scope
        deliberately: a materialized view inlines them as literals, so a changed
        parameter is a changed relation even though the SQL text is identical.
        """
        payload = "\x00".join(
            (query_sql.code, repr(query_sql.params), ",".join(index_cols))
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return f"{_MV_COMMENT_PREFIX}{digest}"

    def _relation_stored_comment(self):
        """Return the comment stored on the relation, or None."""
        self.env.cr.execute(
            SQL(
                "SELECT obj_description(c.oid, 'pg_class') FROM pg_class c "
                "WHERE c.relname = %s AND c.relkind = %s "
                "AND c.relnamespace = current_schema::regnamespace",
                self._table,
                self._relation_kind,
            )
        )
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def _relation_definition_changed(self) -> bool:
        """Whether the relation on disk was built from a different definition.

        True for a missing relation, one of the wrong kind, one created before
        hashes were stamped, and one whose ``_query()`` — code or bound
        parameters — has moved since.
        """
        if self._relkind(self._table) != self._relation_kind:
            return True
        return self._relation_stored_comment() != self._relation_definition_hash(
            self._query(), self._relation_index_cols()
        )

    def _relation_needs_rebuild(self, with_data=True) -> bool:
        """``_relation_definition_changed``, plus emptiness where that matters."""
        if self._relation_definition_changed():
            return True
        if not (with_data and self._relation_rebuild_when_empty):
            return False
        return not self._is_populated(self._table)

    def _relation_create_sql(self, table_name, query_sql, with_data) -> SQL:
        """The CREATE statement for this relation kind."""
        if with_data:
            return SQL("CREATE MATERIALIZED VIEW %s AS %s", table_name, query_sql)
        return SQL(
            "CREATE MATERIALIZED VIEW %s AS %s WITH NO DATA", table_name, query_sql
        )

    def _relation_comment_sql(self, table_name, digest) -> SQL:
        """The COMMENT statement that stamps the definition hash.

        A literal per relation kind, like ``_drop_existing_relation``'s three
        branches and for the same reason: test_lint's SQL checker reads the
        first argument of ``SQL()`` and cannot see through
        ``SQL(label_for(kind))``.
        """
        return SQL("COMMENT ON MATERIALIZED VIEW %s IS %s", table_name, digest)

    def _create_relation(self, with_data=True, index_field=None):
        """(Re)create the relation and its indexes.

        :param with_data: If True (default), populate immediately.  PostgreSQL
            rejects SELECT on unpopulated materialized views with
            ``ObjectNotInPrerequisiteState``, which would make reports fail hard
            between install and the first cron refresh.  Pass ``False`` only for
            relations so large that install latency outweighs availability, and
            queue a refresh immediately after module install.
        :param index_field: Override for ``_relation_index_field`` — a column or
            a list of columns for the UNIQUE index that REFRESH ... CONCURRENTLY
            requires.  A composite key must be unique across the rows.
        :raises UserError: if ``self._table`` is taken by a relation kind this
            model does not own, or if the model also sets ``_table_query``.
        """
        self._check_orm_reads_this_relation()
        index_cols = self._relation_index_cols(index_field)
        if not index_cols:
            raise ValueError(
                f"{self._name}: index_field must name at least one column "
                "for the unique index REFRESH ... CONCURRENTLY requires."
            )

        query_sql = self._query()
        if not isinstance(query_sql, SQL) or not query_sql:
            raise TypeError(
                f"{self._name}._query() must return a non-empty SQL object, "
                f"got {type(query_sql).__name__}: {query_sql!r}",
            )

        self._relation_prepare_schema()
        self._drop_existing_relation()

        table_name = SQL.identifier(self._table)
        _logger.info(
            "Creating %s %s %s DATA",
            _RELKIND_LABELS.get(self._relation_kind, self._relation_kind),
            self._table,
            "WITH" if with_data else "WITH NO",
        )
        self.env.cr.execute(self._relation_create_sql(table_name, query_sql, with_data))
        if not with_data and self._relation_kind == "m":
            _logger.warning(
                "%s was created WITH NO DATA — SELECT on it raises "
                "ObjectNotInPrerequisiteState until the first refresh().",
                self._table,
            )

        self._relation_create_indexes(index_cols)

        # Stamp the definition hash so later init() calls can recognize an
        # up-to-date relation and skip the rebuild.
        self.env.cr.execute(
            self._relation_comment_sql(
                table_name, self._relation_definition_hash(query_sql, index_cols)
            )
        )

    def _check_orm_reads_this_relation(self) -> None:
        """Refuse to build a relation the ORM has been told to bypass.

        ``BaseModel._table_sql`` inlines ``_table_query`` as a subquery when it
        is truthy, ignoring ``_materialized`` — so a model that sets it gets a
        relation that is created, indexed and refreshed by this mixin and never
        read by anything.  That failed silently; it fails loudly now.
        """
        if not self._table_query:
            return
        raise UserError(
            _(
                "Model '%(model)s' sets _table_query, so the ORM inlines its "
                "query as a subquery and would never read the %(kind)s this "
                "mixin builds at '%(table)s'. Override _query() instead, or "
                "inherit 'mixin.sql.report'.",
                model=self._name,
                kind=_RELKIND_LABELS.get(self._relation_kind, self._relation_kind),
                table=self._table,
            )
        )

    def _relation_create_indexes(self, index_cols=None) -> None:
        """Create the unique index, an ``id`` index, and any extras — idempotently.

        The ``id`` index is not optional.  Every ORM read of a report ends in
        ``WHERE id IN (...)``, so a relation whose unique index is on some other
        column has no usable access path: measured on 400k rows, one 80-row page
        costs ~15 ms sequentially scanned against ~0.6 ms indexed.
        """
        if index_cols is None:
            index_cols = self._relation_index_cols()
        table_name = SQL.identifier(self._table)

        unique_name = self._relation_index_name("_".join(index_cols) + "_uidx")
        _logger.info(
            "Creating unique index %s on %s(%s)",
            unique_name,
            self._table,
            ", ".join(index_cols),
        )
        self.env.cr.execute(
            SQL(
                "CREATE UNIQUE INDEX IF NOT EXISTS %s ON %s (%s)",
                SQL.identifier(unique_name),
                table_name,
                SQL(", ").join(SQL.identifier(col) for col in index_cols),
            )
        )

        if index_cols[0] != "id":
            self.env.cr.execute(
                SQL(
                    "CREATE INDEX IF NOT EXISTS %s ON %s (%s)",
                    SQL.identifier(self._relation_index_name("id_idx")),
                    table_name,
                    SQL.identifier("id"),
                )
            )

        for suffix, columns in self._relation_extra_indexes():
            self.env.cr.execute(
                SQL(
                    "CREATE INDEX IF NOT EXISTS %s ON %s (%s)",
                    SQL.identifier(self._relation_index_name(suffix)),
                    table_name,
                    SQL(", ").join(SQL.identifier(col) for col in columns),
                )
            )

        # Older versions of this mixin named the unique index id_<table>
        # whatever its columns were. Dropped only after its replacement exists.
        legacy_name = f"id_{self._table}"
        if legacy_name != unique_name:
            self.env.cr.execute(
                SQL("DROP INDEX IF EXISTS %s", SQL.identifier(legacy_name))
            )

    def _drop_existing_relation(self):
        """Drop the relation currently sitting at ``self._table``, safely.

        Warns loudly when dependent objects would be CASCADE-dropped; refuses
        to proceed when the name is used by a relation kind this model does not
        own (data-loss risk).  A model whose ``_relation_kind`` *is* ``'r'``
        owns its table and may replace it -- that is how a rolling report
        rebuilds, and how one migrates from a materialized view to a table.
        """
        kind = self._relkind(self._table)
        if kind is None:
            return
        droppable = {"v", "m", self._relation_kind}
        if kind not in droppable:
            raise UserError(
                _(
                    "Cannot (re)create '%(table)s': the name is taken by a "
                    "relation of kind '%(kind)s', which this model does not own "
                    "(it owns '%(owned)s'). Drop or rename it manually before "
                    "upgrading the module.",
                    table=self._table,
                    kind=kind,
                    owned=self._relation_kind,
                )
            )

        dependents = self._dependent_relations(self._table)
        if dependents:
            _logger.warning(
                "Dropping %s %s will CASCADE %d dependent relation(s): %s",
                _RELKIND_LABELS.get(kind, kind),
                self._table,
                len(dependents),
                [f"{name} (kind={relkind})" for name, relkind in dependents],
            )

        _logger.info(
            "Dropping %s at %s (relkind %r) to recreate it as %r",
            _RELKIND_LABELS.get(kind, kind),
            self._table,
            kind,
            self._relation_kind,
        )
        table_name = SQL.identifier(self._table)
        # Literal statements per branch rather than a table of them: the SQL
        # checker reads the first argument of SQL() and cannot see through a
        # lookup, and three short branches are clearer than earning a waiver.
        if kind == "v":
            self.env.cr.execute(SQL("DROP VIEW IF EXISTS %s CASCADE", table_name))
        elif kind == "m":
            self.env.cr.execute(
                SQL("DROP MATERIALIZED VIEW IF EXISTS %s CASCADE", table_name),
            )
        else:
            self.env.cr.execute(SQL("DROP TABLE IF EXISTS %s CASCADE", table_name))
