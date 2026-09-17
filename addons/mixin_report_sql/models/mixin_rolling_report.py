import logging

from odoo import models
from odoo.libs.sql import SQL

_logger = logging.getLogger(__name__)


# ``mixin.materialized.view`` re-derives every row on every tick, because
# ``REFRESH MATERIALIZED VIEW`` has no partial form.  That is the right shape
# for a report over mutable source rows.  It is the wrong shape for a report
# whose grain is a closed period -- a day, a week -- where yesterday's answer
# is settled and only the newest period can still move.  Re-deriving the
# settled part is pure waste, and it grows without bound: the GPS daily report
# reached 69s and 2.7 GB of temp spill per hourly tick to produce the 95 rows
# that could change out of 7,404.
#
# So this stores the report in a real table (``_relation_kind = 'r'``) and
# refreshes a trailing window: ``DELETE`` the rows at or after a cutoff,
# ``INSERT`` them back from the source.  Everything older is left alone.
# Creation, drop, hashing, index maintenance and the savepoint around a refresh
# all come from the parent -- only the CREATE statement, the extra index and
# the contents of one refresh differ.
#
# Two things make that give the same answer as a full rebuild rather than
# merely a similar one, and both are mandatory:
#
# - A bounded scan is not a bounded window.  If the report uses window
#   functions (``LAG``, running totals) then the first source row inside the
#   scan has no predecessor and computes differently than it would in a full
#   pass.  ``_rolling_scope`` must therefore also re-admit each partition's
#   last row from *before* the cutoff.  Measured on the GPS report, omitting
#   those seed rows silently dropped one capped time-gap per device that had
#   been quiet across the window edge: an answer that looks plausible and is
#   wrong.
# - The cutoff must land on a grain boundary.  Deleting from the middle of a
#   period and re-inserting only the part of it the scan saw would truncate
#   that period.  ``_rolling_cutoff_sql`` returns a value of the grain column,
#   not "now minus N days".
#
# A subclass declares the grain (``_rolling_key_field``), the window length
# (``_rolling_window_days``) and the scope predicate, and consults
# ``_rolling_scope_sql()`` wherever it builds its FROM.  ``refresh()`` then
# does the window; ``refresh(full=True)`` rebuilds from scratch, which is what
# to call when something feeding the settled part changes.
#
# Why the scope travels in the context
# ------------------------------------
# ``_rolling_query`` sets ``rolling_scope`` on the environment and
# ``_rolling_scope_sql`` reads it back, so one registry serves both the full
# rebuild and the window refresh.  A parameter would say it better, but the
# value has to reach ``_get_from_tables`` / ``_with_cte`` several frames down
# in subclass code, and threading it through every registry hook would change
# their signatures for every report that never uses a window.  The key is read
# in exactly one place, and reads are unaffected by a stray one because
# ``_table_query`` returns ``None`` on a materialized model.
class MixinRollingReport(models.AbstractModel):
    """A report whose oldest rows never change, refreshed one window at a time."""

    _name = "mixin.rolling.report"
    # Only the MV mixin, though mixin.sql.report is a hard requirement too --
    # the window refresh names the report's columns on each side of its
    # INSERT ... SELECT and takes them from _get_fields_select().
    #
    # It cannot be declared here. Consumers write
    # `_inherit = ["mixin.sql.report", "mixin.rolling.report"]`, which asks for
    # mixin.sql.report BEFORE this model; a parent is always linearized AFTER
    # its child, so naming it as a parent makes both orders impossible at once
    # and the registry refuses the model outright:
    #
    #   TypeError: Cannot create a consistent method resolution order (MRO) for
    #   bases BaseModel, mixin.sql.report, mixin.rolling.report, base
    #
    # So the requirement is enforced instead of declared: _rolling_columns()
    # raises with instructions, and _create_relation calls it at install time
    # rather than letting it surface on the second cron tick -- the first finds
    # the table unpopulated and rebuilds in full, never reaching the column list.
    _inherit = ["mixin.materialized.view"]
    _description = "Rolling-Window Report Mixin"

    _relation_kind = "r"

    # An empty table because the source is empty is correct, not a defect: the
    # parent's reason for rebuilding on empty (an unpopulated materialized view
    # cannot be SELECTed at all) does not apply to a table.
    _relation_rebuild_when_empty = False

    #: Report column holding the closed-period grain.  Rows at or after the
    #: cutoff are rewritten; rows before it are never touched.
    _rolling_key_field = "date"

    #: How much of the tail to rewrite.  Must comfortably exceed both the
    #: refresh interval and the lateness of the source data -- devices that
    #: buffer while offline and replay later write rows into past periods.
    _rolling_window_days = 3

    # ------------------------------------------------------------------
    # WINDOW DEFINITION
    # ------------------------------------------------------------------

    def _rolling_cutoff_sql(self) -> SQL:
        """First grain value the window owns.

        Default ``current_date - _rolling_window_days``.  Override when the
        grain is bucketed in a specific timezone, which it usually is -- a
        report keyed on local day must cut on local midnight or it rewrites a
        partial period.
        """
        return SQL("(current_date - %s::int)", self._rolling_window_days)

    def _rolling_scope(self) -> SQL:
        """The SQL fragment that narrows the scan to the window.

        What it *is* is the subclass's choice, because only the subclass knows
        its own FROM: usually either a WHERE predicate or a replacement source
        relation.  Prefer the source relation when the source is large -- a
        predicate of the form ``timestamp >= cutoff OR id IN (seeds)`` cannot
        use an index and degrades into a sequential scan of the whole table,
        which on this fleet cost 9.9s against 1.9s for the equivalent
        per-partition range scan.

        Whichever form, it must cover the seed rows as well as the window.
        Over a postgres_fdw source, every predicate must also be one the FDW
        can ship -- constants and bound parameters, not a correlated subquery
        -- or the remote scan fetches the whole table and filters it here.
        """
        raise NotImplementedError(
            f"{self._name}: override _rolling_scope() to narrow the scan to "
            "the window, seed rows included."
        )

    def _rolling_scope_sql(self) -> SQL:
        """The active scope fragment, or ``SQL.EMPTY`` outside a window refresh.

        Subclasses call this where they build their FROM, so one registry
        serves both the full rebuild and the window refresh.
        """
        return self.env.context.get("rolling_scope") or SQL.EMPTY

    def _rolling_query(self) -> SQL:
        """The report query restricted to the window, seed rows included."""
        return self.with_context(rolling_scope=self._rolling_scope())._query()

    def _rolling_columns(self) -> list:
        """Report columns the window refresh writes, in order.

        Both sides of the ``INSERT ... SELECT`` name them explicitly, so the
        two lists cannot drift apart.  Taken from ``mixin.sql.report``'s
        registry, which this mixin requires but cannot declare — see the class
        comment for why, and ``_create_relation`` for where the requirement is
        checked.
        """
        registry_fields = getattr(self, "_get_fields_select", None)
        if registry_fields is None:
            raise NotImplementedError(
                f"{self._name}: a rolling report needs a column list for its "
                "INSERT ... SELECT. Inherit 'mixin.sql.report' (list it FIRST "
                "in _inherit) or override _rolling_columns()."
            )
        return list(registry_fields())

    def _create_relation(self, with_data=True, index_field=None):
        """Create the table, having first checked this report can refresh itself.

        The column list is only reached by a *window* refresh, so a
        mis-composed rolling report used to install cleanly, tick once against
        an empty table, and fail on the second tick. Asking for it here moves
        that to install time.
        """
        self._rolling_columns()
        return super()._create_relation(with_data=with_data, index_field=index_field)

    # ------------------------------------------------------------------
    # REFRESH
    # ------------------------------------------------------------------

    def refresh(self, full=False) -> bool:
        """Rewrite the trailing window, or every row when a full pass is needed.

        :param full: rebuild from the source.  Required after anything that
            changes already-settled periods.
        :return: True on success, False on a transient failure.
        """
        stale = self._rolling_pop_stale()
        if stale:
            _logger.info(
                "%s was marked stale — rebuilding every period, not just the window",
                self._table,
            )
        if not self._relation_exists(self._table):
            return super().refresh(force_rebuild=True)
        return super().refresh(
            force_rebuild=full or stale or not self._is_populated(self._table)
        )

    def _refresh_contents(self) -> None:
        """DELETE the window and re-INSERT it.  Inside the parent's savepoint."""
        table = SQL.identifier(self._table)
        key = SQL.identifier(self._rolling_key_field)
        cutoff = self._rolling_cutoff_sql()

        self.env.cr.execute(SQL("DELETE FROM %s WHERE %s >= %s", table, key, cutoff))
        deleted = self.env.cr.rowcount

        columns = SQL(", ").join(
            SQL.identifier(name) for name in self._rolling_columns()
        )
        self.env.cr.execute(
            SQL(
                "INSERT INTO %s (%s) SELECT %s FROM (%s) AS rolling WHERE %s >= %s",
                table,
                columns,
                columns,
                self._rolling_query(),
                key,
                cutoff,
            )
        )
        _logger.info(
            "Rolling refresh of %s: %d row(s) replaced by %d over the last %d day(s)",
            self._table,
            deleted,
            self.env.cr.rowcount,
            self._rolling_window_days,
        )

    # ------------------------------------------------------------------
    # STALENESS
    # ------------------------------------------------------------------

    def _rolling_stale_param(self) -> str:
        return f"{self._name}.rolling_full_rebuild"

    def _rolling_mark_stale(self) -> None:
        """Record that the settled part of the report no longer matches source.

        The window refresh never revisits closed periods, so anything that
        rewrites history -- a correction factor, an offset, a bulk import --
        has to say so.  Recorded as a flag rather than rebuilding inline
        because the caller is usually a user saving a form, and a rebuild is a
        full scan of the source.
        """
        self.env["ir.config_parameter"].sudo().set_param(
            self._rolling_stale_param(), "1"
        )
        _logger.info(
            "%s marked stale; the next refresh will rebuild in full", self._name
        )

    def _rolling_pop_stale(self) -> bool:
        """Consume the staleness flag, returning whether it was set."""
        parameters = self.env["ir.config_parameter"].sudo()
        if parameters.get_param(self._rolling_stale_param()) != "1":
            return False
        parameters.set_param(self._rolling_stale_param(), "0")
        return True

    # ------------------------------------------------------------------
    # CREATION
    # ------------------------------------------------------------------

    def _is_populated(self, table) -> bool:
        """True when the backing table holds at least one row.

        The parent reads ``pg_class.relispopulated``, which means something for
        a materialized view and is always true for a table.
        """
        self.env.cr.execute(
            SQL("SELECT EXISTS (SELECT 1 FROM %s)", SQL.identifier(table))
        )
        return bool(self.env.cr.fetchone()[0])

    def _relation_create_sql(self, table_name, query_sql, with_data) -> SQL:
        if with_data:
            return SQL("CREATE TABLE %s AS %s", table_name, query_sql)
        return SQL("CREATE TABLE %s AS %s WITH NO DATA", table_name, query_sql)

    def _relation_comment_sql(self, table_name, digest) -> SQL:
        return SQL("COMMENT ON TABLE %s IS %s", table_name, digest)

    def _relation_extra_indexes(self) -> list:
        # The window refresh deletes and re-inserts by the grain column on
        # every tick, which is a sequential scan of the whole report without
        # an index on it.
        return [
            *super()._relation_extra_indexes(),
            (f"{self._rolling_key_field}_idx", [self._rolling_key_field]),
        ]
